# Public Kalshi collector: design and operating notes

**Status:** implementation added; local execution and endpoint behavior still need to be verified by the project owner.

## Scope

The first code milestone is intentionally read-only. It uses Kalshi's unauthenticated public REST endpoints documented for [market listing](https://docs.kalshi.com/api-reference/market/get-markets) and [order-book retrieval](https://docs.kalshi.com/api-reference/market/get-market-orderbook) to:

1. Paginate through a bounded set of markets for a series such as `KXHIGHNY`.
2. Request an order-book snapshot for a selected ticker.
3. Append each raw response to local JSON Lines storage with request/receive timestamps, HTTP status, response duration, and a SHA-256 hash of the normalized payload.

It does not use API credentials, submit/cancel orders, or write captures into Git. Raw data is ignored by `.gitignore`; the collector prints market summaries so a researcher can select a currently open ticker.

## Setup

From a clone of the repository, install [uv](https://docs.astral.sh/uv/) and run:

```shell
uv sync
uv run weather-mm markets --series-ticker KXHIGHNY --max-markets 100
```

Choose a ticker printed by the discovery command, then capture its current public book:

```shell
uv run weather-mm snapshot --ticker KXHIGHNY-REPLACE-WITH-A-CURRENT-TICKER --depth 0
```

Both commands append to `data/raw/kalshi-public.jsonl`. Use an active ticker returned by the first command; market tickers and availability change over time.

## Capture format

Each JSONL line is one HTTP response envelope. The full response payload is preserved as returned by the API. The order-book endpoint returns YES and NO bids; in a binary market, one side's bid corresponds to the opposite side's ask. The depth parameter accepts 0 through 100, where 0 requests all levels. The market-list page size is capped at 200. The envelope records:

- endpoint including query parameters;
- request start and receive timestamps in UTC;
- client-observed request duration from a monotonic clock;
- HTTP status;
- SHA-256 of a canonical JSON serialization of the payload.

The hash helps detect accidental changes to a payload during later handling. It does not prove when the capture occurred or authenticate the venue as its source. The client timestamp is a local observation time, not exchange event time. Payload fields and venue timestamps must be interpreted separately.

## Measurement limits

A REST snapshot is a point-in-time observation. It does not reveal queue position, order arrivals/cancellations between snapshots, or executable depth after network and processing delay. It is insufficient by itself to claim fill probability, realized market-making P&L, or HFT-grade latency. Those questions require timestamped updates or trades and an explicit replay model.

The collector retries only idempotent GET requests after network errors, rate limits, and server errors. Captures from a retry represent the response ultimately received; failed attempts are not written as observations. This is a research utility, not a production feed handler.

## Next evidence to collect

- Verify the current endpoint response schema against the official API docs and a local run.
- Save a small sample locally and inspect price/size units and field names.
- Compare top-of-book fields from market metadata with the order-book snapshot.
- Add a separate WebSocket capture path only after documenting subscription messages, snapshot/delta sequencing, reconnect behavior, and timestamp semantics.
