import json
import threading
import unittest
from unittest.mock import patch



from btgsolutions_dataservices.book_by_order import BID, MBP, OFFER
from btgsolutions_dataservices.config import market_data_socket_urls
from btgsolutions_dataservices.websocket.realtime_book_events import (
    BookEventsState,
    RealtimeBookEvents,
)


def _snapshot(symb="PETR4", seq=0, bid=None, offer=None):
    return {
        "ev": "book_snapshot", "feed": "A", "symb": symb, "seq": seq, "rptSeq": 10,
        "bid": bid if bid is not None else [
            {"oid": 2, "px": 30.0, "qty": 100, "firm": 85, "ts": "2026-11-13T13:00:00.000000000Z"},
            {"oid": 5, "px": 29.9, "qty": 200, "firm": 3, "ts": None},
        ],
        "offer": offer if offer is not None else [
            {"oid": 3, "px": 30.1, "qty": 300, "firm": 72, "ts": None},
        ],
    }


def _event(seq, act, side=None, oid=None, px=None, qty=None, firm=None, symb="PETR4", **extra):
    msg = {"ev": "book_event", "feed": "A", "symb": symb, "seq": seq, "act": act, "rptSeq": 10 + seq,
           "tTime": "2026-11-13T13:00:01.000000000Z"}
    if side is not None:
        msg["side"] = side
    if oid is not None:
        msg.update({"oid": oid, "px": px, "qty": qty, "firm": firm})
    msg.update(extra)
    return msg


class BookEventsStateTests(unittest.TestCase):
    def setUp(self):
        self.requested = []
        self.state = BookEventsState(view="mbo", n_levels=5, request_snapshot=self.requested.append)

    def test_snapshot_builds_the_book(self):
        [(kind, info)] = self.state.handle(_snapshot())
        self.assertEqual(kind, "book")
        self.assertEqual(info["symbol"], "PETR4")
        self.assertEqual(info["order"]["event_type"], "snapshot")
        self.assertEqual(info["bid"], [(2, 30.0, 100, 85), (5, 29.9, 200, 3)])
        self.assertEqual(info["offer"], [(3, 30.1, 300, 72)])

    def test_snapshot_order_has_the_same_keys_as_an_event(self):
        [(_, snapshot_info)] = self.state.handle(_snapshot())
        [(_, event_info)] = self.state.handle(_event(1, "new", "bid", 7, 30.0, 50, 1))
        self.assertEqual(set(snapshot_info["order"]), set(event_info["order"]))
        self.assertEqual(
            (snapshot_info["order"]["transact_time"], snapshot_info["order"]["end_of_event"], snapshot_info["order"]["prev_size"]),
            (None, True, None),
        )

    def test_events_change_the_book_in_priority_order(self):
        self.state.handle(_snapshot())
        out = self.state.handle(_event(1, "new", "bid", 7, 30.0, 50, 1, ts="2026-11-13T13:00:01.000000000Z"))
        [(kind, info)] = out
        self.assertEqual(kind, "book")
        # same price, larger secondary_order_id: behind order 2
        self.assertEqual(info["bid"][:2], [(2, 30.0, 100, 85), (7, 30.0, 50, 1)])
        order = info["order"]
        self.assertEqual((order["event_type"], order["action"], order["side"], order["broker"]), ("order", "NEW", BID, 1))
        self.assertEqual(order["seq_num"], 1)

        [(_, info)] = self.state.handle(_event(2, "change", "bid", 2, 30.0, 60, 85, prevQty=100))
        self.assertEqual(info["bid"][0], (2, 30.0, 60, 85))
        self.assertEqual((info["order"]["action"], info["order"]["prev_size"]), ("CHANGE", 100))

        [(_, info)] = self.state.handle(_event(3, "delete", "offer", 3, 30.1, 300))
        self.assertEqual(info["offer"], [])
        self.assertEqual(info["order"]["event_type"], "delete_order")

        [(_, info)] = self.state.handle(_event(4, "mass_delete", "bid"))
        self.assertEqual(info["bid"], [])
        self.assertEqual(info["order"]["event_type"], "mass_delete")

    def test_price_less_orders_come_first(self):
        self.state.handle(_snapshot())
        [(_, info)] = self.state.handle(_event(1, "new", "offer", 9, None, 10, 8))
        self.assertEqual(info["offer"][0], (9, None, 10, 8))

    def test_empty_book_clears_both_sides(self):
        self.state.handle(_snapshot())
        [(_, info)] = self.state.handle(_event(1, "empty", eoe=True))
        self.assertEqual((info["bid"], info["offer"]), ([], []))
        self.assertTrue(info["order"]["end_of_event"])

    def test_gap_requests_a_snapshot_and_drops_events_until_it_comes(self):
        self.state.handle(_snapshot())
        [(kind, info)] = self.state.handle(_event(3, "new", "bid", 7, 30.0, 50, 1))
        self.assertEqual((kind, info["status"], info["reason"]), ("status", "resyncing", "seq_gap"))
        self.assertEqual(self.requested, ["PETR4"])
        self.assertEqual(self.state.handle(_event(4, "new", "bid", 8, 30.0, 50, 1)), [])

        reply = {"ev": "get_last_event", "status": "success", "message": _snapshot(seq=10, bid=[], offer=[])}
        [(kind, info)] = self.state.handle(reply)
        self.assertEqual((kind, info["bid"]), ("book", []))
        [(kind, _)] = self.state.handle(_event(11, "new", "bid", 9, 30.0, 1, 1))
        self.assertEqual(kind, "book")
        self.assertEqual(self.requested, ["PETR4"])

    def test_event_before_any_snapshot_requests_one(self):
        [(kind, _)] = self.state.handle(_event(5, "new", "bid", 7, 30.0, 50, 1, symb="VALE3"))
        self.assertEqual(kind, "status")
        self.assertEqual(self.requested, ["VALE3"])

    def test_resync_is_a_new_snapshot(self):
        self.state.handle(_snapshot())
        self.state.handle(_event(1, "new", "bid", 7, 30.0, 50, 1))
        [(kind, info)] = self.state.handle({"ev": "book_status", "symb": "PETR4", "status": "resyncing", "message": "x"})
        self.assertEqual((kind, info["status"]), ("status", "resyncing"))
        [(_, info)] = self.state.handle(_snapshot(seq=0, bid=[], offer=[]))
        self.assertEqual(info["bid"], [])
        [(kind, _)] = self.state.handle(_event(1, "new", "bid", 8, 30.0, 50, 1))
        self.assertEqual(kind, "book")

    def test_status_and_replies(self):
        [(kind, info)] = self.state.handle(
            {"ev": "book_status", "symb": "PETR4", "status": "suspect", "sinceSeq": 4, "reason": "unknown_order", "message": "m"}
        )
        self.assertEqual((kind, info["status"], info["since_seq"]), ("status", "suspect", 4))
        self.assertEqual(self.state.handle({"ev": "message", "status": "success", "message": "subscribed"}), [])
        [(kind, info)] = self.state.handle({"ev": "get_last_event", "status": "failed", "message": "couldn't find X book"})
        self.assertEqual((kind, info["status"]), ("status", "snapshot_failed"))

    def test_mbp_view(self):
        state = BookEventsState(view=MBP, n_levels=1)
        [(_, info)] = state.handle(_snapshot())
        self.assertEqual(info["bid"], [(30.0, 100)])
        self.assertEqual(info["offer"], [(30.1, 300)])

    def test_invalid_view(self):
        with self.assertRaises(ValueError):
            BookEventsState(view="x")


class _FakeClient:
    """Stands in for MarketDataWebSocketClient: plays messages on run()."""

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.snapshots = []
        self.closed = False
        _FakeClient.instances.append(self)

    def request_snapshot(self, ticker):
        self.snapshots.append(ticker)

    def run(self, on_open, on_message, on_error, on_close, reconnect, spawn_thread, default_logs):
        self.run_args = (reconnect, spawn_thread, default_logs)
        on_message(json.dumps(_snapshot()))
        on_message("not json")
        on_message(json.dumps(_event(1, "new", "bid", 7, 30.0, 50, 1)))
        on_close(1000, "Daily disconnection routine.")

    def close(self):
        self.closed = True


class _ControllableFakeClient:
    """Stands in for MarketDataWebSocketClient: only reacts when the test tells it to.

    Saves the callbacks passed to ``run()`` so a test can call ``on_close``
    directly to simulate *that* client's connection closing, without racing
    on real time.
    """

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        self.on_close = None
        _ControllableFakeClient.instances.append(self)

    def request_snapshot(self, ticker):
        pass

    def run(self, on_open, on_message, on_error, on_close, reconnect, spawn_thread, default_logs):
        self.on_close = on_close

    def close(self):
        self.closed = True
        self._closed = True  # matches the real MarketDataWebSocketClient.close() contract


class _BurstFakeClient:
    """Stands in for MarketDataWebSocketClient: delivers several messages at
    once, all already sitting in the queue before get_book's loop starts
    consuming them one at a time."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def request_snapshot(self, ticker):
        pass

    def run(self, on_open, on_message, on_error, on_close, reconnect, spawn_thread, default_logs):
        on_message(json.dumps(_snapshot()))
        on_message(json.dumps(_event(1, "new", "bid", 7, 30.0, 50, 1)))
        on_message(json.dumps(_event(2, "new", "offer", 9, 30.2, 20, 4)))

    def close(self):
        pass


class RealtimeBookEventsTests(unittest.TestCase):
    def test_get_book_streams_entries_in_order_and_closes(self):
        books = RealtimeBookEvents(api_key="key", data_subtype="options")
        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _FakeClient,
        ):
            entries = list(books.get_book(["PETR4"], timeout=0.1))
        client = _FakeClient.instances[-1]
        self.assertEqual(client.kwargs["data_type"], "book-events")
        self.assertEqual(client.kwargs["data_subtype"], "options")
        self.assertNotIn("environment", client.kwargs)
        self.assertEqual(client.run_args, (False, False, False))  # get_book() reconnects itself now
        self.assertTrue(client.closed)
        self.assertEqual([k for k, _ in entries], ["book", "book", "status"])
        self.assertEqual(entries[1][1]["order"]["action"], "NEW")
        self.assertEqual(entries[2][1]["status"], "disconnected")
        self.assertEqual(books.book("PETR4").top_of_book()["best_bid"], (2, 30.0, 100, 85))

    def test_queued_counts_down_to_zero_for_a_burst_of_messages(self):
        books = RealtimeBookEvents(api_key="key")
        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _BurstFakeClient,
        ):
            entries = list(books.get_book(["PETR4"], timeout=0.1))

        book_entries = [info for kind, info in entries if kind == "book"]
        self.assertEqual(len(book_entries), 3)
        self.assertEqual([info["queued"] for info in book_entries], [2, 1, 0])

    def test_there_is_no_option_to_disable_tls_verification(self):
        with self.assertRaises(TypeError):
            RealtimeBookEvents(api_key="key", ssl=False)

    def test_ticker_limit(self):
        books = RealtimeBookEvents(api_key="key")
        with self.assertRaises(ValueError):
            next(books.get_book([f"T{i}" for i in range(11)]))
        with self.assertRaises(ValueError):
            next(books.get_book([]))

    def test_close_from_another_thread_wakes_and_stops_the_generator(self):
        books = RealtimeBookEvents(api_key="key")
        entries = []
        finished = threading.Event()

        def consume():
            for kind, info in books.get_book(["PETR4"]):
                entries.append((kind, info))
            finished.set()

        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _ControllableFakeClient,
        ):
            consumer = threading.Thread(target=consume, daemon=True)
            consumer.start()
            for _ in range(200):  # wait until the generator is blocked waiting for messages
                if books.messages is not None:
                    break
                threading.Event().wait(0.01)
            books.close()
            consumer.join(timeout=2)

        self.assertTrue(finished.is_set(), "get_book() did not stop after close()")
        self.assertEqual(entries, [("status", {
            "symbol": None, "status": "disconnected", "since_seq": None, "reason": None,
            "message": "Closed by close().",
        })])

    def test_a_finishing_stream_does_not_close_a_newer_one_on_the_same_instance(self):
        # a second get_book() on the same RealtimeBookEvents replaces self.client/self.messages;
        # the first generator's own cleanup must only ever touch what *it* created.
        books = RealtimeBookEvents(api_key="key")
        baseline = len(_ControllableFakeClient.instances)
        done_a, done_b = threading.Event(), threading.Event()
        entries_a, entries_b = [], []

        def run_a():
            for entry in books.get_book(["AAAA"]):
                entries_a.append(entry)
            done_a.set()

        def run_b():
            for entry in books.get_book(["BBBB"]):
                entries_b.append(entry)
            done_b.set()

        def _wait_for_client(index):
            for _ in range(200):
                if (
                    len(_ControllableFakeClient.instances) >= index
                    and _ControllableFakeClient.instances[index - 1].on_close is not None
                ):
                    return _ControllableFakeClient.instances[index - 1]
                threading.Event().wait(0.01)
            raise AssertionError("client was never created/started")

        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _ControllableFakeClient,
        ):
            thread_a = threading.Thread(target=run_a, daemon=True)
            thread_a.start()
            client_a = _wait_for_client(baseline + 1)

            # start a second stream on the *same* instance while the first is still running
            # (neither has a `timeout`, so both just sit blocked until told to stop below)
            thread_b = threading.Thread(target=run_b, daemon=True)
            thread_b.start()
            client_b = _wait_for_client(baseline + 2)

            # simulate stream A's connection closing on its own — NOT via books.close(),
            # which would now hit B's client/queue since self.client/self.messages point at B
            client_a.close()
            client_a.on_close(None, "stream A closed on its own")

            thread_a.join(timeout=2)
            self.assertTrue(done_a.is_set(), "stream A did not stop")
            self.assertTrue(client_a.closed, "stream A should have closed its own client")
            self.assertFalse(client_b.closed, "stream A's cleanup must not close stream B's client")

            client_b.close()
            client_b.on_close(None, "stream B closed on its own")
            thread_b.join(timeout=2)
            self.assertTrue(done_b.is_set(), "stream B did not stop")
            self.assertTrue(client_b.closed)


def _closes_without_opening(code=None, message=None):
    """A scripted connection attempt that fails before ever opening."""
    return lambda on_open, on_message, on_close: on_close(code, message)


def _opens_then_closes(code, message):
    """A scripted connection attempt that opens, then immediately closes."""
    def action(on_open, on_message, on_close):
        on_open()
        on_close(code, message)
    return action


def _opens_and_sends(*raw_messages):
    """A scripted connection attempt that opens and delivers some messages."""
    def action(on_open, on_message, on_close):
        on_open()
        for raw in raw_messages:
            on_message(raw)
    return action


class _ScriptedFakeClient:
    """Stands in for MarketDataWebSocketClient: one instance per get_book()
    call (reconnects call run() again on that SAME instance), each run()
    call popping and executing the next scripted connection attempt."""

    instances = []
    script: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        _ScriptedFakeClient.instances.append(self)

    def request_snapshot(self, ticker):
        pass

    def run(self, on_open, on_message, on_error, on_close, reconnect, spawn_thread, default_logs):
        action = _ScriptedFakeClient.script.pop(0)
        action(on_open, on_message, on_close)

    def close(self):
        self.closed = True
        self._closed = True


class ReconnectTests(unittest.TestCase):
    def test_reconnect_false_stops_right_after_disconnected(self):
        _ScriptedFakeClient.instances.clear()
        _ScriptedFakeClient.script = [_opens_then_closes(1000, "bye")]
        books = RealtimeBookEvents(api_key="key")
        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _ScriptedFakeClient,
        ):
            entries = list(books.get_book(["PETR4"], reconnect=False))
        self.assertEqual(entries, [("status", {
            "symbol": None, "status": "disconnected", "since_seq": None, "reason": 1000, "message": "bye",
        })])
        self.assertEqual(_ScriptedFakeClient.script, [])  # never tried a 2nd attempt

    def test_disconnect_reason_and_message_pass_through_from_the_server(self):
        _ScriptedFakeClient.instances.clear()
        _ScriptedFakeClient.script = [_opens_then_closes(1001, "Slow consumer: disconnected.")]
        books = RealtimeBookEvents(api_key="key")
        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _ScriptedFakeClient,
        ):
            entries = list(books.get_book(["PETR4"], reconnect=False))
        self.assertEqual(entries, [("status", {
            "symbol": None, "status": "disconnected", "since_seq": None,
            "reason": 1001, "message": "Slow consumer: disconnected.",
        })])

    def test_reconnect_true_yields_reconnected_then_a_new_snapshot_replaces_the_book(self):
        _ScriptedFakeClient.instances.clear()
        _ScriptedFakeClient.script = [
            _closes_without_opening(1006, None),  # e.g. a connection refused before it ever opened
            _opens_and_sends(json.dumps(_snapshot(seq=0))),
        ]
        books = RealtimeBookEvents(api_key="key")
        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _ScriptedFakeClient,
        ):
            gen = books.get_book(["PETR4"], reconnect=True, max_reconnects=5)
            disconnected = next(gen)
            reconnected = next(gen)
            snapshot_entry = next(gen)
            gen.close()

        self.assertEqual(disconnected, ("status", {
            "symbol": None, "status": "disconnected", "since_seq": None, "reason": 1006,
            "message": "Connection closed.",
        }))
        self.assertEqual(reconnected, ("status", {
            "symbol": None, "status": "reconnected", "since_seq": None, "reason": None, "attempt": 1,
            "message": "Connection restored: every book comes again as a new snapshot.",
        }))
        self.assertEqual(snapshot_entry[0], "book")
        self.assertEqual(snapshot_entry[1]["order"]["event_type"], "snapshot")
        self.assertEqual(_ScriptedFakeClient.script, [])

    def test_reconnect_failed_after_max_reconnects_consecutive_failures(self):
        _ScriptedFakeClient.instances.clear()
        fail = _closes_without_opening(1006, "refused")
        _ScriptedFakeClient.script = [fail, fail, fail]  # the initial attempt + 2 retries
        books = RealtimeBookEvents(api_key="key")
        with patch(
            "btgsolutions_dataservices.websocket.market_data_websocket_client.MarketDataWebSocketClient",
            _ScriptedFakeClient,
        ):
            entries = list(books.get_book(["PETR4"], reconnect=True, max_reconnects=2))

        self.assertEqual([info["status"] for _, info in entries], [
            "disconnected", "disconnected", "disconnected", "reconnect_failed",
        ])
        self.assertEqual(entries[-1][1]["attempts"], 2)
        self.assertEqual(_ScriptedFakeClient.script, [])


class BookEventsUrlTests(unittest.TestCase):
    def test_urls(self):
        urls = market_data_socket_urls["b3"]["book-events"]["realtime"]
        self.assertEqual(
            urls["stocks"],
            "wss://dataservices.btgpactualsolutions.com/stream/v1/marketdata/br/b3/book-events/stocks",
        )
        self.assertEqual(
            urls["derivatives"],
            "wss://dataservices.btgpactualsolutions.com/stream/v1/marketdata/br/b3/book-events/derivatives",
        )


if __name__ == "__main__":
    unittest.main()
