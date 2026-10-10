"""Tests for event-level aggregation of finalized weather outcomes."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from weather_mm.outcomes import OutcomeValidationError, aggregate_weather_outcomes


MARKET_COLUMNS = [
    "ticker", "event_ticker", "status", "result", "expiration_value",
]


def _write_markets(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=MARKET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


class AggregateWeatherOutcomesTests(unittest.TestCase):
    def test_groups_events_and_deduplicates_repeated_market_captures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "markets.csv"
            output = root / "outcomes.csv"
            _write_markets(
                source,
                [
                    {"ticker": "A", "event_ticker": "KXHIGHNY-26OCT09", "status": "finalized", "result": "yes", "expiration_value": "70.00"},
                    {"ticker": "B", "event_ticker": "KXHIGHNY-26OCT09", "status": "finalized", "result": "no", "expiration_value": "70.00"},
                    {"ticker": "A", "event_ticker": "KXHIGHNY-26OCT09", "status": "finalized", "result": "yes", "expiration_value": "70.00"},
                    {"ticker": "C", "event_ticker": "KXHIGHNY-26OCT10", "status": "active", "result": "", "expiration_value": ""},
                ],
            )
            summary = aggregate_weather_outcomes(source, output)
            with output.open(encoding="utf-8", newline="") as result_file:
                rows = list(csv.DictReader(result_file))
            self.assertEqual(summary["events"], 1)
            self.assertEqual(summary["duplicate_capture_rows"], 1)
            self.assertEqual(rows[0]["event_date"], "2026-10-09")
            self.assertEqual(rows[0]["expiration_value"], "70.00")
            self.assertEqual(rows[0]["market_count"], "2")
            self.assertEqual(rows[0]["yes_contracts"], "1")
            self.assertEqual(rows[0]["no_contracts"], "1")

    def test_rejects_conflicting_weather_value_within_an_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "markets.csv"
            _write_markets(
                source,
                [
                    {"ticker": "A", "event_ticker": "KXHIGHNY-26OCT09", "status": "finalized", "result": "yes", "expiration_value": "70.00"},
                    {"ticker": "B", "event_ticker": "KXHIGHNY-26OCT09", "status": "finalized", "result": "no", "expiration_value": "71.00"},
                ],
            )
            with self.assertRaisesRegex(OutcomeValidationError, "conflicting expiration_value"):
                aggregate_weather_outcomes(source, root / "outcomes.csv")

    def test_rejects_missing_result_or_expiration_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "markets.csv"
            _write_markets(
                source,
                [{"ticker": "A", "event_ticker": "KXHIGHNY-26OCT09", "status": "finalized", "result": "yes", "expiration_value": ""}],
            )
            with self.assertRaisesRegex(OutcomeValidationError, "needs ticker, result, and expiration_value"):
                aggregate_weather_outcomes(source, root / "outcomes.csv")


if __name__ == "__main__":
    unittest.main()
