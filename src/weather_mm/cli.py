"""Command-line interface for read-only public market-data capture."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from weather_mm.kalshi import KalshiPublicClient
from weather_mm.normalize import normalize_jsonl
from weather_mm.quotes import QuoteConfig, make_quotes
from weather_mm.replay import replay_markouts
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


async def _sample(args: argparse.Namespace) -> int:
    if not 1 <= args.count <= 1000:
        raise ValueError("count must be between 1 and 1000")
    if args.interval_seconds < 1:
        raise ValueError("interval-seconds must be at least 1")
    async with KalshiPublicClient() as client:
        for sample_number in range(1, args.count + 1):
            capture = await client.get_orderbook(ticker=args.ticker, depth=args.depth)
            append_records(args.output, [capture])
            print(
                f"Sample {sample_number}/{args.count}: HTTP {capture['http_status']}; "
                f"received {capture['received_at_utc']}; "
                f"payload SHA-256 {capture['payload_sha256']}"
            )
            if sample_number < args.count:
                await asyncio.sleep(args.interval_seconds)
    print(f"Appended {args.count} snapshot(s) to {args.output}")
    return 0


def _normalize(args: argparse.Namespace) -> int:
    counts = normalize_jsonl(args.input, args.markets_output, args.levels_output)
    print(f"Validated {counts['capture_records']} capture record(s)")
    print(f"Wrote {counts['market_rows']} market row(s) to {args.markets_output}")
    print(f"Wrote {counts['orderbook_levels']} order-book level(s) to {args.levels_output}")
    return 0


def _quote(args: argparse.Namespace) -> int:
    config = QuoteConfig(
        tick_size=args.tick_size,
        min_price=args.min_price,
        max_price=args.max_price,
        base_half_spread=args.base_half_spread,
        inventory_skew_per_contract=args.inventory_skew_per_contract,
        base_size=args.base_size,
        max_inventory=args.max_inventory,
    )
    quote = make_quotes(
        fair_value=args.fair_value,
        inventory=args.inventory,
        config=config,
        uncertainty_widening=args.uncertainty_widening,
        adverse_selection_widening=args.adverse_selection_widening,
    )
    print(
        json.dumps(
            {name: str(value) for name, value in quote.__dict__.items()},
            ensure_ascii=True,
        )
    )
    return 0


def _markout(args: argparse.Namespace) -> int:
    try:
        horizons = tuple(int(value.strip()) for value in args.horizons.split(","))
    except ValueError as exc:
        raise ValueError("horizons must be comma-separated positive integers") from exc
    config = QuoteConfig(base_half_spread=args.base_half_spread)
    summary = replay_markouts(
        args.input,
        args.output,
        horizons=horizons,
        config=config,
    )
    print(json.dumps(summary, indent=2))
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

    sample = commands.add_parser(
        "sample", help="collect a bounded series of public REST book snapshots"
    )
    sample.add_argument("--ticker", required=True)
    sample.add_argument("--count", type=int, default=20)
    sample.add_argument("--interval-seconds", type=float, default=30.0)
    sample.add_argument("--depth", type=int, default=0)
    sample.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    normalize = commands.add_parser(
        "normalize", help="validate raw capture hashes and write normalized CSV files"
    )
    normalize.add_argument("--input", type=Path, default=DEFAULT_OUTPUT)
    normalize.add_argument("--markets-output", type=Path, default=DEFAULT_MARKETS_OUTPUT)
    normalize.add_argument("--levels-output", type=Path, default=DEFAULT_LEVELS_OUTPUT)

    quote = commands.add_parser(
        "quote", help="calculate a deterministic inventory-aware YES quote"
    )
    quote.add_argument("--fair-value", type=Decimal, default=Decimal("0.50"))
    quote.add_argument("--inventory", type=Decimal, default=Decimal("0"))
    quote.add_argument("--tick-size", type=Decimal, default=Decimal("0.01"))
    quote.add_argument("--min-price", type=Decimal, default=Decimal("0.01"))
    quote.add_argument("--max-price", type=Decimal, default=Decimal("0.99"))
    quote.add_argument("--base-half-spread", type=Decimal, default=Decimal("0.02"))
    quote.add_argument(
        "--inventory-skew-per-contract", type=Decimal, default=Decimal("0.001")
    )
    quote.add_argument("--base-size", type=Decimal, default=Decimal("5"))
    quote.add_argument("--max-inventory", type=Decimal, default=Decimal("20"))
    quote.add_argument("--uncertainty-widening", type=Decimal, default=Decimal("0"))
    quote.add_argument(
        "--adverse-selection-widening", type=Decimal, default=Decimal("0")
    )

    markout = commands.add_parser(
        "markout",
        help="replay normalized snapshots and calculate hypothetical quote markouts",
    )
    markout.add_argument("--input", type=Path, default=Path("data/derived/orderbook-levels.csv"))
    markout.add_argument("--output", type=Path, default=Path("data/derived/snapshot-markouts.csv"))
    markout.add_argument("--horizons", default="1,3,5", help="future observations, e.g. 1,3,5")
    markout.add_argument("--base-half-spread", type=Decimal, default=Decimal("0.02"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.command == "normalize":
            exit_code = _normalize(args)
        elif args.command == "quote":
            exit_code = _quote(args)
        elif args.command == "markout":
            exit_code = _markout(args)
        else:
            handler = {
                "markets": _markets,
                "snapshot": _snapshot,
                "sample": _sample,
            }[args.command]
            exit_code = asyncio.run(handler(args))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)



