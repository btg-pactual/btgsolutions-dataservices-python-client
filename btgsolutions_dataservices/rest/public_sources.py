from typing import Optional
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator
import pandas as pd
import json

class PublicSources:
    """
    This class provides data from public sources

    * Main use case:

    >>> from btgsolutions_dataservices import PublicSources
    >>> public_sources = PublicSources(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> public_sources.get_opas(
    >>>     start_date = '2024-05-10',
    >>>     end_date = '2024-05-31'
    >>> )

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """
    def __init__(
        self,
        api_key:str
    ):
        self.api_key = api_key
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"Bearer {self.token}"}

    def get_opas(self, start_date:str, end_date:str, asset:Optional[str]=None, type:Optional[str]=None, raw_data:bool=False): 

        """
        This method uses OPAs filtered by a range of dates (registration_date), asset or type.

        Parameters
        ----------------
        start_date: string<date>
            Lower bound for OPAS. Filtering by registration_date. Format: "YYYY-MM-DD".
            Field is required. Example: '2023-10-06'.
        end_date: string<date>
            Upper bound for OPAS. Filtering by registration_date. Format: "YYYY-MM-DD".
            Field is required. Example: '2023-10-06'.
        asset: str
            Ticker asset.
            Field is not required. Example: VALE. Default: None.
        type: str
            Filtering by OPA type
            Field is not required. Example: VOLUNTARIO. Default: None.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """

        url = f"{url_api_v1}/public-sources/opas?start_date={start_date}&end_date={end_date}" + (f"&asset={asset}" if asset else "") + (f"&type={type}" if type else "") 

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            if raw_data:
                return response.json()
            else:
                return pd.DataFrame(response.json())
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("error", "")}')

    def get_share_repurchase(self, start_date:str, end_date:str, asset:Optional[str]=None, raw_data:bool=False): 

        """
        This method returns a list of share repurchase transactions filtered by period (reference_date) and/or asset.

        Parameters
        ----------------
        start_date: string<date>
            Lower bound. Filtering by reference_date. Format: "YYYY-MM-DD".
            Field is required. Example: '2023-10-06'.
        end_date: string<date>
            Upper bound. Filtering by reference_date. Format: "YYYY-MM-DD".
            Field is required. Example: '2023-10-06'.
        asset: str
            Ticker asset.
            Field is not required. Example: VALE. Default: None.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """

        url = f"{url_api_v1}/public-sources/share-repurchase?start_date={start_date}&end_date={end_date}" + (f"&asset={asset}" if asset else "") 

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            if raw_data:
                return response.json()
            else:
                return pd.DataFrame(response.json())
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("error", "")}')