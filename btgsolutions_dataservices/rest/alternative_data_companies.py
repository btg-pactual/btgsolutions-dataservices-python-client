from typing import Optional, Sequence, Union
import requests
from ..exceptions import BadResponse
from ..config import url_api_v1
from .authenticator import Authenticator


class AlternativeDataCompanies:
    """
    This class provides company-level alternative data: corporate governance,
    board composition, financial statements, and issuer disclosures.

    Technical endpoint descriptions, parameters, known data gaps and endpoint
    relationships are available in ``alternative_data_catalog``:
    ``PUBLIC_SOURCES_ENDPOINTS`` and ``get_public_sources_endpoint_description``.

    * Main use case:

    >>> from btgsolutions_dataservices import AlternativeDataCompanies
    >>> companies = AlternativeDataCompanies(api_key='YOUR_API_KEY')
    >>> companies.list_companies(query='PETROBRAS', jurisdiction='BR')
    >>> companies.get_board(company_id='PETR4')
    >>> companies.get_governance_summary(company_id='VALE3')
    >>> companies.get_financial_statements(company_id='ITUB4')
    >>> companies.get_disclosures(company_id='PETR4', document_type='insider')

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
    def _csv_param(value: Optional[Union[str, Sequence[str]]]) -> Optional[str]:
        if value is None or isinstance(value, str):
            return value
        return ",".join(str(item) for item in value if item is not None and str(item) != "")

    @staticmethod
    def _raise_error(response):
        try:
            body = response.json()
            detail = body.get("detail", body.get("error", body.get("ApiClientError", response.text)))
        except Exception:
            detail = response.text
        raise BadResponse(f"Error {response.status_code}: {detail}")

    def list_companies(
        self,
        query: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        List or search companies available in the public-sources company directory.
        Use this to resolve company identifiers before governance, ownership,
        sector, statement or disclosure endpoints. ETFs and funds are not indexed
        here; use fund endpoints directly with fund CNPJ or supported ETF ticker.

        Parameters
        ----------------
        query: str
            Free-text search over company name, ticker, CNPJ, or CVM code.
            US rows can include CIK and ISIN in the response, but directory
            search by CIK/ISIN/LEI is not a guaranteed resolver; call the
            target endpoint directly when it documents those identifiers.
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
        return self._get("companies/list", {
            "query": query,
            "jurisdiction": jurisdiction,
            "limit": limit,
            "offset": offset,
        })

    def get_board(
        self,
        company_id: str,
        reference_date: Optional[str] = None,
        body: Optional[str] = None,
        committee: Optional[str] = None,
        include_alternates: Optional[bool] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        """
        Board and executive composition for a company. Brazilian and US SEC
        coverage are the primary loaded sources; UK Companies House coverage is
        conditional on upstream UK data for the identifier.
        Use get_board_changes() for appointment/departure events and
        get_governance_history() for historical snapshot series.

        For Brazilian filings, the latest FRE raw rows are preferred over
        older materialized snapshots and numeric FRE versions are ordered
        numerically (for example version 13 is newer than version 9).
        ``body='board'`` preserves the historical contract and can include
        Conselho Fiscal rows alongside Conselho de Administracao rows; for a
        board-of-directors answer, filter returned rows by governance_body or
        role. ``body='executive'`` returns one row per person after resolving
        duplicate mixed board/executive FRE rows. Committee responses can
        include broad aggregate groups such as Outros Comites; do not infer
        granular committee names unless they are present in returned fields.

        Parameters
        ----------------
        company_id: str
            Company identifier. Accepts CNPJ, CVM code, B3 ticker, SEC
            ticker/CIK and, where endpoint resolution supports it, ISIN or
            company name. LEI and UK company-number resolution depend on
            upstream coverage and should be verified with the returned data.
            Field is required. Example: 'PETR4'.
        reference_date: str
            Reference date in YYYY-MM-DD format. Defaults to the most recent filing.
            Field is not required. Example: '2024-12-31'.
        body: str
            Governance body filter: 'board', 'executive', or 'committee'.
            Field is not required. Default: 'board'.
        committee: str
            Committee name filter (used when body='committee').
            Field is not required.
        include_alternates: bool
            Whether to include alternate members.
            Field is not required. Default: True.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 200.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/board", {
            "company_id": company_id,
            "reference_date": reference_date,
            "body": body,
            "committee": committee,
            "include_alternates": include_alternates,
            "limit": limit,
            "offset": offset,
        })

    def get_governance_summary(self, company_id: str) -> dict:
        """
        Latest governance snapshot for a company (board size, independence,
        fiscal council size, executive count, committees, CEO name, etc.).
        For Brazilian companies, the API derives current counts from the
        latest available FRE raw filing when present, exposes
        latest_reference_date/latest_version/latest_document_id and can mark
        structure_source='fre_raw'. This avoids stale materialized summaries
        and fixes B3 tickers that resolve through alternate traded classes
        such as units.
        Use get_board() for individual directors/officers and
        AlternativeDataOwnership.get_ownership_free_float() for detailed
        free-float breakdowns.

        Parameters
        ----------------
        company_id: str
            Company identifier (CNPJ, CVM code, B3 ticker, SEC ticker/CIK, etc.).
            Field is required. Example: 'VALE3'.
        """
        return self._get("companies/governance-summary", {"company_id": company_id})

    def get_governance_history(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        body: Optional[str] = None,
        limit: int = 12,
    ) -> dict:
        """
        Monthly governance history snapshots (member counts per governance body).
        Use get_board_changes() when the question asks for event-style changes
        such as appointments or resignations.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'ITUB4'.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        body: str
            Governance body filter: 'board', 'executive', or 'committee'.
            Field is not required.
        limit: int
            Maximum number of snapshots to return.
            Field is not required. Default: 12.
        """
        return self._get("companies/governance-history", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "body": body,
            "limit": limit,
        })

    def get_governance_documents(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        governance_topic: Optional[str] = None,
        event_tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        CVM IPE governance documents for a Brazilian company.
        For share-repurchase or Brazilian insider-trading disclosures, use
        get_disclosures() instead of this governance-only document endpoint.

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
        category: str
            Document category filter.
            Field is not required.
        governance_topic: str
            Governance topic filter.
            Field is not required.
        event_tag: str
            Event tag filter.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/governance-documents", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "category": category,
            "governance_topic": governance_topic,
            "event_tag": event_tag,
            "limit": limit,
            "offset": offset,
        })

    def get_governance_compensation(
        self,
        company_id: str,
        fiscal_year: Optional[str] = None,
        reference_date: Optional[str] = None,
        governance_body: Optional[str] = None,
        summary: bool = False,
        latest_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Executive compensation data from CVM FRE (BR) or SEC proxy filings (US).

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'VALE3'.
        fiscal_year: str
            Four-digit fiscal year filter.
            Field is not required. Example: '2024'.
        reference_date: str
            Exact filing/reference date filter (YYYY-MM-DD).
            Field is not required.
        governance_body: str
            Governance body filter. Example: 'Conselho de Administração'.
            Field is not required.
        summary: bool
            When true, returns one compact record per fiscal year and governance body.
            Field is not required. Default: False.
        latest_only: bool
            When true, restricts records to the latest matching reference date.
            Field is not required. Default: False.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/governance-compensation", {
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "reference_date": reference_date,
            "governance_body": governance_body,
            "summary": summary,
            "latest_only": latest_only,
            "limit": limit,
            "offset": offset,
        })

    def get_governance_related_party(
        self,
        company_id: str,
        relation_category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Related-party transactions from CVM FRE filings.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'ITUB4'.
        relation_category: str
            Relation category filter.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/governance-related-party", {
            "company_id": company_id,
            "relation_category": relation_category,
            "limit": limit,
            "offset": offset,
        })

    def get_governance_beneficial_ownership(
        self,
        company_id: str,
        holder_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Beneficial ownership records from US SEC proxy DEF14A data and, when
        loaded upstream, UK Companies House PSC data. Brazilian companies are
        not available in this endpoint and can return 404 / "Company not
        found". For Brazilian listed-company ownership context, prefer
        AlternativeDataOwnership.get_ownership_current(),
        get_ownership_control_group() or get_ownership_free_float().

        Parameters
        ----------------
        company_id: str
            SEC ticker/CIK/ISIN, or a UK company number/name when Companies
            House PSC coverage is loaded. Field is required. Example: 'AAPL'.
        holder_type: str
            Holder classification filter such as individual, institution,
            director, officer or ten_percent_owner.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/governance-beneficial-ownership", {
            "company_id": company_id,
            "holder_type": holder_type,
            "limit": limit,
            "offset": offset,
        })

    def get_sec_filings(
        self,
        company_id: str,
        form_type: Optional[Union[str, Sequence[str]]] = None,
        item: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        SEC EDGAR filing metadata for a US company. Use this when the filing
        itself is the analytical object, for example 8-K Item 5.02 director or
        executive changes, DEF 14A proxy statements, or SC 13D/13G ownership
        filings. This endpoint returns filing metadata and source document
        URLs; it does not parse full filing text.

        Parameters
        ----------------
        company_id: str
            SEC ticker, CIK, ISIN or company name.
            Field is required. Example: 'AAPL'.
        form_type: str or sequence
            Optional SEC form type filter, comma-separated or a sequence.
            Examples: '8-K', 'DEF 14A', 'SC 13D,SC 13G'.
        item: str
            Optional 8-K item filter. Example: '5.02'.
        start_date: str
            Start filing date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End filing date in YYYY-MM-DD format.
            Field is not required.
        limit: int
            Maximum number of filings to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/sec-filings", {
            "company_id": company_id,
            "form_type": self._csv_param(form_type),
            "item": item,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        })

    def get_sec_schedule_13d_13g(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Parsed SEC Schedule 13D/13G beneficial-ownership filing rows for a US
        company. Use get_sec_filings() for the filing metadata and this endpoint
        for holder, share-count and percent-of-class fields.

        Parameters
        ----------------
        company_id: str
            SEC ticker, CIK, ISIN or company name.
            Field is required. Example: 'AAPL'.
        start_date: str
            Start filing date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End filing date in YYYY-MM-DD format.
            Field is not required.
        limit: int
            Maximum number of rows to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/sec-schedule-13d-13g", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        })

    def get_corporate_registry(
        self,
        company_id: str,
        direction: str = "partners",
        reference_month: Optional[str] = None,
        partner_type: Optional[str] = None,
        qualification: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Brazilian corporate registry (Receita Federal QSA + CVM FRE).

        Parameters
        ----------------
        company_id: str
            Company identifier (CNPJ, CVM code, or B3 ticker).
            Field is required. Example: 'PETR4'.
        direction: str
            'partners' (default) returns the company's shareholders/partners;
            'investees' returns the companies this entity holds stakes in.
            Field is not required. Default: 'partners'.
        reference_month: str
            Reference month in YYYY-MM format.
            Field is not required.
        partner_type: str
            Partner type filter.
            Field is not required.
        qualification: str
            Partner qualification filter.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/corporate-registry", {
            "company_id": company_id,
            "direction": direction,
            "reference_month": reference_month,
            "partner_type": partner_type,
            "qualification": qualification,
            "limit": limit,
            "offset": offset,
        })

    def get_insider_trades(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        transaction_code: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """
        Insider trade transactions from SEC Forms 3/4/5 (US only). Populated
        rows are commonly Form 4 rows and carry source fields such as
        ``SEC/Form4``; inspect source/accession_number before stating which
        SEC form supplied a transaction.
        Do not use this endpoint for Brazilian companies; use get_disclosures()
        with document_type='insiders' for Brazilian insider-trading disclosures.

        Parameters
        ----------------
        company_id: str
            Company identifier (SEC ticker or CIK).
            Field is required. Example: 'AAPL'.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        transaction_code: str
            SEC transaction code filter (e.g. 'P' for purchase, 'S' for sale).
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        """
        return self._get("companies/insider-trades", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "transaction_code": transaction_code,
            "limit": limit,
        })

    def get_board_changes(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """
        Board and executive change events.

        Brazilian listed-company events can include FRE-derived ``elected``,
        ``replaced`` and ``resigned`` rows. Inspect ``event_date`` as the
        effective timeline date when present; ``reference_date`` and
        ``previous_reference_date`` describe the source snapshots used to
        detect the change. Brazilian rows derived from FRE snapshots use
        ``source='fre'`` unless a more specific source is stored.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required. Example: 'VALE3'.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        event: str
            Event type filter, for example 'elected', 'replaced',
            'resigned' or 'appointed' depending on jurisdiction.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        """
        return self._get("companies/board-changes", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "event": event,
            "limit": limit,
        })

    def get_financial_statements(
        self,
        company_id: Optional[str] = None,
        statement: str = "income_statement",
        statements: Optional[Union[str, Sequence[str]]] = None,
        quarter: Optional[str] = None,
        reference_date: Optional[str] = None,
        statement_type: Optional[str] = None,
        account_code: Optional[str] = None,
        account_codes: Optional[Union[str, Sequence[str]]] = None,
        summary: Optional[bool] = None,
        metrics: Optional[Union[str, Sequence[str]]] = None,
        include_raw: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Financial statements from CVM DFP/ITR filings (BR companies).
        Use AlternativeDataMetadata.get_financial_statement_types() when the
        statement name or alias is uncertain. Quarter filters use Brazilian
        quarter codes such as 1T24 and 4T24.

        Omit ``company_id`` only for universe-level screens or rankings; in
        that mode, paginate with ``limit``/``offset`` and deduplicate repeated
        filings by company and source document version before ranking.

        Parameters
        ----------------
        company_id: str
            Company identifier (CNPJ, CVM code, or B3 ticker).
            Field is not required for universe-level screens. Example: 'PETR4'.
        statement: str
            Statement type (e.g. 'income_statement', 'balance_sheet', 'cash_flow').
            Field is not required. Default: 'income_statement'.
        statements: str | list[str]
            Optional comma-separated list (or Python sequence) of statement types
            to query in a single call. When omitted, ``statement`` preserves the
            historical single-statement behavior.
            Field is not required.
        quarter: str
            Brazilian quarter code filter (e.g. '1T24' or '4T24').
            Field is not required.
        reference_date: str
            Reference date in YYYY-MM-DD format.
            Field is not required.
        statement_type: str
            Statement presentation/filter when supported by the endpoint, such
            as 'consolidated' or 'individual'. Some payloads also expose filing
            source fields such as DFP/ITR separately; inspect returned columns.
            Field is not required.
        account_code: str
            Specific account code filter.
            Field is not required.
        account_codes: str | list[str]
            Optional comma-separated list (or Python sequence) of account codes.
            This is useful for dashboard summaries that need only a few CVM
            account lines instead of the full statement.
            Field is not required.
        summary: bool
            When true, include a ``summary`` block with direct CVM account-line
            metrics such as revenue, EBIT, net income, assets, equity and
            operating cash flow. EBITDA is not returned because it is not a
            standardized direct CVM account line.
            Field is not required. Default: False.
        metrics: str | list[str]
            Optional summary metrics to return, for example
            ``['revenue', 'ebit', 'net_income']``. ``ebitda`` is not returned
            because it is not a standardized direct CVM account line.
            Field is not required.
        include_raw: bool
            When false and ``summary=True``, suppress raw line items and return
            only metadata plus the summary block.
            Field is not required. Default: True.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/financial-statements", {
            "company_id": company_id,
            "statement": statement,
            "statements": self._csv_param(statements),
            "quarter": quarter,
            "reference_date": reference_date,
            "statement_type": statement_type,
            "account_code": account_code,
            "account_codes": self._csv_param(account_codes),
            "summary": summary,
            "metrics": self._csv_param(metrics),
            "include_raw": include_raw,
            "limit": limit,
            "offset": offset,
        })

    def get_financial_notes(
        self,
        company_id: str,
        quarter: Optional[str] = None,
        sections: Optional[Union[str, Sequence[str]]] = None,
        summary: Optional[bool] = None,
        include_raw: Optional[bool] = None,
        only_with_data: Optional[bool] = None,
        latest_only: Optional[bool] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """
        LLM-parsed structured data from CVM DFP/ITR explanatory notes
        (notas explicativas): geographic_segments, fx_exposure, and
        supplier_concentration.

        Parameters
        ----------------
        company_id: str
            Company identifier (CNPJ, CVM code, or B3 ticker).
            Field is required. Example: 'VALE3'.
        quarter: str
            Brazilian quarter code filter (e.g. '1T24' or '4T24').
            Field is not required.
        sections: str | list[str]
            Optional note sections to return. Supported values are
            geographic_segments, fx_exposure and supplier_concentration.
            Field is not required.
        summary: bool
            When true, includes compact per-document counts by selected section.
            Field is not required. Default: False.
        include_raw: bool
            When false, suppresses raw note documents from ``results``.
            Field is not required. Default: True.
        only_with_data: bool
            When true, returns only periods where at least one selected section
            has parsed rows.
            Field is not required. Default: False.
        latest_only: bool
            When true and quarter is omitted, restricts the response to the
            latest matching quarter.
            Field is not required. Default: False.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 10.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/financial-notes", {
            "company_id": company_id,
            "quarter": quarter,
            "sections": self._csv_param(sections),
            "summary": summary,
            "include_raw": include_raw,
            "only_with_data": only_with_data,
            "latest_only": latest_only,
            "limit": limit,
            "offset": offset,
        })

    def get_disclosures(
        self,
        company_id: Optional[str] = None,
        document_type: str = "repurchase",
        asset: Optional[str] = None,
        protocol_number: Optional[str] = None,
        reference_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        transaction: Optional[str] = None,
        transaction_type: Optional[str] = None,
        transaction_types: Optional[Union[str, Sequence[str]]] = None,
        participant_group: Optional[str] = None,
        group_by: Optional[Union[str, Sequence[str]]] = None,
        include_raw: Optional[bool] = None,
        operation_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        CVM IPE regulatory disclosure documents (buyback programs and insider
        activity notifications).
        document_type='insiders' is the Brazilian insider-trading source; use
        get_insider_trades() only for US SEC insider transactions.

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is not required. Example: 'PETR4'.
        document_type: str
            Document type: 'repurchase' (buyback programs) or 'insiders'
            (Brazilian insider trading notifications). The 'insider' alias is
            also accepted upstream.
            Field is not required. Default: 'repurchase'.
        asset: str
            Ticker asset filter.
            Field is not required.
        protocol_number: str
            CVM protocol number filter.
            Field is not required.
        reference_date: str
            Reference date in YYYY-MM-DD format.
            Field is not required.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        transaction: str
            Transaction description filter.
            Field is not required.
        transaction_type: str
            Transaction type filter.
            Field is not required.
        transaction_types: str | list[str]
            Optional comma-separated list (or Python sequence) of normalized
            transaction types.
            Field is not required.
        participant_group: str
            Participant group filter.
            Field is not required.
        group_by: str | list[str]
            Optional aggregation dimensions. Supported values include month,
            participant_group, side, asset, company, transaction_type, security
            and characteristics. For dashboard insider charts, use
            ``['month', 'participant_group', 'side']``.
            Field is not required.
        include_raw: bool
            When false, suppress raw disclosure documents and return only
            metadata plus aggregations.
            Field is not required. Default: True.
        operation_type: str
            Optional operation class. ``spot`` narrows insider aggregations to
            cash buy/sell operations and excludes transfers/conversions.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("companies/disclosures", {
            "company_id": company_id,
            "document_type": document_type,
            "asset": asset,
            "protocol_number": protocol_number,
            "reference_date": reference_date,
            "start_date": start_date,
            "end_date": end_date,
            "transaction": transaction,
            "transaction_type": transaction_type,
            "transaction_types": self._csv_param(transaction_types),
            "participant_group": participant_group,
            "group_by": self._csv_param(group_by),
            "include_raw": include_raw,
            "operation_type": operation_type,
            "limit": limit,
            "offset": offset,
        })

    def get_assemblies(
        self,
        company_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Shareholder assembly index (AGO/AGE) for a Brazilian company.
        Returned CVM RAD URLs can be passed to
        AlternativeDataOwnership.get_notice_summary() for an AI-generated
        document summary.

        Parameters
        ----------------
        company_id: str
            Company identifier (ticker, CNPJ or company name).
            Field is required. Example: 'PINE4'.
        start_date: str
            Start date in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date in YYYY-MM-DD format.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 50.
        """
        return self._get("companies/assemblies", {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        })
