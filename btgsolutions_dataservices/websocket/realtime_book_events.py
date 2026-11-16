from collections import namedtuple
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
import json
import queue
import time

import pandas as pd

from ..book_by_order import (
    ACTION_LABELS,
    BID,
    CHANGE,
    DELETE,
    DELETE_THRU,
    EVENT_TYPE_LABELS,
    MBO,
    NEW,
    OFFER,
    TMPL_DELETE_ORDER,
    TMPL_EMPTY_BOOK,
    TMPL_MASS_DELETE,
    TMPL_ORDER,
    TMPL_SNAPSHOT_ORDERS,
    VALID_VIEWS,
    BookByOrder,
)
from ..config import BOOK_EVENTS

MAX_TICKERS = 10

# the row shape BookByOrder.apply_row reads (same columns as the historical replay)
_Row = namedtuple(
    "_Row",
    [
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
        "md_entry_datetime",
    ],
)

_Closed = namedtuple("_Closed", ["code", "message"])
_OPENED = object()  # sentinel: the connection for the current attempt has opened


def _close(client: Optional[Any], messages: Optional["queue.Queue[Any]"]) -> None:
    """Close ``client`` and wake up a generator blocked waiting on ``messages``.

    Used both by a ``get_book`` generator's own ``finally`` (closing what it
    created) and by :meth:`RealtimeBookEvents.close` (closing whatever is
    currently the instance's active stream) — never a mix of one generator's
    client with another's queue.
    """
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
    if messages is not None:
        messages.put(_Closed(None, "Closed by close()."))


_SIDES = {"bid": BID, "offer": OFFER}
# book_event "act" -> (tmpl_id, md_update_action)
_ACTS = {
    "new": (TMPL_ORDER, NEW),
    "change": (TMPL_ORDER, CHANGE),
    "delete": (TMPL_DELETE_ORDER, DELETE),
    "mass_delete": (TMPL_MASS_DELETE, DELETE_THRU),
    "empty": (TMPL_EMPTY_BOOK, None),
}


def _timestamp(value: Optional[str]) -> Optional[pd.Timestamp]:
    return pd.Timestamp(value) if value else None


class BookEventsState:
    """Order books of the tickers of one ``book-events`` connection, rebuilt from its messages.

    Network-free: :meth:`handle` takes one decoded server message and returns
    the entries to yield (see :meth:`RealtimeBookEvents.get_book`). Keeps one
    :class:`BookByOrder` per ticker and checks each ticker's ``seq``: on a gap
    the ticker waits for a new snapshot (``request_snapshot`` is called) and
    its events are dropped until it arrives.
    """

    def __init__(
        self,
        view: str = MBO,
        n_levels: int = 5,
        request_snapshot: Optional[Callable[[str], None]] = None,
    ):
        if view not in VALID_VIEWS:
            raise ValueError(f"Invalid 'view': {view!r}. Expected one of: {', '.join(VALID_VIEWS)}.")
        self.view = view
        self.n_levels = n_levels
        self.request_snapshot = request_snapshot
        self.books: Dict[str, BookByOrder] = {}
        self.last_seq: Dict[str, int] = {}
        self.awaiting_snapshot: set = set()
        self.gaps = 0

    def handle(self, msg: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        ev = msg.get("ev")
        if ev == "book_snapshot":
            return [self._snapshot(msg)]
        if ev == "get_last_event":
            if isinstance(msg.get("message"), dict):
                return [self._snapshot(msg["message"])]
            return [("status", {"symbol": None, "status": "snapshot_failed", "message": msg.get("message")})]
        if ev == "book_event":
            return self._event(msg)
        if ev == "book_status":
            return [("status", {
                "symbol": msg.get("symb"),
                "status": msg.get("status"),
                "since_seq": msg.get("sinceSeq"),
                "reason": msg.get("reason"),
                "message": msg.get("message"),
            })]
        # subscribe replies, notices, etc.
        return []

    def _book(self, symbol: str) -> BookByOrder:
        book = self.books.get(symbol)
        if book is None:
            book = self.books[symbol] = BookByOrder(symbol=symbol)
        return book

    def _snapshot(self, msg: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        symbol, seq, rpt_seq = msg["symb"], msg.get("seq", 0), msg.get("rptSeq")
        book = self._book(symbol)
        book.reset()
        for side, orders in ((BID, msg.get("bid") or []), (OFFER, msg.get("offer") or [])):
            for o in orders:
                broker = o.get("firm")
                book.apply_row(_Row(
                    seq, rpt_seq, TMPL_SNAPSHOT_ORDERS, side, None, o["oid"], o.get("px"), o["qty"],
                    broker if side == BID else None, broker if side == OFFER else None, _timestamp(o.get("ts")),
                ))
        self.last_seq[symbol] = seq
        self.awaiting_snapshot.discard(symbol)
        order = {
            "order_id": None, "side": None, "price": None, "size": None, "broker": None,
            "event_type": EVENT_TYPE_LABELS[TMPL_SNAPSHOT_ORDERS], "action": None,
            "seq_num": seq, "rpt_seq": rpt_seq, "timestamp": None,
            "transact_time": None, "end_of_event": True, "prev_size": None,
        }
        return "book", self._entry(symbol, book, order)

    def _event(self, msg: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        symbol, seq = msg["symb"], msg["seq"]
        if symbol in self.awaiting_snapshot:
            return []
        last = self.last_seq.get(symbol)
        if last is None or seq != last + 1:
            # a gap (or an event before any snapshot): the book can't be trusted until a new one
            self.gaps += 1
            self.awaiting_snapshot.add(symbol)
            if self.request_snapshot is not None:
                self.request_snapshot(symbol)
            return [("status", {
                "symbol": symbol, "status": "resyncing", "since_seq": last, "reason": "seq_gap",
                "message": f"Expected seq {None if last is None else last + 1}, got {seq}: waiting for a new snapshot.",
            })]
        tmpl_id, action = _ACTS[msg["act"]]
        side = _SIDES.get(msg.get("side"))
        broker = msg.get("firm")
        row = _Row(
            seq, msg.get("rptSeq"), tmpl_id, side, action, msg.get("oid"), msg.get("px"), msg.get("qty"),
            broker if side == BID else None, broker if side == OFFER else None,
            _timestamp(msg.get("ts") or msg.get("tTime")),
        )
        book = self._book(symbol)
        book.apply_row(row)
        self.last_seq[symbol] = seq
        order = {
            "order_id": row.secondary_order_id, "side": side, "price": row.md_entry_px, "size": row.md_entry_size,
            "broker": broker, "event_type": EVENT_TYPE_LABELS[tmpl_id], "action": ACTION_LABELS.get(action),
            "seq_num": seq, "rpt_seq": row.rpt_seq, "timestamp": row.md_entry_datetime,
            "transact_time": _timestamp(msg.get("tTime")),
            "end_of_event": bool(msg.get("eoe")), "prev_size": msg.get("prevQty"),
        }
        return [("book", self._entry(symbol, book, order))]

    def _entry(self, symbol: str, book: BookByOrder, order: Dict[str, Any]) -> Dict[str, Any]:
        info = book.book_snapshot(view=self.view, n_levels=self.n_levels)
        info["symbol"] = symbol
        info["order"] = order
        return info


class RealtimeBookEvents(object):
    """Realtime order-by-order (market-by-order) book of B3 tickers.

    The realtime counterpart of
    :meth:`btgsolutions_dataservices.TradesAndBookEvents.get_book`
    (book only, no trades): it connects to the ``book-events``
    WebSocket, keeps each ticker's book in a :class:`BookByOrder` (snapshot,
    then every order change) and yields one entry per change, in the same
    shape as the historical ``"book"`` entries.

    Example
    -------
    >>> books = RealtimeBookEvents(api_key="YOUR_API_KEY", data_subtype="stocks")
    >>> for kind, info in books.get_book(["PETR4", "VALE3"], view="mbo", n_levels=5):  # doctest: +SKIP
    ...     if kind == "book":
    ...         print(info["symbol"], info["bid"][:1], info["offer"][:1], info["order"]["action"])
    ...     else:
    ...         print("status:", info)
    >>> books.book("PETR4").top_of_book()  # doctest: +SKIP
    """

    def __init__(self, api_key: str, data_subtype: str = "stocks"):
        """
        Parameters
        ----------
        api_key:
            Data Services API key (its key must allow the ``book-events`` route).
        data_subtype:
            ``"stocks"``, ``"options"`` or ``"derivatives"``.

        The server's TLS certificate is always verified.
        """
        if not api_key:
            raise ValueError("Must provide a valid 'api_key' parameter")
        self.api_key = api_key
        self.data_subtype = data_subtype
        self.state: Optional[BookEventsState] = None
        self.client = None
        self.messages: Optional["queue.Queue[Any]"] = None

    def get_book(
        self,
        tickers: List[str],
        view: str = MBO,
        n_levels: int = 5,
        timeout: Optional[float] = None,
        reconnect: bool = True,
        max_reconnects: int = 5,
    ) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Subscribe to ``tickers`` and stream their books as they change.

        A generator: the connection opens when you start iterating it and
        closes when you stop (``break``, or :meth:`close`).

        Parameters
        ----------
        tickers:
            Up to 10 tickers.
        view:
            ``"mbo"`` (top orders per side, ``(order_id, price, size, broker)``)
            or ``"mbp"`` (top price levels, ``(price, total_size)``), as in
            :meth:`BookByOrder.book_snapshot`.
        n_levels:
            Orders/levels per side in each entry.
        timeout:
            Stop when nothing arrives for this many seconds (``None``: never).
            Not checked while a connection attempt is itself in progress
            (that wait is bounded by the client's own ``connect_timeout``,
            10s by default) — only between attempts — so the actual silence
            before stopping can exceed ``timeout`` by up to that much during
            a reconnect.
        reconnect:
            ``True`` (default): on a disconnect, reconnect with an
            exponential backoff (1s, 2s, 4s, ... capped at 30s) for up to
            ``max_reconnects`` consecutive failed attempts in a row — the
            count resets on every successful connection. ``False``: a
            disconnect yields ``"disconnected"`` and the generator ends
            right there; reconnecting (or not) is then entirely up to the
            caller.
        max_reconnects:
            Consecutive failed reconnect attempts allowed before giving up
            (``"reconnect_failed"``, then the generator ends). Ignored when
            ``reconnect=False``.

        Yields
        ------
        tuple[str, dict]
            ``("book", {"symbol", "bid", "offer", "order", "queued"})`` for
            each snapshot (``order["event_type"] == "snapshot"``) and each
            order change (``"order"``, ``"delete_order"``, ``"mass_delete"``,
            ``"empty_book"``); ``order`` has the same keys as the historical
            ``get_book`` (``seq_num`` is the WebSocket's per-ticker sequence)
            (``timestamp`` is the order's insert time) plus ``transact_time``
            (the exchange's time of the change), ``end_of_event`` (last change
            of an exchange event) and ``prev_size`` (on a ``CHANGE``).
            ``queued`` is how many messages were already waiting, right
            behind this one, when it was taken off the queue — it has
            nothing to do with the exchange/server, only with how this
            process is keeping up locally. Near 0 means the loop body is
            keeping up with the feed; if it keeps growing, whatever runs
            inside the loop is slower than the feed itself. Since the book
            kept in memory (:meth:`book`) is always current regardless of
            what a particular iteration does with it, a common pattern for
            heavy per-entry work is to only do it when ``queued == 0``
            (skipping an entry never skips the event in the book — only the
            reaction to it): ``if info["queued"] == 0: heavy_work(info)``.
            ``("status", {"symbol", "status", "since_seq", "reason", "message"})``
            (no ``queued``) when a book's status changes: ``"suspect"``/
            ``"ok"``/``"waiting_snapshot"``/``"resyncing"`` from the server
            (e.g. the exchange sent a new snapshot and the book restarts at
            ``seq`` 0), ``"resyncing"`` with ``reason="seq_gap"`` on a gap in
            ``seq`` detected by this client (a new snapshot is requested),
            ``"snapshot_failed"`` when a requested snapshot is refused (e.g.
            unknown ticker), ``"disconnected"`` whenever the connection ends
            — ``reason``/``message`` are the server's own close code/reason
            when it sends one, else a generic message. What follows a
            ``"disconnected"`` depends on ``reconnect``: with
            ``reconnect=False``, or if :meth:`close` was called, the
            generator ends right there. With ``reconnect=True``: either
            ``{"status": "reconnected", "attempt": n, ...}`` once a new
            connection opens (every book comes back as a new snapshot — the
            book kept in memory is stale until then), or, once
            ``max_reconnects`` consecutive attempts have all failed,
            ``{"status": "reconnect_failed", "attempts": n, ...}`` and the
            generator ends.
        """
        if not tickers or len(tickers) > MAX_TICKERS:
            raise ValueError(f"'tickers' must have between 1 and {MAX_TICKERS} tickers")
        if max_reconnects < 0:
            raise ValueError("'max_reconnects' must be >= 0")
        from .market_data_websocket_client import MarketDataWebSocketClient

        # kept local (not just on self): a second get_book() on this same instance replaces
        # self.client/self.messages/self.state, and this generator's own cleanup (finally,
        # below) must only ever touch the client and queue it created, never a later one.
        messages: "queue.Queue[Any]" = queue.Queue()
        self.messages = messages
        client = MarketDataWebSocketClient(
            api_key=self.api_key,
            data_type=BOOK_EVENTS,
            data_subtype=self.data_subtype,
            instruments=list(tickers),
        )
        self.client = client
        state = BookEventsState(view=view, n_levels=n_levels, request_snapshot=client.request_snapshot)
        self.state = state

        def _connect() -> None:
            client.run(
                on_open=lambda: messages.put(_OPENED),
                on_message=messages.put,
                on_error=lambda error: None,
                on_close=lambda code, msg: messages.put(_Closed(code, msg)),
                reconnect=False,  # get_book() is the one deciding whether/when to reconnect
                spawn_thread=False,  # one thread, so messages are handled in the order they arrive
                default_logs=False,
            )

        _connect()
        failed_attempts = 0  # consecutive failures since the last successful open
        next_attempt_at: Optional[float] = None
        last = time.monotonic()
        try:
            while True:
                try:
                    raw = messages.get(timeout=1.0)
                except queue.Empty:
                    now = time.monotonic()
                    if timeout is not None and now - last >= timeout:
                        return
                    if next_attempt_at is not None and now >= next_attempt_at:
                        next_attempt_at = None
                        _connect()
                    continue
                last = time.monotonic()

                if raw is _OPENED:
                    # a reconnection only if a failure (tracked below) preceded this open —
                    # not just whether *some* earlier connection in this call ever succeeded,
                    # since the very first attempt can itself fail-then-retry-then-open
                    attempt_number = failed_attempts
                    failed_attempts = 0
                    if attempt_number > 0:
                        yield "status", {
                            "symbol": None, "status": "reconnected", "since_seq": None, "reason": None,
                            "attempt": attempt_number,
                            "message": "Connection restored: every book comes again as a new snapshot.",
                        }
                    continue

                if isinstance(raw, _Closed):
                    yield "status", {
                        "symbol": None, "status": "disconnected", "since_seq": None, "reason": raw.code,
                        "message": raw.message or "Connection closed.",
                    }
                    if getattr(client, "_closed", False) or not reconnect:
                        # closed on purpose, or the caller doesn't want reconnection: done
                        return
                    failed_attempts += 1
                    if failed_attempts > max_reconnects:
                        yield "status", {
                            "symbol": None, "status": "reconnect_failed", "since_seq": None, "reason": None,
                            "attempts": failed_attempts - 1,
                            "message": f"Gave up after {max_reconnects} consecutive failed reconnect attempts.",
                        }
                        return
                    next_attempt_at = time.monotonic() + min(2 ** (failed_attempts - 1), 30)
                    continue

                queued = messages.qsize()
                try:
                    msg = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                for kind, info in state.handle(msg):
                    if kind == "book":
                        info["queued"] = queued
                    yield kind, info
        finally:
            _close(client, messages)

    def book(self, ticker: str) -> Optional[BookByOrder]:
        """Current :class:`BookByOrder` of a ticker (``None`` before its first snapshot)."""
        return self.state.books.get(ticker) if self.state else None

    def close(self) -> None:
        """Close the current stream and wake up a running :meth:`get_book`.

        Safe to call from another thread while ``get_book`` is being
        iterated elsewhere: it unblocks the generator immediately (instead
        of leaving it waiting on network messages that will never come) so
        it yields a final ``"disconnected"`` status entry and returns.
        """
        _close(self.client, self.messages)
