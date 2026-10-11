"""Reconstruct a single-market Kalshi YES/NO order book from WSS messages.

This module is deliberately transport-independent. It accepts decoded messages
so sequence and book-state behavior can be tested without network credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


class OrderBookError(ValueError):
    """Raised when an exchange message cannot safely update the local book."""


class SequenceGapError(OrderBookError):
    """Raised when a message is missing, duplicated, or out of sequence."""


def _number(value: Any, *, field_name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise OrderBookError(f"{field_name} must be a decimal string or number")
    try:
        result = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise OrderBookError(f"invalid {field_name}: {value!r}") from exc
    if not result.is_finite():
        raise OrderBookError(f"{field_name} must be finite")
    return result


@dataclass(frozen=True)
class TopOfBook:
    ticker: str
    yes_bid: Decimal | None
    yes_ask: Decimal | None
    yes_bid_size: Decimal
    no_bid_size: Decimal
    sequence: int
    exchange_timestamp_ms: int | None

    @property
    def midpoint(self) -> Decimal | None:
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return (self.yes_bid + self.yes_ask) / Decimal(2)


@dataclass
class OrderBookReconstructor:
    """Apply one market's snapshot and contiguous deltas in sequence order.

    Subscribe to one ticker per orderbook subscription when using this
    single-book reducer, so each received sequence belongs to this book.
    A gap invalidates the state; a fresh snapshot is required before deltas
    can be applied again.
    """

    ticker: str
    yes_bids: dict[Decimal, Decimal] = field(default_factory=dict)
    no_bids: dict[Decimal, Decimal] = field(default_factory=dict)
    sid: int | None = None
    sequence: int | None = None
    exchange_timestamp_ms: int | None = None
    synced: bool = False

    def apply(self, event: dict[str, Any]) -> TopOfBook | None:
        event_type = event.get("type")
        if event_type == "orderbook_snapshot":
            return self._snapshot(event)
        if event_type == "orderbook_delta":
            return self._delta(event)
        return None

    def _identity(self, event: dict[str, Any]) -> tuple[int, int, dict[str, Any]]:
        msg = event.get("msg")
        if not isinstance(msg, dict):
            raise OrderBookError("message must contain an object in 'msg'")
        if msg.get("market_ticker") != self.ticker:
            raise OrderBookError(
                f"expected ticker {self.ticker!r}, got {msg.get('market_ticker')!r}"
            )
        sid = event.get("sid")
        seq = event.get("seq")
        if isinstance(sid, bool) or not isinstance(sid, int) or sid < 0:
            raise OrderBookError("sid must be a non-negative integer")
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise OrderBookError("seq must be a non-negative integer")
        return sid, seq, msg

    def _snapshot(self, event: dict[str, Any]) -> TopOfBook:
        sid, seq, msg = self._identity(event)
        self.synced = False
        exchange_timestamp_ms = self._timestamp(event)
        new_books: dict[str, dict[Decimal, Decimal]] = {"yes": {}, "no": {}}
        for side in ("yes", "no"):
            levels = msg.get(f"{side}_dollars_fp")
            if not isinstance(levels, list):
                raise OrderBookError(f"snapshot must contain {side}_dollars_fp list")
            for index, level in enumerate(levels):
                if not isinstance(level, list) or len(level) != 2:
                    raise OrderBookError(f"{side} level {index} must be [price, size]")
                price = _number(level[0], field_name=f"{side} level {index} price")
                size = _number(level[1], field_name=f"{side} level {index} size")
                self._validate_price(price)
                if size <= 0:
                    raise OrderBookError(f"{side} level {index} size must be positive")
                if price in new_books[side]:
                    raise OrderBookError(f"duplicate {side} price level {price}")
                new_books[side][price] = size

        self.yes_bids = new_books["yes"]
        self.no_bids = new_books["no"]
        self.sid = sid
        self.sequence = seq
        self.exchange_timestamp_ms = exchange_timestamp_ms
        self.synced = True
        return self.top()

    def _delta(self, event: dict[str, Any]) -> TopOfBook:
        sid, seq, msg = self._identity(event)
        if not self.synced or self.sequence is None or self.sid is None:
            raise OrderBookError("cannot apply a delta before a valid snapshot")
        if sid != self.sid:
            self.synced = False
            raise SequenceGapError(f"subscription changed from sid {self.sid} to {sid}; resnapshot")
        expected = self.sequence + 1
        if seq != expected:
            self.synced = False
            raise SequenceGapError(f"expected seq {expected}, received {seq}; resnapshot")
        # Until every part of this next state transition validates, callers
        # must not mistake the previous book for a current one.
        self.synced = False

        side = msg.get("side")
        if side not in {"yes", "no"}:
            raise OrderBookError("delta side must be 'yes' or 'no'")
        price = _number(msg.get("price_dollars"), field_name="price_dollars")
        delta = _number(msg.get("delta_fp"), field_name="delta_fp")
        self._validate_price(price)
        levels = self.yes_bids if side == "yes" else self.no_bids
        updated_size = levels.get(price, Decimal(0)) + delta
        if updated_size < 0:
            self.synced = False
            raise OrderBookError(
                f"delta would make {side} size negative at {price}; resnapshot required"
            )
        if updated_size == 0:
            levels.pop(price, None)
        else:
            levels[price] = updated_size
        self.sequence = seq
        self.exchange_timestamp_ms = self._timestamp(event)
        self.synced = True
        return self.top()

    @staticmethod
    def _validate_price(price: Decimal) -> None:
        if not Decimal(0) <= price <= Decimal(1):
            raise OrderBookError("binary contract price must be between 0 and 1")

    @staticmethod
    def _timestamp(event: dict[str, Any]) -> int | None:
        value = event.get("sending_ts_ms")
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise OrderBookError("sending_ts_ms must be a non-negative integer")
        return value

    def top(self) -> TopOfBook:
        if not self.synced or self.sequence is None:
            raise OrderBookError("book is not synchronized")
        yes_bid = max(self.yes_bids, default=None)
        best_no_bid = max(self.no_bids, default=None)
        yes_ask = Decimal(1) - best_no_bid if best_no_bid is not None else None
        return TopOfBook(
            ticker=self.ticker,
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            yes_bid_size=self.yes_bids.get(yes_bid, Decimal(0)) if yes_bid is not None else Decimal(0),
            no_bid_size=self.no_bids.get(best_no_bid, Decimal(0)) if best_no_bid is not None else Decimal(0),
            sequence=self.sequence,
            exchange_timestamp_ms=self.exchange_timestamp_ms,
        )
