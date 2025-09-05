from typing import Optional, Callable, List
import websocket
import time
from datetime import date, datetime
import multiprocessing
import logging
from logging.handlers import QueueHandler, QueueListener
import json
import ssl
import threading
import uuid
from ..rest import Authenticator
from ..config import market_data_socket_urls, market_data_feedb_socket_urls, REALTIME, B3, TRADES, BOOKS, FEED_A, FEED_B, MAX_WS_RECONNECT_RETRIES
from .websocket_default_functions import _on_open, _on_message_already_serialized, _on_error, _on_close

multiprocessing.set_start_method("spawn", force=True)

class LogConstFilter(logging.Filter):
    def __init__(self, consts):
        super().__init__()
        self.consts = consts

    def filter(self, record):
        for key, value in self.consts.items():
            setattr(record, key, value)
        return True

class MarketDataFeed:
    """
    WebSocket client that connects with BTG Solutions Data Services WebSocket servers. The servers streams realtime and delayed market data, such as trades and book events.
    This is a multiprocessing-based WebSocket client designed for high-performance, scalable message handling applications. It leverages a system of inter-process communication to efficiently separate concerns and prevent the main application thread from blocking during WebSocket operations or message processing.

    * Main use case:

    >>> from btgsolutions_dataservices import MarketDataFeed
    >>> ws = MarketDataFeed(
    >>>     api_key='YOUR_API_KEY',
    >>>     stream_type='realtime',
    >>>     exchange='b3',
    >>>     data_type='trades',
    >>>     data_subtype='stocks',
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
        Options: 'trades', 'processed-trades', 'books', 'indices', 'securities', 'stoploss', 'candles-1S', 'candles-1M', 'instrument_status', 'settlement-price'.
        Field is not required. Default: 'trades'.
    data_subtype: str
        Market Data subtype (when applicable).
        Options: 'stocks', 'options', 'derivatives'.
        Field is not required. Default: None.
    feed: str
        Market Data Feed.
        Options: 'A', 'B'.
        Field is not required. Default: 'A' (enable).
    ssl: bool
        Enable or disable ssl configuration.
        Field is not required. Default: True (enable).
    reconnect: bool
        Try reconnect if connection is closed.
        Field is not required.
        Default: True.
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
    log_level: str
        Log level sets how much information the program will print to the log file.
        Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'NOTSET'.
        'DEBUG' provides the most detailed logs, with verbosity decreasing through each level down to 'NOTSET', which disables all logging.
        Field is not required. Default: 'DEBUG'.
    """

    def __init__(
        self, 
        api_key: str,
        stream_type: Optional[str]=REALTIME,
        exchange: Optional[str]=B3,
        data_type: Optional[str]=TRADES,
        data_subtype: Optional[str]=None,
        feed: Optional[str]=FEED_A,
        ssl: Optional[bool]=True,
        reconnect: bool=True,
        on_open: Optional[Callable]=None,
        on_message: Optional[Callable]=None,
        on_error: Optional[Callable]=None,
        on_close: Optional[Callable]=None,
        log_level: str="DEBUG",
    ):

        if feed == FEED_B:
            url_feed_map = market_data_feedb_socket_urls
        else:
            url_feed_map = market_data_socket_urls

        try:
            self.url = url_feed_map[exchange][data_type][stream_type][data_subtype]
        except:
            raise Exception(f"There is no WebSocket type for your specifications (stream_type:{stream_type}, exchange:{exchange}, data_type:{data_type}, data_subtype:{data_subtype})\nPlease check your request parameters and try again")
        
        self.__authenticator = Authenticator(api_key)

        self.data_type = data_type
        self.on_open = _on_open if on_open is None else on_open
        self.on_message = _on_message_already_serialized if on_message is None else on_message
        self.on_error = _on_error if on_error is None else on_error
        self.on_close = _on_close if on_close is None else on_close
        
        self.ssl = ssl
        self.reconnect = reconnect
        self.__nro_reconnect_retries = 0

        client_feed = f'feed_{exchange}_{data_type}_{stream_type}_{data_subtype}'
        client_id = str(uuid.uuid4())

        self.server_message_queue = multiprocessing.Queue()
        self.client_message_queue = multiprocessing.Queue()
        self.log_queue = multiprocessing.Queue()

        log_level = getattr(logging, log_level)
        self.log_level = log_level

        log_constants = {'client_feed': client_feed, 'client_id': client_id}
        log_handler = logging.FileHandler(filename=f"MarketDataFeed_{date.today().isoformat()}.log")
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(client_feed)s - %(client_id)s - %(levelname)s - %(message)s'))
        log_handler.addFilter(LogConstFilter(log_constants))

        log_queue_listener = QueueListener(self.log_queue, log_handler)
        log_queue_listener.start()

        self.logger = logging.getLogger("main")
        self.logger.setLevel(log_level)
        self.logger.addHandler(QueueHandler(self.log_queue))

        self.process = None
        self.running = False

        self.head_message_count = 0
        self.head_avg_latency = 0

        self.instruments = []

    def set_instruments(self, instruments: List[str]):
        self.instruments = instruments

    def _ws_client_process(self, server_message_queue: multiprocessing.Queue, client_message_queue: multiprocessing.Queue, log_queue: multiprocessing.Queue, log_level: int):

        logger = logging.getLogger("client")
        logger.setLevel(log_level)
        logger.addHandler(QueueHandler(log_queue))

        def on_message(ws, message):
            message = json.loads(message)
            server_message_queue.put(message)

            if self.log_level != logging.DEBUG:
                return

            msg_datetime = None
            if self.data_type == BOOKS:
                bid = message.get("bid")
                offer = message.get("offer")
                if bid:
                    msg_datetime = bid[0]["datetime"]
                elif offer:
                    msg_datetime = offer[0]["datetime"]
            else:
                msg_datetime = message.get("tTime")
            if msg_datetime:
                msg_datetime = datetime.strptime(msg_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
                latency = (time.time() - msg_datetime.timestamp()) * 1000
                self.head_message_count += 1
                self.head_avg_latency += (latency - self.head_avg_latency) / self.head_message_count

        def on_error(ws, error):
            logger.error(f"On Error | {error}")
            self.on_error(error)

        def on_close(ws, close_status_code, close_msg):
            logger.warning(f"On Close | Connection closed")
            self.on_close(close_status_code, close_msg)
            if self.reconnect:
                if self.__nro_reconnect_retries == MAX_WS_RECONNECT_RETRIES:
                    logger.critical(f"On Close | Maximum number of reconnect attempts reached")
                    return
                self.__nro_reconnect_retries += 1
                logger.warning(f"On Close | Reconnecting... attempt: {self.__nro_reconnect_retries}/{MAX_WS_RECONNECT_RETRIES}")
                run_forever_new_thread()

        def on_open(ws):
            logger.info(f"On Open | Connection open")
            if self.instruments:
                logger.info(f"On Open | Subscribing to {len(self.instruments)} instruments")
                self.subscribe(self.instruments)
            self.on_open()
            self.__nro_reconnect_retries = 0

        ws = websocket.WebSocketApp(
            url=self.url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            header={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36",
                "Sec-WebSocket-Protocol": self.__authenticator.token,
            }
        )

        def run_forever_new_thread():
            ssl_conf = {} if self.ssl else {"sslopt": {"cert_reqs": ssl.CERT_NONE}}
            t = threading.Thread(target=ws.run_forever, kwargs=ssl_conf)
            t.daemon = True
            t.start()

            while True:
                if ws.sock is not None and ws.sock.connected:
                    break
                pass

            log_metrics_interval = 5
            log_timer = time.time()
            while True:
                try:
                    if not client_message_queue.empty():
                        msg = client_message_queue.get()
                        ws.send(json.dumps(msg))
                    
                    if self.log_level != logging.DEBUG:
                        continue
                    
                    if time.time() - log_timer >= log_metrics_interval:
                        if self.head_avg_latency == 0:
                            logger.debug(f"HEAD - (ServerQ) Relative Latency: N/A; Throughput: N/A")
                        else:
                            logger.debug(f"HEAD - (ServerQ) Relative Latency: {round(self.head_avg_latency, 1)} ms; Throughput: {round(self.head_message_count/log_metrics_interval, 1)} msg/s")
                        self.head_message_count = 0
                        self.head_avg_latency = 0
                        log_timer = time.time()

                except Exception as e:
                    time.sleep(0.01)

        run_forever_new_thread()

    def run(self):
        """
        Opens a new connection with the websocket server.
        """
        self.process = multiprocessing.Process(target=self._ws_client_process, args=(self.server_message_queue, self.client_message_queue, self.log_queue, self.log_level))
        self.process.start()
        self.running = True

        def run_on_new_thread(*args):
            log_timer = time.time()
            log_metrics_interval = 5

            message_count = 0
            latency_message_count = 0
            latency_average = 0
            while self.running:
                if not self.server_message_queue.empty():
                    msg = self.server_message_queue.get()
                    self.on_message(msg)

                    if self.log_level != logging.DEBUG:
                        continue
                    
                    message_count += 1
                    msg_datetime = None
                    if self.data_type == BOOKS:
                        bid = msg.get("bid")
                        offer = msg.get("offer")
                        if bid:
                            msg_datetime = bid[0]["datetime"]
                        elif offer:
                            msg_datetime = offer[0]["datetime"]
                    else:
                        msg_datetime = msg.get("tTime")
                    if msg_datetime:
                        msg_datetime = datetime.strptime(msg_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
                        latency = (time.time() - msg_datetime.timestamp()) * 1000
                        latency_message_count += 1
                        latency_average += (latency - latency_average) / latency_message_count

                if time.time() - log_timer >= log_metrics_interval:
                    server_queue_size = self.server_message_queue.qsize()
                    client_queue_size = self.client_message_queue.qsize()
                    if message_count == 0:
                        self.logger.debug(f"TAIL - (ServerQ) Relative Latency: N/A; Throughput: N/A; Size: {server_queue_size} | (ClientQ) Size: {client_queue_size}")
                    else:
                        self.logger.debug(f"TAIL - (ServerQ) Relative Latency: {round(latency_average, 1)} ms; Throughput: {round(message_count/log_metrics_interval, 1)} msg/s; Size: {server_queue_size} | (ClientQ) Size: {client_queue_size}")
                    log_timer = time.time()
                    message_count = 0
                    latency_message_count = 0
                    latency_average = 0
        
        threading.Thread(target=run_on_new_thread).start()

    def close(self):
        """
        Closes the connection with the websocket server.
        """
        self.running = False
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join()

    def _send(self, message):
        """
        Sends a message to the websocket server.
        """
        if not isinstance(message, str):
            message = json.dumps(message)
        self.client_message_queue.put(json.loads(message))

    def subscribe(self, list_instruments: List[str], n=None, initial_snapshot: bool=False):
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
            self._send(message)
        else:
            self._send({'action': 'subscribe', 'params': list_instruments})

    def unsubscribe(self, list_instruments: List[str]):
        """
        Unsubscribes a list of instruments.

        Parameters
        ----------
        list_instruments: list
            Field is required.
        """
        self._send({'action': 'unsubscribe', 'params': list_instruments})
    
    def subscribed_to(self):
        """
        Return client subscribed tickers.
        """
        self._send({'action': 'subscribed_to'})

    def available_to_subscribe(self):
        """
        Return avaiable tickers to subscribe.
        """
        self._send({'action': 'available_to_subscribe'})

    def get_last_event(self, ticker: str):
        """
        Get the last event for the provided ticker.

        Parameters
        ----------
        ticker: str
            Field is required.
        """
        self._send({'action': 'get_last_event', 'params': ticker})