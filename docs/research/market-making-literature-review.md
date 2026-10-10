# Market-making literature and systems review

**Review date:** 2026-10-11  
**Project stage:** initial research review; no strategy results  
**Purpose:** turn the source material into implementable design choices and a reading plan.

> This is a curated first-pass review of primary papers, official venue/data documentation, and relevant open-source systems. It is not an exhaustive review of every paper or repository in the field. The summaries below are research notes, not a claim that the project author has personally completed every suggested reading. Work through the reading list and add questions, derivations, and replication notes as the project develops.

## 1. Project framing

The useful research question is not simply whether a weather model predicts tomorrow's temperature. It is whether information available at a decision time improves the quotes and inventory decisions of a passive liquidity provider after accounting for fees, fill probability, queue uncertainty, latency, adverse selection, and binary settlement.

For a contract with a $1 payout when outcome (Y) occurs and a model probability (p=P(Y=1)), the gross value of buying YES at price (q) is (p-q) per contract before fees, execution costs, and risk. For a maker, execution is conditional: the probability and timing of being filled matter, and a fill can arrive precisely when the market's fair value has moved against the quote. A high fill rate or a good forecast score alone does not demonstrate profitable market making.

The project has two linked but separable questions:

1. **Forecasting:** Are weather probabilities calibrated for the exact contract outcome and settlement process, using only forecast vintages available at each historical decision time?
2. **Quoting/execution:** Given a probability estimate, book state, inventory, and costs, do adaptive quotes improve fee-adjusted performance over transparent baselines under defensible fill assumptions?

The initial market-making core should be venue-independent. A Kalshi adapter can supply a concrete weather-contract example. Prediction-market weather contracts are episodic and can be thin; the project should be described as event-driven market-making research, not as proof of production HFT performance.

## 2. Venue and contract mechanics

### Kalshi data path

Kalshi's official [market-data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data) documents unauthenticated REST access to series, events, markets, and order-book snapshots at `https://external-api.kalshi.com/trade-api/v2`. The example weather series is `KXHIGHNY`. The [Get Markets endpoint](https://docs.kalshi.com/api-reference/market/get-markets) exposes filters including series, market status, and settlement time. The [Get Market Orderbook endpoint](https://docs.kalshi.com/api-reference/market/get-market-orderbook) returns aggregated YES and NO bid levels; the quick start explains that asks are represented through the complementary YES/NO relationship.

The real-time [Orderbook Updates WebSocket](https://docs.kalshi.com/websockets/orderbook-updates) sends a snapshot followed by deltas, but requires API-key authentication. Therefore, a research collector that only uses public unauthenticated REST can capture snapshots, not a complete sequence of intervening book events. Sparse snapshots do not reveal exact queue priority and can miss short-lived changes. We must record the polling interval and data gaps and avoid presenting this collection as exchange-grade tick history. Historical market metadata or a final settlement value is not the same thing as historical order-book replay data.

**Eligibility constraint:** Kalshi's [Member Agreement](https://kalshi.com/docs/kalshi-member-agreement.pdf), Section VI, lists France among restricted jurisdictions for event-contract trading. The agreement distinguishes trading from non-trading access, but live orders must not be placed from a restricted location or account. Any later execution requires checking current terms, actual account eligibility, physical location, domicile, and applicable law. A VPN does not change those facts. This project can proceed with public-data research and paper simulation.

### Weather contract rules are part of the data

Kalshi's [weather-market guide](https://help.kalshi.com/en/articles/13823837-weather-markets) says each market names its official settlement source. Daily high/low temperature markets settle using the final NWS Daily Climate Report; hourly temperature contracts use The Weather Company and specific station coordinates. Its guide also documents that daily climate reports use local standard time, so daylight-saving transitions alter the effective temperature window.

The data model must preserve, per market:

- contract ticker, title, strike/range, opening and closing times;
- exact settlement station/location and source named in the rules;
- local timezone and the contract's measurement window;
- market rule text and rule version as observed at collection time;
- final settlement value and when it became available.

Do not silently map a city forecast to a nearby airport or use a convenient daily maximum if the contract settles on a different station/window. Parse the market rules and verify a sample of settlements manually before scoring forecasts.

## 3. Market-making theory and microstructure

### Avellaneda–Stoikov as a starting benchmark

Avellaneda and Stoikov's [2008 paper](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf) derives bid/ask quotes from an inventory-dependent reservation value and a model of order-arrival probability as a function of quote distance. It gives us a clean baseline for separating **fair value / inventory skew** from **quote width / fill likelihood**.

Its assumptions are intentionally simplified for our use: a continuous stock price model, a stylized arrival process, and an abstract limit-order setting. It does not directly model a bounded binary payoff, discrete contract ticks, exchange fees, a multi-outcome weather ladder, order cancellation latency, or queue priority. We should implement the intuition as a transparent baseline, then state and test each adaptation instead of treating the formula as a production strategy.

For a probability-valued contract, an initial reservation-value baseline can shift a fair probability against inventory, while quote width responds to uncertainty and modeled adverse selection. This is only a candidate design. Its parameters must be fit on training data and evaluated on later dates.

### Order-flow imbalance and adverse selection

Cont, Kukanov, and Stoikov's [order-book event study](https://arxiv.org/abs/1011.6402) finds a short-horizon relationship between order-flow imbalance (limit additions, market orders, and cancellations at the best quotes) and price changes in equities, with impact depending on depth. This suggests useful book-only features and a measurable adverse-selection diagnostic. It does **not** establish that the same relationship transfers to binary weather contracts; that is an empirical question.

Possible first features: best-level and multi-level size imbalance, spread, depth, recent quote/trade intensity, price changes, and order-flow imbalance where event data is sufficiently granular. Each feature must be computed using only data timestamped at or before the simulated decision.

### Queue position and fill modeling

Erik Rigtorp's practical note, [Estimating order queue position](https://rigtorp.se/2013/06/08/estimating-order-queue-position), explains why FIFO queue estimates depend on order acknowledgement, observed aggregate depth changes, cancellations, and trade prints. It presents a probabilistic way to allocate unexplained size decreases ahead of versus behind a simulated order. This is a useful model family, not ground truth.

The [hftbacktest fill-model documentation](https://hftbacktest.readthedocs.io/en/latest/order_fill.html) makes two critical limitations explicit: replayed market data cannot be changed by the simulated order, so market impact is absent; and market-by-price data requires assumptions about queue position. It offers conservative and probabilistic queue models. We should copy the *discipline* of reporting multiple fill assumptions, not assume its defaults exactly match Kalshi's matching rules.

For a first simulator, report at least:
- **Conservative:** cancellations do not advance our order; trades at our price consume queue ahead first.
- **Base:** probabilistic cancellation allocation and explicit order-entry/cancel latency.
- **Optimistic bound:** a stated, more favorable queue assumption, shown only as a sensitivity bound.

Calibrate or reject these assumptions against our own paper-trading acknowledgements/fills if an eligible authenticated paper or live interface is ever available. Never tune the fill model on the final holdout.

## 4. Weather forecast data and evaluation

### Use forecast vintages, not hindsight

[Open-Meteo's Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) documents archived operational forecast data, with coverage depending on model and availability. Its companion [Previous Runs API](https://open-meteo.com/en/docs/previous-runs-api) provides fixed lead-time slices; [Single Runs](https://open-meteo.com/en/docs/single-runs-api) preserves complete forecast runs selected by initialization time. The documentation distinguishes these products because a stitched historical forecast series is not equivalent to retrieving the exact complete model run available at a decision time. Model coverage and versions change over time.

[NOAA's GEFS documentation](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast) describes an ensemble forecast system and its member forecasts. Ensemble spread can represent forecast uncertainty, but raw model members are not automatically calibrated probabilities for a station-specific market outcome.

A safe initial protocol:
1. Define a decision timestamp and contract settlement interval.
2. Retrieve forecast values from a model run initialized no later than that timestamp.
3. Map the forecast grid to the named settlement station and document the mapping.
4. Convert the forecast distribution into probabilities for the exact contract range/outcome.
5. Calibrate with earlier dates only; freeze the calibration before each chronological test block.
6. Compare against simple baselines, including historical climatology and the market-implied probability.
7. Score forecasts with proper probabilistic metrics such as Brier score and log loss, plus reliability plots. Separately score trading decisions after fees and simulated fills.

Do not substitute ERA5/reanalysis or observed weather for point-in-time forecast vintages: those describe realized/past conditions and would create look-ahead bias if presented as information known at quote time. Match units, rounding, station, timezone, and daylight-saving rules before scoring.

## 5. Comparable open-source systems and datasets

### Directly relevant prediction-market research: lobpred

The [lobpred repository](https://github.com/FrederikBenirschke/lobpred) describes a pipeline for short-horizon book-move prediction and reports its own recordings of 12 million book events across 371 daily-temperature markets from Kalshi and Polymarket. Its README lays out a useful canonical row schema, feature families (depth, imbalance, queue shape, trade flow, activity, impact), chronological splits, and baseline comparisons.

This is the closest public project found in this first pass. Its reported dataset is not bundled in the repository; the README says raw recordings remain private because they contain trader usernames and data are available on request. Treat its reported results as the authors' results, not independently reproduced facts. The project we build should differentiate through a transparent market-making simulator, weather forecast vintages/calibration, fee-aware P&L decomposition, and sensitivity to queue/fill assumptions. Do not copy or redistribute its data without permission and an appropriate licence.

### hftbacktest

[hftbacktest](https://github.com/nkaz001/hftbacktest) is a strong reference for event replay, timestamp handling, latency models, and queue-model sensitivity. Its replay design is useful for strategies whose order size is small enough that market impact can be neglected. That assumption may be especially fragile in thin event contracts, so the simulator must disclose it and cap simulated size relative to displayed depth.

### NautilusTrader

[NautilusTrader](https://nautilustrader.io/docs/latest/) is a mature event-driven framework spanning research, deterministic backtesting, and live execution. Its [data-granularity guide](https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues/) distinguishes L3 market-by-order, L2 market-by-price, L1 quotes, trades, and bars, and warns that lower-granularity data cannot recover higher-granularity queue information.

This is valuable architectural prior art, but likely too much framework for the first implementation. Build a small, inspectable event-driven replay engine first; revisit NautilusTrader if the project grows to multiple venues or reusable adapters.

### FI-2010 as a benchmark, not strategy evidence

The [FI-2010 paper](https://arxiv.org/abs/1705.03233) describes a public limit-order-book dataset for mid-price prediction across five Nordic stocks and ten trading days. It can provide an external smoke-test of feature/label plumbing or model comparison. It is neither Kalshi data nor evidence that a market-making strategy can earn money; it lacks the target weather contracts, contract settlement, and our queue/fill economics.

## 6. Initial engineering choices

| Component | First choice | Reason / boundary |
|---|---|---|
| Language/runtime | Python 3.11+ with `uv` | Fast iteration and reproducible environment for an intermediate Python project. |
| Public REST collector | `httpx` with `asyncio`, bounded concurrency, retries/backoff | Directly exercises endpoint semantics without hiding them behind an SDK. Preserve raw response, request time, response time, and status. |
| Authenticated WebSocket | Defer | Requires API-key authentication; not necessary for public REST research and not available as a France-based trading workaround. |
| Raw archive | JSON Lines initially; Parquet for normalized events | Easy append-only capture first, columnar replay/analysis later. Keep large/raw files out of Git and record checksums/manifests. |
| Analysis | DuckDB + Polars or Pandas | SQL over Parquet and familiar tabular analysis; avoid premature infrastructure. |
| Backtest | Small deterministic event-driven engine | Makes fill assumptions and state transitions inspectable. Compare design ideas with hftbacktest/NautilusTrader rather than adding a large framework immediately. |
| Strategy models | Fixed-width baseline, inventory-skew baseline, then forecast-aware quotes | Ablations show whether each added mechanism helps. No deep model before simple baselines. |
| Reporting | Config files, run manifests, CSV/Parquet metrics, plots, narrative notes | Every result should be reproducible from a commit, dataset version, and parameter set. |

## 7. Evaluation plan and failure checks

Use chronological, walk-forward evaluation. Split by calendar date/weather event, not random rows; a single weather event's markets must not leak across train/test. Keep a final holdout untouched until the design is frozen.

Report:
- forecast calibration and skill against climatology and market-implied probabilities;
- filled quantity, fill rate, quote lifetime, spread captured, and maker/taker assumptions;
- markouts after fills at stated horizons, including the sign convention;
- gross trading P&L, fees, settlement P&L, net P&L, inventory path, worst drawdown, and exposure near settlement;
- results by city/station, temperature range, time to close, liquidity regime, and forecast lead time;
- uncertainty intervals across dates/markets and a parameter sensitivity table.

Required ablations:
1. market/book-only quoting with no weather signal;
2. weather fair-value signal with fixed quote width;
3. inventory skew without weather signal;
4. combined forecast + inventory skew;
5. each strategy under conservative/base/optimistic queue models and latency settings.

A strategy is not supported by a high win rate, a good classification score, or a profitable optimistic fill model. We need net results that survive realistic fees, conservative fills, chronological holdouts, and sizing limits. A negative result is publishable if the experiment is sound and explains where the edge disappears.

## 8. Initial reading order

1. Kalshi's [market-data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data), [orderbook WebSocket](https://docs.kalshi.com/websockets/orderbook-updates), and [weather-market rules](https://help.kalshi.com/en/articles/13823837-weather-markets).
2. Avellaneda–Stoikov, [High-frequency trading in a limit order book](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf): derive reservation value and quote-distance logic.
3. Cont–Kukanov–Stoikov, [The Price Impact of Order Book Events](https://arxiv.org/abs/1011.6402): implement and test OFI, without assuming transfer.
4. [Rigtorp's queue-position note](https://rigtorp.se/2013/06/08/estimating-order-queue-position) and [hftbacktest fill assumptions](https://hftbacktest.readthedocs.io/en/latest/order_fill.html): write down queue uncertainty before calculating simulated P&L.
5. Burgi, Deng, and Whelan, [Makers and Takers: The Economics of the Kalshi Prediction Market](https://www.ifo.de/en/cesifo/publications/2026/working-paper/makers-and-takers-economics-kalshi-prediction-market): venue-specific fee and maker/taker economics.
6. [Open-Meteo historical forecast products](https://open-meteo.com/en/docs/historical-forecast-api) and [NOAA GEFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast): choose the point-in-time weather archive and document its coverage.
7. Inspect [lobpred](https://github.com/FrederikBenirschke/lobpred) and [NautilusTrader](https://nautilustrader.io/docs/latest/) for data schema, causal features, execution assumptions, and architecture.

## 9. Source register

All links below were consulted for this first-pass review on the date above. Web/API documentation can change; record retrieval dates and relevant versions in future experiments.

### Venue and weather data
- [Kalshi public market-data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data) — unauthenticated REST endpoints and `KXHIGHNY` example.
- [Kalshi Get Markets API](https://docs.kalshi.com/api-reference/market/get-markets) — market metadata, status/time filters, pagination.
- [Kalshi Get Market Orderbook API](https://docs.kalshi.com/api-reference/market/get-market-orderbook) — aggregated YES/NO bid depth.
- [Kalshi Orderbook Updates WebSocket](https://docs.kalshi.com/websockets/orderbook-updates) — authenticated snapshot-and-delta stream.
- [Kalshi Weather Markets guide](https://help.kalshi.com/en/articles/13823837-weather-markets) — settlement sources, daily/hourly rules, station/time conventions.
- [Kalshi Member Agreement](https://kalshi.com/docs/kalshi-member-agreement.pdf) — eligibility restriction referenced in Section 2; re-check before any venue use.
- [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) — archived operational forecast model data.
- [Open-Meteo Previous Runs API](https://open-meteo.com/en/docs/previous-runs-api) — forecasts at fixed lead times.
- [Open-Meteo Single Runs API](https://open-meteo.com/en/docs/single-runs-api) — complete individual model runs.
- [NOAA NCEI GEFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast) — official ensemble model overview and archive links.

### Papers, systems, and datasets
- Avellaneda & Stoikov, 2008, [High-frequency trading in a limit order book](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf) — inventory-aware quoting baseline.
- Cont, Kukanov & Stoikov, 2014, [The Price Impact of Order Book Events](https://arxiv.org/abs/1011.6402) — order-flow imbalance and depth.
- Bürgi, Deng & Whelan, 2026, [Makers and Takers: The Economics of the Kalshi Prediction Market](https://www.ifo.de/en/cesifo/publications/2026/working-paper/makers-and-takers-economics-kalshi-prediction-market) — prediction-market maker/taker and fee economics.
- Rigtorp, 2013, [Estimating order queue position](https://rigtorp.se/2013/06/08/estimating-order-queue-position) — L2 queue estimate heuristic.
- [hftbacktest source repository](https://github.com/nkaz001/hftbacktest) and [order-fill docs](https://hftbacktest.readthedocs.io/en/latest/order_fill.html) — replay, fill, and queue models.
- [lobpred source repository](https://github.com/FrederikBenirschke/lobpred) — prediction-market LOB schema and analysis pipeline; its private dataset/results are not independently reproduced here.
- [NautilusTrader docs](https://nautilustrader.io/docs/latest/) and [backtest data-granularity guide](https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues/) — event-driven framework and data requirements.
- Ntakaris et al., 2018, [FI-2010 benchmark dataset paper](https://arxiv.org/abs/1705.03233) — external LOB forecasting benchmark; not venue/strategy evidence.

## 10. Questions to resolve before implementation

1. Which single weather series and station have enough active markets and a verifiable settlement archive?
2. Can we reliably retrieve enough historical market metadata, trade prints, settlement values, and book snapshots to test anything beyond a collector prototype?
3. Which market rules define a daily high's exact time window, station, revisions, and rounding?
4. Which raw data may be stored locally or redistributed, and which must remain excluded from the public repository?
5. What fee schedule and maker/taker assumptions apply to each sampled contract and date?
6. What is the least optimistic queue model supported by the data we can actually collect?
7. Does the weather signal improve net market-making P&L beyond book-only and market-implied baselines out of sample?

These questions determine whether the Kalshi weather case remains the main empirical track or whether the simulator should use a more data-rich public LOB benchmark while keeping weather forecasting as a separate module.
