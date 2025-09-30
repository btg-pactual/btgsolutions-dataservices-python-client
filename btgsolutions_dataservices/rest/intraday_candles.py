
from typing import Optional
from ..exceptions import BadResponse, MarketTypeError, DelayError
import requests
from ..config import url_apis_v3
import json
import pandas as pd
from .authenticator import Authenticator

class IntradayCandles:
    """
    This class provides realtime intraday candles for a given ticker or all tickers available for query.

    * Main use case:

    >>> from btgsolutions_dataservices import IntradayCandles
    >>> intraday_candles = IntradayCandles(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> candles = intraday_candles.get_intraday_candles(
    >>>     market_type = 'stocks',
    >>>     tickers = ['PETR4', 'ABEV3'],
    >>>     candle_period = '1m',
    >>>     delay='delayed',
    >>>     mode='absolute',
    >>>     timezone='UTC',
    >>>     raw_data=False
    >>> )    
    >>> PETR4 = candles.get('PETR4')
    >>> ABEV3 = candles.get('ABEV3')

    >>> intraday_candles.get_available_tickers(
    >>>     market_type='stocks',
    >>>     delay='delayed'
    >>> )

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """
    def __init__(
        self,
        api_key: Optional[str]
    ):
        self.api_key = api_key
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"authorization {self.token}"}

    def get_intraday_candles(
        self,
        market_type:str,
        tickers:list,
        delay:str,
        timezone:str,
        candle_period:str,
        start:int=0,
        end:int=0,
        mode:str='absolute',
        raw_data:bool=False,
        cross_filter:str='',
    ):     
        """
        This method provides realtime intraday candles for a given ticker.

        Parameters
        ----------------
        market_type: str
            Market type.
            Options: 'stocks', 'derivatives', 'options' or 'indices'.
            Field is required.
        tickers: list of str
            Tickers that needs to be returned.
            Example: ['PETR4', 'ABEV3']
            Field is required.
        delay: str
            Data delay.
            Options: 'delayed' or 'realtime'.
            Field is required.
        timezone: str
            Timezone of the datetime.
            Options: 'America/Sao_Paulo' or 'UTC'.
            Field is required.
        candle_period: str
            Grouping interval.
            Example: '1m', '5m', '30m', '1h' or '1d'.
            Field is required.
        start: int
            Start date (in Unix timestamp format).
        end: int
            End date (in Unix timestamp format)
        mode: str
            Candle mode.
            Example: 'absolute', 'relative' or 'spark'.
            Default: absolute.
        cross_filter: str
            Filter trades by cross status. Available only when market_type is derivatives.
            Options: 'all', 'only_cross' or 'without_cross'.
            Default: 'all'.
        raw_data: bool
            If false, returns data in a dict of dataframes. If true, returns raw data.
            Default: False.
        """

        if market_type not in ['stocks', 'derivatives', 'options', 'indices']: raise MarketTypeError(f"Must provide a valid 'market_type' parameter. Input: '{market_type}'. Accepted values: 'stocks', 'derivatives', 'options' or 'indices'.")

        if delay not in ['delayed', 'realtime']: raise DelayError(f"Must provide a valid 'delay' parameter. Input: '{delay}'. Accepted values: 'delayed' or 'realtime'.")
        
        if cross_filter and market_type != 'derivatives': raise DelayError(f"The 'cross_filter' flag is only valid for market_type 'derivatives'.")

        tickers = ','.join(tickers) if type(tickers) is list else tickers 

        url = f"{url_apis_v3}/marketdata/candles/intraday/{delay}/{market_type}?tickers={tickers}&candle_period={candle_period}&mode={mode}&timezone={timezone}"

        if start: url += f'&start={start}'

        if end: url += f'&end={end}'
        
        if cross_filter: url += f'&cross_filter={cross_filter}'

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            if raw_data: return response_data
            ret = {}
            for key, value in response_data.items():
                ret[key] = pd.DataFrame(value) 
            return ret
        raise BadResponse(response.json())

    def get_available_tickers(
        self,
        market_type:str,
        delay:str,
    ):
        """
        This method provides all tickers available for query.   

        Parameters
        ----------------
        market_type: str
            Market type.
            Options: 'stocks', 'derivatives' or 'options'.
            Field is required.
        delay: str
            Data delay.
            Options: 'delayed' or 'realtime'.
            Field is required.
        """

        if market_type not in ['stocks', 'derivatives', 'options', 'indices']: raise MarketTypeError(f"Must provide a valid 'market_type' parameter. Input: '{market_type}'. Accepted values: 'stocks', 'derivatives', 'options' or 'indices'.")

        if delay not in ['delayed', 'realtime']: raise DelayError(f"Must provide a valid 'delay' parameter. Input: '{delay}'. Accepted values: 'delayed' or 'realtime'.")
        
        url = f"{url_apis_v3}/marketdata/candles/intraday/{delay}/{market_type}/available_tickers"

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200: return json.loads(response.text)
        raise BadResponse(response.json())