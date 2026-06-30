from typing import Optional
import requests
from ..exceptions import BadResponse
from ..config import url_api_v1
from .authenticator import Authenticator


class AlternativeDataOwnership:
    """
    This class provides ownership alternative data: top shareholders, ownership
    structure, change events, official notices, control group, free float,
    shareholder holdings, and institutional/fund holders of assets.

    Technical endpoint descriptions, parameters, known data gaps and endpoint
    relationships are available in ``alternative_data_catalog``:
    ``PUBLIC_SOURCES_ENDPOINTS`` and ``get_public_sources_endpoint_description``.

    * Main use case:

    >>> from btgsolutions_dataservices import AlternativeDataOwnership
    >>> ownership = AlternativeDataOwnership(api_key='YOUR_API_KEY')
    >>> ownership.get_top_shareholders(company_id='VALE3')
    >>> ownership.get_ownership_current(company_id='ITUB4')
    >>> ownership.get_shareholder_holdings(shareholder_id='00.000.000/0001-91')

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.__authenticator = Authenticator(self.api_key)

    def _get(self, path: str, params: dict) -> dict:
        url = f"{url_api_v1}/public-sources/{path}"
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        headers = {"authorization": f"Bearer {self.__authenticator.token}"}
        response = requests.get(url, params=params, headers=headers, timeout=30)
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

    def get_top_shareholders(
        self,
        company_id: str,
        reference_date: Optional[str] = None,
        ownership_category: str = "all",
        limit: int = 20,
    ) -> dict:
        """
        Top shareholders for a company from the normalized ownership_snapshot
        layer. For Brazilian listed companies, CVM/FRE rows are periodic filing
        snapshots, often annual or quarterly reference dates. When
        ``reference_date`` is omitted, the endpoint uses the latest loaded
        snapshot per ownership_category; when ``reference_date`` is provided,
        it must match a loaded snapshot date.

        This endpoint does not synthesize current ownership from control/free
        float tables; ``total=0`` means no matching rows were found in the
        normalized snapshot layer for the selected company/date/category
        filter. For Brazilian ownership questions, call get_ownership_current(),
        get_ownership_control_group(), get_ownership_free_float() and
        get_ownership_official_notices() when this endpoint returns no rows.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'VALE3'.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the latest loaded
            snapshot per ownership_category. When provided, it is an exact
            loaded snapshot date, not an as-of lookup.
            Field is not required.
        ownership_category: str
            Ownership category filter.
            Field is not required. Default: 'all'.
        limit: int
            Maximum number of shareholders to return.
            Field is not required. Default: 20.
        """
        return self._get("companies/shareholders/top", {
            "company_id": company_id,
            "reference_date": reference_date,
            "ownership_category": ownership_category,
            "limit": limit,
        })

    def get_ownership_current(self, company_id: str) -> dict:
        """
        Current ownership structure snapshot for a company.
        Use this as the primary current ownership summary when top-shareholder
        snapshots are empty or when a compact ownership object is sufficient.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'ITUB4'.
        """
        return self._get("companies/ownership-current", {"company_id": company_id})

    def get_ownership_history(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ownership_category: str = "all",
        limit: int = 12,
    ) -> dict:
        """
        Historical ownership snapshots for a company from the same normalized
        ownership_snapshot layer used by get_top_shareholders(). For Brazilian
        listed companies, CVM/FRE snapshots are periodic filing dates rather
        than guaranteed calendar month-ends. This endpoint does not synthesize
        history from current ownership or notice tables. For Brazilian ownership
        timelines, use get_ownership_change_events() and
        get_ownership_official_notices() as the event/document sources when
        snapshots are empty, and get_ownership_current(),
        get_ownership_control_group() or get_ownership_free_float() for current
        context.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'PETR4'.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        ownership_category: str
            Ownership category filter.
            Field is not required. Default: 'all'.
        limit: int
            Maximum number of snapshot reference dates to return.
            Field is not required. Default: 12.
        """
        return self._get("companies/ownership-history", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "ownership_category": ownership_category,
            "limit": limit,
        })

    def get_ownership_change_events(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ownership_category: str = "all",
        limit: int = 100,
    ) -> dict:
        """
        Ownership change events for a company (with inline official notices).
        Use get_ownership_official_notices() when the question needs the filed
        notice documents and download URLs.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        ownership_category: str
            Ownership category filter.
            Field is not required. Default: 'all'.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        """
        return self._get("companies/ownership-change-events", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "ownership_category": ownership_category,
            "limit": limit,
        })

    def get_ownership_official_notices(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        parser_status: str = "all",
        limit: int = 100,
    ) -> dict:
        """
        Official ownership notices and related IR evidence for a company.

        The response can contain three list blocks:
        ``official_notices`` (CVM/IPE ownership-related disclosures and SEC
        13D/13G/13F summaries), ``ir_page_sources`` (candidate investor-relations
        pages), and ``ir_structures`` (parsed IR ownership/free-float/control
        structures, filterable by parser_status). start_date/end_date filter
        the ``official_notices`` block; IR page/source metadata and parsed IR
        structures are discovery/parser evidence and can still be returned when
        the requested official-notice date range is empty. Returned CVM RAD
        download URLs can be passed to get_notice_summary() for an AI-generated
        document summary.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        parser_status: str
            Filter by parser status.
            Field is not required. Default: 'all'.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        """
        return self._get("companies/ownership-official-notices", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "parser_status": parser_status,
            "limit": limit,
        })

    def get_notice_summary(
        self,
        url: str,
        lang: str = "pt",
        timeout: int = 120,
    ) -> dict:
        """
        AI-generated summary for a CVM RAD PDF document.
        Use URLs returned by AlternativeDataCompanies.get_assemblies() or
        get_ownership_official_notices().

        Parameters
        ----------------
        url: str
            CVM RAD download URL for the PDF to summarize.
            Field is required.
        lang: str
            Summary language: 'pt', 'en', or 'es'.
            Field is not required. Default: 'pt'.
        timeout: int
            Request timeout in seconds. AI summaries can take longer than
            standard data endpoints when a new summary is generated.
            Field is not required. Default: 120.
        """
        endpoint = f"{url_api_v1}/public-sources/companies/notices/summary"
        params = {"url": url, "lang": lang}
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        headers = {"authorization": f"Bearer {self.__authenticator.token}"}
        response = requests.get(endpoint, params=params, headers=headers, timeout=timeout)
        if response.status_code != 200:
            self._raise_error(response)
        return response.json()

    def get_ownership_control_group(self, company_id: str) -> dict:
        """
        Control group composition for a Brazilian company (CVM FRE).
        Use this for who controls the company; use get_shareholder_holdings()
        for a reverse lookup of one holder across companies.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'VALE3'.
        """
        return self._get("companies/ownership-control-group", {"company_id": company_id})

    def get_ownership_free_float(self, company_id: str, limit: int = 20) -> dict:
        """
        Free float breakdown for a company.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'PETR4'.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 20.
        """
        return self._get("companies/ownership-free-float", {
            "company_id": company_id,
            "limit": limit,
        })

    def get_shareholder_holdings(
        self,
        shareholder_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ownership_category: str = "all",
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Holdings owned by a shareholder across companies (reverse lookup).

        Parameters
        ----------------
        shareholder_id: str
            Shareholder identifier (CNPJ, CPF, or name).
            Field is required.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        ownership_category: str
            Ownership category filter.
            Field is not required. Default: 'all'.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("shareholders/holdings", {
            "shareholder_id": shareholder_id,
            "start_date": start_date,
            "end_date": end_date,
            "ownership_category": ownership_category,
            "limit": limit,
            "offset": offset,
        })

    def get_institutional_holders(
        self,
        identifier: str,
        identifier_type: str = "b3_ticker",
        reference_date: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Institutional holders of a specific asset from the precomputed
        asset-holder layer. Coverage can be sparse for B3 tickers. This
        endpoint does not run the live fund-portfolio/ETF holding lookup used
        by get_fund_holders(); when this endpoint returns no holders,
        get_fund_holders() is often the richer inverse relationship for
        Brazilian assets because it uses fund portfolio and ETF holding
        snapshots.

        Parameters
        ----------------
        identifier: str
            Asset identifier.
            Field is required. Example: 'VALE3'.
        identifier_type: str
            Type of identifier: 'b3_ticker', 'isin', 'cusip', or 'issuer_cnpj'.
            Field is not required. Default: 'b3_ticker'.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the most recent snapshot.
            Field is not required.
        limit: int
            Maximum number of holders to return.
            Field is not required. Default: 50.
        """
        return self._get("assets/institutional-holders", {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "reference_date": reference_date,
            "limit": limit,
        })

    def get_fund_holders(
        self,
        identifier: str,
        identifier_type: str = "b3_ticker",
        reference_date: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Funds or ETFs that hold a specific asset.
        This is the inverse relationship of fund holdings for a B3 asset and is
        often richer than institutional-holder coverage because it uses fund
        portfolio and ETF holding snapshots.

        Parameters
        ----------------
        identifier: str
            Asset identifier.
            Field is required. Example: 'PETR4'.
        identifier_type: str
            Type of identifier: 'b3_ticker', 'isin', 'cusip', or 'issuer_cnpj'.
            Field is not required. Default: 'b3_ticker'.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the most recent snapshot.
            Field is not required.
        limit: int
            Maximum number of fund holders to return (max 500).
            Field is not required. Default: 50.
        """
        return self._get("assets/fund-holders", {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "reference_date": reference_date,
            "limit": limit,
        })
