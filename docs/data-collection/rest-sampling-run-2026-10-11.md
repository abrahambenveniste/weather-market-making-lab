# First bounded REST sampling run

**Run date:** 2026-10-10 UTC (2026-10-11 in Europe/Paris)  
**Market:** `KXHIGHNY-26OCT11-B68.5`  
**Command:** `weather-mm sample --count 3 --interval-seconds 5 --depth 0`  
**Venue/API:** unauthenticated Kalshi public REST; no credentials or orders.

## Observations

All three requests returned HTTP 200 and were appended to the local raw JSONL file. Receive timestamps:

| Sample | Receive time (UTC) | Payload SHA-256 |
|---|---|---|
| 1 | 2026-10-10T23:37:38.578931Z | `111e5ff02f5f5037ef6aad283d3eec90fcffb425be9a8a69d43b51d21f7fdb69` |
| 2 | 2026-10-10T23:37:43.905130Z | `490338fb6a3777f07848a57d65c32e313e6a78cfdd10167ba25184f9ac9fb0db` |
| 3 | 2026-10-10T23:37:49.233277Z | `24079dba7972615b30aca1da4b5a252b519e61bf3c6c685866e4cdb483cd64fb` |

The response intervals were about 5.33 seconds. Each snapshot contained 1 YES bid level and 47 NO bid levels. The payloads were distinct. Re-normalizing all local captures accepted six response records and produced 13 market rows and 193 order-book level rows.

## Interpretation

This run confirms that the bounded sampler appends timestamped public snapshots and that the normalizer accepts them. Three observations over roughly eleven seconds are only a pipeline smoke run; they do not estimate queue position, fills, market impact, or strategy performance. REST polling also misses changes between requests. Kalshi's current order-book WebSocket requires API-key authentication and delivers a snapshot followed by deltas; see the [venue feed documentation](https://docs.kalshi.com/websockets/orderbook-updates). The current [rate-limit page](https://docs.kalshi.com/getting_started/rate_limits) describes token budgets for authenticated calls, and does not establish a public REST polling allowance.
