# Market settlement audit — 2026-10-11

## Scope

Before creating weather labels or fair probabilities, inspect the rules for one actual market rather than infer them from the series title or a generic help page. This was a read-only public API request; it did not use account authentication or place an order.

## Captured market

- Ticker: `KXHIGHNY-26OCT11-B68.5`
- Event: `KXHIGHNY-26OCT11`
- Title: “Will the maximum temperature be 68–69° on Oct 11, 2026?”
- Status at capture: `active`
- Market close: `2026-10-12T05:00:00Z`
- Expiration: `2026-10-18T14:00:00Z`
- `rules_primary`: “If the maximum temperature recorded at New York City (CLINYC) for Oct 11, 2026, is between 68-69° fahrenheit according to The Weather Company, then the market resolves to Yes.”
- `rules_secondary`: Kalshi says the final maximum/minimum reported by The Weather Company determines settlement; preliminary values may differ due to rounding/conversion, and an exchange-determined material error can delay expiration.
- `expiration_value`: not yet populated at the time of this active-market capture.
- Top of book at detail capture: YES bid/ask `$0.01` / `$0.02`; NO bid/ask `$0.98` / `$0.99`.
- HTTP status: `200`.
- Canonical response payload SHA-256: `b50977161053d76a0d32baaaf5d3683a4f22909f60404e236934b4ee72b595a7`.

The full raw response is retained locally in `data/raw/kalshi-public.jsonl` and is excluded from Git. The selected rule text, fields needed to understand the result, and payload hash are recorded here.

## Sources

- Kalshi [Get Market API endpoint](https://docs.kalshi.com/api-reference/market/get-market).
- Kalshi [Get Markets endpoint](https://docs.kalshi.com/api-reference/market/get-markets).
- Kalshi [weather markets overview](https://help.kalshi.com/en/articles/13823837-weather-markets) (general guidance; individual contract rules control for the selected market).

## Resolved market outcome probe

The public market-list endpoint also returned finalized markets when queried with `series_ticker=KXHIGHNY&status=settled&limit=3`:

| Ticker | Status | Result | Settlement value | Expiration value |
|---|---|---|---:|---:|
| `KXHIGHNY-26OCT09-T76` | finalized | no | `$0.0000` | `70.00` |
| `KXHIGHNY-26OCT09-T69` | finalized | no | `$0.0000` | `70.00` |
| `KXHIGHNY-26OCT09-B75.5` | finalized | no | `$0.0000` | `70.00` |

The query returned HTTP 200 at `2026-10-10T23:50:18.534810+00:00`; the canonical payload SHA-256 was `b50bdbd35d3b2a5830a7e679ddd8038a28e17d700101726d0ff08f279b867a35`. `weather-mm markets --status settled` saves such response pages, and `weather-mm normalize` carries `result`, `settlement_value_dollars`, and `expiration_value` into the local market table. The `expiration_value` offers a potential exchange-reported weather outcome label, subject to validating its units, meaning, and linkage across more markets.

This demonstrates one public path to resolved outcomes; it does not yet establish historical coverage depth, completeness across all markets, or a multi-year training sample.

## What this resolves—and what remains open

For this specific observed market, the primary rule confirms the series metadata's settlement source: The Weather Company. The generic weather help page mentions a different source for some daily temperature markets; it should not override the rule text attached to this market.

The market rule still does not by itself give us a redistributable historical feed of The Weather Company's final values, a precise observation-station mapping behind `CLINYC`, or every timestamp/rounding detail. We must not silently substitute an NWS report, ERA5 reanalysis, or a gridded Open-Meteo value and call it the exact settlement target.

Before a calibrated probability or resolved-outcome backtest, establish one of these paths:

1. Expand the Kalshi resolved-market sample, verify `expiration_value` semantics and coverage, and use exchange outcomes with market/date linkage; or
2. Obtain a permitted historical The Weather Company feed and confirm how it maps to `CLINYC`; or
3. Change to a contract whose outcome maps directly to an openly archived authoritative source.

Until then, any open weather data model is a proxy study and must be described that way. The market-making execution diagnostic remains separate from weather forecast accuracy.

## Reproduce the capture

```shell
uv run weather-mm market --ticker KXHIGHNY-26OCT11-B68.5
```

The command saves a timestamped raw capture locally, prints the relevant market fields, and reports the payload hash. The displayed book and market status are transient; only the captured response describes this observation.
