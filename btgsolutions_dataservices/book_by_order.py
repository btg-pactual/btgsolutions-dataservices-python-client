from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple
import math

import pandas as pd
from sortedcontainers import SortedDict

BID, OFFER = "BID", "OFFER"

# md_update_action (tag 279)
NEW, CHANGE, DELETE, DELETE_THRU = 0, 1, 2, 3

TMPL_SNAPSHOT_ORDERS = 71
TMPL_ORDER = 50
TMPL_DELETE_ORDER = 51
TMPL_MASS_DELETE = 52
TMPL_EMPTY_BOOK = 9
TMPL_TRADE = 53

# tmpl_ids that mutate the order book state
BOOK_TMPL_IDS = (TMPL_EMPTY_BOOK, TMPL_ORDER, TMPL_DELETE_ORDER, TMPL_MASS_DELETE, TMPL_SNAPSHOT_ORDERS)
# tmpl_ids that describe a trade and never touch the book state
# (ExecutionSummary rows are intentionally excluded from both sets: they are
# neither book nor trade for this engine's purposes, so they're just skipped)
TRADE_TMPL_IDS = (TMPL_TRADE,)

# human-readable labels for info["event_type"] (flat) / info["order"]["event_type"] (nested)
EVENT_TYPE_LABELS = {
    TMPL_EMPTY_BOOK: "empty_book",
    TMPL_ORDER: "order",
    TMPL_DELETE_ORDER: "delete_order",
    TMPL_MASS_DELETE: "mass_delete",
    TMPL_SNAPSHOT_ORDERS: "snapshot",
    TMPL_TRADE: "trade",
}

# human-readable labels for info["action"] / info["order"]["action"] (md_update_action, tag 279)
ACTION_LABELS = {
    NEW: "NEW",
    CHANGE: "CHANGE",
    DELETE: "DELETE",
    DELETE_THRU: "DELETE_THRU",
}

MBO, MBP = "mbo", "mbp"
VALID_VIEWS = (MBO, MBP)

_REPLAY_COLUMNS = [
    "seq_num",
    "rpt_seq",
    "tmpl_id",
    "md_entry_type",
    "md_update_action",
    "secondary_order_id",
    "md_entry_px",
    "md_entry_size",
    "buyer",
    "seller",
]


def _is_missing_price(price: Optional[float]) -> bool:
    return price is None or (isinstance(price, float) and math.isnan(price))


class _PriceLevel:
    """Orders resting at a single price, ordered by priority (FIFO by order_id).

    Follows B3's UMDF book priority rules (price, then order priority).
    ``total_size`` is maintained incrementally so market-by-price queries
    never need to re-sum the level's orders.
    """

    __slots__ = ("total_size", "orders")

    def __init__(self) -> None:
        self.total_size = 0
        self.orders: "SortedDict[int, Tuple[float, int, Optional[Any]]]" = SortedDict()

    def insert(self, order_id: int, price: float, size: int, broker: Optional[Any]) -> None:
        old = self.orders.get(order_id)
        self.orders[order_id] = (price, size, broker)
        self.total_size += size - (old[1] if old is not None else 0)

    def remove(self, order_id: int) -> Optional[Tuple[float, int, Optional[Any]]]:
        old = self.orders.pop(order_id, None)
        if old is not None:
            self.total_size -= old[1]
        return old

    def is_empty(self) -> bool:
        return not self.orders


class _BookSide:
    """One side (BID or OFFER) of the book: price levels ordered by price.

    Price levels are kept in a tree ordered by price, so "best N price
    levels" or "best N orders" is a bounded walk from one end of the tree
    (``O(n)`` for the ``n`` requested) instead of a full scan and sort of
    every live order on every query.

    Orders without a usable price (e.g. market orders) can't be used as a
    ``SortedDict`` key, so they're kept in a dedicated bucket that is always
    visited first, matching B3's priority rule: missing-price orders have
    priority over every priced level.
    """

    __slots__ = ("levels", "no_price_level", "reverse")

    def __init__(self, reverse: bool) -> None:
        self.levels: "SortedDict[float, _PriceLevel]" = SortedDict()
        self.no_price_level = _PriceLevel()
        self.reverse = reverse  # True for BID: best = highest price

    def insert(self, price: float, order_id: int, size: int, broker: Optional[Any]) -> None:
        if _is_missing_price(price):
            self.no_price_level.insert(order_id, price, size, broker)
            return
        level = self.levels.get(price)
        if level is None:
            level = _PriceLevel()
            self.levels[price] = level
        level.insert(order_id, price, size, broker)

    def remove(self, price: float, order_id: int) -> None:
        if _is_missing_price(price):
            self.no_price_level.remove(order_id)
            return
        level = self.levels.get(price)
        if level is None:
            return
        level.remove(order_id)
        if level.is_empty():
            del self.levels[price]

    def clear(self) -> None:
        self.levels.clear()
        self.no_price_level = _PriceLevel()

    def _ordered_levels(self) -> Iterator[_PriceLevel]:
        if self.no_price_level.orders:
            yield self.no_price_level
        values = self.levels.values()
        yield from (reversed(values) if self.reverse else values)

    def ordered_orders(self, n: Optional[int] = None) -> List[Tuple[int, float, int, Optional[Any]]]:
        """Top ``n`` orders best-first, walking only as many levels as needed."""
        result: List[Tuple[int, float, int, Optional[Any]]] = []
        for level in self._ordered_levels():
            for order_id, (price, size, broker) in level.orders.items():
                result.append((order_id, price, size, broker))
                if n is not None and len(result) >= n:
                    return result
        return result

    def ordered_price_levels(self, n: Optional[int] = None) -> List[Tuple[float, int]]:
        """Top ``n`` priced levels best-first (the no-price bucket is excluded:
        it has no single meaningful price to aggregate under)."""
        result: List[Tuple[float, int]] = []
        items = self.levels.items()
        for price, level in reversed(items) if self.reverse else items:
            result.append((price, level.total_size))
            if n is not None and len(result) >= n:
                return result
        return result


class BookByOrder(object):
    """Order-by-order (market-by-order) limit order book replay engine.

    ``BookByOrder`` consumes the trades-and-book-events stream returned by
    :class:`btgsolutions_dataservices.rest.trades_and_book_events.TradesAndBookEvents`
    and replays it to reconstruct the book's current state. Internally, each
    side is kept as a price-ordered tree of price levels, so both
    market-by-order and market-by-price top-N queries are bounded by the
    number of entries requested, not by how many orders are live.

    Orders are identified by ``secondary_order_id``. Within the same price,
    a lower ``secondary_order_id`` has higher priority (FIFO).

    Example
    -------
    >>> book = BookByOrder(symbol="PETR4")
    >>> book.replay(events)  # doctest: +SKIP
    >>> book.top_of_book()  # doctest: +SKIP
    {'best_bid': (..., ..., ..., ...), 'best_offer': (..., ..., ..., ...)}
    """

    def __init__(self, symbol: str):
        """Create an empty book for a symbol.

        Parameters
        ----------
        symbol:
            Ticker symbol this book replays events for.
        """
        self.symbol = symbol
        self.orders: Dict[int, Tuple[str, float, int, Optional[Any]]] = {}
        self.bids = _BookSide(reverse=True)
        self.offers = _BookSide(reverse=False)
        self.last_seq_num: Optional[int] = None
        self.last_rpt_seq: Optional[int] = None
        self.events_applied = 0
        self.events_skipped = 0

    def reset(self) -> None:
        """Clear all orders and price levels (both sides)."""
        self.orders.clear()
        self.bids.clear()
        self.offers.clear()

    def _book_side(self, side: str) -> _BookSide:
        return self.bids if side == BID else self.offers

    def _upsert(self, order_id: int, side: str, price: float, size: int, broker: Optional[Any]) -> None:
        old = self.orders.get(order_id)
        if old is not None:
            self._book_side(old[0]).remove(old[1], order_id)
        self.orders[order_id] = (side, price, size, broker)
        self._book_side(side).insert(price, order_id, size, broker)

    def _remove(self, order_id: int) -> None:
        old = self.orders.pop(order_id, None)
        if old is not None:
            self._book_side(old[0]).remove(old[1], order_id)

    def _clear_side(self, side: str) -> None:
        to_remove = [oid for oid, o in self.orders.items() if o[0] == side]
        for oid in to_remove:
            del self.orders[oid]
        self._book_side(side).clear()

    def apply_row(self, row) -> None:
        """Apply a single event row to the book's state.

        Parameters
        ----------
        row:
            A namedtuple/row exposing ``tmpl_id``, ``md_entry_type``,
            ``md_update_action``, ``secondary_order_id``, ``md_entry_px``,
            ``md_entry_size``, ``buyer``, ``seller``, ``seq_num`` and
            ``rpt_seq`` (as produced by
            ``DataFrame[_REPLAY_COLUMNS].itertuples(index=False)``). The
            broker of each order (``entering_firm``) comes in ``buyer`` for
            ``BID`` rows and ``seller`` for ``OFFER`` rows, sharing those
            columns with trade counterparty ids on ``"trade"`` rows.
        """
        tmpl_id = row.tmpl_id

        if tmpl_id == TMPL_EMPTY_BOOK:
            self.reset()

        elif tmpl_id == TMPL_MASS_DELETE:
            self._clear_side(row.md_entry_type)

        elif tmpl_id == TMPL_DELETE_ORDER:
            self._remove(row.secondary_order_id)

        elif tmpl_id in (TMPL_ORDER, TMPL_SNAPSHOT_ORDERS):
            # a snapshot has no md_update_action (always a bootstrap, equivalent to NEW)
            if tmpl_id == TMPL_SNAPSHOT_ORDERS or row.md_update_action in (NEW, CHANGE):
                broker = self._field(row, "buyer" if row.md_entry_type == BID else "seller")
                self._upsert(row.secondary_order_id, row.md_entry_type, row.md_entry_px, row.md_entry_size, broker)
            else:
                self.events_skipped += 1
                return

        else:
            # messages that don't affect the book (Trade, ExecutionSummary, etc)
            self.events_skipped += 1
            return

        self.events_applied += 1
        self.last_seq_num = row.seq_num
        if not pd.isna(row.rpt_seq):
            self.last_rpt_seq = row.rpt_seq

    def replay(self, df: pd.DataFrame) -> "BookByOrder":
        """Replay a DataFrame of events into this book.

        This is a building block used internally by
        :meth:`btgsolutions_dataservices.rest.trades_and_book_events.TradesAndBookEvents.get_book`.
        Prefer calling ``get_book`` directly unless you already have an
        events DataFrame from another source.

        Parameters
        ----------
        df:
            Events DataFrame with the same columns consumed by
            :meth:`apply_row`.

        Returns
        -------
        BookByOrder
            ``self``, for chaining.
        """
        for row in df[_REPLAY_COLUMNS].itertuples(index=False):
            self.apply_row(row)
        return self

    def replay_stream(
        self,
        batches: Iterable[pd.DataFrame],
    ) -> "BookByOrder":
        """Replay an iterable of event chunks into this book.

        This is a building block used internally by
        :meth:`btgsolutions_dataservices.rest.trades_and_book_events.TradesAndBookEvents.get_book`
        to reconstruct a book without ever holding the full event stream in
        memory at once — only one chunk (``batch_size`` rows) is materialized
        at a time. Prefer calling ``get_book`` directly unless you already
        have your own chunked source of events.

        Parameters
        ----------
        batches:
            An iterable (typically a generator) of event DataFrames, each
            with the same columns as the DataFrame accepted by
            :meth:`replay`.

        Returns
        -------
        BookByOrder
            ``self``, for chaining.
        """
        for batch in batches:
            for row in batch[_REPLAY_COLUMNS].itertuples(index=False):
                self.apply_row(row)
        return self

    def book_snapshot(self, view: str = MBO, n_levels: int = 5) -> Dict[str, List[Tuple]]:
        """Return the current top-of-book levels for both sides.

        Parameters
        ----------
        view:
            ``"mbo"`` (market-by-order): top ``n_levels`` individual orders
            per side, as ``(order_id, price, size, broker)`` — ``broker`` is
            the entering firm id for that order (``None`` if missing), and
            aggregating it would require picking one value per price level so
            it is only available per-order, not in ``"mbp"``. ``"mbp"``
            (market-by-price): top ``n_levels`` aggregated price levels per
            side, as ``(price, total_size)``.
        n_levels:
            Number of entries to return per side.

        Returns
        -------
        dict
            ``{"bid": [...], "offer": [...]}`` in the shape determined by
            ``view``.

        Raises
        ------
        ValueError
            If ``view`` is not one of ``"mbo"``/``"mbp"``.
        """
        if view not in VALID_VIEWS:
            allowed = ", ".join(VALID_VIEWS)
            raise ValueError(f"Invalid 'view': {view!r}. Expected one of: {allowed}.")

        if view == MBP:
            return {
                "bid": self.depth_by_price(BID, n_levels),
                "offer": self.depth_by_price(OFFER, n_levels),
            }

        return {
            "bid": self.side_orders(BID, n=n_levels),
            "offer": self.side_orders(OFFER, n=n_levels),
        }

    @staticmethod
    def _field(row, name: str) -> Optional[Any]:
        value = getattr(row, name, None)
        if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
            return None
        return value

    @classmethod
    def _event_fields(cls, row) -> Dict[str, Any]:
        """Fields describing the triggering row's place in the stream.

        Common to both ``"book"`` and ``"trade"`` entries: ``event_type``
        always identifies which kind of message the row was; ``action`` is
        the translated ``md_update_action``, ``None`` when the message
        doesn't carry one (e.g. ``"trade"``, ``"snapshot"``,
        ``"empty_book"``).
        """
        action = cls._field(row, "md_update_action")
        return {
            "event_type": EVENT_TYPE_LABELS.get(row.tmpl_id),
            "action": ACTION_LABELS.get(action),
            "seq_num": row.seq_num,
            "rpt_seq": cls._field(row, "rpt_seq"),
            "timestamp": cls._field(row, "md_entry_datetime"),
        }

    @classmethod
    def _order_info(cls, row) -> Dict[str, Any]:
        """Fully describe the single order/event that caused a ``"book"`` entry.

        Besides the common :meth:`_event_fields`, every order-specific field
        is pulled straight from the triggering row and is ``None`` when that
        row's ``tmpl_id`` doesn't carry it (e.g. ``TMPL_MASS_DELETE`` has a
        ``side`` but no ``order_id``/``price``/``size``; ``TMPL_EMPTY_BOOK``
        has none of them).
        """
        side = cls._field(row, "md_entry_type")
        broker = None
        if side == BID:
            broker = cls._field(row, "buyer")
        elif side == OFFER:
            broker = cls._field(row, "seller")
        return {
            **cls._event_fields(row),
            "order_id": cls._field(row, "secondary_order_id"),
            "side": side,
            "price": cls._field(row, "md_entry_px"),
            "size": cls._field(row, "md_entry_size"),
            "broker": broker,
        }

    @classmethod
    def _trade_info(cls, row) -> Dict[str, Any]:
        price = cls._field(row, "last_px")
        if price is None:
            price = cls._field(row, "md_entry_px")
        size = cls._field(row, "fill_qty")
        if size is None:
            size = cls._field(row, "md_entry_size")
        return {
            **cls._event_fields(row),
            "side": cls._field(row, "md_entry_type"),
            "trade_id": cls._field(row, "trade_id"),
            "price": price,
            "size": size,
            "buyer": cls._field(row, "buyer"),
            "seller": cls._field(row, "seller"),
        }

    def replay_classified(
        self,
        batches: Iterable[pd.DataFrame],
        view: str = MBO,
        n_levels: int = 5,
    ) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Replay event chunks, yielding a classified ``(kind, info)`` per row.

        This is the engine behind
        :meth:`btgsolutions_dataservices.rest.trades_and_book_events.TradesAndBookEvents.get_book`:
        it consumes chunks of events (as produced by ``iter_batches``-style
        sources), applies book-affecting rows to this book's state, and
        yields one entry per row so a caller can react to each line as it is
        processed — without ever loading the full event stream at once.

        Parameters
        ----------
        batches:
            An iterable (typically a generator) of event DataFrames in
            non-decreasing ``seq_num`` order, with the trade-related columns
            (``trade_id``, ``last_px``, ``fill_qty``, ``buyer``, ``seller``)
            and timestamp columns (``md_entry_datetime``, ``sending_time``)
            available alongside the usual book columns.
        view:
            Passed to :meth:`book_snapshot` for every ``"book"`` entry:
            ``"mbo"`` (order-by-order) or ``"mbp"`` (aggregated by price).
        n_levels:
            Passed to :meth:`book_snapshot`: how many levels/orders per side
            to include in each ``"book"`` entry.

        Yields
        ------
        tuple[str, dict]
            ``("book", info)`` for rows that mutate the order book
            (new/change/delete/mass-delete/empty-book/snapshot), or
            ``("trade", info)`` for trade rows. ExecutionSummary rows and
            any other unrecognized ``tmpl_id`` are counted in
            ``events_skipped`` and produce no entry.

            For ``"book"``, ``info`` is ``book_snapshot`` (``{"bid": [...],
            "offer": [...]}``) plus an ``"order"`` key fully describing the
            single event that caused this entry: ``{"order_id", "side",
            "price", "size", "broker", "event_type", "action", "seq_num",
            "rpt_seq", "timestamp"}``. For ``"trade"``, ``info`` is
            ``{"side", "trade_id", "price", "size", "buyer", "seller",
            "event_type", "action", "seq_num", "rpt_seq", "timestamp"}`` —
            the same stream-position fields, flat at the top level since
            there's no separate aggregate snapshot to distinguish them from.

            In both cases: ``event_type`` is one of ``"empty_book"``,
            ``"order"``, ``"delete_order"``, ``"mass_delete"``,
            ``"snapshot"``, ``"trade"`` and is always present; ``action`` is
            the translated ``md_update_action`` (``"NEW"``/``"CHANGE"``/
            ``"DELETE"``/``"DELETE_THRU"``) when present, else ``None``
            (e.g. for ``"snapshot"``/``"empty_book"``); order-specific
            fields (``order_id``/``side``/``price``/``size``/``broker``)
            are ``None`` when the triggering row's ``tmpl_id`` doesn't carry
            them (e.g. ``"mass_delete"`` has ``side`` but no ``order_id``;
            ``"empty_book"`` has none of them).
        """
        if view not in VALID_VIEWS:
            allowed = ", ".join(VALID_VIEWS)
            raise ValueError(f"Invalid 'view': {view!r}. Expected one of: {allowed}.")

        for batch in batches:
            for row in batch.itertuples(index=False):
                if row.tmpl_id in TRADE_TMPL_IDS:
                    yield "trade", self._trade_info(row)
                elif row.tmpl_id in BOOK_TMPL_IDS:
                    self.apply_row(row)
                    info = self.book_snapshot(view=view, n_levels=n_levels)
                    info["order"] = self._order_info(row)
                    yield "book", info
                else:
                    self.events_skipped += 1

    def side_orders(self, side: str, n: Optional[int] = None) -> List[Tuple[int, float, int, Optional[Any]]]:
        """List ``(order_id, price, size, broker)`` for a side, sorted by priority.

        Priority is by price first (best price wins), then by
        ``secondary_order_id`` (FIFO within the same price). ``broker`` is
        the entering firm id for that order (``None`` if the source row had
        no ``buyer``/``seller`` value for it).

        Parameters
        ----------
        side:
            ``"BID"`` or ``"OFFER"``.
        n:
            If given, only the top ``n`` orders are returned. This walks the
            side's price-ordered levels from the best price, stopping as
            soon as ``n`` orders are collected — ``O(n)`` in the number of
            orders/levels actually visited, not in how many orders are live
            on the side. If omitted, every order on the side is returned.
        """
        return self._book_side(side).ordered_orders(n)

    def book_df(self, side: str, depth: Optional[int] = None) -> pd.DataFrame:
        """Return the order-by-order book for a side as a DataFrame.

        Parameters
        ----------
        side:
            ``"BID"`` or ``"OFFER"``.
        depth:
            If given, only the top ``depth`` orders (by priority) are returned.
        """
        items = self.side_orders(side, n=depth)
        return pd.DataFrame(items, columns=["secondary_order_id", "price", "size", "broker"])

    def top_of_book(self) -> Dict[str, Optional[Tuple[int, float, int, Optional[Any]]]]:
        """Return the best bid and best offer orders.

        Returns
        -------
        dict
            ``{"best_bid": (order_id, price, size, broker) or None, "best_offer": (...) or None}``.
        """
        bids = self.side_orders(BID, n=1)
        offers = self.side_orders(OFFER, n=1)
        best_bid = bids[0] if bids else None
        best_offer = offers[0] if offers else None
        return {"best_bid": best_bid, "best_offer": best_offer}

    def depth_by_price(self, side: str, n_levels: int = 5) -> List[Tuple[float, int]]:
        """Return aggregated size totals per price level (book-by-price/MBP view).

        Parameters
        ----------
        side:
            ``"BID"`` or ``"OFFER"``.
        n_levels:
            Number of price levels to return, best price first. This walks
            the side's price-ordered levels from the best price, stopping
            once ``n_levels`` are collected — ``O(n_levels)``, not in how
            many price levels are active.

        Returns
        -------
        list[tuple[float, int]]
            ``(price, total_size)`` pairs, best price first.
        """
        pairs = self._book_side(side).ordered_price_levels(n_levels)
        return [(round(price, 2), total_size) for price, total_size in pairs]

    def __len__(self) -> int:
        return len(self.orders)
