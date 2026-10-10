"""Read-only client for Kalshi's unauthenticated public market-data endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class KalshiPublicClient:
    """Small async client for public market metadata and order-book snapshots.

    This client deliberately has no authentication, order-entry, or account
    endpoints. It retries only idempotent GET requests after transient failures.
    """

    def __init__(self, *, timeout_seconds: float = 15.0, max_retries: int = 3) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "weather-market-making-lab/0.1"},
        )
        self.max_retries = max_retries

    async def __aenter__(self) -> "KalshiPublicClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started_at = utc_now()
            started_ns = time.monotonic_ns()
            try:
                response = await self._client.get(path, params=params)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else min(0.5 * (2**attempt), 8.0)
                        await asyncio.sleep(max(0.0, delay))
                        continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError(f"Expected a JSON object from {response.url}")
                received_ns = time.monotonic_ns()
                payload_bytes = json.dumps(
                    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8")
                return {
                    "record_type": "kalshi_public_rest",
                    "endpoint": str(response.url),
                    "request_started_at_utc": started_at,
                    "received_at_utc": utc_now(),
                    "request_duration_ns": received_ns - started_ns,
                    "http_status": response.status_code,
                    "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
                    "payload": payload,
                }
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(min(0.5 * (2**attempt), 8.0))
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError("GET request exhausted retries without a response")

    async def list_markets(
        self,
        *,
        series_ticker: str,
        status: str = "open",
        max_markets: int = 100,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch up to max_markets and return (page captures, market objects)."""
        if not series_ticker.strip():
            raise ValueError("series_ticker must not be empty")
        if max_markets < 1:
            raise ValueError("max_markets must be positive")
        if page_size < 1 or page_size > 200:
            raise ValueError("page_size must be between 1 and 200")

        captures: list[dict[str, Any]] = []
        markets: list[dict[str, Any]] = []
        cursor: str | None = None
        while len(markets) < max_markets:
            limit = min(page_size, max_markets - len(markets))
            params: dict[str, Any] = {
                "series_ticker": series_ticker,
                "status": status,
                "limit": limit,
            }
            if cursor:
                params["cursor"] = cursor
            capture = await self._get("/markets", params)
            captures.append(capture)
            page = capture["payload"].get("markets", [])
            if not isinstance(page, list):
                raise ValueError("Kalshi response field 'markets' was not a list")
            markets.extend(item for item in page if isinstance(item, dict))
            cursor = capture["payload"].get("cursor") or None
            if not cursor or not page:
                break
        return captures, markets

    async def get_orderbook(self, *, ticker: str, depth: int = 0) -> dict[str, Any]:
        """Fetch a public order-book snapshot for one market ticker."""
        if not ticker.strip():
            raise ValueError("ticker must not be empty")
        if depth < 0 or depth > 100:
            raise ValueError("depth must be between 0 and 100; zero requests all levels")
        return await self._get(
            f"/markets/{quote(ticker, safe='')}/orderbook",
            {"depth": depth},
        )

    async def get_market(self, *, ticker: str) -> dict[str, Any]:
        """Fetch public details and settlement rules for one market ticker."""
        if not ticker.strip():
            raise ValueError("ticker must not be empty")
        return await self._get(f"/markets/{quote(ticker, safe='')}", {})
