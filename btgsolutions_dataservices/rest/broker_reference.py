from typing import Optional
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator
import pandas as pd
import json

class BrokerReference:
    """
    This class provides broker reference information.

    * Main use case:

    >>> from btgsolutions_dataservices import BrokerReference
    >>> broker_reference = BrokerReference(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> broker_reference.get()

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

    def get(self, raw_data:bool=False): 

        """
        Returns the full broker reference dataset from the API.

        Parameters
        ----------------
        raw_data: bool
            If False, returns the response as a pandas DataFrame.
            If True, returns the raw JSON payload.
            Field is not required. Default: False.

        Returns
        ----------------
        pandas.DataFrame | dict | list
            Broker reference data returned by the API.
        """

        url = f"{url_api_v1}/marketdata/broker/info/all-brokers"

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            if raw_data:
                return response.json()
            else:
                return pd.DataFrame(response.json())
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("error", "")}')