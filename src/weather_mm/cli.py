"""Command-line interface for read-only public market-data capture."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from weather_mm.kalshi import KalshiPublicClient
from weather_mm.normalize import normalize_jsonl
from weather_mm.storage import append_records

DEFAULT_OUTPUT = Path("data/raw/kalshi-public.jsonl")
DEFAULT_MARKETS_OUTPUT = Path("data/derived/markets.csv")
DEFAULT_LEVELS_OUTPUT = Path("data/derived/orderbook-levels.csv")


def _market_summary(market: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "ticker",
        "event_ticker",
        "title",
        "subtitle",
        "status",
        "yes_bid_dollars",
        "yes_ask_dollars",
        "no_bid_dollars",
        "no_ask_dollars",
        "volume_fp",
        "open_interest_fp",
        "close_time",
        "expiration_time",
    )
    return {field: market[field] for field in fields if field in market}


async def _markets(args: argparse.Namespace) -> int:
    async with KalshiPublicClient() as client:
        captures, markets = await client.list_markets(
            series_ticker=args.series_ticker,
            status=args.status,
            max_markets=args.max_markets,
            page_size=args.page_size,
        )
    append_records(args.output, captures)
    print(f"Saved {len(captures)} page capture(s) to {args.output}")
    print(f"Discovered {len(markets)} market(s):")
    for market in markets:
        print(json.dumps(_market_summary(market), ensure_ascii=False))
    return 0


async def _snapshot(args: argparse.Namespace) -> int:
    async with KalshiPublicClient() as client:
        capture = await client.get_orderbook(ticker=args.ticker, depth=args.depth)
    append_records(args.output, [capture])
    print(f"Saved order-book snapshot for {args.ticker} to {args.output}")
    print(f"HTTP {capture['http_status']}; payload SHA-256 {capture['payload_sha256']}")
    return 0


def _normalize(args: argparse.Namespace) -> int:
    counts = normalize_jsonl(args.input, args.markets_output, args.levels_output)
    print(f"Validated {counts['capture_records']} capture record(s)")
    print(f"Wrote {counts['market_rows']} market row(s) to {args.markets_output}")
    print(f"Wrote {counts['orderbook_levels']} order-book level(s) to {args.levels_output}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather-mm",
        description="Capture public Kalshi weather-market data; this CLI cannot place orders.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    markets = commands.add_parser("markets", help="discover markets in a series")
    markets.add_argument("--series-ticker", default="KXHIGHNY")
    markets.add_argument("--status", default="open")
    markets.add_argument("--max-markets", type=int, default=100)
    markets.add_argument("--page-size", type=int, default=100)
    markets.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    snapshot = commands.add_parser("snapshot", help="capture one public order-book snapshot")
    snapshot.add_argument("--ticker", required=True)
    snapshot.add_argument("--depth", type=int, default=0)
    snapshot.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    normalize = commands.add_parser(
        "normalize", help="validate raw capture hashes and write normalized CSV files"
    )
    normalize.add_argument("--input", type=Path, default=DEFAULT_OUTPUT)
    normalize.add_argument("--markets-output", type=Path, default=DEFAULT_MARKETS_OUTPUT)
    normalize.add_argument("--levels-output", type=Path, default=DEFAULT_LEVELS_OUTPUT)
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.command == "normalize":
            exit_code = _normalize(args)
        else:
            exit_code = asyncio.run(
                _markets(args) if args.command == "markets" else _snapshot(args)
            )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)

