import time
from typing import Optional, List
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator
import pandas as pd
import json
from datetime import datetime, timezone, timedelta
import threading

class TickerLastEventPolling:
    """
    This class continuously polls and caches the latest ticker market data in the background for quick and up-to-date access.

    * Main use case:

    >>> from btgsolutions_dataservices import TickerLastEventPolling
    >>> last_event = TickerLastEventPolling(
    >>>     api_key='YOUR_API_KEY',
    >>>     data_type='top-of-books',
    >>>     data_subtype='stocks',
    >>> )

    >>> last_event.get(
    >>>     raw_data=False
    >>> )

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    data_type: str
        Market Data type.
        Options: 'top-of-books', 'snapshot-tob'.
        Field is required.
    data_subtype: str
        Market Data subtype.
        Options: 'stocks', 'options', 'derivatives', 'equities'.
        Field is required.
    """
    def __init__(
        self,
        api_key:Optional[str],
        data_type: str,
        data_subtype: str,
        interval_seconds: Optional[float]=None
    ):
        self.api_key = api_key
        self.authenticator = Authenticator(self.api_key)
        self.data_type = data_type

        self._last_request_datetime = None
        self._cache = {}

        self._available_data_types = {
            "top-of-books": ['stocks', 'derivatives', 'options'],
            "snapshot-tob": ['equities', 'derivatives']
        }

        self._default_interval_seconds  = {
            "top-of-books": 1,
            "snapshot-tob": 1
        }

        self._available_url = {
            "top-of-books": {
                "data": f"{url_api_v1}/marketdata/last-event/books/top/{data_subtype}/batch", 
                "available": f"{url_api_v1}/marketdata/last-event/books/{data_subtype}/availables"
            },
            "snapshot-tob": {
                "data": f"{url_api_v1}/marketdata/br/b3/snapshot/book/tob/{data_subtype}/batch", 
                "available": f"{url_api_v1}/marketdata/br/b3/snapshot/book/tob/{data_subtype}/available-tickers"
            }
        }
        
        if data_type not in self._available_data_types:
            raise Exception(f"Must provide a valid data_type. Valid data types are: {self._available_data_types}")

        if data_subtype not in self._available_data_types[data_type]:
            raise Exception(f"Must provide a valid data_subtype. Valid data subtypes are: {self._available_data_types[data_type]}")


        if interval_seconds is None:
            self.interval_seconds = self._default_interval_seconds[data_type]
        else:
            self.interval_seconds = interval_seconds

        self.url = self._available_url[self.data_type]["data"]

        self._update_data()

        threading.Thread(target=self._polling_loop, daemon=True).start()

    def _polling_loop(self):

        while True:
            try:
                self._update_data()
            except Exception as e:
                print("error on updating data:", e)
                continue

            time.sleep(self.interval_seconds)


    def _update_data(self):
        url = self.url + (f"?dt={(self._last_request_datetime - timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%S.000Z')}" if self._last_request_datetime else "")

        request_datetime = datetime.now(timezone.utc)

        response = requests.request("GET", url, headers={"authorization": f"Bearer {self.authenticator.token}"})

        if response.status_code != 200:
            return


        self._last_request_datetime = request_datetime
        
        new_data = { tob["sb"]: tob for tob in response.json() if tob.get("sb")}

        self._cache.update(new_data)


    def get(self, force_update: bool=False, raw_data:bool=False):

        """
        This method provides the last events for all tickers of the given data type and data subtype.

        Parameters
        ----------------
        force_update: bool
            If true, forces an update before returning the data. If false, returns the data.
            Field is not required. Default: False.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """
        if force_update:
            self._update_data()

        if raw_data:
            return list(self._cache.values())
        else:
            return pd.DataFrame(self._cache.values())

            

    def get_available_tickers(self):

        """
        This method provides all the available tickers for the specific data type and data subtype.

        """

        url = self._available_url[self.data_type]["available"]

        response = requests.request("GET", url,  headers={"authorization": f"Bearer {self.authenticator.token}"})
        if response.status_code == 200:
            return response.json()
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("error", "")}')