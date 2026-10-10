"""Aggregate finalized Kalshi weather contracts into event-level outcomes."""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


class OutcomeValidationError(ValueError):
    """Raised when finalized market rows do not form consistent event outcomes."""


def _event_date(event_ticker: str, *, row_number: int) -> str:
    date_token = event_ticker.rsplit("-", 1)[-1]
    try:
        return datetime.strptime(date_token, "%y%b%d").date().isoformat()
    except ValueError as exc:
        raise OutcomeValidationError(
            f"row {row_number}: cannot parse date from event ticker {event_ticker!r}"
        ) from exc


def aggregate_weather_outcomes(
    input_path: str | Path,
    output_path: str | Path,
    *,
    event_prefix: str = "KXHIGHNY-",
) -> dict[str, object]:
    """Write one row per finalized weather event after checking source consistency.

    `expiration_value` is preserved exactly as Kalshi returns it. The function does
    not rename it to degrees Fahrenheit because units/semantics must be verified
    from market rules before downstream modeling.
    """
    if not event_prefix.strip():
        raise ValueError("event_prefix must not be empty")
    source_rows = 0
    unique_markets: dict[str, dict[str, str]] = {}
    required = {"ticker", "event_ticker", "status", "result", "expiration_value"}
    with Path(input_path).open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise OutcomeValidationError(
                "input market CSV is missing required fields: " + ", ".join(sorted(required))
            )
        for row_number, row in enumerate(reader, start=2):
            event_ticker = (row.get("event_ticker") or "").strip()
            if not event_ticker.startswith(event_prefix):
                continue
            if (row.get("status") or "").lower() not in {"finalized", "settled"}:
                continue
            ticker = (row.get("ticker") or "").strip()
            result = (row.get("result") or "").strip().lower()
            value = (row.get("expiration_value") or "").strip()
            if not ticker or not result or not value:
                raise OutcomeValidationError(
                    f"row {row_number}: finalized market needs ticker, result, and expiration_value"
                )
            if result not in {"yes", "no", "void"}:
                raise OutcomeValidationError(f"row {row_number}: unsupported result {result!r}")
            try:
                numeric_value = Decimal(value)
            except InvalidOperation as exc:
                raise OutcomeValidationError(
                    f"row {row_number}: expiration_value must be a decimal"
                ) from exc
            if not numeric_value.is_finite():
                raise OutcomeValidationError(
                    f"row {row_number}: expiration_value must be finite"
                )
            _event_date(event_ticker, row_number=row_number)
            source_rows += 1
            record = {
                "event_ticker": event_ticker,
                "result": result,
                "expiration_value": format(numeric_value, "f"),
            }
            previous = unique_markets.get(ticker)
            if previous is not None and previous != record:
                raise OutcomeValidationError(
                    f"row {row_number}: duplicate market {ticker} has conflicting settlement fields"
                )
            unique_markets[ticker] = record

    events: dict[str, dict[str, object]] = {}
    for ticker, market in unique_markets.items():
        event_ticker = market["event_ticker"]
        assert isinstance(event_ticker, str)
        value = market["expiration_value"]
        result = market["result"]
        assert isinstance(value, str) and isinstance(result, str)
        event = events.setdefault(
            event_ticker,
            {
                "event_date": _event_date(event_ticker, row_number=0),
                "expiration_value": value,
                "market_tickers": [],
                "yes_contracts": 0,
                "no_contracts": 0,
                "void_contracts": 0,
            },
        )
        if event["expiration_value"] != value:
            raise OutcomeValidationError(
                f"event {event_ticker} has conflicting expiration_value values"
            )
        tickers = event["market_tickers"]
        assert isinstance(tickers, list)
        tickers.append(ticker)
        count_field = f"{result}_contracts"
        event[count_field] = int(event[count_field]) + 1

    columns = (
        "event_date",
        "event_ticker",
        "expiration_value",
        "market_count",
        "yes_contracts",
        "no_contracts",
        "void_contracts",
    )
    rows: list[dict[str, str | int]] = []
    for event_ticker, event in events.items():
        tickers = event["market_tickers"]
        assert isinstance(tickers, list)
        rows.append(
            {
                "event_date": str(event["event_date"]),
                "event_ticker": event_ticker,
                "expiration_value": str(event["expiration_value"]),
                "market_count": len(tickers),
                "yes_contracts": int(event["yes_contracts"]),
                "no_contracts": int(event["no_contracts"]),
                "void_contracts": int(event["void_contracts"]),
            }
        )
    rows.sort(key=lambda row: str(row["event_date"]))

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "source_rows": source_rows,
        "unique_markets": len(unique_markets),
        "duplicate_capture_rows": source_rows - len(unique_markets),
        "events": len(rows),
        "first_event_date": rows[0]["event_date"] if rows else None,
        "last_event_date": rows[-1]["event_date"] if rows else None,
        "output_path": str(destination),
        "expiration_value_units": "preserved from Kalshi; not assigned here",
    }
