# Kalshi data feasibility: first read-only probe

**Observed:** 2026-10-11  
**Status:** public market enumeration, exact market-detail capture, order-book snapshots, and bounded REST sampling have been exercised. See the dated capture logs and [market settlement audit](market-settlement-audit-2026-10-11.md).
**Scope:** public-data feasibility only. No account credentials, trading requests, or order placement.

## Probe

A read-only GET to the public series endpoint returned JSON:

`GET https://external-api.kalshi.com/trade-api/v2/series/KXHIGHNY`

The observed response identified:

| Field | Observed value |
|---|---|
| Ticker | `KXHIGHNY` |
| Title | Highest temperature in NYC |
| Category | Climate and Weather |
| Frequency | daily |
| Fee type / multiplier | `quadratic` / `1` |
| Settlement source in series response | The Weather Company |
| Contract terms URL | GLOBALTEMPERATURE.pdf |
| Series metadata updated | 2026-10-01T20:50:16.961991Z |

This is a live metadata observation, not a historical data set. The response did not enumerate particular daily markets or establish their exact settlement interval.

## Finding: use market-specific rules

Kalshi's [general weather guide](https://help.kalshi.com/en/articles/13823837-weather-markets) describes NWS reports for some daily high/low markets. The live `KXHIGHNY` series response names The Weather Company. We fetched exact rules for `KXHIGHNY-26OCT11-B68.5`; its market-level rule explicitly says the New York City (`CLINYC`) maximum for October 11, 2026 is determined according to The Weather Company.

For this observed contract, market-level terms agree with the series-level source. The generic help article does not override the individual market rule. The market rule still leaves questions about a freely available historical The Weather Company feed, precise station mapping, and some time/rounding details; see the dated audit. Do not substitute another weather source and call it the exact target without validating the mapping.

### Required resolution before forecast modeling

For one specific open daily market, the public REST collector and market-detail command now capture:

1. Retrieve open market objects using the public [Get Markets endpoint](https://docs.kalshi.com/api-reference/market/get-markets).
2. Fetch the individual market using the public [Get Market endpoint](https://docs.kalshi.com/api-reference/market/get-market); save its ticker, rules, strike/range, close, expiry, and settlement fields as observed.
3. Establish a permitted historical source for final outcomes and verify at least one resolved market before defining labels.
4. Record any mismatch in a dated note and retain the raw local payload. Do not silently rewrite earlier findings.

## What the public API docs establish

Kalshi's [market-data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data) documents unauthenticated REST access to series, events, markets, and order-book snapshots. It gives `KXHIGHNY` as its example and explains that the public production API provides access to all market categories.

The public [market endpoint](https://docs.kalshi.com/api-reference/market/get-markets) describes market metadata and filtering/pagination. The [order-book endpoint](https://docs.kalshi.com/api-reference/market/get-market-orderbook) returns aggregated YES and NO bid depth. The real-time [order-book WebSocket](https://docs.kalshi.com/websockets/orderbook-updates) requires API-key authentication and emits a snapshot followed by deltas.

In the project environment, unauthenticated public requests successfully retrieved series metadata, open markets, the selected market's exact rule text, and order-book snapshots. A three-snapshot REST sample also completed. This verifies those request paths and observed response shapes for the recorded runs; it does **not** prove an uninterrupted feed, a complete historical order-book archive, or the availability of a permitted historical settlement feed.

## Implications for the collector

Keep the first collector read-only and small:

- Query series and open-market metadata; use a bounded request rate and pagination.
- Inspect the exact market rule fields before subscribing to or polling its book.
- Fetch a book snapshot for a chosen ticker and preserve the response as an append-only local record.
- Store request start/end UTC, local monotonic receive time, HTTP status, endpoint/ticker, and payload hash.
- Keep raw response and normalized schema separate so API changes can be diagnosed.
- Log rate limits, retries, missing fields, and gaps; do not conceal them through interpolation.
- Store sampled market metadata and documentation references in GitHub; keep larger raw time series out of Git unless size and terms have been reviewed.
- Do not claim L2 snapshots reconstruct a continuous event stream or exact queue position.

## Eligibility and operational boundary

Kalshi's [current Member Agreement](https://kalshi.com/docs/kalshi-member-agreement.pdf), Section VI, names France among restricted jurisdictions for event-contract trading. This probe accessed a public metadata URL and placed no orders. The research/paper track remains separate from live eligibility. No VPN-based trading workaround is part of the project.

## Remaining feasibility checkpoint

The first read-only endpoints work, so the next data decisions are:

- Find a permitted source for historical settled market outcomes and public trades.
- Determine if settlement labels are enough for a forecast model, or if licensed Weather Company data is needed.
- Compare forecast data coverage and issue-time semantics with the selected market's exact close and settlement date.
- Keep the sparse REST quote-markout diagnostic separate from any later fill and P&L simulator.

Do not estimate profitability until the outcome labels, quote/fill assumptions, fees, and timestamp coverage are defensible.
