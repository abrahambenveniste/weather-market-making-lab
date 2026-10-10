# Inventory-aware quote baseline

**Status:** deterministic quoting mechanics implemented; no fills, fees, or P&L are simulated.

## Run a quote example

```shell
uv run weather-mm quote --fair-value 0.50 --inventory 10
```

All prices use exact decimal arithmetic. The default configuration returns a YES bid and ask, order sizes, reservation price, half-spread, and normalized inventory ratio as JSON.

For the command above, the observed output was:

```json
{"fair_value":"0.50","reservation_price":"0.490","half_spread":"0.02","bid_price":"0.47","ask_price":"0.51","bid_size":"2.5","ask_size":"7.5","inventory_ratio":"0.5"}
```

## Model

Let `p` be the supplied fair probability and `q` signed YES inventory, where positive `q` is long. The reservation price is:

```text
r = clamp(p - q * inventory_skew_per_contract, min_price, max_price)
```

The half-spread is the sum of a base half-spread, an uncertainty widening input, and an adverse-selection widening input. The bid is rounded down to the tick; the ask is rounded up. Bounds and a one-tick minimum separation keep the quote inside the configured price grid.

Inventory is scaled by the configured maximum and clipped to `[-1, 1]`. Bid and ask sizes are `base_size * (1 - inventory_ratio)` and `base_size * (1 + inventory_ratio)`. A long position therefore lowers both quotes, reduces bid size, and increases ask size; a short position does the reverse. At the inventory limit, the quote stops adding size in the risk-increasing direction.

## Assumptions and limits

- `fair_value` is an external input. This module does not estimate weather probabilities.
- The spread widening values are supplied parameters, not calibrated estimates.
- The baseline is fee-agnostic. Venue fees, contract-specific tick rules, queue position, fills, latency, and market impact are not modeled.
- It does not read the captured order book or submit, amend, or cancel orders.
- A quote output is a deterministic example, not a recommendation or profitability claim.

Next, connect these quotes to a replay simulator and test fee-aware edge, inventory paths, conservative fill assumptions, and markouts against chronological data.

