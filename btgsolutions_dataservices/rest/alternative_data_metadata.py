from typing import Optional
import requests
from ..exceptions import BadResponse
from ..config import url_api_v1
from .authenticator import Authenticator


class AlternativeDataMetadata:
    """
    This class provides metadata endpoints for the Alternative Data public sources:
    datasets catalog, available assets, available indicators, company directory,
    financial statement types, and sector/CNAE taxonomy.

    * Main use case:

    >>> from btgsolutions_dataservices import AlternativeDataMetadata
    >>> meta = AlternativeDataMetadata(api_key='YOUR_API_KEY')
    >>> meta.get_company_directory(query='PETROBRAS')
    >>> meta.get_taxonomy(system='b3')
    >>> meta.get_company_sector(identifier='PETR4')

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

    def get_datasets(self) -> dict:
        """
        List the public-source market-data datasets available for discovery
        (maximum_theoretical_margin, investor_categories).
        """
        return self._get("datasets", {})

    def get_available_assets(
        self,
        report_date: Optional[str] = None,
        dataset: str = "all",
        prefix: Optional[str] = None,
        limit: int = 1000,
    ) -> dict:
        """
        List available asset codes for a dataset on a given reference date.

        Parameters
        ----------------
        report_date: str
            Reference date in YYYY-MM-DD format. Defaults to the latest available day.
            Field is not required.
        dataset: str
            Dataset to scope the listing: 'maximum_theoretical_margin',
            'investor_categories', or 'all' (default).
            Field is not required. Default: 'all'.
        prefix: str
            Ticker/code prefix filter (e.g. 'PETR' to list only PETR3, PETR4, ...).
            Field is not required.
        limit: int
            Maximum number of asset codes to return.
            Field is not required. Default: 1000.
        """
        return self._get("available-assets", {
            "report_date": report_date,
            "dataset": dataset,
            "prefix": prefix,
            "limit": limit,
        })

    def get_available_indicators(self) -> dict:
        """
        List the available macro indicator codes for use with
        AlternativeDataMacroMarkets.get_macro_indicators().
        """
        return self._get("available-indicators", {})

    def get_company_directory(
        self,
        query: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        Free-text company search to discover company_id values.

        Parameters
        ----------------
        query: str
            Free-text search over company name, ticker, CNPJ, or CIK.
            Field is not required. Example: 'PETROBRAS'.
        jurisdiction: str
            Filter by jurisdiction: 'BR' or 'US'.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 50.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/directory", {
            "query": query,
            "jurisdiction": jurisdiction,
            "limit": limit,
            "offset": offset,
        })

    def get_financial_statement_types(self) -> dict:
        """
        List the available financial statement types (e.g. income_statement,
        balance_sheet, cash_flow).
        """
        return self._get("financial-statements/types", {})

    def get_taxonomy(
        self,
        system: Optional[str] = None,
        limit: int = 5000,
    ) -> dict:
        """
        Full sector taxonomy tree (B3 or CNAE classification system).

        Parameters
        ----------------
        system: str
            Classification system: 'b3' or 'cnae'.
            Field is not required. Example: 'b3'.
        limit: int
            Maximum number of taxonomy entries to return.
            Field is not required. Default: 5000.
        """
        return self._get("taxonomy", {"system": system, "limit": limit})

    def get_cnae(self, code: str) -> dict:
        """
        CNAE code lookup (Brazilian National Classification of Economic Activities).

        Parameters
        ----------------
        code: str
            CNAE code.
            Field is required. Example: '6422100'.
        """
        return self._get("cnae", {"code": code})

    def get_company_sector(self, identifier: str) -> dict:
        """
        Sector classification for a company.

        Parameters
        ----------------
        identifier: str
            Company identifier (CNPJ, CVM code, or B3 ticker).
            Field is required. Example: 'PETR4'.
        """
        return self._get("companies/sector", {"identifier": identifier})

    def get_sector_companies(
        self,
        sector: Optional[str] = None,
        subsector: Optional[str] = None,
        segment: Optional[str] = None,
        active_only: bool = False,
        limit: int = 500,
    ) -> dict:
        """
        Companies belonging to a given sector, subsector, or segment.

        Parameters
        ----------------
        sector: str
            Sector name filter.
            Field is not required. Example: 'Petróleo, Gás e Biocombustíveis'.
        subsector: str
            Subsector name filter.
            Field is not required.
        segment: str
            Segment name filter.
            Field is not required.
        active_only: bool
            If True, returns only companies with active listings.
            Field is not required. Default: False.
        limit: int
            Maximum number of companies to return.
            Field is not required. Default: 500.
        """
        return self._get("sectors/companies", {
            "sector": sector,
            "subsector": subsector,
            "segment": segment,
            "active_only": active_only,
            "limit": limit,
        })

    def get_sectors_summary(self) -> dict:
        """
        Aggregate sector summary statistics across all classified companies.
        """
        return self._get("sectors/summary", {})
