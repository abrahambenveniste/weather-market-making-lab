"""Validate and normalize captured public Kalshi responses into CSV tables."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlparse

MARKET_COLUMNS = (
    "received_at_utc",
    "ticker",
    "event_ticker",
    "title",
    "status",
    "yes_bid_dollars",
    "yes_ask_dollars",
    "no_bid_dollars",
    "no_ask_dollars",
    "volume_fp",
    "open_interest_fp",
    "settlement_value_dollars",
    "result",
    "expiration_value",
    "close_time",
    "expiration_time",
    "source_payload_sha256",
)

LEVEL_COLUMNS = (
    "received_at_utc",
    "ticker",
    "contract_side",
    "book_side",
    "level_index",
    "price_dollars",
    "size_fp",
    "source_payload_sha256",
)


class CaptureValidationError(ValueError):
    """Raised when a capture cannot be trusted or normalized safely."""


def _canonical_payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _decimal(value: Any, *, context: str) -> Decimal:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise CaptureValidationError(f"{context}: expected a numeric value")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise CaptureValidationError(f"{context}: invalid decimal {value!r}") from exc
    if not number.is_finite():
        raise CaptureValidationError(f"{context}: value must be finite")
    return number


def _timestamp(record: dict[str, Any], *, context: str) -> str:
    value = record.get("received_at_utc")
    if not isinstance(value, str):
        raise CaptureValidationError(f"{context}: received_at_utc must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureValidationError(f"{context}: invalid received_at_utc {value!r}") from exc
    if parsed.tzinfo is None:
        raise CaptureValidationError(f"{context}: received_at_utc must include a timezone")
    return value


def _market_rows(
    markets: list[Any], timestamp: str, payload_hash: str, *, context: str
) -> Iterator[dict[str, Any]]:
    for market_index, market in enumerate(markets):
        market_context = f"{context}, market {market_index}"
        if not isinstance(market, dict):
            raise CaptureValidationError(f"{market_context}: expected an object")
        ticker = market.get("ticker")
        if not isinstance(ticker, str) or not ticker:
            raise CaptureValidationError(f"{market_context}: missing ticker")
        row: dict[str, Any] = {column: "" for column in MARKET_COLUMNS}
        row.update(
            {
                "received_at_utc": timestamp,
                "ticker": ticker,
                "source_payload_sha256": payload_hash,
            }
        )
        for column in MARKET_COLUMNS:
            if column in market and column not in {"received_at_utc", "source_payload_sha256"}:
                value = market[column]
                if value is not None:
                    row[column] = value
        for column in (
            "yes_bid_dollars",
            "yes_ask_dollars",
            "no_bid_dollars",
            "no_ask_dollars",
            "settlement_value_dollars",
        ):
            if row[column] != "":
                price = _decimal(row[column], context=f"{market_context} {column}")
                if price < 0 or price > 1:
                    raise CaptureValidationError(
                        f"{market_context} {column}: price must be between 0 and 1"
                    )
                row[column] = format(price, "f")
        if row["result"] != "" and str(row["result"]).lower() not in {"yes", "no", "void"}:
            raise CaptureValidationError(
                f"{market_context} result: expected yes, no, or void"
            )
        if row["expiration_value"] != "":
            value = _decimal(row["expiration_value"], context=f"{market_context} expiration_value")
            row["expiration_value"] = format(value, "f")
        yield row


def _ticker_from_endpoint(endpoint: Any, *, context: str) -> str:
    if not isinstance(endpoint, str):
        raise CaptureValidationError(f"{context}: endpoint must be a URL string")
    segments = urlparse(endpoint).path.strip("/").split("/")
    if len(segments) < 3 or segments[-1] != "orderbook" or segments[-3] != "markets":
        raise CaptureValidationError(f"{context}: cannot read market ticker from endpoint")
    ticker = unquote(segments[-2])
    if not ticker:
        raise CaptureValidationError(f"{context}: order-book endpoint has an empty ticker")
    return ticker


def _level_rows(
    orderbook: Any,
    ticker: str,
    timestamp: str,
    payload_hash: str,
    *,
    context: str,
) -> Iterator[dict[str, Any]]:
    if not isinstance(orderbook, dict):
        raise CaptureValidationError(f"{context}: orderbook_fp must be an object")
    for contract_side in ("yes", "no"):
        levels = orderbook.get(f"{contract_side}_dollars")
        if not isinstance(levels, list):
            raise CaptureValidationError(
                f"{context}: orderbook_fp.{contract_side}_dollars must be a list"
            )
        for level_index, level in enumerate(levels):
            level_context = f"{context}, {contract_side} level {level_index}"
            if not isinstance(level, list) or len(level) != 2:
                raise CaptureValidationError(f"{level_context}: expected [price, size]")
            price = _decimal(level[0], context=f"{level_context} price")
            size = _decimal(level[1], context=f"{level_context} size")
            if price < 0 or price > 1:
                raise CaptureValidationError(f"{level_context}: price must be between 0 and 1")
            if size <= 0:
                raise CaptureValidationError(f"{level_context}: size must be positive")
            yield {
                "received_at_utc": timestamp,
                "ticker": ticker,
                "contract_side": contract_side,
                "book_side": "bid",
                "level_index": level_index,
                "price_dollars": format(price, "f"),
                "size_fp": format(size, "f"),
                "source_payload_sha256": payload_hash,
            }


def _parse_capture(
    record: Any, *, line_number: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context = f"line {line_number}"
    if not isinstance(record, dict):
        raise CaptureValidationError(f"{context}: capture must be a JSON object")
    if record.get("record_type") != "kalshi_public_rest":
        raise CaptureValidationError(f"{context}: unsupported record_type")
    if record.get("http_status") != 200:
        raise CaptureValidationError(f"{context}: expected HTTP 200")
    timestamp = _timestamp(record, context=context)
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise CaptureValidationError(f"{context}: payload must be a JSON object")
    expected_hash = record.get("payload_sha256")
    actual_hash = _canonical_payload_hash(payload)
    if not isinstance(expected_hash, str) or expected_hash != actual_hash:
        raise CaptureValidationError(
            f"{context}: payload SHA-256 mismatch (expected {expected_hash!r}, got {actual_hash})"
        )

    markets: list[dict[str, Any]] = []
    levels: list[dict[str, Any]] = []
    if "markets" in payload:
        market_payload = payload["markets"]
        if not isinstance(market_payload, list):
            raise CaptureValidationError(f"{context}: payload.markets must be a list")
        markets.extend(_market_rows(market_payload, timestamp, actual_hash, context=context))
    if "market" in payload:
        market_payload = payload["market"]
        if not isinstance(market_payload, dict):
            raise CaptureValidationError(f"{context}: payload.market must be an object")
        markets.extend(_market_rows([market_payload], timestamp, actual_hash, context=context))
    if "orderbook_fp" in payload:
        ticker = _ticker_from_endpoint(record.get("endpoint"), context=context)
        levels.extend(
            _level_rows(
                payload["orderbook_fp"],
                ticker,
                timestamp,
                actual_hash,
                context=context,
            )
        )
    if not {"markets", "market", "orderbook_fp"}.intersection(payload):
        raise CaptureValidationError(f"{context}: payload contains no supported market data")
    return markets, levels


def normalize_jsonl(
    input_path: str | Path,
    markets_output: str | Path,
    levels_output: str | Path,
) -> dict[str, int]:
    """Validate captures and atomically replace normalized CSV outputs."""
    source = Path(input_path)
    markets_path = Path(markets_output)
    levels_path = Path(levels_output)
    paths = {path.resolve() for path in (source, markets_path, levels_path)}
    if len(paths) != 3:
        raise ValueError("input and the two output paths must be different files")

    markets_path.parent.mkdir(parents=True, exist_ok=True)
    levels_path.parent.mkdir(parents=True, exist_ok=True)
    markets_temp = markets_path.with_name(markets_path.name + ".tmp")
    levels_temp = levels_path.with_name(levels_path.name + ".tmp")
    capture_count = market_count = level_count = 0
    try:
        with (
            source.open("r", encoding="utf-8") as input_file,
            markets_temp.open("w", encoding="utf-8", newline="") as markets_file,
            levels_temp.open("w", encoding="utf-8", newline="") as levels_file,
        ):
            market_writer = csv.DictWriter(markets_file, fieldnames=MARKET_COLUMNS)
            level_writer = csv.DictWriter(levels_file, fieldnames=LEVEL_COLUMNS)
            market_writer.writeheader()
            level_writer.writeheader()
            for line_number, line in enumerate(input_file, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CaptureValidationError(
                        f"line {line_number}: invalid JSON ({exc.msg})"
                    ) from exc
                market_rows, level_rows = _parse_capture(record, line_number=line_number)
                market_writer.writerows(market_rows)
                level_writer.writerows(level_rows)
                capture_count += 1
                market_count += len(market_rows)
                level_count += len(level_rows)
        os.replace(markets_temp, markets_path)
        os.replace(levels_temp, levels_path)
    except Exception:
        markets_temp.unlink(missing_ok=True)
        levels_temp.unlink(missing_ok=True)
        raise
    return {
        "capture_records": capture_count,
        "market_rows": market_count,
        "orderbook_levels": level_count,
    }

