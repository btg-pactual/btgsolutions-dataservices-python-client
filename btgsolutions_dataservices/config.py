base_url = "https://dataservices.btgpactualsolutions.com"

# WS
url_ws = "wss://dataservices.btgpactualsolutions.com/stream/"
ws_br_b3_base_path = "/stream/v1/marketdata/br/b3/"

# Rest
url_apis = "https://dataservices.btgpactualsolutions.com/api/v2"
url_api_v1 = "https://dataservices.btgpactualsolutions.com/api/v1"
url_apis_v3 = "https://dataservices.btgpactualsolutions.com/api/v3"

# WebSocket
MAX_WS_RECONNECT_RETRIES = 5

REALTIME = 'realtime'
DELAYED = 'delayed'
THROTTLE = 'throttle'
PROCESSED = 'processed'

BR = 'brazil'
MX = 'mexico'
CL = 'chile'

B3 = 'b3'
BMV = 'bmv'
NASDAQ = 'nasdaq'

TRADES = 'trades'
PROCESSEDTRADES = 'processed-trades'
INSTRUMENTSTATUS = 'instrument_status'
SETTLEMENTPRICES = 'settlement-price'
BOOKS = 'books'
INDICES = 'indices'

ALL = 'all'
STOCKS = 'stocks'
OPTIONS = 'options'
DERIVATIVES = 'derivatives'

VALID_STREAM_TYPES = [REALTIME, DELAYED, THROTTLE]
VALID_COUNTRIES = [BR, MX, CL]
VALID_EXCHANGES = [B3, BMV, NASDAQ]
VALID_MARKET_DATA_TYPES = [
    TRADES,
    PROCESSEDTRADES,
    BOOKS,
    INDICES,
    INSTRUMENTSTATUS,
    SETTLEMENTPRICES
]
VALID_MARKET_DATA_SUBTYPES = [ALL, STOCKS, OPTIONS, DERIVATIVES]

FEED_A = "A"
FEED_B = "B"
VALID_FEEDS = [FEED_A, FEED_B]

market_data_socket_urls = {
    B3: {
        TRADES: {
            REALTIME: {
                STOCKS: f'{base_url}{ws_br_b3_base_path}trade/{STOCKS}',
                OPTIONS: f'{base_url}{ws_br_b3_base_path}trade/{OPTIONS}',
                DERIVATIVES: f'{base_url}{ws_br_b3_base_path}trade/{DERIVATIVES}',
            },
            DELAYED: {
                STOCKS: f'{base_url}{ws_br_b3_base_path}{DELAYED}/trade/{STOCKS}/{DELAYED}',
                OPTIONS: f'{base_url}{ws_br_b3_base_path}{DELAYED}/trade/{OPTIONS}/{DELAYED}',
                DERIVATIVES: f"{base_url}{ws_br_b3_base_path}{DELAYED}/trade/{DERIVATIVES}/{DELAYED}",
            },
        },
        PROCESSEDTRADES: {
            REALTIME: {
                STOCKS: f'{base_url}{ws_br_b3_base_path}{PROCESSED}-trade/{STOCKS}',
                OPTIONS: f'{base_url}{ws_br_b3_base_path}{PROCESSED}-trade/{OPTIONS}',
                DERIVATIVES: f'{base_url}{ws_br_b3_base_path}{PROCESSED}-trade/{DERIVATIVES}',
            },
        },
        BOOKS: {
            REALTIME: {
                STOCKS: f'{base_url}{ws_br_b3_base_path}book-snapshot-mbp/{STOCKS}',
                OPTIONS: f'{base_url}{ws_br_b3_base_path}book-snapshot-mbp/{OPTIONS}',
                DERIVATIVES: f'{base_url}{ws_br_b3_base_path}book-snapshot-mbp/{DERIVATIVES}',
            },
            THROTTLE: {
                STOCKS: f"{base_url}{ws_br_b3_base_path}throttled/book-snapshot-mbp/{STOCKS}",
                OPTIONS: f"{base_url}{ws_br_b3_base_path}throttled/book-snapshot-mbp/{OPTIONS}",
                DERIVATIVES: f"{base_url}{ws_br_b3_base_path}throttled/book-snapshot-mbp/{DERIVATIVES}",
            },
        },
        INDICES: {
            REALTIME: {
                ALL: f"{url_ws}v2/marketdata/{INDICES}",
            },
            DELAYED: {
                ALL: f"{url_ws}v2/marketdata/{INDICES}/{DELAYED}",
            }
        },
        INSTRUMENTSTATUS: {
            REALTIME: {
                STOCKS: f"{base_url}{ws_br_b3_base_path}instrument-status/{STOCKS}",
                DERIVATIVES: f"{base_url}{ws_br_b3_base_path}instrument-status/{DERIVATIVES}",
                OPTIONS: f"{base_url}{ws_br_b3_base_path}instrument-status/{OPTIONS}",
            }
        },
        SETTLEMENTPRICES: {
            REALTIME: {
                ALL: f"{base_url}{ws_br_b3_base_path}{SETTLEMENTPRICES}",
            }
        }
    },
    BMV: {
        TRADES: {
            REALTIME: {
                ALL: f'{url_ws}v1/marketdata/bmv/{TRADES}',
            },
        },
    },
    NASDAQ: {
        TRADES: {
            REALTIME: {
                ALL: f'{url_ws}v1/marketdata/us/nasdaq/{TRADES}',
            }
        }
    }
}

market_data_feedb_socket_urls = {
}

hfn_socket_urls = {
    BR: {
        REALTIME: f'{url_ws}v2/hfn/{BR}',
    },
    CL: {
        REALTIME: f'{url_ws}v2/hfn/{CL}',
    },
}
