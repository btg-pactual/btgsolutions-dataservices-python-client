from typing import Optional
from ..exceptions import BadResponse
import requests
from ..config import base_url
from .authenticator import Authenticator
import json
import pandas as pd

class Quotes:
    """
    This class provides ticker quote information and quotes sorted by top-bottom quote variation, filtered by ticker market type.

    * Main use case:

    >>> from btgsolutions_dataservices import Quotes
    >>> quotes = Quotes(
    >>>     api_key='YOUR_API_KEY',
    >>> )

    >>> quotes.get_quote(
    >>>     market_type = 'stocks',
    >>>     tickers = ['PETR4', 'VALE3'],
    >>> )

    >>> quotes.get_top_bottom(
    >>>     market_type = 'stocks',
    >>>     ticker_type = 'IBOV',
    >>> )

    >>> quotes.get_available_tickers(market_type="stocks")

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
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"authorization {self.token}"}

        self.available_market_types = ['stocks', 'options', 'derivatives']
        self.available_modes = ['realtime', 'delayed']
        self.available_variations = ['intraday', 'interday']

    def get_quote(
        self,
        tickers:list,
        market_type:str,
        mode:str='realtime',
        raw_data:bool=False,
    ):
        """
        This method provides realtime and delayed quote information for a given ticker.

        Parameters
        ----------------
        tickers: list
            List of tickers that needs to be returned.
            Field is required. Example: ['VALE3'], ['PETR4', 'PRIO3'].
        market_type: str
            Market type.
            Field is required. Example: 'stocks', 'options', 'derivatives'.
        mode: str
            Realtime or 15-minutes delayed.
            Field is required. Example: 'realtime' or 'delayed'.
            Default: 'realtime'.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """     

        if market_type not in self.available_market_types:
            raise Exception(f"Must provide a valid 'market_type' parameter. Input: '{market_type}'. Accepted values: {self.available_market_types}")
        
        if mode not in self.available_modes:
            raise Exception(f"Must provide a valid 'mode' parameter. Input: '{mode}'. Accepted values: {self.available_modes}")

        try:
            tickers = ','.join(tickers)
        except:
            raise Exception(f"'tickers' parameter must be an array of strings.")

        url = f"{base_url}/api/v1/marketdata/br/b3/{mode}/quotes/{market_type}/tickers?tickers={tickers}"

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            return response_data if raw_data else pd.DataFrame(response_data)

        response = json.loads(response.text)
        raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')

    def get_top_bottom(
        self,
        market_type:str,
        mode:str='realtime',
        ticker_type:str='IBOV',
        variation:str='interday',
        n:int=5,
        raw_data:bool=False,
    ):
        """
        This method provides realtime and delayed quotes sorted by top-bottom quote variation, filtered by ticker market type.

        Parameters
        ----------------
        market_type: str
            Market type.
            Field is required. Example: 'stocks', 'options', 'derivatives'.
        mode: str
            Realtime or 15-minutes delayed.
            Field is not required. Example: 'realtime' or 'delayed'.
            Default: 'realtime'.
        ticker_type: str
            Type of tickers to be returned.
            Field is not required. Example: 'SHARE', 'BDR', 'FII', 'ETF', 'UNIT', 'IBOV'.
            Default: 'IBOV'.
        variation: str
            Choose between intraday or interday quotes.
            Field is not required. Example: 'interday' or 'intraday'.
            Default: 'interday'.
        n: int
            Top-N tickers to be returned.
            Field is not required.
            Default: 5.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """

        if market_type not in self.available_market_types:
            raise Exception(f"Must provide a valid 'market_type' parameter. Input: '{market_type}'. Accepted values: {self.available_market_types}")
        
        if mode not in self.available_modes:
            raise Exception(f"Must provide a valid 'mode' parameter. Input: '{mode}'. Accepted values: {self.available_modes}")
        
        if variation not in self.available_variations:
            raise Exception(f"Must provide a valid 'variation' parameter. Input: '{variation}'. Accepted values: {self.available_variations}")

        if not isinstance(n, int):
            raise Exception(f"'n' parameter must be an integer greater than 0. Input: '{n}'")
    
        if not isinstance(ticker_type, str):
            raise Exception(f"'ticker_type' parameter must be a string. Input: '{ticker_type}'")

        url = f"{base_url}/api/v1/marketdata/br/b3/{mode}/quotes/{market_type}/top-bottom?variation={variation}&n={n}&type={ticker_type}"

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            if raw_data:
                return response_data
            else:
                return {
                    'top': pd.DataFrame(response_data.get('top')),
                    'bottom': pd.DataFrame(response_data.get('bottom')),
                }

        response = json.loads(response.text)
        raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')

    def get_available_tickers(self, market_type:str, mode:str='realtime'):  
        """
        This method provides all tickers available for query, for the provided market type.

        Parameters
        ----------------
        market_type: str
            Market type.
            Field is required. Example: 'stocks', 'options', 'derivatives'.
        mode: str
            Realtime or 15-minutes delayed.
            Field is not required. Example: 'realtime' or 'delayed'.
            Default: 'realtime'.
        """

        if market_type not in self.available_market_types:
            raise Exception(f"Must provide a valid 'market_type' parameter. Input: '{market_type}'. Accepted values: {self.available_market_types}")

        if mode not in self.available_modes:
            raise Exception(f"Must provide a valid 'mode' parameter. Input: '{mode}'. Accepted values: {self.available_modes}")

        url = f"{base_url}/api/v1/marketdata/br/b3/{mode}/quotes/{market_type}/available-tickers"
        response = requests.request("GET", url,  headers=self.headers)

        if response.status_code == 200:
            return json.loads(response.text)
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')
