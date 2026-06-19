
from typing import Optional, Dict, List, Any
from ..exceptions import WSTypeError, FeedError
from ..rest import Authenticator
from ..config import hfn_v3_socket_url, MAX_WS_RECONNECT_RETRIES
from .websocket_default_functions import _on_open, _on_message, _on_error, _on_close
import websocket
import json
import ssl
import threading


class HFNV3WebSocketClient:
    """
    This class connects with the BTG Solutions Data Services HFN V3 WebSocket,
    providing a bidirectional real-time news stream with rich subscription filters,
    on-demand queries, and reader engagement metrics.

    **Lifecycle**:

    1. Connect via :meth:`run` — the server immediately sends a ``message`` event with the assigned ``clientId``.
    2. Call :meth:`subscribe` with filter settings to start receiving live broadcasts.
       The server replies with a subscription confirmation followed by a ``latest-news`` snapshot.
    3. New matching news items are pushed as ``broadcast`` events via the ``on_message`` callback.
    4. Call :meth:`unsubscribe` to stop broadcasts without closing the connection.
    5. A ``ping`` heartbeat is sent by the server every 30 seconds to keep the connection alive.
    6. All connections are terminated daily at midnight (America/Sao_Paulo).

    * Main use case:

    >>> from btgsolutions_dataservices import HFNV3WebSocketClient

    >>> ws = HFNV3WebSocketClient(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> ws.run()

    >>> # Subscribe to live economy news in Portuguese
    >>> ws.subscribe(settings={'feed': 'economy', 'text_language': 'portuguese'})

    >>> # Request latest news on demand (without subscribing)
    >>> ws.latest_news(settings={'feed': 'crypto', 'limit': '10'})

    >>> # Retrieve available filter values
    >>> ws.available_filters()

    >>> # Stop receiving broadcasts (keeps connection open)
    >>> ws.unsubscribe()

    >>> ws.close()

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.

    ssl: bool
        Enable or disable SSL verification.
        Field is not required. Default: True (enabled).
    """

    def __init__(
        self,
        api_key: str,
        ssl: Optional[bool] = True,
        **kwargs,
    ):
        self.api_key = api_key
        self.ssl = ssl
        self.url = hfn_v3_socket_url

        self.__authenticator = Authenticator(self.api_key)
        self.__nro_reconnect_retries = 0

        self.websocket_cfg = kwargs

    def run(
        self,
        on_open=None,
        on_message=None,
        on_error=None,
        on_close=None,
        reconnect: bool = True,
    ):
        """
        Initializes a connection to the HFN V3 WebSocket.

        Upon successful connection the server sends a ``message`` event containing
        the server-assigned ``clientId``.  Use :meth:`subscribe` afterwards to start
        receiving live news broadcasts.

        Parameters
        ----------
        on_open: function
            Called when the connection is opened.
            Field is not required.
            Default: prints a confirmation message.

        on_message: function
            Called every time a message is received from the server.
            Arguments:

                1. Data received from the server (JSON string).

            Field is not required.
            Default: prints the data.

        on_error: function
            Called when an error occurs.
            Arguments:

                1. Exception object.

            Field is not required.
            Default: prints the error.

        on_close: function
            Called when the connection is closed.
            Arguments:

                1. close_status_code.
                2. close_msg.

            Field is not required.
            Default: prints a closure message.

        reconnect: bool
            Automatically attempt to reconnect if the connection drops.
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
                print(
                    f"### Reconnecting.... Attempts: {self.__nro_reconnect_retries}/{MAX_WS_RECONNECT_RETRIES}"
                )
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
            },
        )

        ssl_conf = {} if self.ssl else {"sslopt": {"cert_reqs": ssl.CERT_NONE}}
        wst = threading.Thread(target=self.ws.run_forever, kwargs=ssl_conf)
        wst.daemon = True
        wst.start()

        while True:
            if self.ws.sock is not None and self.ws.sock.connected:
                break

    def __send(self, data):
        """
        Class method to be used internally. Sends data to websocket.
        """
        if not isinstance(data, str):
            data = json.dumps(data)
        print(f'Sending data: {data}')
        return self.ws.send(data)

    def close(self):
        """
        Closes the connection with the WebSocket.
        """
        self.ws.close()

    def subscribe(self, settings: Optional[Dict[str, Any]] = None):
        """
        Subscribe to live news matching the provided filter settings.
        The server will immediately send a subscription confirmation followed by
        a ``latest-news`` snapshot of recent matching news.
        Subsequent matching news items will be pushed as ``broadcast`` events.

        Parameters
        ----------
        settings: dict
            Filter settings that control which news items are broadcast.
            All fields are optional; omitting a field disables that filter.
            Accepted keys:

            - ``countries`` (list of str): Filter by country codes. Example: ``['BR']``.
            - ``source_type`` (str): Filter by ingestion source type. Values: ``'rss'``, ``'html'``, ``'pdf'``.
            - ``source`` (str): Filter by a specific news source name. Example: ``'Exame - Mercado'``.
            - ``feed`` (str): Filter by thematic feed. Values: ``'politics'``, ``'economy'``, ``'crypto'``,
              ``'technology'``, ``'sports'``, ``'health'``, ``'commodities'``, ``'energy'``, ``'general'``.
            - ``text_language`` (str): Filter by content language. Values: ``'portuguese'``, ``'english'``,
              ``'spanish'``, ``'german'``, ``'french'``.
            - ``categories`` (list of str): Filter by category keywords. Example: ``['Bitcoin', 'Ethereum']``.
            - ``text`` (str): Full-text search filter applied to title and content.

            Field is not required. Default: ``{}`` (no filters — receive all news).
        """
        if settings is None:
            settings = {}
        self.__send({'action': 'subscribe', 'settings': settings})

    def unsubscribe(self):
        """
        Stop receiving live news ``broadcast`` events without closing the connection.
        """
        self.__send({'action': 'unsubscribe'})

    def latest_news(self, settings: Optional[Dict[str, Any]] = None):
        """
        Fetch a batch of news items matching the given filters on demand,
        without subscribing to a live stream.
        The server responds with a ``latest-news`` event containing the matching items.

        Parameters
        ----------
        settings: dict
            Query parameters for the news request. All fields are optional.
            Accepted keys:

            - ``countries`` (list of str): Filter by country codes. Example: ``['BR']``.
            - ``source_type`` (str): Filter by ingestion source type. Values: ``'rss'``, ``'html'``, ``'pdf'``.
            - ``source`` (str): Filter by a specific source name.
            - ``feed`` (str): Filter by thematic feed. Values: ``'politics'``, ``'economy'``, ``'crypto'``,
              ``'technology'``, ``'sports'``, ``'health'``, ``'commodities'``, ``'energy'``, ``'general'``.
            - ``text_language`` (str): Filter by content language.
            - ``start_date`` (str): ISO 8601 start datetime filter (inclusive). Example: ``'2025-01-01T00:00:00.000Z'``.
            - ``end_date`` (str): ISO 8601 end datetime filter (inclusive). Example: ``'2025-12-31T23:59:59.999Z'``.
            - ``status`` (str): Filter by pipeline processing status. Values: ``'raw'``, ``'ingested'``, ``'processed'``.
            - ``limit`` (str): Maximum number of results to return (as string). Example: ``'20'``.
            - ``categories`` (list of str): Filter by category keywords. Example: ``['Petrobras', 'Vale']``.
            - ``text`` (str): Full-text search filter.
            - ``tags`` (list of str): Filter by tag values. Example: ``['PETR4', 'VALE3']``.

            Field is not required. Default: ``{}`` (returns latest news without filters).
        """
        if settings is None:
            settings = {}
        self.__send({'action': 'latest-news', 'settings': settings})

    def available_filters(self, settings: Optional[Dict[str, Any]] = None):
        """
        Request all distinct filter values currently available in the cache.
        The server responds with an ``available-filters`` event listing each filter
        dimension and its distinct available values.

        Parameters
        ----------
        settings: dict
            Optional narrowing filters. All fields are optional.
            Accepts the same keys as :meth:`latest_news` ``settings``.
            Field is not required. Default: ``{}`` (returns all available filter values).
        """
        if settings is None:
            settings = {}
        self.__send({'action': 'available-filters', 'settings': settings})

    def post_metrics(self, tracking: Dict[str, Any]):
        """
        Report a user engagement event for analytics tracking.
        ``view`` events trigger incremental metrics broadcasts to all clients
        currently watching metrics via :meth:`watch_metrics`.

        The server responds with a ``post-metrics`` acknowledgement event.

        Parameters
        ----------
        tracking: dict
            Engagement event record.
            Required keys:

            - ``event_type`` (str): Type of engagement. Values: ``'view'``, ``'filter'``.
            - ``origin`` (str): Application or page that generated the event. Example: ``'mobile-app'``.

            Optional keys:

            - ``news_id`` (str): ID of the news item. Required for ``view`` events. Example: ``'664f1a2b3c4d5e6f7a8b9c0d'``.
            - ``session_id`` (str): Client session identifier for deduplication. Example: ``'abc123'``.
            - ``metadata`` (dict): Arbitrary extra information about the event.

            Field is required.
        """
        self.__send({'action': 'post-metrics', 'tracking': tracking})

    def watch_metrics(self):
        """
        Start receiving incremental view-count updates for news items seen during
        the current session. Requires an active subscription (call :meth:`subscribe` first).

        The server responds with a ``watch-metrics`` event containing the full view-count
        snapshot for the current session.  Subsequent view-count changes are pushed
        automatically as ``incremental-watch-metrics`` events.
        """
        self.__send({'action': 'watch-metrics'})
