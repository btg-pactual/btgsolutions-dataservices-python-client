import json
import ssl
import unittest
from unittest.mock import patch

from btgsolutions_dataservices.exceptions import WSTypeError
from btgsolutions_dataservices.websocket import market_data_websocket_client as module


class _FakeWSApp:
    """Stands in for websocket.WebSocketApp: ``on_run_forever`` plays what the
    background thread would do (open, close, or nothing) without a socket."""

    instances = []
    on_run_forever = staticmethod(lambda ws: None)

    def __init__(self, url, on_open, on_message, on_error, on_close, header):
        self.url, self.header = url, header
        self.on_open, self.on_message, self.on_error, self.on_close = on_open, on_message, on_error, on_close
        self.sent = []
        self.run_forever_kwargs = None
        self.closed = False
        _FakeWSApp.instances.append(self)

    def run_forever(self, **kwargs):
        self.run_forever_kwargs = kwargs
        type(self).on_run_forever(self)

    def send(self, data):
        self.sent.append(json.loads(data))

    def close(self, **kwargs):
        self.closed = True


class BookEventsClientTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(module, "Authenticator")
        self.authenticator = patcher.start()
        self.addCleanup(patcher.stop)
        _FakeWSApp.instances.clear()
        _FakeWSApp.on_run_forever = staticmethod(lambda ws: None)

    def _client(self, **kwargs):
        return module.MarketDataWebSocketClient(api_key="key", data_type="book-events", **kwargs)

    def test_url_and_default_subtype(self):
        self.assertEqual(
            self._client().url,
            "wss://dataservices.btgpactualsolutions.com/stream/v1/marketdata/br/b3/book-events/stocks",
        )
        self.assertEqual(
            self._client(data_subtype="derivatives").url,
            "wss://dataservices.btgpactualsolutions.com/stream/v1/marketdata/br/b3/book-events/derivatives",
        )

    def test_validation(self):
        with self.assertRaises(ValueError):
            self._client(ssl=False)
        with self.assertRaises(ValueError):
            self._client(instruments=[f"T{i}" for i in range(11)])
        with self.assertRaises(WSTypeError):
            self._client(stream_type="delayed")

    def test_run_opens_subscribes_and_handles_messages_in_order(self):
        _FakeWSApp.on_run_forever = staticmethod(lambda ws: ws.on_open(ws))
        with patch.object(module.websocket, "WebSocketApp", _FakeWSApp):
            ws = self._client(instruments=["PETR4"])
            opened, messages = [], []
            ws.run(on_open=lambda: opened.append(True), on_message=messages.append, default_logs=False)
            fake = _FakeWSApp.instances[-1]
            fake.on_message(fake, "a message")  # handled synchronously: one thread, in order
        self.assertEqual(opened, [True])
        self.assertEqual(messages, ["a message"])
        self.assertEqual(fake.sent, [{"action": "subscribe", "params": ["PETR4"]}])
        self.assertEqual(fake.header["Sec-WebSocket-Protocol"], self.authenticator.return_value.token)

    def test_run_always_verifies_the_server_certificate(self):
        _FakeWSApp.on_run_forever = staticmethod(lambda ws: ws.on_open(ws))
        with patch.object(module.websocket, "WebSocketApp", _FakeWSApp):
            self._client().run(default_logs=False)
        self.assertEqual(_FakeWSApp.instances[-1].run_forever_kwargs, {"sslopt": {"cert_reqs": ssl.CERT_REQUIRED}})

    def test_run_does_not_reconnect_by_itself_on_close(self):
        _FakeWSApp.on_run_forever = staticmethod(lambda ws: ws.on_close(ws, 1000, "Daily disconnection routine."))
        closed = []
        with patch.object(module.websocket, "WebSocketApp", _FakeWSApp):
            self._client().run(on_close=lambda code, msg: closed.append((code, msg)), default_logs=False)
        self.assertEqual(closed, [(1000, "Daily disconnection routine.")])
        self.assertEqual(len(_FakeWSApp.instances), 1)

    def test_run_gives_up_after_connect_timeout(self):
        closed = []
        with patch.object(module.websocket, "WebSocketApp", _FakeWSApp):
            self._client().run(on_close=lambda code, msg: closed.append((code, msg)), default_logs=False, connect_timeout=0.05)
        self.assertEqual(len(closed), 1)
        self.assertIsNone(closed[0][0])
        self.assertIn("Timed out", closed[0][1])
        self.assertTrue(_FakeWSApp.instances[-1].closed)

    def test_close_prevents_a_further_run(self):
        _FakeWSApp.on_run_forever = staticmethod(lambda ws: ws.on_open(ws))
        with patch.object(module.websocket, "WebSocketApp", _FakeWSApp):
            ws = self._client()
            ws.run(default_logs=False)
            ws.close()
            ws.run(default_logs=False)
        self.assertEqual(len(_FakeWSApp.instances), 1)
        self.assertIsNone(_FakeWSApp.instances[0].on_close)

    def test_get_last_event_sends_the_ticker_in_a_list(self):
        _FakeWSApp.on_run_forever = staticmethod(lambda ws: ws.on_open(ws))
        with patch.object(module.websocket, "WebSocketApp", _FakeWSApp):
            ws = self._client()
            ws.run(default_logs=False)
            ws.get_last_event("WINZ26")
        self.assertEqual(_FakeWSApp.instances[-1].sent[-1], {"action": "get_last_event", "params": ["WINZ26"]})


class OtherDataTypesTests(unittest.TestCase):
    def test_other_data_types_keep_their_behaviour(self):
        with patch.object(module, "Authenticator"):
            ws = module.MarketDataWebSocketClient(api_key="key", data_type="trades", data_subtype="stocks", ssl=False)
        self.assertEqual(ws.url, "wss://dataservices.btgpactualsolutions.com/stream/v1/marketdata/br/b3/trade/stocks")
        self.assertFalse(ws.ssl)


if __name__ == "__main__":
    unittest.main()
