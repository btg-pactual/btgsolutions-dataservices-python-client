from typing import List, Optional
from ..exceptions import BadResponse
import requests
from ..config import base_url
from .authenticator import Authenticator
import pandas as pd
import json

class ReferenceData:
    """
    This class provides market reference data, such as ticker info, broker codes, index composition, etc.

    * Main use case:

    >>> from btgsolutions_dataservices import ReferenceData
    >>> ref = ReferenceData(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> ref.ticker_reference(
    >>>     tickers = ['PETR4', 'VALE3']
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

    def ticker_reference(self, tickers: List[str], raw_data: bool=False):
        """
        This method provides ticker reference data from current day, such as SecurityId, Currency, MinLotSize, MinTickSize, etc.

        Parameters
        ----------------
        tickers: List[str]
            List of tickers.
            Field is required. Example: ['PETR4', 'VALE3'].
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """

        if not isinstance(tickers, list) or len(tickers) == 0:
            raise BadResponse(f'Error: Must provide a valid list of tickers')
        
        url = f"{base_url}/api/v1/marketdata/br/b3/snapshot/instruments/batch?tickers={','.join(tickers)}"

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            if raw_data:
                return response.json()
            else:
                return pd.DataFrame(response.json().values())
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("ApiClientError", "")}')