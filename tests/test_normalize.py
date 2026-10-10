"""Unit tests for capture validation and normalized output."""

from __future__ import annotations

import csv
import asyncio
import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import Any

from weather_mm.normalize import CaptureValidationError, normalize_jsonl
from weather_mm.cli import _sample


def _capture(payload: dict[str, Any], endpoint: str) -> dict[str, Any]:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return {
        "record_type": "kalshi_public_rest",
        "endpoint": endpoint,
        "request_started_at_utc": "2026-10-11T00:00:00+00:00",
        "received_at_utc": "2026-10-11T00:00:00.010000+00:00",
        "request_duration_ns": 10_000_000,
        "http_status": 200,
        "payload_sha256": hashlib.sha256(canonical).hexdigest(),
        "payload": payload,
    }


class NormalizeJsonlTests(unittest.TestCase):
    def test_normalizes_market_metadata_and_both_bid_sides(self) -> None:
        market_record = _capture(
            {
                "markets": [
                    {
                        "ticker": "KXHIGHNY-26OCT11-B68.5",
                        "event_ticker": "KXHIGHNY-26OCT11",
                        "title": "68 to 69 degrees",
                        "status": "active",
                        "yes_bid_dollars": "0.0100",
                        "yes_ask_dollars": "0.0200",
                        "volume_fp": "100.00",
                    }
                ],
                "cursor": "",
            },
            "https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXHIGHNY",
        )
        book_record = _capture(
            {
                "orderbook_fp": {
                    "yes_dollars": [["0.0100", "219.43"]],
                    "no_dollars": [["0.9800", "300.00"], ["0.9700", "100.00"]],
                }
            },
            "https://external-api.kalshi.com/trade-api/v2/markets/KXHIGHNY-26OCT11-B68.5/orderbook?depth=0",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "captures.jsonl"
            source.write_text(
                "\n".join(json.dumps(record) for record in (market_record, book_record)) + "\n",
                encoding="utf-8",
            )
            markets_path = root / "derived" / "markets.csv"
            levels_path = root / "derived" / "levels.csv"

            result = normalize_jsonl(source, markets_path, levels_path)

            self.assertEqual(result, {"capture_records": 2, "market_rows": 1, "orderbook_levels": 3})
            with markets_path.open(encoding="utf-8", newline="") as source_file:
                market_rows = list(csv.DictReader(source_file))
            with levels_path.open(encoding="utf-8", newline="") as source_file:
                level_rows = list(csv.DictReader(source_file))
            self.assertEqual(market_rows[0]["yes_bid_dollars"], "0.0100")
            self.assertEqual(level_rows[0]["ticker"], "KXHIGHNY-26OCT11-B68.5")
            self.assertEqual([row["contract_side"] for row in level_rows], ["yes", "no", "no"])
            self.assertEqual(level_rows[1]["size_fp"], "300.00")

    def test_rejects_payload_hash_mismatch_without_replacing_outputs(self) -> None:
        record = _capture({"markets": []}, "https://example.test/markets")
        record["payload"]["markets"].append({"ticker": "changed-after-hash"})

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "captures.jsonl"
            source.write_text(json.dumps(record) + "\n", encoding="utf-8")
            markets_path = root / "derived" / "markets.csv"
            levels_path = root / "derived" / "levels.csv"
            markets_path.parent.mkdir()
            markets_path.write_text("previous markets\n", encoding="utf-8")
            levels_path.write_text("previous levels\n", encoding="utf-8")

            with self.assertRaisesRegex(CaptureValidationError, "SHA-256 mismatch"):
                normalize_jsonl(source, markets_path, levels_path)

            self.assertEqual(markets_path.read_text(encoding="utf-8"), "previous markets\n")
            self.assertEqual(levels_path.read_text(encoding="utf-8"), "previous levels\n")

    def test_rejects_out_of_range_book_price(self) -> None:
        record = _capture(
            {"orderbook_fp": {"yes_dollars": [["1.01", "2"]], "no_dollars": []}},
            "https://external-api.kalshi.com/trade-api/v2/markets/TICKER/orderbook",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "captures.jsonl"
            source.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(CaptureValidationError, "between 0 and 1"):
                normalize_jsonl(source, root / "markets.csv", root / "levels.csv")

    def test_sampler_rejects_invalid_bounds_before_network_access(self) -> None:
        common = {"ticker": "TICKER", "depth": 0, "output": Path("unused.jsonl")}
        with self.assertRaisesRegex(ValueError, "count must be between"):
            asyncio.run(
                _sample(Namespace(**common, count=0, interval_seconds=30.0))
            )
        with self.assertRaisesRegex(ValueError, "interval-seconds must be at least"):
            asyncio.run(
                _sample(Namespace(**common, count=1, interval_seconds=0.0))
            )


if __name__ == "__main__":
    unittest.main()


