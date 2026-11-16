from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
import json
import tempfile

import pandas as pd
import pyarrow.parquet as pq
import requests

from ..book_by_order import MBO, BookByOrder
from ..config import url_apis_v3
from ..exceptions import BadResponse
from .authenticator import Authenticator

DEFAULT_BATCH_SIZE = 10_000
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
BOUNDARY_FIELDS = ("timestamp", "seq_num", "rpt_seq")
BOUNDARY_MODES = ("until", "after")


class TradesAndBookEvents(object):
    """Client for the Bulk Data v3 trades-and-book-events endpoint.

    ``TradesAndBookEvents`` fetches the raw order-by-order event stream
    (trades, order adds/changes/deletes, mass deletes, book resets and
    snapshots) for a ticker and date, and ``get_book`` replays it as a
    generator: one ``(kind, info)`` pair per event row, where ``kind`` is
    ``"book"`` or ``"trade"`` (ExecutionSummary rows are dropped) and
    ``info`` is the kind-specific payload — it always carries
    ``seq_num``/``rpt_seq``/``timestamp``/``event_type``/``action`` too,
    flat at the top level for ``"trade"`` or nested under ``info["order"]``
    for ``"book"`` (alongside the ``bid``/``offer`` snapshot). The raw event
    stream is never exposed as a single, fully-materialized DataFrame:
    internally it is streamed in bounded-size chunks, so peak memory stays
    low regardless of how much volume the ticker/date has.

    Example
    -------
    >>> client = TradesAndBookEvents(api_key="YOUR_API_KEY")
    >>> for kind, info in client.get_book(ticker="PETR4", date="2026-05-15"):  # doctest: +SKIP
    ...     if kind == "trade":
    ...         print("trade:", info)
    ...     else:
    ...         print("book:", info)
    """

    def __init__(self, api_key: Optional[str]):
        """Create a Trades and Book Events client.

        Parameters
        ----------
        api_key:
            Data Services API key. The key is exchanged for a bearer-like access
            token by :class:`Authenticator`.

        Raises
        ------
        ValueError
            If ``api_key`` is empty.
        BadResponse
            If authentication fails.
        """
        if not api_key:
            raise ValueError("Must provide a valid 'api_key' parameter")

        self.api_key = api_key
        self.url_apis_v3 = url_apis_v3
        self.authenticator = Authenticator(self.api_key)

    @property
    def token(self) -> str:
        """Current access token, refreshed automatically near expiration."""
        return self.authenticator.token

    @property
    def headers(self) -> Dict[str, str]:
        """Request headers for the current token.

        The property rebuilds the header each time so long-lived clients pick up
        refreshed authenticator tokens.
        """
        return {"authorization": f"authorization {self.token}"}

    @staticmethod
    def _raise_bad_response(response: requests.Response) -> None:
        try:
            body = response.json() if response.content else {}
        except ValueError:
            try:
                body = json.loads(response.text)
            except ValueError:
                body = {}
        message = body.get("ApiClientError") or body.get("ApiServerMessage") or getattr(response, "reason", "") or ""
        raise BadResponse(
            f'Error {response.status_code}: {message}.\n{body.get("SuggestedAction", "")}'
        )

    def _iter_batches(
        self,
        ticker: str,
        date: str,
        batch_size: int,
    ) -> Iterator[pd.DataFrame]:
        """Stream the trades-and-book-events for a ticker and date in chunks.

        The HTTP response is streamed to a temporary file on disk, then read
        back row-group by row-group with :class:`pyarrow.parquet.ParquetFile`,
        yielding at most ``batch_size`` rows per chunk. Peak memory is bounded
        by ``batch_size`` (plus one download chunk), regardless of how large
        the event stream is.

        Events within the file are assumed to already be stored in
        non-decreasing ``seq_num`` order (the bulk data feed is an
        append-only log); each chunk is defensively stable-sorted by
        ``seq_num``/``rpt_seq`` on its own, but no global re-sort across
        chunks is performed.

        Raises
        ------
        BadResponse
            If the API returns a non-200 response.
        """
        response = requests.request(
            "GET",
            f"{self.url_apis_v3}/marketdata/bulkdata/events",
            headers=self.headers,
            params={"ticker": ticker, "date": date},
            stream=True,
        )
        if response.status_code != 200:
            self._raise_bad_response(response)

        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp_file:
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                tmp_file.write(chunk)
            tmp_file.flush()

            parquet_file = pq.ParquetFile(tmp_file.name)
            for record_batch in parquet_file.iter_batches(batch_size=batch_size):
                yield record_batch.to_pandas().sort_values(
                    ["seq_num", "rpt_seq"], kind="stable"
                ).reset_index(drop=True)

    def get_book(
        self,
        ticker: str,
        date: str,
        view: str = MBO,
        n_levels: int = 5,
        batch_size: int = DEFAULT_BATCH_SIZE,
        boundary: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    ) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Fetch a ticker/date's events and stream them as a classified book.

        This is the only way this client exposes event data: the raw stream
        is fetched and consumed internally, in chunks of at most
        ``batch_size`` rows, and only a classified ``(kind, info)`` per row
        is yielded — the raw per-row DataFrame is never exposed. This is a
        generator: nothing is fetched until you start iterating it.

        Parameters
        ----------
        ticker:
            Ticker symbol, e.g. ``"PETR4"``.
        date:
            Date in ``YYYY-MM-DD`` format.
        view:
            Shape of every ``"book"`` entry: ``"mbo"`` (market-by-order, top
            individual orders per side) or ``"mbp"`` (market-by-price,
            aggregated totals per price level). See
            :meth:`btgsolutions_dataservices.book_by_order.BookByOrder.book_snapshot`.
        n_levels:
            Number of levels/orders per side included in every ``"book"``
            entry.
        batch_size:
            Maximum number of rows kept in memory per processed chunk.
            Defaults to ``10_000``.
        boundary:
            Optional ``{"field": ..., "value": ..., "mode": ...}`` dict, or a
            list of such dicts, that restricts which events are *yielded*
            (the book is always replayed from the very first event, so its
            state stays correct regardless of where the boundary cuts in).
            When a list is given, every condition must hold for a row to be
            yielded (logical AND) — e.g. a range between two timestamps is
            ``[{"field": "timestamp", "value": start, "mode": "after"},
            {"field": "timestamp", "value": end, "mode": "until"}]``;
            conditions don't need to share the same ``field``, so a
            ``seq_num`` floor combined with a ``timestamp`` ceiling also
            works.

            Each condition:

            - ``field``: ``"timestamp"``, ``"seq_num"`` or ``"rpt_seq"`` —
              which field the boundary compares against (``info["order"][field]``
              for ``"book"`` entries, ``info[field]`` for ``"trade"`` entries).
            - ``value``: the reference value. For ``field="timestamp"`` it is
              parsed with :class:`pandas.Timestamp`; anything accepted by it
              (e.g. ``"2026-11-03 14:30:00"``) works.
            - ``mode``: ``"until"`` yields events up to and including
              ``value``. ``"after"`` skips events up to and including
              ``value`` and yields only the ones strictly past it. Events
              where the compared field is ``None`` (e.g. a row missing a
              timestamp) are skipped regardless of mode, since they can't be
              placed relative to ``value``.

            Iteration stops as soon as any single ``"until"`` condition is
            passed (no further batches are processed) — safe because the
            stream is non-decreasing, so once a field's value is past an
            ``"until"`` threshold it stays past it for every later row.

        Yields
        ------
        tuple[str, dict]
            ``("book", {"bid": [...], "offer": [...], "order": {...}})`` for
            rows that change the order book — each side entry is
            ``(order_id, price, size, broker)`` for ``view="mbo"`` (``broker``
            is the entering firm id, ``None`` if missing) or
            ``(price, total_size)`` for ``view="mbp"``; ``"order"`` fully
            describes the single event that caused this entry:
            ``{"order_id", "side", "price", "size", "broker", "event_type",
            "action", "seq_num", "rpt_seq", "timestamp"}``, with the
            order-specific fields ``None`` when the triggering row's
            ``tmpl_id`` doesn't carry them (e.g. a mass-delete has ``side``
            but no ``order_id``). Or ``("trade", {"side", "trade_id",
            "price", "size", "buyer", "seller", "event_type", "action",
            "seq_num", "rpt_seq", "timestamp"})`` for trade rows
            (ExecutionSummary rows are dropped) — the same stream-position
            fields as ``"book"``'s ``"order"``, just flat at the top level
            since there's no separate aggregate snapshot to distinguish them
            from. See
            :meth:`btgsolutions_dataservices.book_by_order.BookByOrder.replay_classified`.

        Raises
        ------
        BadResponse
            If the API returns a non-200 response.
        ValueError
            If ``boundary`` is given with an unknown ``field`` or ``mode``.
        """
        book = BookByOrder(symbol=ticker)
        stream = book.replay_classified(
            self._iter_batches(ticker, date, batch_size),
            view=view,
            n_levels=n_levels,
        )

        if boundary is None:
            yield from stream
            return

        conditions = [boundary] if isinstance(boundary, dict) else boundary
        parsed_conditions = []
        for condition in conditions:
            field = condition["field"]
            mode = condition["mode"]
            value = condition["value"]
            if field not in BOUNDARY_FIELDS:
                raise ValueError(f"boundary['field'] must be one of {BOUNDARY_FIELDS}, got {field!r}")
            if mode not in BOUNDARY_MODES:
                raise ValueError(f"boundary['mode'] must be one of {BOUNDARY_MODES}, got {mode!r}")
            if field == "timestamp":
                value = pd.Timestamp(value)
            parsed_conditions.append((field, mode, value))

        for kind, info in stream:
            stop = False
            skip = False
            for field, mode, value in parsed_conditions:
                ref = info["order"][field] if kind == "book" else info[field]
                if ref is None:
                    # Can't place this event relative to the boundary: skip it
                    # rather than raising on an unorderable `None` comparison.
                    skip = True
                    break
                if mode == "until":
                    if ref > value:
                        stop = True
                        break
                else:  # mode == "after"
                    if ref <= value:
                        skip = True
                        break
            if stop:
                break
            if skip:
                continue
            yield kind, info
