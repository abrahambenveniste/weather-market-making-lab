# Kalshi data feasibility: first read-only probe

**Observed:** 2026-10-11  
**Status:** one public series-metadata request succeeded; market enumeration and order-book capture have not yet been implemented or independently exercised in this project.  
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

## Finding: generic help and current series metadata differ

Kalshi's [general weather guide](https://help.kalshi.com/en/articles/13823837-weather-markets) says daily high/low temperature markets settle using the final NWS Daily Climate Report, while hourly temperature markets use The Weather Company. The live `KXHIGHNY` series response instead names The Weather Company as its settlement source even though the series frequency is daily.

This discrepancy is material. It may reflect differences between series-level and individual-market rules, a product/rule update, or general documentation that does not cover this series' current contract terms. We have not resolved which explanation applies. Do not select the weather target, station data, daily window, or settlement verification source based only on a generic help article or a series-level field.

### Required resolution before forecast modeling

For one specific open daily market:

1. Retrieve the market object using the public [Get Markets endpoint](https://docs.kalshi.com/api-reference/market/get-markets), filtered by `series_ticker=KXHIGHNY` and open status.
2. Save the ticker, title, `rules_primary`, `rules_secondary`, settlement source, strike/range, close time, and expiration/settlement fields as observed.
3. Open the market's linked contract terms and identify the authoritative weather station/source, units, rounding, time window, revisions, and settlement timing.
4. Cross-check at least one resolved market against the final source record before defining outcome labels.
5. Record any disagreement in a dated note and keep the original observed response. Do not silently rewrite earlier findings.

## What the public API docs establish

Kalshi's [market-data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data) documents unauthenticated REST access to series, events, markets, and order-book snapshots. It gives `KXHIGHNY` as its example and explains that the public production API provides access to all market categories.

The public [market endpoint](https://docs.kalshi.com/api-reference/market/get-markets) describes market metadata and filtering/pagination. The [order-book endpoint](https://docs.kalshi.com/api-reference/market/get-market-orderbook) returns aggregated YES and NO bid depth. The real-time [order-book WebSocket](https://docs.kalshi.com/websockets/orderbook-updates) requires API-key authentication and emits a snapshot followed by deltas.

In the project environment, the public series GET returned data without credentials. That confirms this one metadata route is reachable; it does **not** yet prove the market-list endpoint, order-book endpoint, polling rate, or any historical order-book archive is available from our collector. Those are the next checks.

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

## Next feasibility checkpoint

Before building quoting logic, run one reproducible collector session against a specific open market and answer:

- Can the market list and exact market rules be retrieved unauthenticated?
- Can a public order-book snapshot be retrieved for that ticker?
- What prices, sizes, levels, and timestamp fields are actually returned?
- How quickly do those fields change under a documented polling interval?
- Is there a permitted source for historical trades and final settlement values?
- Do the market-level settlement rules agree with the series response and the official weather record?

Only after these answers should we lock the event schema, choose a capture cadence, or estimate whether the available data can support a meaningful execution simulation.
