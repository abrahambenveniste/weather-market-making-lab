# Weather probability data plan

## What the current evidence supports

The Kalshi public endpoint gave us 408 unique finalized `KXHIGHNY` contracts over 68 consecutive event dates, 2026-08-03 through 2026-10-09. Kalshi's market rules name The Weather Company as the settlement source, and its API returns an `expiration_value` shared by each day's six contracts. The outcome pipeline preserves that source field without assuming its units or observation window.

This is enough to test the data pipeline. It is a short sample for forecast calibration, and it contains no archived historical order books or quote-level trading prices.

## Forecast archive choices

| Source | Useful for | Caution |
|---|---|---|
| [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) | A convenient hourly historical forecast series, with coverage beginning around 2022 depending on model. | The API stitches the first hours of successive runs into a continuous series; use it for exploratory skill analysis, not as proof of the exact forecast visible at a past decision time. |
| [Open-Meteo Single Runs API](https://open-meteo.com/en/docs/single-runs-api) | Reconstructing a specific model run by its initialization time; IFS HRES archive begins in March 2024, and most other model archives begin April 2026. | Initialization is not publication time. Global forecasts typically become available several hours after initialization, so the backtest must impose an availability delay and exclude runs not yet published at the decision timestamp. |
| [Open-Meteo Previous Runs API](https://open-meteo.com/en/docs/previous-runs-api) | Measuring forecast error at fixed lead times, with series for offsets such as one to seven days. | Good for lead-time skill studies; check that the selected series corresponds to the contract's actual decision time and valid-date window. |
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) / ERA5 | Exploratory weather climatology and model comparisons. | Reanalysis is not an as-issued forecast and must not be used as a predictor in a historical trading replay. |

Open-Meteo describes the Single Runs API as retaining the original run structure and the Historical Forecast API as a stitched series. Those distinctions matter for avoiding look-ahead bias. See the official [Single Runs documentation](https://open-meteo.com/en/docs/single-runs-api) and [Historical Forecast documentation](https://open-meteo.com/en/docs/historical-forecast-api).

## Proposed first probability baseline

After verifying `expiration_value` semantics and choosing an as-of timestamp:

1. Pair each event date with Kalshi's exchange-reported final outcome value.
2. Retrieve a weather-model run that was actually available before that event's hypothetical decision timestamp.
3. Convert hourly forecast temperatures for the contract's station/location and local date into one predicted daily maximum per run.
4. Estimate forecast error only from earlier event dates, using an expanding or rolling chronological window.
5. Convert the forecast and historical residual distribution into a probability for each contract's exact strike range.
6. Evaluate out of sample with Brier score, log loss, calibration tables, and a simple forecast-error baseline. Compare against market prices only when a valid historical price series is available.

IFS HRES is a reasonable deterministic starting model because Open-Meteo documents a longer single-run archive for it. It is not an ensemble; uncertainty must come from a separately calibrated past-error distribution and must be labeled as such. Later compare another archived model or an ensemble product if its run history is sufficient and licensing allows the intended research use.

## Decision gates before modeling

- Confirm what `expiration_value` means, its unit, and its relationship to the final daily high through market rules/API documentation and cross-contract checks.
- Identify the location mapping behind `CLINYC` and the date/timezone window used for the reported high.
- Set a decision timestamp from actual quote/book observations. Do not use market close as a proxy for an earlier quote time.
- Confirm API data-use and attribution terms before publishing any downloaded weather data.
- Keep forecast accuracy and market-making performance as separate experiments. Weather skill alone does not establish a profitable strategy.
