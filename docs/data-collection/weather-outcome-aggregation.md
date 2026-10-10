# Event-level weather outcome aggregation

## Purpose

Kalshi returns a `result` and an `expiration_value` for finalized contracts. Because one weather event has several strike contracts, the aggregator creates one row per event date and checks that all contracts agree on the reported event value.

## Run

```shell
uv run weather-mm normalize
uv run weather-mm outcomes
```

The default inputs are `data/derived/markets.csv`; the output is `data/derived/weather-outcomes.csv`. Both stay local because `data/derived/` is Git-ignored.

## Validation

- Includes only finalized/settled markets whose event ticker matches `--event-prefix` (default `KXHIGHNY-`).
- Requires market ticker, event ticker, result, and expiration value.
- Parses the event date from the event ticker.
- Deduplicates repeated captures by market ticker and rejects conflicting settlement fields.
- Requires one common `expiration_value` across all contracts for an event.
- Writes event date, ticker, preserved expiration value, unique contract count, and YES/NO/void counts.

The command intentionally preserves the API field `expiration_value` rather than assigning units. The selected market's rule says Fahrenheit, but mapping the field to a meteorological observation and its exact timestamp/window should be validated before using it as a model target.

## First sample

The 2026-10-11 collection returned 408 unique finalized contracts for 68 consecutive dates, 2026-08-03 through 2026-10-09. Each date had six contracts, one YES and five NO, and the event contracts agreed on their reported expiration value. Three repeated records from an earlier request were deduplicated. See the [collection run record](settled-weather-outcomes-run-2026-10-11.md).

This sample is enough to exercise the label pipeline, but it is not enough to claim a calibrated forecast model or profitability.
