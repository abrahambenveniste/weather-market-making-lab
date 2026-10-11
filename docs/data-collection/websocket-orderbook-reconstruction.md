# WebSocket order-book reconstruction

**Status:** the transport-independent snapshot/delta reducer is implemented and unit-tested. A live authenticated WebSocket collector has not been built or run.

## Why this step

REST snapshots show isolated book states and miss the intervening updates. Kalshi's order-book WebSocket sends an initial aggregated snapshot and then price-level deltas. Correctly reconstructing the local state, tracking sequence numbers, and refusing to quote from a stale book are prerequisites for any later execution simulation.

## Current implementation

`src/weather_mm/book.py` accepts decoded `orderbook_snapshot` and `orderbook_delta` messages. It:

- loads YES and NO bid levels from `yes_dollars_fp` and `no_dollars_fp`;
- adds each `delta_fp` to the indicated side and price, deleting a level when its size reaches zero;
- derives the YES ask as `1 - best NO bid` for binary contracts;
- checks ticker identity, price/size validity, subscription ID, and contiguous sequence numbers;
- invalidates the local book after a sequence gap or impossible negative size, requiring a fresh snapshot before updates resume;
- exposes the best levels, top sizes, sequence, and exchange-supplied send timestamp.

The reducer is transport-independent, which lets tests exercise state transitions without keys, network access, or a live market. It expects one market per subscription; routing multiple markets through a shared subscription needs a subscription-level sequence tracker before use.

## Venue interface and access gate

The current official [WebSocket quick start](https://docs.kalshi.com/getting_started/quick_start_websockets) documents a signed API-key handshake, subscription commands, reconnect guidance, and automatic WebSocket ping/pong. The [order-book update reference](https://docs.kalshi.com/websockets/orderbook-updates) specifies an initial snapshot followed by deltas and marks the channel as authenticated. The venue's [API-key guide](https://docs.kalshi.com/getting_started/api_keys) describes asymmetric signing keys.

Consequently, the public REST collector can keep running without credentials, but this project cannot yet capture the event feed until the user has eligible access and a suitable API key. Do not put API keys or private-key files in Git, fixtures, logs, or screenshots. Production trading eligibility is a separate question from whether a market-data API key can be issued; no VPN or other location workaround is part of this project.

## Sequence and recovery policy

The reducer accepts a snapshot as the new baseline. For a single-market subscription, each subsequent delta must have the same `sid` and `seq == previous_seq + 1`. A missing, duplicate, or out-of-order sequence invalidates local state. The caller must request/reconnect for a new snapshot before treating the book as current. This simple per-market rule will be checked against an actual authorized feed capture before we build reconnect automation.

## Not implemented yet

- network connection, request signing, subscription management, reconnect/backoff, disk capture, or heartbeats;
- a multi-market subscription router or durable event-log replay CLI;
- trade-side classification, queue position, fills, fees, latency calibration, or P&L.

When authorized feed access becomes available, the next collector should write one immutable JSONL envelope per received frame with local receive time, exchange `sending_ts_ms`, subscription ID, sequence, raw frame, and a canonical payload hash. Network receive timestamps and exchange timestamps must remain separate.

## Checks

`tests/test_book.py` covers snapshots, positive and negative deltas, level removal, top-of-book calculation, sequence gaps and recovery, negative-size protection, ticker mismatch, malformed prices, and irrelevant control messages. The messages are test fixtures, not captured venue data.
