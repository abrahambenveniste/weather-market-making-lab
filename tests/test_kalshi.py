"""Tests for the public Kalshi client routes."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from weather_mm.kalshi import KalshiPublicClient


class KalshiPublicClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_market_ticker_is_url_encoded_for_detail_route(self) -> None:
        client = KalshiPublicClient()
        try:
            client._get = AsyncMock(return_value={"http_status": 200})  # type: ignore[method-assign]
            result = await client.get_market(ticker="KX A/B")
            self.assertEqual(result, {"http_status": 200})
            client._get.assert_awaited_once_with("/markets/KX%20A%2FB", {})
        finally:
            await client._client.aclose()

    async def test_market_detail_route_rejects_empty_ticker(self) -> None:
        client = KalshiPublicClient()
        try:
            with self.assertRaisesRegex(ValueError, "ticker must not be empty"):
                await client.get_market(ticker=" ")
        finally:
            await client._client.aclose()


if __name__ == "__main__":
    unittest.main()
