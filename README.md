# Weather Market Making Lab

Research and engineering project on event-driven market making for weather prediction contracts.

> **Project status: quote baseline, sparse-snapshot markout diagnostic, and resolved-outcome pipeline implemented.** The repository contains a read-only public REST collector, capture validation and normalization, deterministic inventory-aware quotes, hypothetical quote markouts, and an aggregator for Kalshi-reported weather outcomes. No fills, forecast model, strategy backtest, paper-trading result, or live-trading result have been produced. Nothing here is evidence of profitability.

## Research question

Can a calibrated probability distribution for a weather outcome improve market-making decisions in a thin, binary-contract order book after accounting for inventory, fees, queue uncertainty, latency, and adverse selection?

The initial venue study focuses on Kalshi daily temperature contracts because the contract rules specify the settlement source and the public API exposes market metadata and order-book snapshots. Live trading is out of scope unless the account holder is eligible under the venue's current rules and local law. The current Kalshi Member Agreement lists France as restricted for event-contract trading.

## Work plan

1. **Scope and data feasibility** — review contract rules, endpoint access, forecast vintages, settlement observations, and data-use terms.
2. **Capture and data quality** — collect public market metadata/order-book snapshots where permitted; preserve source timestamps and local receive timestamps; validate schema and gaps.
3. **Weather probabilities** — verify the outcome field and location/time mapping, then build simple calibrated probabilities using only forecasts that were available at each simulated decision time.
4. **Market-making baseline** — quote around a fair probability, then add inventory skew, risk limits, and fee-aware quote selection.
5. **Execution simulator** — first measure hypothetical quote markouts; then replay richer event-level data with conservative/base/optimistic fill assumptions, queue uncertainty, cancellation and order-entry latency, and explicit no-market-impact caveats.
6. **Evaluation** — compare against simple baselines using chronological holdouts and report net P&L, markouts, inventory, calibration, fill assumptions, and uncertainty.
7. **Paper-trading adapter** — only after replay and operational controls are documented. No live adapter is planned for a restricted jurisdiction.

## First data-collection step

The read-only CLI discovers current markets and captures a public REST order-book snapshot. Setup, capture format, limitations, and next verification steps are documented in [the collector notes](docs/data-collection/public-kalshi-collector.md). The first successful local run is recorded in [the run log](docs/data-collection/first-collector-run-2026-10-11.md). A bounded three-snapshot sampler run is recorded [here](docs/data-collection/rest-sampling-run-2026-10-11.md).

```shell
uv sync
uv run weather-mm markets --series-ticker KXHIGHNY --max-markets 100
uv run weather-mm market --ticker <ticker-returned-by-discovery>
uv run weather-mm markets --series-ticker KXHIGHNY --status settled --max-markets 1000 --page-size 200 --summary-only
uv run weather-mm snapshot --ticker <ticker-returned-by-discovery> --depth 0
uv run weather-mm normalize
uv run weather-mm outcomes
uv run weather-mm sample --ticker <ticker-returned-by-discovery> --count 20 --interval-seconds 30
uv run weather-mm quote --fair-value 0.50 --inventory 10
uv run weather-mm markout --horizons 1,3,5
```

Captures append to `data/raw/kalshi-public.jsonl`, which is intentionally excluded from Git. Use a ticker that the discovery command currently reports as open. The `normalize` command validates each payload hash and writes local market and order-book CSVs under `data/derived/`; see [normalization notes](docs/data-collection/normalization.md).

## Repository map

- [Research landscape review](docs/research/market-making-literature-review.md) — initial source review, design implications, and open questions.
- [Market settlement audit](docs/research/market-settlement-audit-2026-10-11.md) — actual market terms, captured payload hash, and remaining source questions.
- [Weather probability data plan](docs/research/weather-probability-data-plan.md) — archived forecast options, look-ahead controls, and modeling decision gates.
- [Public Kalshi collector notes](docs/data-collection/public-kalshi-collector.md) — setup, record format, operating limits, and verification plan.
- [First collector run](docs/data-collection/first-collector-run-2026-10-11.md) — environment, observed API responses, payload hash, and scope of the verification.
- [Capture normalization](docs/data-collection/normalization.md) — integrity checks, CSV schema, and data limitations.
- [Outcome aggregation](docs/data-collection/weather-outcome-aggregation.md) — validation and event-level label construction.
- [Settled outcome collection run](docs/data-collection/settled-weather-outcomes-run-2026-10-11.md) — API query, coverage summary, hashes, and limits.
- [REST sampling run](docs/data-collection/rest-sampling-run-2026-10-11.md) — observations from the first bounded snapshot series.
- [Quote engine](docs/strategy/quote-engine.md) — formulas, configuration, example, and limitations.
- [Sparse-snapshot markout study](docs/strategy/snapshot-markout-study.md) — quote replay, markout definitions, runnable command, and limitations.
- [First markout run](docs/experiments/snapshot-markout-run-2026-10-11.md) — command, small-sample output, verification, and interpretation.
- `tests/` — focused tests for quote generation, normalization, and replay markout mechanics.
- `uv.lock` — resolved Python dependencies for reproducible setup.
- `src/weather_mm/` — read-only REST client, JSONL storage, validation/normalization, deterministic quote baseline, sparse snapshot replay diagnostic, and CLI.
- `data/raw/` and `data/derived/` — local API captures and normalized CSVs; ignored by Git by default.
- `experiments/` — versioned configurations and reproducible run outputs (planned).

## Reproducibility principles

- Separate venue data, weather inputs, strategy decisions, execution simulation, and reporting.
- Keep event time, source time, and local receive time distinct.
- Preserve raw source payloads locally where terms allow; record schema versions, collection windows, and checksums.
- Never use realized weather observations as if they were forecasts available at the simulated decision time.
- Treat L2 queue position as uncertain; publish sensitivity to fill-model assumptions.
- Include fees, settlement mechanics, and inventory mark-to-settlement in P&L.
- Record negative, inconclusive, and positive results with the same care.
- Do not publish credentials, private user data, or data whose licence/terms do not allow redistribution.

## Current limitations

- Twenty-two focused unit tests pass. The local outcome sample contains 68 daily labels, and the quote replay contains only four usable snapshots. The outcome field's exact semantics still need verification. The markout diagnostic does not model fills, venue fees, or P&L; a short REST sample does not establish feed continuity or queue position.
- Kalshi REST market data is public, but its order-book WebSocket requires authentication. REST snapshots can support a collector prototype, but sparse snapshots cannot reveal exact queue priority or all intervening book events.
- Kalshi's current Member Agreement lists France as restricted for trading event contracts. A VPN does not change eligibility. Any eventual execution must comply with actual location, account eligibility, venue terms, and applicable law.
- Weather contract settlement is rule-specific. A model must match the named station, time convention, measurement source, rounding, and revision rules for each market.

## Source and decision trail

Research notes and design decisions will be added as the project advances. Source summaries distinguish published findings from our own hypotheses; all strategy claims will be tied to reproducible runs rather than inferred from a model score alone.
