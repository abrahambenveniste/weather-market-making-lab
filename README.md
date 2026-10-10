# Weather Market Making Lab

Research and engineering project on event-driven market making for weather prediction contracts.

> **Project status: research setup.** The repository currently contains project framing and a first-pass literature and systems review. No strategy backtest, paper-trading result, or live-trading result has been produced. Nothing in this repository should be read as evidence of profitability.

## Research question

Can a calibrated probability distribution for a weather outcome improve market-making decisions in a thin, binary-contract order book after accounting for inventory, fees, queue uncertainty, latency, and adverse selection?

The initial venue study focuses on Kalshi daily temperature contracts because the contract rules specify the settlement source and the public API exposes market metadata and order-book snapshots. Live trading is out of scope unless the account holder is eligible under the venue's current rules and local law. The current Kalshi Member Agreement lists France as restricted for event-contract trading.

## Work plan

1. **Scope and data feasibility** — review contract rules, endpoint access, forecast vintages, settlement observations, and data-use terms.
2. **Capture and data quality** — collect public market metadata/order-book snapshots where permitted; preserve source timestamps and local receive timestamps; validate schema and gaps.
3. **Weather probabilities** — build simple, calibrated probabilities for the contract's actual settlement outcome using only forecasts that were available at each simulated decision time.
4. **Market-making baseline** — quote around a fair probability, then add inventory skew, risk limits, and fee-aware quote selection.
5. **Execution simulator** — replay the collected data with conservative/base/optimistic fill assumptions, queue uncertainty, cancellation and order-entry latency, and explicit no-market-impact caveats.
6. **Evaluation** — compare against simple baselines using chronological holdouts and report net P&L, markouts, inventory, calibration, fill assumptions, and uncertainty.
7. **Paper-trading adapter** — only after replay and operational controls are documented. No live adapter is planned for a restricted jurisdiction.

## Repository map

- [Research landscape review](docs/research/market-making-literature-review.md) — initial source review, design implications, and open questions.
- `src/` — strategy and data code (planned).
- `data/` — local data only; raw and derived datasets are excluded from Git by default (planned).
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

- The repo is at the research stage; no performance result is available.
- Kalshi REST market data is public, but its order-book WebSocket requires authentication. REST snapshots can support a collector prototype, but sparse snapshots cannot reveal exact queue priority or all intervening book events.
- Kalshi's current Member Agreement lists France as restricted for trading event contracts. A VPN does not change eligibility. Any eventual execution must comply with actual location, account eligibility, venue terms, and applicable law.
- Weather contract settlement is rule-specific. A model must match the named station, time convention, measurement source, rounding, and revision rules for each market.

## Source and decision trail

Research notes and design decisions will be added as the project advances. Source summaries distinguish published findings from our own hypotheses; all strategy claims will be tied to reproducible runs rather than inferred from a model score alone.
