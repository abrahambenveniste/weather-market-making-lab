# Snapshot markout diagnostic run — 2026-10-11

## Purpose

Record the first execution of `weather-mm markout` against the small local Kalshi REST sample. This is a code-path and arithmetic check, not evidence that a strategy is profitable.

## Environment and command

- Repository commit before this work: `7aa83e8` (`Document deterministic quote baseline milestone`).
- Local environment: project virtual environment, Python 3.13.
- Input: local `data/derived/orderbook-levels.csv`, regenerated from the ignored raw JSONL captures using `weather-mm normalize`.
- Command: `weather-mm markout --horizons 1,3,5`.
- Quote baseline: default two-cent half-spread, zero inventory, fair value set to each snapshot midpoint.

## Output observed

- 4 usable snapshots, all for 1 ticker.
- 4 output rows in local `data/derived/snapshot-markouts.csv`.
- Horizon 1: 3 bid and 3 ask markouts; mean bid markout `$0.0050` and mean ask markout `$0.0250` per contract.
- Horizon 3: 1 bid and 1 ask markout; mean bid markout `$0.0050` and mean ask markout `$0.0250` per contract.
- Horizon 5: no observations had enough later snapshots.
- All values are before fees and conditional on a hypothetical fill that is not established by this dataset.

These values are descriptive outputs from a tiny sparse sample. They are not realized P&L, fill-adjusted returns, statistically meaningful estimates, or a profitability claim. The generated CSV is ignored by Git along with the source market data; the code, command, definitions, and observed summary are recorded here so the computation can be repeated with local captures.

## Verification

`python -m unittest discover -s tests -v` passed all 15 tests after this feature was added. Tests include market midpoint reconstruction from complementary YES/NO bids, markout arithmetic, incomplete future horizons, invalid horizons, and crossed-book rejection.

## Next data requirement

This run exposed the main limitation: only four usable timestamps are available, and horizons represent observations rather than fixed durations. Collect a longer permitted sample and preserve receive timestamps. For actual fill analysis, obtain event-level book updates and public trade prints, then document and stress-test queue and latency assumptions.
