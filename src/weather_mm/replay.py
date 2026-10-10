"""Snapshot replay diagnostics; this module deliberately does not simulate fills."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from weather_mm.quotes import QuoteConfig, make_quotes


class ReplayInputError(ValueError):
    """Raised when normalized order-book rows cannot be replayed safely."""


@dataclass(frozen=True)
class Snapshot:
    ticker: str
    received_at_utc: str
    timestamp: datetime
    yes_bid: Decimal
    yes_ask: Decimal
    mid: Decimal


def _decimal(value: str, *, field: str, row_number: int) -> Decimal:
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ReplayInputError(f"row {row_number}: invalid {field} {value!r}") from exc
    if not number.is_finite():
        raise ReplayInputError(f"row {row_number}: {field} must be finite")
    return number


def _parse_timestamp(value: str, *, row_number: int) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReplayInputError(
            f"row {row_number}: invalid received_at_utc {value!r}"
        ) from exc
    if timestamp.tzinfo is None:
        raise ReplayInputError(f"row {row_number}: timestamp must include a timezone")
    return timestamp


def load_snapshots(path: str | Path) -> list[Snapshot]:
    """Build one top-of-book snapshot per ticker and receive timestamp."""
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    with Path(path).open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {"received_at_utc", "ticker", "contract_side", "book_side", "price_dollars"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ReplayInputError(
                "input must be normalized orderbook-levels.csv with columns "
                + ", ".join(sorted(required))
            )
        for row_number, row in enumerate(reader, start=2):
            ticker = (row.get("ticker") or "").strip()
            received = (row.get("received_at_utc") or "").strip()
            side = (row.get("contract_side") or "").strip().lower()
            book_side = (row.get("book_side") or "").strip().lower()
            if not ticker or not received:
                raise ReplayInputError(f"row {row_number}: ticker and timestamp are required")
            if side not in {"yes", "no"} or book_side != "bid":
                raise ReplayInputError(
                    f"row {row_number}: expected yes/no contract-side bid levels"
                )
            price = _decimal(row.get("price_dollars", ""), field="price_dollars", row_number=row_number)
            if not Decimal("0") <= price <= Decimal("1"):
                raise ReplayInputError(f"row {row_number}: price must be between 0 and 1")
            key = (ticker, received)
            bucket = grouped.setdefault(
                key,
                {"timestamp": _parse_timestamp(received, row_number=row_number), "yes": [], "no": []},
            )
            cast_levels = bucket[side]
            assert isinstance(cast_levels, list)
            cast_levels.append(price)

    snapshots: list[Snapshot] = []
    for (ticker, received), book in grouped.items():
        yes_levels = book["yes"]
        no_levels = book["no"]
        if not yes_levels or not no_levels:
            continue
        yes_bid = max(yes_levels)
        # In a binary contract, a NO bid at x is a YES offer at 1-x.
        yes_ask = Decimal("1") - max(no_levels)
        if yes_bid >= yes_ask:
            continue
        snapshots.append(
            Snapshot(
                ticker=ticker,
                received_at_utc=received,
                timestamp=book["timestamp"],  # type: ignore[arg-type]
                yes_bid=yes_bid,
                yes_ask=yes_ask,
                mid=(yes_bid + yes_ask) / Decimal("2"),
            )
        )
    return sorted(snapshots, key=lambda item: (item.ticker, item.timestamp))


def _validate_horizons(horizons: Iterable[int]) -> tuple[int, ...]:
    unique = tuple(sorted(set(horizons)))
    if not unique or any(isinstance(value, bool) or value < 1 for value in unique):
        raise ValueError("horizons must contain positive snapshot counts")
    return unique


def replay_markouts(
    input_path: str | Path,
    output_path: str | Path,
    *,
    horizons: Iterable[int] = (1, 3, 5),
    config: QuoteConfig = QuoteConfig(),
) -> dict[str, object]:
    """Quote around each observed midpoint and measure future midpoint markouts.

    A markout is conditional arithmetic: future mid minus hypothetical bid, or
    hypothetical ask minus future mid. It does not assert either quote filled.
    Horizons count subsequent observations for the same ticker, not wall-clock time.
    """
    steps = _validate_horizons(horizons)
    snapshots = load_snapshots(input_path)
    by_ticker: dict[str, list[Snapshot]] = {}
    for snapshot in snapshots:
        by_ticker.setdefault(snapshot.ticker, []).append(snapshot)

    columns = [
        "ticker", "received_at_utc", "yes_bid_dollars", "yes_ask_dollars", "mid_dollars",
        "quote_bid_dollars", "quote_ask_dollars", "quote_spread_dollars",
    ]
    for horizon in steps:
        columns.extend(
            [
                f"future_mid_h{horizon}_dollars",
                f"future_timestamp_h{horizon}_utc",
                f"bid_markout_h{horizon}_dollars_per_contract",
                f"ask_markout_h{horizon}_dollars_per_contract",
            ]
        )

    rows: list[dict[str, str]] = []
    for ticker, observations in by_ticker.items():
        for index, snapshot in enumerate(observations):
            quote = make_quotes(fair_value=snapshot.mid, inventory=Decimal("0"), config=config)
            row = {
                "ticker": ticker,
                "received_at_utc": snapshot.received_at_utc,
                "yes_bid_dollars": str(snapshot.yes_bid),
                "yes_ask_dollars": str(snapshot.yes_ask),
                "mid_dollars": str(snapshot.mid),
                "quote_bid_dollars": str(quote.bid_price),
                "quote_ask_dollars": str(quote.ask_price),
                "quote_spread_dollars": str(quote.ask_price - quote.bid_price),
            }
            for horizon in steps:
                future_index = index + horizon
                if future_index >= len(observations):
                    continue
                future = observations[future_index]
                row[f"future_mid_h{horizon}_dollars"] = str(future.mid)
                row[f"future_timestamp_h{horizon}_utc"] = future.received_at_utc
                row[f"bid_markout_h{horizon}_dollars_per_contract"] = str(
                    future.mid - quote.bid_price
                )
                row[f"ask_markout_h{horizon}_dollars_per_contract"] = str(
                    quote.ask_price - future.mid
                )
            rows.append(row)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, object] = {
        "input_snapshots": len(snapshots),
        "tickers": len(by_ticker),
        "output_rows": len(rows),
        "horizons_in_observations": list(steps),
        "output_path": str(destination),
        "interpretation": "hypothetical quote markouts; no fills, fees, queue, or P&L modeled",
        "markouts": {},
    }
    markout_summary: dict[str, dict[str, object]] = {}
    for horizon in steps:
        for side in ("bid", "ask"):
            field = f"{side}_markout_h{horizon}_dollars_per_contract"
            values = [Decimal(row[field]) for row in rows if row.get(field)]
            markout_summary[f"{side}_h{horizon}"] = {
                "observations": len(values),
                "mean_dollars_per_contract": (
                    str(sum(values) / len(values)) if values else None
                ),
            }
    summary["markouts"] = markout_summary
    return summary
