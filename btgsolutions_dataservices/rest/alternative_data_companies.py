from typing import Optional
import requests
from ..exceptions import BadResponse
from ..config import url_api_v1
from .authenticator import Authenticator


class AlternativeDataCompanies:
    """
    This class provides company-level alternative data: corporate governance,
    board composition, financial statements, and issuer disclosures.

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
        Board and executive composition for a company (BR, US, or UK).

        Parameters
        ----------------
        company_id: str
            Company identifier. Accepts CNPJ, CVM code, B3 ticker, ISIN, LEI,
            UK company number, SEC ticker/CIK, or company name.
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
        committees, CEO name, etc.).

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
        Beneficial ownership records (UK PSC or BR equivalents).

        Parameters
        ----------------
        company_id: str
            Company identifier.
            Field is required.
        holder_type: str
            Holder type filter.
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
        Insider trade transactions from SEC Forms 3/4/5 (US only).

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
        Board appointment and resignation events.

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
            Event type filter: 'appointed' or 'resigned'.
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
        company_id: str,
        statement: str = "income_statement",
        quarter: Optional[str] = None,
        reference_date: Optional[str] = None,
        statement_type: Optional[str] = None,
        account_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Financial statements from CVM DFP/ITR filings (BR companies).

        Parameters
        ----------------
        company_id: str
            Company identifier (CNPJ, CVM code, or B3 ticker).
            Field is required. Example: 'PETR4'.
        statement: str
            Statement type (e.g. 'income_statement', 'balance_sheet', 'cash_flow').
            Field is not required. Default: 'income_statement'.
        quarter: str
            Brazilian quarter code filter (e.g. '1T24' or '4T24').
            Field is not required.
        reference_date: str
            Reference date in YYYY-MM-DD format.
            Field is not required.
        statement_type: str
            Statement type filter (e.g. 'DFP', 'ITR').
            Field is not required.
        account_code: str
            Specific account code filter.
            Field is not required.
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
            "quarter": quarter,
            "reference_date": reference_date,
            "statement_type": statement_type,
            "account_code": account_code,
            "limit": limit,
            "offset": offset,
        })

    def get_financial_notes(
        self,
        company_id: str,
        quarter: Optional[str] = None,
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
        participant_group: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        CVM IPE regulatory disclosure documents (buyback programs and insider
        activity notifications).

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
        participant_group: str
            Participant group filter.
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
            "participant_group": participant_group,
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
