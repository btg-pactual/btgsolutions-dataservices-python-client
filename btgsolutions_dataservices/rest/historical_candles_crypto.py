from typing import Optional
from ..exceptions import BadResponse, MarketTypeError
import requests
from ..config import url_apis_v3
from .authenticator import Authenticator
import json
import pandas as pd

class HistoricalCandlesCrypto:
    """
    This class provides historical candles for cryptocurrencies.

    Available tickers: ETH, SOL, BTC
    Available exchanges: coinbase, mercado_bitcoin, consolidated
    Available currencies: BRL, USD
    Available candles: '1s', '30s', '1m', '5m', '15m', '30m', '1h'

    * Main use case - Interday:

    >>> from btgsolutions_dataservices import HistoricalCandlesCrypto
    >>> hist_candles = HistoricalCandlesCrypto(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> hist_candles.get_interday_history_candles(
    >>>     ticker = 'BTC',
    >>>     currency = 'BRL',
    >>>     exchange = 'consolidated',
    >>>     start_date = '2025-06-01',
    >>>     end_date = '2025-07-01', 
    >>>     timezone = 'UTC',
    >>>     raw_data = False
    >>> )

    * Main use case - Intraday:

    >>> hist_candles.get_intraday_history_candles(
    >>>     ticker = 'BTC',
    >>>     currency = 'BRL',
    >>>     exchange = 'consolidated',
    >>>     date = '2025-06-01', 
    >>>     timezone = 'America/Sao_Paulo',
    >>>     candle='1h',
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
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"authorization {self.token}"}

    def get_intraday_history_candles(
        self,
        ticker:str,
        currency:str,
        exchange:str,
        date:str,
        candle:str,
        timezone:str,
        raw_data:bool=False
    ):
        """
        This method provides historical intraday candles for cryptocurrencies.

        Parameters
        ----------------
        ticker: str
            Cryptocurrency ticker.
            Field is required. Allowed values: 'BTC', 'ETH', 'SOL'.
        currency: str
            Currency for the prices.
            Field is required. Allowed values: 'BRL' or 'USD'.
        exchange: str
            Exchange name.
            Field is required. Allowed values: 'coinbase', 'mercado_bitcoin', 'consolidated'.
        date: string<date>
            Date of requested data. Format: "YYYY-MM-DD".
            Field is required. Example: '2025-06-01'.
        candle: str
            Candle period.
            Field is required. Allowed values: '1s', '30s', '1m', '5m', '15m', '30m', '1h'.
        timezone: str
            Timezone of the datetime.
            Field is required. Allowed values: 'America/Sao_Paulo' or 'UTC'.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """     
        
        url = f"{url_apis_v3}/marketdata/history/candles/intraday/crypto?ticker={ticker}&currency={currency}&exchange={exchange}&date={date}&candle={candle}&timezone={timezone}"
        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            return response_data if raw_data else pd.DataFrame(response_data)

        response = json.loads(response.text)
        raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')
    
    def get_interday_history_candles(
        self,
        ticker:str,
        currency:str,
        exchange:str,
        start_date:str,
        end_date:str,
        timezone:str,
        raw_data:bool=False
    ):
        """
        This method provides historical daily candles for cryptocurrencies.

        Parameters
        ----------------
        ticker: str
            Cryptocurrency ticker.
            Field is required. Allowed values: 'BTC', 'ETH', 'SOL'.
        currency: str
            Currency for the prices.
            Field is required. Allowed values: 'BRL' or 'USD'.
        exchange: str
            Exchange name.
            Field is required. Allowed values: 'coinbase', 'mercado_bitcoin', 'consolidated'.
        start_date: string<date>
            Start date of analysis. Format: "YYYY-MM-DD".
            Field is required. Example: '2025-06-01'.
        end_date: string<date>
            End date of analysis. Format: "YYYY-MM-DD".
            Field is required. Example: '2025-07-01'.
        timezone: str
            Timezone of the datetime.
            Field is required. Allowed values: 'America/Sao_Paulo' or 'UTC'.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """     
        
        url = f"{url_apis_v3}/marketdata/history/candles/interday/crypto?ticker={ticker}&currency={currency}&exchange={exchange}&start_date={start_date}&end_date={end_date}&timezone={timezone}"
        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            return response_data if raw_data else pd.DataFrame(response_data)

        response = json.loads(response.text)
        raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')

    def get_available_tickers(
        self,
        exchange:str,
        date:str,
    ):
        """
        This method provides all cryptocurrency tickers available for query.   

        Parameters
        ----------------
        exchange: str
            Exchange name.
            Field is required. Allowed values: 'coinbase', 'mercado_bitcoin', 'consolidated'.
        date: string<date>
            Date of requested data. Format: "YYYY-MM-DD".
            Field is required. Example: '2023-01-13'.
        """

        url = f"{url_apis_v3}/marketdata/history/candles/available-tickers/crypto?date={date}&exchange={exchange}"

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200: return response.json()
        response = response.json()
        raise BadResponse(f'Error: {response.get("ApiClientError", "") or response.get("ApiServerMessage", "")}.\n{response.get("SuggestedAction", "")}')