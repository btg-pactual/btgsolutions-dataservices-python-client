from typing import Optional, List
from ..exceptions import WSTypeError
from ..rest import Authenticator
from ..config import broker_analytics_socket_urls, MAX_WS_RECONNECT_RETRIES, REALTIME, BR
from .websocket_default_functions import _on_open, _on_message, _on_error, _on_close
import websocket
import json
import ssl
import threading


class BrokerAnalyticsWebSocketClient:
    """
    This class connects with BTG Solutions Data Services Broker Analytics WebSocket,
    receiving broker analytics events (top tickers by broker and top brokers by ticker).

    * Main use case:

    >>> from btgsolutions_dataservices import BrokerAnalyticsWebSocketClient
    >>> ws = BrokerAnalyticsWebSocketClient(
    >>>     api_key='YOUR_API_KEY',
    >>>     ssl=True
    >>> )
    >>> ws.run()
    >>> ws.available_tickers()
    >>> ws.available_brokers()
    >>> ws.subscribe_top_tickers(n=10, brokers=['85'])
    >>> ws.subscribe_top_brokers(n=5)
    >>> ws.subscribed_to()
    >>> ws.get_last_event(analytics_type='top_tickers', n=3, brokers=['85', '3'])
    >>> ws.get_last_event(analytics_type='top_brokers', n=5)
    >>> ws.unsubscribe_top_tickers(brokers=['85'])
    >>> ws.unsubscribe_top_brokers()
    >>> ws.close()

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.

    ssl: bool
        Enable or disable ssl configuration.
        Field is not required. Default: True (enable).
    """

    def __init__(
        self,
        api_key: str,
        ssl: Optional[bool] = True,
        **kwargs,
    ):
        self.api_key = api_key
        self.ssl = ssl

        self.__authenticator = Authenticator(self.api_key)
        self.__nro_reconnect_retries = 0

        try:
            self.url = broker_analytics_socket_urls[BR][REALTIME]
        except Exception:
            raise WSTypeError(
                "There is no WebSocket type for Broker Analytics (brazil/realtime).\nPlease check your request parameters and try again"
            )

        self.websocket_cfg = kwargs

    def run(
        self,
        on_open=None,
        on_message=None,
        on_error=None,
        on_close=None,
        reconnect=True
    ):
        """
        Initializes a connection to websocket and starts to receive Broker Analytics events.

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
        """
        if on_open is None:
            on_open = _on_open
        if on_message is None:
            on_message = _on_message
        if on_error is None:
            on_error = _on_error
        if on_close is None:
            on_close = _on_close

        def intermediary_on_open(ws):
            on_open()
            self.__nro_reconnect_retries = 0

        def intermediary_on_message(ws, data):
            on_message(data)

        def intermediary_on_error(ws, error):
            on_error(error)

        def intermediary_on_close(ws, close_status_code, close_msg):
            on_close(close_status_code, close_msg)

            if reconnect:
                if self.__nro_reconnect_retries == MAX_WS_RECONNECT_RETRIES:
                    print("### Fail retriyng reconnect")
                    return
                self.__nro_reconnect_retries += 1
                print(f"### Reconnecting.... Attempts: {self.__nro_reconnect_retries}/{MAX_WS_RECONNECT_RETRIES}")
                self.run(on_open, on_message, on_error, on_close, reconnect)

        self.ws = websocket.WebSocketApp(
            url=self.url,
            on_open=intermediary_on_open,
            on_message=intermediary_on_message,
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

    def __send(self, data):
        if not isinstance(data, str):
            data = json.dumps(data)
        print(f"Sending data: {data}")
        return self.ws.send(data)

    def close(self):
        """
        Closes connection with websocket.
        """
        self.ws.close()

    def subscribe_top_tickers(self, n: int = 10, brokers: Optional[List[str]] = None):
        """
        Subscribes to top tickers by broker.

        Parameters
        ----------
        n: int
            Number of results.
            Field is not required. Default: 10.

        brokers: list
            Broker ids filter.
            Field is not required.
        """
        params = {'type': 'top_tickers', 'n': n}
        if brokers is not None:
            params['brokers'] = brokers
        self.__send({'action': 'subscribe', 'params': params})

    def subscribe_top_brokers(self, n: int = 5, tickers: Optional[List[str]] = None):
        """
        Subscribes to top brokers by ticker.

        Parameters
        ----------
        n: int
            Number of results.
            Field is not required. Default: 5.
        tickers: list
            Ticker symbols filter.
            Field is not required.
        """
        params = {'type': 'top_brokers', 'n': n}
        if tickers is not None:
            params['tickers'] = tickers
        self.__send({'action': 'subscribe', 'params': params})

    def unsubscribe_top_tickers(self, brokers: Optional[List[str]] = None):
        """
        Unsubscribes from top tickers by broker.

        Parameters
        ----------
        brokers: list
            Broker ids filter.
            Field is not required.
        """
        params = {'type': 'top_tickers'}
        if brokers is not None:
            params['brokers'] = brokers
        self.__send({'action': 'unsubscribe', 'params': params})

    def unsubscribe_top_brokers(self, tickers: Optional[List[str]] = None):
        """
        Unsubscribes from top brokers by ticker.

        Parameters
        ----------
        tickers: list
            Ticker symbols filter.
            Field is not required.
        """
        params = {'type': 'top_brokers'}
        if tickers is not None:
            params['tickers'] = tickers
        self.__send({'action': 'unsubscribe', 'params': params})

    def get_last_event(
        self,
        analytics_type: Optional[str] = None,
        n: Optional[int] = None,
        brokers: Optional[List[str]] = None,
        tickers: Optional[List[str]] = None,
    ):
        """
        Returns latest broker analytics event.

        Parameters
        ----------
        analytics_type: str
            Analytics type.
            Options: 'top_tickers' or 'top_brokers'.
            Field is not required.

        n: int
            Number of results.
            Field is not required.

        brokers: list
            Broker ids filter.
            Field is not required.
        tickers: list
            Ticker symbols filter.
            Field is not required.
        """
        payload = {'action': 'get_last_event'}
        if analytics_type is not None:
            params = {'type': analytics_type}
            if n is not None:
                params['n'] = n
            if brokers is not None:
                params['brokers'] = brokers
            if tickers is not None:
                params['tickers'] = tickers
            payload['params'] = params
        self.__send(payload)

    def subscribed_to(self):
        """
        Returns current subscriptions.
        """
        self.__send({'action': 'subscribed_to'})

    def available_tickers(self):
        """
        Returns available tickers.
        """
        self.__send({'action': 'available_tickers'})

    def available_brokers(self):
        """
        Returns available brokers.
        """
        self.__send({'action': 'available_brokers'})