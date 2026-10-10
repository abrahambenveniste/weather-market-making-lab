# Kalshi data feasibility: market-level follow-up

**Observed:** 2026-10-11  
**Status:** unauthenticated series and open-market metadata requests succeeded. Standalone full order-book endpoint and continuous capture are still unverified.  
**Scope:** public read-only market metadata. No credentials or trading actions.

## Query

`GET https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXHIGHNY&status=open`

The response returned active daily contracts for the `KXHIGHNY-26OCT11` event, with market tickers, top-of-book prices and available size fields, rules, and event timestamps.

One returned market was `KXHIGHNY-26OCT11-B68.5`:

| Field | Observed value |
|---|---|
| Event / market | `KXHIGHNY-26OCT11` / `KXHIGHNY-26OCT11-B68.5` |
| Contract title | Will the maximum temperature be 68–69° on Oct 11, 2026? |
| Primary rule | NYC station CLINYC maximum temperature for Oct 11, 2026, 68–69°F according to The Weather Company |
| Secondary rule | Weather Company final value is official; preliminary values can differ due to rounding/conversion; material-error revisions may delay expiration |
| Open / close | 2026-10-10T14:00:00Z / 2026-10-12T05:00:00Z |
| YES bid / size | $0.01 / 150.43 |
| YES ask / size | $0.02 / 442.85 |
| NO bid / ask | $0.98 / $0.99 |
| NO bid / ask sizes | Not present in this market-list response |
| Reported volume / open interest | 717.96 / 716.96 contracts |

Prices and quantities are a single API observation, not a historical series and not a realized fill. The market-list response exposes top-of-book fields; it does not establish that we have full-depth snapshots or an event-by-event book history.

The endpoint used was the documented public [Get Markets API](https://docs.kalshi.com/api-reference/market/get-markets). The live response can be reproduced from [this query URL](https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXHIGHNY&status=open); the result will change as markets open, close, and settle.

## Settlement-rule discrepancy resolved for this contract

The [generic weather-market guide](https://help.kalshi.com/en/articles/13823837-weather-markets) says daily high/low markets settle from the final NWS Daily Climate Report. The current series response and this individual market's `rules_primary` / `rules_secondary` instead name The Weather Company. For this NYC contract, market-level rules specify the applicable source and take precedence for the research label.

This resolves the source question for the sampled contract only. It does not prove that every Kalshi daily weather series uses the same source. Store and inspect rules per ticker/date; do not hard-code one source across all markets.

## Data feasibility status

| Capability | Status | Evidence / remaining work |
|---|---|---|
| Public series metadata | **Observed working** | `GET /series/KXHIGHNY` returned series title, frequency, category, fee fields, and source metadata. |
| Public open-market listing | **Observed working** | `GET /markets?series_ticker=KXHIGHNY&status=open` returned current market rules, timestamps, top-of-book fields, and sizes. |
| Exact settlement source for sample | **Observed in market rules** | Sampled market rules name The Weather Company and station CLINYC. Cross-check final resolved value later. |
| Top-of-book prices/sizes | **Observed working** | Present in public market-list response for sampled markets. |
| Full-depth REST order book | **Documented, not yet independently queried** | Official [Get Market Orderbook API](https://docs.kalshi.com/api-reference/market/get-market-orderbook); next collector task should request it for the sample ticker. |
| Authenticated real-time order-book deltas | **Not attempted** | Official [WebSocket docs](https://docs.kalshi.com/websockets/orderbook-updates) require an API key. No keys are needed or used for this public-data probe. |
| Historical order-book replay | **Not established** | A current listing is not a historical L2 archive. We need to find a permitted historical source or begin timestamped capture going forward. |
| Historical forecast vintages | **Available in principle; market match pending** | Select a forecast model/grid/station and verify its archive coverage against this contract's settlement date and target. |
| Realized settlement history | **Not established** | Need a permitted, reproducible archive for final Weather Company values or resolved Kalshi outcomes with documented settlement source. |

## Implications

The project can begin with a live public-data capture and later event-driven paper replay, but backtesting historical market-making from this endpoint alone is not currently supported. The first collector should preserve both market-list observations and full-depth order-book snapshots if the latter endpoint is reachable. The key timestamps in the returned market object include market open/close/expiration fields; our collector must also timestamp its own request and response because polling time and exchange-provided timestamps are different things.

A strategy P&L claim needs fills and settlement outcomes. Do not infer a fill from displayed depth, multiply a current spread by a hypothetical fill rate, or treat volume as our executable liquidity. Until queue data or fill calibration exists, present fill assumptions as scenarios and report sensitivity.

## Next implementation slice

1. Build a read-only market-discovery command for `KXHIGHNY` using bounded HTTP requests.
2. Select one open ticker from the response and request its full-depth order book.
3. Normalize the raw market and book payloads into versioned JSONL records with local UTC and monotonic receive timestamps.
4. Run a short capture, then summarize request failures, response cadence, observed book levels, and data gaps.
5. Add a data dictionary and sample manifest; keep bulk raw data out of Git unless its size and terms have been checked.

The discovery command is the immediate coding milestone. Strategy and P&L work depends on proving that this market data can be captured and interpreted correctly first.
