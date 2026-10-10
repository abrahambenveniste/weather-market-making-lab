# Sparse-snapshot quote markouts

## Purpose

This is the first replay diagnostic for the quote baseline. For each valid normalized book snapshot, it builds a YES midpoint from the best YES bid and the complement of the best NO bid, places symmetric hypothetical quotes around that midpoint, then compares those quote prices with later observed midpoints.

It helps answer a narrow question: **if a hypothetical quote had filled, how did the market midpoint move afterward?** It does not establish that the quote would have filled or that the strategy made money.

## Run it

```shell
uv run weather-mm markout
```

By default, the command reads `data/derived/orderbook-levels.csv`, writes `data/derived/snapshot-markouts.csv`, and reports horizons of 1, 3, and 5 later observations for the same ticker. You can choose another quote half-spread or set different observation horizons:

```shell
uv run weather-mm markout --horizons 1,2,4 --base-half-spread 0.03
```

The raw and derived market data directories are ignored by Git. The command output and source code are reproducible, but local captures are not published by default.

## Calculation

For each snapshot:

1. `YES best bid = max(YES bid levels)`.
2. `YES best ask = 1 - max(NO bid levels)` because a NO bid at price `x` implies a YES offer at `1-x`.
3. `mid = (YES best bid + YES best ask) / 2`.
4. The baseline quote engine places a bid and ask around this midpoint with zero inventory.
5. At horizon `h`, the markouts are `future midpoint - hypothetical bid` and `hypothetical ask - future midpoint`, in dollars per contract before fees.

Horizons count observed snapshots, not elapsed seconds. Each output row preserves the future observation timestamp so the actual elapsed time can be inspected. Rows without enough future observations have blank markout cells.

## What this does not model

- Whether either hypothetical quote was resting in the book or received a fill.
- Queue position, cancellations ahead, trade direction, partial fills, or market impact.
- Fees, rebates, funding, settlement, inventory, or realized P&L.
- A weather forecast or predictive fair-value model; the current fair value is the contemporaneous book midpoint.
- Events between REST polls. Sparse snapshots can miss rapid quote changes and price paths.

Therefore, positive markouts are not strategy profits; negative markouts are not realized losses. This diagnostic is a measurement tool, not a profitability claim. A credible execution simulator will need event-level order-book changes and public trade prints, plus explicitly conservative queue and latency assumptions. Data coverage and endpoint access must be verified before using those inputs.

## Checks

Unit tests verify binary-book midpoint construction, markout arithmetic, incomplete horizon handling, malformed horizon rejection, and skipping crossed books. The project test suite is the code-level check; any result from the local small capture is exploratory only.
