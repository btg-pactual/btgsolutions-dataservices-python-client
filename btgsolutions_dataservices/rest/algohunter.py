from typing import List
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator


class AlgoHunter:
    """
    This class provides access to the AlgoHunter analytics endpoints.

    * Main use case:

    >>> from btgsolutions_dataservices import AlgoHunter
    >>> algohunter = AlgoHunter(api_key='YOUR_API_KEY')
    >>> algohunter.get_thermometer()
    >>> algohunter.get_recently_detected(ticker='PETR4')

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """

    _BASE_PATH = f"{url_api_v1}/marketdata/analytics/algohunter"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.__authenticator = Authenticator(self.api_key)

    def get_thermometer(self) -> List[dict]:
        """
        Returns thermometer values for assets with algorithmic activity
        detected in the last 5 minutes.
        """
        url = f"{self._BASE_PATH}/thermometer"
        headers = {"authorization": f"Bearer {self.__authenticator.token}"}
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            self._raise_error(response)

        return response.json()

    def get_recently_detected(self, ticker: str) -> dict:
        """
        Returns algorithms likely running in the last few minutes
        for a given ticker, grouped by side (buyer/seller) and broker.

        Parameters
        ----------
        ticker : str
            Ticker symbol. Required.

        """
        url = f"{self._BASE_PATH}/recently-detected"
        headers = {"authorization": f"Bearer {self.__authenticator.token}"}
        response = requests.get(url, params={"ticker": ticker}, headers=headers, timeout=30)

        if response.status_code != 200:
            self._raise_error(response)

        return response.json()

    @staticmethod
    def _raise_error(response):
        try:
            error_body = response.json()
            detail = error_body.get("detail", error_body.get("error", response.text))
        except Exception:
            detail = response.text
        raise BadResponse(f"Error {response.status_code}: {detail}")
