# Settled weather outcome collection — 2026-10-11

## Question

Can the public market endpoint provide resolved outcome labels for the weather series? We queried finalized markets only; no account credentials or trading endpoints were used.

## Collection

```shell
uv run weather-mm markets --series-ticker KXHIGHNY --status settled --max-markets 1000 --page-size 200
uv run weather-mm normalize
uv run weather-mm outcomes
```

The query requested up to 1,000 records and returned 408 markets over three pages. The third page returned 8 records and no further cursor. All responses were HTTP 200. Page payload hashes:

- `601945a8148d920468ea0592b74b3daa2da53d91982e88418da94eccf0319550` (200 markets)
- `ede4e261afde3c47ef97f42aa576840a3cd1c3cad53527c4dfe502c85cebee3f` (200 markets)
- `ceae13f255780ca167ab09f2e4515fac436c3ca2f133e58588d4032a867c3b63` (8 markets)

The normalizer independently verified the hashes against the raw payloads during normalization.

## Aggregation results

- 408 unique finalized market tickers across 68 daily events.
- Event dates: 2026-08-03 through 2026-10-09, with no missing dates in that interval.
- Six resolved contracts per event; each event had one YES and five NO outcomes.
- Every captured finalized market had a result and `expiration_value`; all six contracts within an event agreed on that value.
- Three market rows from an earlier small query were repeated in the local raw file; the event aggregator detected and removed these duplicate captures by market ticker.
- Local `data/derived/weather-outcomes.csv` contains one row per event and the Kalshi-reported `expiration_value` as an unconverted string.

The output is a useful small target-label sample, not a forecast model or a trading backtest. The 68 observations cover only a recent interval and are too few to support strong claims. We preserve the source field name and do not silently assign units. The market rule states Fahrenheit, but the API field's full semantics and cross-market coverage should be verified before model training.

## Tooling change

The CLI now supports `--summary-only` for bounded bulk queries so future runs can report counts without printing hundreds of market rows. The original capture was made before that option was added; this run record retains the exact command used.

## Reproducibility and Git

Raw API responses, normalized tables, and the derived outcome CSV are excluded from Git. The collector, hash validation, normalizer, aggregator, tests, query parameters, payload hashes, and summary statistics are committed so another researcher can repeat the collection and inspect the transformation.
