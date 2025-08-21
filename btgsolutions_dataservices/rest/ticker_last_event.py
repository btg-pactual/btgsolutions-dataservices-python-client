from typing import Optional, List
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator
import pandas as pd
import json

class TickerLastEvent:
    """
    This class provides the last market data event available, for the provided ticker

    * Main use case:

    >>> from btgsolutions_dataservices import TickerLastEvent
    >>> last_event = TickerLastEvent(
    >>>     api_key='YOUR_API_KEY',
    >>> )

    >>> last_event.get_trades(
    >>>     data_type = 'equities',
    >>>     ticker = 'PETR4',
    >>>     raw_data = False
    >>> )

    >>> last_event.get_tob(
    >>>     data_type = 'stocks',
    >>>     raw_data = False
    >>> )

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """
    def __init__(
        self,
        api_key:Optional[str]
    ):
        self.api_key = api_key
        self.authenticator = Authenticator(self.api_key)

        self.available_data_types = {
            "trades": ['equities', 'derivatives'],
            "books": ['stocks', 'derivatives', 'options']
        }

    def get_trades(self, data_type:str, ticker:str, raw_data:bool=False):

        """
        This method provides the last market data event available, for the provided ticker.

        Parameters
        ----------------
        data_type: str
            Market Data Type.
            Field is required. 
            Example: 'equities', 'derivatives'.
        ticker: str
            Ticker symbol.
            Field is required. Example: 'PETR4'.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """
        if data_type not in self.available_data_types["trades"]:
            raise Exception(f"Must provide a valid data_type. Valid data types are: {self.available_data_types['trades']}")

        url = f"{url_api_v1}/marketdata/last-event/trades/{data_type}?ticker={ticker}"

        response = requests.request("GET", url,  headers={"authorization": f"Bearer {self.authenticator.token}"})
        if response.status_code == 200:
            if raw_data:
                return response.json()
            else:
                return pd.DataFrame([response.json()])
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("error", "")}')
        
    def get_tobs(self, data_type:str, raw_data:bool=False):

        """
        This method provides the last available top of book for all tickers of the given market type.

        Parameters
        ----------------
        data_type: str
            Market Data Type.
            Field is required. 
            Example: 'stocks', 'derivatives', 'options'.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """

        if data_type not in self.available_data_types["books"]:
            raise Exception(f"Must provide a valid data_type. Valid data types are: {self.available_data_types}")

        url = f"{url_api_v1}/marketdata/last-event/books/top/{data_type}/batch"

        response = requests.request("GET", url,  headers={"authorization": f"Bearer {self.authenticator.token}"})

        if response.status_code == 200:
            if raw_data:
                return response.json()
            else:
                return pd.DataFrame(response.json())
        else:

            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("error", "")}')

    def get_status(self, tickers:List[str]=None, raw_data:bool=False):

        """
        This method provides the current ticker trading status information.

        Parameters
        ----------------
        tickers: List[str]
            Ticker symbol.
            Field is not required. Default: None
            Example: ['PETR4', 'VALE3', 'DOLM25'].
            If no ticker is provided, it returns trading status information for all available tickers.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """

        if tickers:
            tickers = ','.join(tickers)
            url = f"{url_api_v1}/marketdata/last-event/status/all/batch?tickers={tickers}"
        else:
            url = f"{url_api_v1}/marketdata/last-event/status/all/batch"

        response = requests.request("GET", url,  headers={"authorization": f"Bearer {self.authenticator.token}"})
        if response.status_code == 200:
            if raw_data:
                return response.json()
            else:
                return pd.DataFrame(response.json())
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response}')

    def get_available_tickers(self,type:str, data_type:str):

        """
        This method provides all the available tickers for the specific data type.

        Parameters
        ----------------
        type: str
            Data Type.
            Field is required. 
            Example: 'trades', 'books'
        data_type: str
            Market Data Type.
            Field is required. 
            Example: 'equities', 'derivatives', 'options', 'stocks'.
        """

        if type not in self.available_data_types:
            raise Exception(f"Must provide a valid type. Valid data types are: {list(self.available_data_types.keys())}")
        
        if data_type not in self.available_data_types[type]:
            raise Exception(f"Must provide a valid data_type. Valid data types are: {self.available_data_types['books']}")

        url = f"{url_api_v1}/marketdata/last-event/trades/{data_type}/available-tickers" if type == "trades" else \
            f"{url_api_v1}/marketdata/last-event/books/{data_type}/availables"

        response = requests.request("GET", url,  headers={"authorization": f"Bearer {self.authenticator.token}"})
        if response.status_code == 200:
            return response.json()
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("error", "")}')