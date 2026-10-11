"""Tests for the transport-independent Kalshi order-book reducer."""

from __future__ import annotations

import unittest
from decimal import Decimal

from weather_mm.book import OrderBookError, OrderBookReconstructor, SequenceGapError


def snapshot(*, seq: int = 10, yes: list[list[str]] | None = None, no: list[list[str]] | None = None) -> dict:
    return {
        "type": "orderbook_snapshot",
        "sid": 4,
        "seq": seq,
        "sending_ts_ms": 1_800_000_000_000,
        "msg": {
            "market_ticker": "KXHIGHNY-TEST",
            "yes_dollars_fp": yes if yes is not None else [["0.40", "8.00"], ["0.42", "5.00"]],
            "no_dollars_fp": no if no is not None else [["0.55", "7.00"], ["0.52", "4.00"]],
        },
    }


def delta(seq: int, *, side: str = "yes", price: str = "0.42", amount: str = "-2.00") -> dict:
    return {
        "type": "orderbook_delta",
        "sid": 4,
        "seq": seq,
        "sending_ts_ms": 1_800_000_000_100 + seq,
        "msg": {
            "market_ticker": "KXHIGHNY-TEST",
            "side": side,
            "price_dollars": price,
            "delta_fp": amount,
        },
    }


class OrderBookReconstructorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.book = OrderBookReconstructor("KXHIGHNY-TEST")

    def test_snapshot_and_delta_update_best_levels_and_sizes(self) -> None:
        initial = self.book.apply(snapshot())
        self.assertEqual(initial.yes_bid, Decimal("0.42"))
        self.assertEqual(initial.yes_ask, Decimal("0.45"))
        self.assertEqual(initial.yes_bid_size, Decimal("5.00"))
        self.assertEqual(initial.no_bid_size, Decimal("7.00"))

        updated = self.book.apply(delta(11))
        self.assertEqual(updated.yes_bid, Decimal("0.42"))
        self.assertEqual(updated.yes_bid_size, Decimal("3.00"))
        self.assertEqual(updated.sequence, 11)

    def test_zero_size_delta_removes_level_and_changes_best_bid(self) -> None:
        self.book.apply(snapshot())
        updated = self.book.apply(delta(11, amount="-5.00"))
        self.assertEqual(updated.yes_bid, Decimal("0.40"))

    def test_new_level_delta_adds_to_empty_price(self) -> None:
        self.book.apply(snapshot())
        updated = self.book.apply(delta(11, price="0.43", amount="2.00"))
        self.assertEqual(updated.yes_bid, Decimal("0.43"))
        self.assertEqual(updated.yes_bid_size, Decimal("2.00"))

    def test_sequence_gap_invalidates_book_until_new_snapshot(self) -> None:
        self.book.apply(snapshot())
        with self.assertRaisesRegex(SequenceGapError, "expected seq 11, received 12"):
            self.book.apply(delta(12))
        with self.assertRaisesRegex(OrderBookError, "before a valid snapshot"):
            self.book.apply(delta(13))
        self.book.apply(snapshot(seq=20))
        self.assertEqual(self.book.apply(delta(21)).sequence, 21)

    def test_delta_cannot_make_size_negative(self) -> None:
        self.book.apply(snapshot())
        with self.assertRaisesRegex(OrderBookError, "negative"):
            self.book.apply(delta(11, amount="-6.00"))
        self.assertFalse(self.book.synced)

    def test_rejects_wrong_ticker_and_bad_snapshot_without_mutating_state(self) -> None:
        wrong = snapshot()
        wrong["msg"]["market_ticker"] = "OTHER"
        with self.assertRaisesRegex(OrderBookError, "expected ticker"):
            self.book.apply(wrong)
        malformed = snapshot(yes=[["1.01", "1.00"]])
        with self.assertRaisesRegex(OrderBookError, "between 0 and 1"):
            self.book.apply(malformed)
        self.assertFalse(self.book.synced)

    def test_ignores_non_book_messages(self) -> None:
        self.assertIsNone(self.book.apply({"type": "subscribed", "sid": 4}))


if __name__ == "__main__":
    unittest.main()
