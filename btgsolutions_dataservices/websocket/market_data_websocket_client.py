
from typing import Optional, List
from ..exceptions import WSTypeError, DelayedError, FeedError
from ..rest import Authenticator
from ..config import market_data_socket_urls, market_data_feedb_socket_urls, MAX_WS_RECONNECT_RETRIES, VALID_STREAM_TYPES, VALID_EXCHANGES, VALID_MARKET_DATA_TYPES, VALID_MARKET_DATA_SUBTYPES, REALTIME, B3, TRADES, INDICES, ALL, STOCKS, BOOKS, BOOK_EVENTS, BOOK_EVENTS_MAX_TICKERS, FEED_A, FEED_B, SETTLEMENTPRICES
from .websocket_default_functions import _on_open, _on_message, _on_error, _on_close
import websocket
import json
import ssl
import threading

# book-events: how long run() waits for the connection to open before giving up
DEFAULT_CONNECT_TIMEOUT = 10.0


class MarketDataWebSocketClient:
    """
    This class connects with BTG Solutions Data Services WebSocket, receiving trade and index data, in real time or delayed.

    * Main use case:

    >>> from btgsolutions_dataservices import MarketDataWebSocketClient
    >>> ws = MarketDataWebSocketClient(
    >>>     api_key='YOUR_API_KEY',
    >>>     stream_type='realtime',
    >>>     exchange='b3',
    >>>     data_type='trades',
    >>>     data_subtype='stocks',
    >>>     instruments=['PETR4'],
    >>>     ssl=True
    >>> )
    >>> ws.run()
    >>> ws.subscribe(['MGLU3'])
    >>> ws.unsubscribe(['PETR4'])
    >>> ws.close()

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.

    stream_type: str
        Websocket connection feed.
        Options: 'realtime', 'delayed'.
        Field is not required. Default: 'realtime'.

    exchange: str
        Exchange name.
        Options: 'b3' or 'bmv'.
        Field is not required. Default: 'b3'.

    data_type: str
        Market Data type.
        Options: 'trades', 'processed-trades', 'books', 'book-events', 'indices', 'securities', 'stoploss', 'candles-1S', 'candles-1M', 'instrument_status', 'settlement-price'.
        'book-events' is the B3 order-by-order book (market-by-order): a ``book_snapshot`` of each
        subscribed ticker, then one ``book_event`` per order change, with the broker of each order
        (realtime only, at most 10 tickers per connection). To keep the book in memory, see
        :class:`btgsolutions_dataservices.RealtimeBookEvents`.
        Field is not required. Default: 'trades'.

    data_subtype: str
        Market Data subtype (when applicable).
        Options: 'stocks', 'options', 'derivatives'.
        Field is not required. Default: None.

    instruments: list
        List of tickers or indexes to subscribe.
        Field is not required. Default: [].

    ssl: bool
        Enable or disable ssl configuration.
        Field is not required. Default: True (enable).
        'book-events' always verifies the server certificate ('ssl=False' is refused).

    feed: str
        Market Data Feed.
        Options: 'A', 'B'.
        Field is not required. Default: 'A' (enable).
    """

    def __init__(
        self,
        api_key: str,
        stream_type: Optional[str] = REALTIME,
        exchange: Optional[str] = B3,
        data_type: Optional[str] = TRADES,
        data_subtype: Optional[str] = None,
        instruments: Optional[List[str]] = [],
        ssl: Optional[bool] = True,
        feed: Optional[str] = FEED_A,
        **kwargs,
    ):
        self.api_key = api_key
        self.instruments = instruments
        self.data_type = data_type
        self.ssl = ssl
        self.default_logs = True

        self.__authenticator = Authenticator(self.api_key)
        self.__nro_reconnect_retries = 0

        if data_subtype is None:
            if exchange is B3 and not data_type in [INDICES, SETTLEMENTPRICES]:
                data_subtype = STOCKS
            else:
                data_subtype = ALL

        if stream_type not in VALID_STREAM_TYPES:
            raise FeedError(
                f"Must provide a valid 'stream_type' parameter. Valid options are: {VALID_STREAM_TYPES}")
        if exchange not in VALID_EXCHANGES:
            raise FeedError(
                f"Must provide a valid 'exchange' parameter. Valid options are: {VALID_EXCHANGES}")
        if exchange not in VALID_EXCHANGES:
            raise FeedError(
                f"Must provide a valid 'exchange' parameter. Valid options are: {VALID_EXCHANGES}")
        if data_type not in VALID_MARKET_DATA_TYPES:
            raise FeedError(
                f"Must provide a valid 'data_type' parameter. Valid options are: {VALID_MARKET_DATA_TYPES}")
        if data_subtype not in VALID_MARKET_DATA_SUBTYPES:
            raise FeedError(
                f"Must provide a valid 'data_subtype' parameter. Valid options are: {VALID_MARKET_DATA_SUBTYPES}")

        if data_type == BOOK_EVENTS:
            if not ssl:
                # the connection carries the access token: the server certificate is always verified
                raise ValueError("'book-events' always verifies the server's TLS certificate: 'ssl=False' is not supported")
            if instruments and len(instruments) > BOOK_EVENTS_MAX_TICKERS:
                raise ValueError(f"'book-events' accepts at most {BOOK_EVENTS_MAX_TICKERS} tickers per connection")

        if feed == FEED_B:
            url_feed_map = market_data_feedb_socket_urls
        else:
            url_feed_map = market_data_socket_urls

        try:
            self.url = url_feed_map[exchange][data_type][stream_type][data_subtype]
        except:
            raise WSTypeError(
                f"There is no WebSocket type for your specifications (stream_type:{stream_type}, exchange:{exchange}, data_type:{data_type}, data_subtype:{data_subtype})\nPlease check your request parameters and try again")

        self.websocket_cfg = kwargs

    def run(
        self,
        on_open=None,
        on_message=None,
        on_error=None,
        on_close=None,
        reconnect=True,
        spawn_thread:bool=True,
        default_logs:bool=True,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    ):
        """
        Initializes a connection to websocket and subscribes to the instruments, if it was passed in the class initialization.

        Parameters
        ----------
        on_open: function
            - Called at opening connection to websocket.
            - Field is not required. 
            - Default: prints that the connection was opened in case of success.

        on_message: function
            - Called every time it receives a message.
            - Arguments:
                1. Data received from the server.
            - Field is not required. 
            - Default: prints the data.

        on_error: function
            - Called when a error occurs.
            - Arguments: 
                1. Exception object.
            - Field is not required. 
            - Default: prints the error.

        on_close: function
            - Called when connection is closed.
            - Arguments: 
                1. close_status_code.
                2. close_msg.
            - Field is not required. 
            - Default: prints a message that the connection was closed.
        reconnect: bool
            Try reconnect if connection is closed.
            Field is not required.
            Default: True.
        spawn_thread: bool
            Spawn a new thread for incoming server messages (on_message callback function)
            Field is not required.
            Default: True.
        default_logs: bool
            Default non-required logs, detailing messages sent from the client to the WebSocket server.
            Field is not required.
            Default: True.
        connect_timeout: float
            Only for 'book-events': seconds to wait for the connection to open (default 10).

        For 'book-events', run() handles messages in a single thread (book changes must be
        applied in the order they arrive), never reconnects by itself (a dropped connection
        calls on_close once; RealtimeBookEvents reconnects at its level) and never waits
        longer than connect_timeout for the connection to open: if it doesn't, on_close is
        called with a timeout message.
        """
        if self.data_type == BOOK_EVENTS:
            return self._run_book_events(on_open, on_message, on_error, on_close, connect_timeout, default_logs)

        if on_open is None:
            on_open = _on_open
        if on_message is None:
            on_message = _on_message
        if on_error is None:
            on_error = _on_error
        if on_close is None:
            on_close = _on_close
        self.default_logs = default_logs if default_logs is True else False

        def intermediary_on_open(ws):
            on_open()
            if self.instruments:
                self.subscribe(self.instruments)
            self.__nro_reconnect_retries = 0

        def intermediary_on_message(ws, data):
            on_message(data)

        def new_thread_intermediary_on_message(ws, data):
            def run(*args):
                on_message(data)
            threading.Thread(target=run).start()

        def intermediary_on_error(ws, error):
            on_error(error)

        def intermediary_on_close(ws, close_status_code, close_msg):
            on_close(close_status_code, close_msg)

            if reconnect:
                if self.__nro_reconnect_retries == MAX_WS_RECONNECT_RETRIES:
                    print(f"### Fail retriyng reconnect")
                    return
                self.__nro_reconnect_retries += 1
                print(
                    f"### Reconnecting.... Attempts: {self.__nro_reconnect_retries}/{MAX_WS_RECONNECT_RETRIES}")
                self.run(on_open, on_message, on_error, on_close, reconnect)

        if spawn_thread:
            print('on_message callback function running on a new thread')
            on_message_callback = new_thread_intermediary_on_message
        else:
            on_message_callback = intermediary_on_message

        self.ws = websocket.WebSocketApp(
            url=self.url,
            on_open=intermediary_on_open,
            on_message=on_message_callback,
            on_error=intermediary_on_error,
            on_close=intermediary_on_close,
            header={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36",
                "Sec-WebSocket-Protocol": self.__authenticator.token,
            }
        )

        ssl_conf = {} if self.ssl else {"sslopt": {"cert_reqs": ssl.CERT_NONE}}
        wst = threading.Thread(target=self.ws.run_forever, kwargs=ssl_conf)
        wst.daemon = True
        wst.start()

        while True:
            if self.ws.sock is not None and self.ws.sock.connected:
                break
            pass

    def __print(self, log: str):
        if self.default_logs:
            print(log)

    def __send(self, data):
        """
        Class method to be used internally. Sends data to websocket.
        """
        if not isinstance(data, str):
            data = json.dumps(data)
        self.__print(f'Sending data: {data}')
        return self.ws.send(data)

    def close(self):
        """
        Closes connection with websocket.
        """
        if self.data_type == BOOK_EVENTS:
            self._closed = True
            if getattr(self, "ws", None) is not None:
                self.ws.on_close = None
                self.ws.close()
            return
        self.ws.close()

    def request_snapshot(self, ticker: str) -> None:
        """
        'book-events' only: ask for a ticker's current book (a ``book_snapshot`` inside the
        ``get_last_event`` reply), e.g. to recover after a gap in ``seq``.
        """
        self.__send({'action': 'get_last_event', 'params': [ticker]})

    def _run_book_events(self, on_open, on_message, on_error, on_close, connect_timeout, default_logs):
        if getattr(self, "_closed", False):
            return None  # closed by close(): no reconnection

        self.default_logs = default_logs is True
        on_open = on_open or (lambda: None)
        on_message = on_message or (lambda data: None)
        on_error = on_error or (lambda error: None)
        on_close = on_close or (lambda code, message: None)

        # set by whichever of on_open/on_close happens first: the wait below is bounded
        resolved = threading.Event()

        def _on_open(ws):
            resolved.set()
            on_open()
            if self.instruments:
                self.subscribe(self.instruments)

        def _on_message(ws, data):
            on_message(data)  # single thread: book changes are applied in order

        def _on_error(ws, error):
            on_error(error)

        def _on_close(ws, code, message):
            resolved.set()
            on_close(code, message)

        self.ws = websocket.WebSocketApp(
            url=self.url,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close,
            header={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36",
                "Sec-WebSocket-Protocol": self.__authenticator.token,
            },
        )
        ssl_conf = {"sslopt": {"cert_reqs": ssl.CERT_REQUIRED}}  # always verify the server certificate
        thread = threading.Thread(target=self.ws.run_forever, kwargs=ssl_conf)
        thread.daemon = True
        thread.start()

        if not resolved.wait(timeout=connect_timeout):
            # neither opened nor closed in time: give up on this attempt
            ws, self.ws.on_close, self.ws.on_open = self.ws, None, None
            try:
                ws.close()
            except Exception:
                pass
            on_close(None, f"Timed out waiting {connect_timeout}s for the connection to open.")
        return None

    def subscribe(self, list_instruments, n=None, initial_snapshot: bool=False):
        """
        Subscribes a list of instruments.

        Parameters
        ----------
        list_instruments: list
            Field is required.
        n: int
            Field is not required.
            **For books data_type only.**
            Maximum book level. It must be between 1 and 10. 
        initial_snapshot: float
            If True, client receives ticker last event (snapshot) of the provided ticker. 
            Field is not required.
            Default: False
        """

        if initial_snapshot or n is not None:
            message = {'action': 'subscribe', 'params': {"tickers": list_instruments, "initial_snapshot": initial_snapshot}}
            if n is not None:
                message['params']['n'] = n
            self.__send(message)
            self.__print(f'Socket subscribed the following instrument(s) with n = {n}: {list_instruments} and initial_snapshot = {initial_snapshot}')
        else:
            self.__send({'action': 'subscribe', 'params': list_instruments})
            self.__print(f'Socket subscribed the following instrument(s): {list_instruments}')


    def unsubscribe(self, list_instruments):
        """
        Unsubscribes a list of instruments.

        Parameters
        ----------
        list_instruments: list
            Field is required.
        """
        self.__send({'action': 'unsubscribe', 'params': list_instruments})
        self.__print(
            f'Socket unsubscribed the following instrument(s): {list_instruments}')

    def subscribed_to(self):
        """
        Return client subscribed tickers.
        """
        self.__send({'action': 'subscribed_to'})

    def available_to_subscribe(self):
        """
        Return avaiable tickers to subscribe.
        """
        self.__send({'action': 'available_to_subscribe'})

    def instrument_status(self, ticker:str):
        """
        Returns the instrument latest status.
        """
        self.__send({'action': 'instrument_status', 'params': [ticker]})

    def instrument_status_history(self, ticker:str):
        """
        Returns the latest 10 status of the instrument.
        """
        self.__send({'action': 'instrument_history', 'params': [ticker]})

    def notify_stoploss(self, instrument_params):
        """
        Create a stoploss notification routine on the provided instrument(s).

        Parameters
        ----------
        instrument_params: dict
            Field is required.
        """
        self.__send({'action': 'notify_stoploss', 'params': instrument_params})

    def stoploss_status(self):
        """
        Return client stop loss status.
        """
        self.__send({'action': 'stoploss_status'})

    def clear_stoploss(self):
        """
        Clears client stop loss notifications.
        """
        self.__send({'action': 'clear_stoploss'})

    def get_last_event(self, ticker: str):
        """
        Get the last event for the provided ticker.

        Parameters
        ----------
        ticker: str
            Field is required.
        """
        if self.data_type == BOOK_EVENTS:
            # 'book-events' takes the ticker in a list; the reply carries its current book
            return self.request_snapshot(ticker)
        self.__send({'action': 'get_last_event', 'params': ticker})

    def candle_subscribe(self, list_instruments: list, candle_type: str):
        """
        Subscribes a list of instruments, for partial/closed candle updates.

        Parameters
        ----------
        list_instruments: list
            Field is required.
        candle_type: str
            Field is required.
        """
        self.__send(
            {'action': 'subscribe', 'params': list_instruments, 'type': candle_type})
        self.__print(
            f'Socket subscribed the following instrument(s): {list_instruments}')

    def candle_unsubscribe(self, list_instruments: list, candle_type: str):
        """
        Unsubscribes a list of instruments, for partial/closed candle updates.

        Parameters
        ----------
        list_instruments: list
            Field is required.
        candle_type: str
            Field is required.
        """
        self.__send({'action': 'unsubscribe',
                    'params': list_instruments, 'type': candle_type})
        self.__print(
            f'Socket unsubscribed the following instrument(s): {list_instruments}')
