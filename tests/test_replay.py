"""Tests for sparse-snapshot quote markout diagnostics."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from weather_mm.replay import ReplayInputError, load_snapshots, replay_markouts


LEVEL_COLUMNS = [
    "received_at_utc", "ticker", "contract_side", "book_side", "level_index",
    "price_dollars", "size_fp", "source_payload_sha256",
]


def _write_levels(path: Path, mids: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=LEVEL_COLUMNS)
        writer.writeheader()
        for index, mid in enumerate(mids):
            # Keep a one-cent spread around each requested midpoint.
            bid = str(float(mid) - 0.005)
            ask = str(float(mid) + 0.005)
            timestamp = f"2026-10-11T00:00:0{index}+00:00"
            for side, price in (("yes", bid), ("no", str(1 - float(ask)))):
                writer.writerow(
                    {
                        "received_at_utc": timestamp,
                        "ticker": "WX-TEST",
                        "contract_side": side,
                        "book_side": "bid",
                        "level_index": 0,
                        "price_dollars": price,
                        "size_fp": "10",
                        "source_payload_sha256": "test",
                    }
                )


class ReplayMarkoutTests(unittest.TestCase):
    def test_builds_yes_market_from_yes_and_no_bids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            levels_path = Path(temp_dir) / "levels.csv"
            _write_levels(levels_path, ["0.50"])
            snapshots = load_snapshots(levels_path)
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(str(snapshots[0].yes_bid), "0.495")
            self.assertEqual(str(snapshots[0].yes_ask), "0.505")
            self.assertEqual(str(snapshots[0].mid), "0.500")

    def test_calculates_hypothetical_markouts_without_claiming_fills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "levels.csv"
            output = root / "markouts.csv"
            _write_levels(source, ["0.50", "0.51", "0.49"])
            summary = replay_markouts(source, output, horizons=(1,))
            with output.open(encoding="utf-8", newline="") as result_file:
                rows = list(csv.DictReader(result_file))
            self.assertEqual(summary["input_snapshots"], 3)
            self.assertIn("no fills", summary["interpretation"])
            self.assertEqual(rows[0]["bid_markout_h1_dollars_per_contract"], "0.030")
            self.assertEqual(rows[0]["ask_markout_h1_dollars_per_contract"], "0.010")
            self.assertEqual(rows[-1].get("bid_markout_h1_dollars_per_contract"), "")

    def test_skips_incomplete_or_crossed_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "levels.csv"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=LEVEL_COLUMNS)
                writer.writeheader()
                for side, price in (("yes", "0.60"), ("no", "0.50")):
                    writer.writerow(
                        {
                            "received_at_utc": "2026-10-11T00:00:00+00:00",
                            "ticker": "CROSSED",
                            "contract_side": side,
                            "book_side": "bid",
                            "level_index": 0,
                            "price_dollars": price,
                            "size_fp": "1",
                            "source_payload_sha256": "test",
                        }
                    )
            self.assertEqual(load_snapshots(path), [])

    def test_rejects_invalid_horizons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "levels.csv"
            _write_levels(source, ["0.50"])
            with self.assertRaisesRegex(ValueError, "positive snapshot counts"):
                replay_markouts(source, Path(temp_dir) / "out.csv", horizons=(0,))


if __name__ == "__main__":
    unittest.main()
