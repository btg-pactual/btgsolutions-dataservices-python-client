
from typing import Optional
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
import json
from .authenticator import Authenticator
import pandas as pd

class StockLoan:
    """
    This class provides trades related to stock loan operations.

    * Main use case:

    >>> from btgsolutions_dataservices import StockLoan
    >>> stock_loan = StockLoan(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> trades = stock_loan.get_trades(
    >>>     ticker = 'PETR4'
    >>> )
    >>> trades = stock_loan.get_paginated_trades(
    >>>     page = 1,
    >>>     limit = 1000
    >>> )
    >>> stock_loan.get_available_tickers()

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

    def get_trades(
        self,
        ticker:Optional[str]='',
    ):     
        """
        Returns trades related to stock loan operations.

        Parameters
        ----------------
        ticker : str, optional
            The ticker symbol to be returned.
            Example: 'PETR4'

        """
        page = 1
        df = pd.DataFrame()
        while True:
            url = f"{url_api_v1}/marketdata/stock-loan/daily-trades?page={page}&limit=20000"
            if ticker: url += f'&ticker={ticker}'
            response = requests.request("GET", url,  headers=self.headers)
            if response.status_code != 200: raise BadResponse(response.json())
            response = response.json()
            df = pd.concat([df, pd.DataFrame(response['data'])])
            if response['totalPages'] <= page: break
            page += 1
        
        return df.reset_index(drop=True)
    
    def get_paginated_trades(
        self,
        page:int,
        limit:int,
        ticker:Optional[str]='',
    ):     
        """
        Returns paginated trades related to stock loan operations.

        Parameters
        ----------------
        ticker : str, optional
            The ticker symbol to be returned.
            Example: 'PETR4'

        page : int
            Page number for paginated results.
            Example: 1

        limit : int
            Maximum number of items to return per page.
            Example: 1000

        """
        url = f"{url_api_v1}/marketdata/stock-loan/daily-trades?page={page}&limit={limit}"
        if ticker: url += f'&ticker={ticker}'
        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200: return json.loads(response.text)
        raise BadResponse(response.json())

    def get_available_tickers(
        self,
    ):
        """
        This method provides all tickers available for query.   
        """
        url = f"{url_api_v1}/marketdata/stock-loan/available-tickers"
        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200: return json.loads(response.text)
        raise BadResponse(response.json())