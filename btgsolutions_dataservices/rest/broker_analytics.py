from typing import Optional, List
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator

VALID_MARKET_TYPES = {"derivatives", "stocks", "options"}

class BrokerAnalytics:
    """
    This class provides broker analytics data (summary, top brokers, top tickers)
    for a given market type.

    * Main use case:

    >>> from btgsolutions_dataservices import BrokerAnalytics
    >>> broker_analytics = BrokerAnalytics(
    >>>     api_key='YOUR_API_KEY',
    >>>     market_type='stocks',
    >>> )
    >>> broker_analytics.get_summary(
    >>>     brokers=['85', '3'],
    >>>     tickers=['ABCB4', 'PETR4'],
    >>> )
    >>> broker_analytics.get_top_brokers(n=10, tickers=['ABCB4'])
    >>> broker_analytics.get_top_tickers(n=10, brokers=['85', '3'])

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    market_type: str
        Market type to query. One of: 'derivatives', 'stocks', 'options'.
        Field is required.
    """

    def __init__(
        self,
        api_key: str,
        market_type: str,
    ):
        self.api_key = api_key
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"authorization {self.token}"}

        market_type = market_type.strip().lower()
        if market_type not in VALID_MARKET_TYPES:
            raise ValueError(
                f"Invalid market_type '{market_type}'. Must be one of: {sorted(VALID_MARKET_TYPES)}"
            )
        self.market_type = market_type

    def _build_url(self, suffix: str) -> str:
        return f"{url_api_v1}/marketdata/br/b3/realtime/broker-analytics/{self.market_type}/{suffix}"

    def get_summary(
        self,
        brokers: List[str],
        tickers: List[str],
        side: Optional[str] = None,
    ) -> dict:
        """
        Get day analytics summary for specific brokers and tickers.

        Parameters
        ----------
        brokers : List[str]
            List of broker names to filter. Required.
        tickers : List[str]
            List of ticker symbols to filter. Required.
        side : str, optional
            Filter by side ('buy' or 'sell'). If None, both sides are returned.

        Returns
        -------
        dict
            JSON response with broker analytics summary data.
        """
        params = {
            "brokers": ",".join(brokers),
            "tickers": ",".join(tickers),
        }
        if side is not None: params["side"] = side

        url = self._build_url("summary")
        response = requests.get(url, params=params, headers=self.headers, timeout=30)

        if response.status_code != 200:
            self._raise_error(response)

        return response.json()

    def get_top_brokers(
        self,
        n: int,
        tickers: Optional[List[str]] = None,
        side: Optional[str] = None,
    ) -> dict:
        """
        Get top N brokers ranked by financial volume, with ticker breakdown.

        Parameters
        ----------
        n : int
            Number of top brokers to return. Required.
        tickers : List[str], optional
            List of ticker symbols to filter.
        side : str, optional
            Filter by side ('buy' or 'sell').

        Returns
        -------
        dict
            JSON response with top brokers and their top assets breakdown.
        """
        params = {"n": str(n)}

        if tickers: params["tickers"] = ",".join(tickers)
        if side is not None: params["side"] = side

        url = self._build_url("top-brokers")
        response = requests.get(url, params=params, headers=self.headers, timeout=30)

        if response.status_code != 200:
            self._raise_error(response)

        return response.json()

    def get_top_tickers(
        self,
        n: int,
        brokers: Optional[List[str]] = None,
        side: Optional[str] = None,
    ) -> dict:
        """
        Get top N tickers ranked by financial volume, with broker breakdown.

        Parameters
        ----------
        n : int
            Number of top tickers to return. Required.
        brokers : List[str], optional
            List of broker names to filter.
        side : str, optional
            Filter by side ('buy' or 'sell').

        Returns
        -------
        dict
            JSON response with top tickers and their top brokers breakdown.
        """
        params = {"n": str(n)}

        if brokers: params["brokers"] = ",".join(brokers)
        if side is not None: params["side"] = side

        url = self._build_url("top-tickers")
        response = requests.get(url, params=params, headers=self.headers, timeout=30)

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