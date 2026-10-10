"""Tests for the deterministic inventory-aware quoting baseline."""

from __future__ import annotations

import unittest
from decimal import Decimal

from weather_mm.quotes import QuoteConfig, make_quotes


class QuoteTests(unittest.TestCase):
    def test_flat_inventory_quotes_symmetrically_around_fair_value(self) -> None:
        quote = make_quotes(fair_value="0.50", inventory="0")
        self.assertEqual(quote.bid_price, Decimal("0.48"))
        self.assertEqual(quote.ask_price, Decimal("0.52"))
        self.assertEqual(quote.bid_size, Decimal("5"))
        self.assertEqual(quote.ask_size, Decimal("5"))

    def test_long_inventory_skews_quotes_down_and_reduces_bid_size(self) -> None:
        quote = make_quotes(fair_value="0.50", inventory="10")
        self.assertEqual(quote.reservation_price, Decimal("0.490"))
        self.assertEqual(quote.bid_price, Decimal("0.47"))
        self.assertEqual(quote.ask_price, Decimal("0.51"))
        self.assertEqual(quote.bid_size, Decimal("2.50"))
        self.assertEqual(quote.ask_size, Decimal("7.50"))

    def test_short_inventory_skews_quotes_up(self) -> None:
        quote = make_quotes(fair_value="0.50", inventory="-10")
        self.assertEqual(quote.reservation_price, Decimal("0.510"))
        self.assertEqual(quote.bid_price, Decimal("0.49"))
        self.assertEqual(quote.ask_price, Decimal("0.53"))
        self.assertEqual(quote.bid_size, Decimal("7.50"))
        self.assertEqual(quote.ask_size, Decimal("2.50"))

    def test_uncertainty_and_adverse_selection_widen_both_sides(self) -> None:
        quote = make_quotes(
            fair_value="0.50",
            inventory="0",
            uncertainty_widening="0.01",
            adverse_selection_widening="0.005",
        )
        self.assertEqual(quote.half_spread, Decimal("0.035"))
        self.assertEqual(quote.bid_price, Decimal("0.46"))
        self.assertEqual(quote.ask_price, Decimal("0.54"))

    def test_inventory_limit_stops_adding_to_the_position(self) -> None:
        quote = make_quotes(fair_value="0.50", inventory="20")
        self.assertEqual(quote.bid_size, Decimal("0"))
        self.assertEqual(quote.ask_size, Decimal("10"))
        self.assertLess(quote.bid_price, quote.ask_price)

    def test_binary_float_inputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "avoid binary floats"):
            make_quotes(fair_value=0.5, inventory="0")

    def test_invalid_tick_grid_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "align to tick_size"):
            QuoteConfig(tick_size=Decimal("0.03"))


if __name__ == "__main__":
    unittest.main()

