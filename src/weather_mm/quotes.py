"""A deterministic, fee-agnostic binary-contract quoting baseline."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR


def _as_decimal(value: Decimal | str | int, *, name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{name} must be Decimal, string, or integer; avoid binary floats")
    try:
        result = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be a finite decimal")
    return result


@dataclass(frozen=True)
class QuoteConfig:
    """Fixed parameters for a small inventory-aware quote baseline."""

    tick_size: Decimal = Decimal("0.01")
    min_price: Decimal = Decimal("0.01")
    max_price: Decimal = Decimal("0.99")
    base_half_spread: Decimal = Decimal("0.02")
    inventory_skew_per_contract: Decimal = Decimal("0.001")
    base_size: Decimal = Decimal("5")
    max_inventory: Decimal = Decimal("20")

    def __post_init__(self) -> None:
        names = (
            "tick_size",
            "min_price",
            "max_price",
            "base_half_spread",
            "inventory_skew_per_contract",
            "base_size",
            "max_inventory",
        )
        for name in names:
            value = _as_decimal(getattr(self, name), name=name)
            object.__setattr__(self, name, value)
        if self.tick_size <= 0:
            raise ValueError("tick_size must be positive")
        if not (Decimal("0") <= self.min_price < self.max_price <= Decimal("1")):
            raise ValueError("prices must satisfy 0 <= min_price < max_price <= 1")
        if (self.min_price / self.tick_size) % 1 or (self.max_price / self.tick_size) % 1:
            raise ValueError("min_price and max_price must align to tick_size")
        if self.base_half_spread < 0 or self.inventory_skew_per_contract < 0:
            raise ValueError("spread and inventory skew parameters cannot be negative")
        if self.base_size <= 0 or self.max_inventory <= 0:
            raise ValueError("base_size and max_inventory must be positive")


@dataclass(frozen=True)
class Quote:
    fair_value: Decimal
    reservation_price: Decimal
    half_spread: Decimal
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal
    ask_size: Decimal
    inventory_ratio: Decimal


def _floor_tick(price: Decimal, tick: Decimal) -> Decimal:
    return (price / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


def _ceil_tick(price: Decimal, tick: Decimal) -> Decimal:
    return (price / tick).to_integral_value(rounding=ROUND_CEILING) * tick


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(max(value, low), high)


def make_quotes(
    *,
    fair_value: Decimal | str | int,
    inventory: Decimal | str | int,
    config: QuoteConfig = QuoteConfig(),
    uncertainty_widening: Decimal | str | int = Decimal("0"),
    adverse_selection_widening: Decimal | str | int = Decimal("0"),
) -> Quote:
    """Return a YES bid and YES ask around a probability and inventory-skewed price.

    Positive inventory means long YES contracts. The reservation price moves down
    when long, bid size shrinks, and ask size grows. Extra uncertainty and
    adverse-selection inputs widen both sides symmetrically. This function does
    not model fees, queue position, fills, or profitability.
    """
    fair = _as_decimal(fair_value, name="fair_value")
    position = _as_decimal(inventory, name="inventory")
    uncertainty = _as_decimal(uncertainty_widening, name="uncertainty_widening")
    adverse = _as_decimal(adverse_selection_widening, name="adverse_selection_widening")
    if not Decimal("0") <= fair <= Decimal("1"):
        raise ValueError("fair_value must be between 0 and 1")
    if uncertainty < 0 or adverse < 0:
        raise ValueError("spread widening inputs cannot be negative")

    reservation = _clamp(
        fair - position * config.inventory_skew_per_contract,
        config.min_price,
        config.max_price,
    )
    half_spread = config.base_half_spread + uncertainty + adverse
    bid = _clamp(
        _floor_tick(reservation - half_spread, config.tick_size),
        config.min_price,
        config.max_price,
    )
    ask = _clamp(
        _ceil_tick(reservation + half_spread, config.tick_size),
        config.min_price,
        config.max_price,
    )
    if ask <= bid:
        if bid + config.tick_size <= config.max_price:
            ask = bid + config.tick_size
        else:
            bid = ask - config.tick_size

    inventory_ratio = _clamp(position / config.max_inventory, Decimal("-1"), Decimal("1"))
    bid_size = config.base_size * (Decimal("1") - inventory_ratio)
    ask_size = config.base_size * (Decimal("1") + inventory_ratio)
    return Quote(
        fair_value=fair,
        reservation_price=reservation,
        half_spread=half_spread,
        bid_price=bid,
        ask_price=ask,
        bid_size=bid_size,
        ask_size=ask_size,
        inventory_ratio=inventory_ratio,
    )

