from typing import Optional
import requests
from ..exceptions import BadResponse
from ..config import url_api_v1
from .authenticator import Authenticator


class AlternativeDataFunds:
    """
    This class provides fund-level alternative data: holdings snapshots,
    portfolio exposures, history, look-through, and manager aggregate holdings.

    * Main use case:

    >>> from btgsolutions_dataservices import AlternativeDataFunds
    >>> funds = AlternativeDataFunds(api_key='YOUR_API_KEY')
    >>> funds.get_holdings(fund_id='73.232.530/0001-46')
    >>> funds.get_exposures(fund_id='73.232.530/0001-46')
    >>> funds.get_history(fund_id='73.232.530/0001-46')

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"Bearer {self.token}"}

    def _get(self, path: str, params: dict) -> dict:
        url = f"{url_api_v1}/public-sources/{path}"
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        response = requests.get(url, params=params, headers=self.headers, timeout=30)
        if response.status_code != 200:
            self._raise_error(response)
        return response.json()

    @staticmethod
    def _raise_error(response):
        try:
            body = response.json()
            detail = body.get("detail", body.get("error", body.get("ApiClientError", response.text)))
        except Exception:
            detail = response.text
        raise BadResponse(f"Error {response.status_code}: {detail}")

    def get_holdings(
        self,
        fund_id: str,
        reference_date: Optional[str] = None,
        asset_class: Optional[str] = None,
        source: str = "official",
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        """
        Holdings snapshot for a Brazilian CVM fund, ETF, or US fund.

        Parameters
        ----------------
        fund_id: str
            Fund identifier. Accepts CNPJ (BR funds/ETFs) or US fund identifier.
            Field is required. Example: '73.232.530/0001-46'.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the most recent snapshot.
            Field is not required.
        asset_class: str
            Asset class filter (e.g. 'equity', 'fixed_income').
            Field is not required.
        source: str
            Data source: 'official', 'approximate', or 'index'.
            Field is not required. Default: 'official'.
        limit: int
            Maximum number of holdings to return (max 5000).
            Field is not required. Default: 200.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("funds/holdings", {
            "fund_id": fund_id,
            "reference_date": reference_date,
            "asset_class": asset_class,
            "source": source,
            "limit": limit,
            "offset": offset,
        })

    def get_exposures(
        self,
        fund_id: str,
        reference_date: Optional[str] = None,
        exposure_type: str = "all",
    ) -> dict:
        """
        Portfolio exposures for a Brazilian CVM fund (asset class, issuer,
        sector, indexer, maturity, country).

        Parameters
        ----------------
        fund_id: str
            Fund CNPJ.
            Field is required. Example: '73.232.530/0001-46'.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the most recent snapshot.
            Field is not required.
        exposure_type: str
            Exposure breakdown to return: 'all', 'asset_class', 'issuer',
            'sector', 'indexer', 'maturity', or 'country'.
            Field is not required. Default: 'all'.
        """
        return self._get("funds/exposures", {
            "fund_id": fund_id,
            "reference_date": reference_date,
            "exposure_type": exposure_type,
        })

    def get_history(
        self,
        fund_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 12,
    ) -> dict:
        """
        Holdings history time-series for a Brazilian CVM fund (snapshot metadata
        per reference date: positions count, total value, NAV).

        Parameters
        ----------------
        fund_id: str
            Fund CNPJ.
            Field is required. Example: '73.232.530/0001-46'.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        limit: int
            Maximum number of snapshots to return (max 60).
            Field is not required. Default: 12.
        """
        return self._get("funds/history", {
            "fund_id": fund_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        })

    def get_lookthrough(
        self,
        fund_id: str,
        reference_date: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """
        Look-through resolution for a fund-of-funds (resolves nested fund
        positions to underlying assets).

        Parameters
        ----------------
        fund_id: str
            Fund CNPJ.
            Field is required.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the most recent snapshot.
            Field is not required.
        limit: int
            Maximum number of results to return (max 1000).
            Field is not required. Default: 100.
        """
        return self._get("funds/lookthrough", {
            "fund_id": fund_id,
            "reference_date": reference_date,
            "limit": limit,
        })

    def get_manager_aggregate_holdings(
        self,
        manager_id: str,
        reference_date: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """
        Aggregate holdings managed by a given investment manager across all
        their funds.

        Parameters
        ----------------
        manager_id: str
            Manager identifier (CNPJ or name).
            Field is required.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the most recent snapshot.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        """
        return self._get("managers/aggregate-holdings", {
            "manager_id": manager_id,
            "reference_date": reference_date,
            "limit": limit,
        })
