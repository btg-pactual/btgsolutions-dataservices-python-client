from typing import Optional
import requests
from ..exceptions import BadResponse
from ..config import url_api_v1
from .authenticator import Authenticator


class AlternativeDataMacroMarkets:
    """
    This class provides macro and market alternative data: macro indicator
    time-series, Brazilian public debt (DPMFi), and B3 maximum theoretical margin.

    Technical endpoint descriptions, parameters, known data gaps and endpoint
    relationships are available in ``alternative_data_catalog``:
    ``PUBLIC_SOURCES_ENDPOINTS`` and ``get_public_sources_endpoint_description``.

    * Main use case:

    >>> from btgsolutions_dataservices import AlternativeDataMacroMarkets
    >>> macro = AlternativeDataMacroMarkets(api_key='YOUR_API_KEY')
    >>> macro.get_macro_indicators(indicator='selic')
    >>> macro.get_macro_indicators(indicator='ipca', start_date='2024-01', end_date='2024-12')
    >>> macro.get_dpmfi(status='dados_oficiais')
    >>> macro.get_maximum_theoretical_margin(asset='PETR4')

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

    def get_macro_indicators(
        self,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        year: Optional[str] = None,
        month: Optional[str] = None,
        period: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        source: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Time-series observations for a macro indicator. Defaults to the most
        recent period when no date filter is supplied.

        Available indicators: selic, ipca, ipca_contributions, copom, pim, pmc,
        pms, pnad, gdp, comexstat, rreo.
        Use AlternativeDataMetadata.get_available_indicators() first when the
        indicator code is uncertain.

        Parameters
        ----------------
        indicator: str
            Macro indicator code.
            Field is required. Example: 'selic'.
        start_date: str
            Start of the query period in YYYY-MM format.
            Field is not required. Example: '2024-01'.
        end_date: str
            End of the query period in YYYY-MM format.
            Field is not required. Example: '2024-12'.
        year: str
            Four-digit year filter (ComexStat and RREO).
            Field is not required.
        month: str
            Numeric month filter 1-12 (ComexStat only).
            Field is not required.
        period: str
            Bimester filter 1-6 (RREO only).
            Field is not required.
        state: str
            Brazilian state UF filter (ComexStat or RREO).
            Field is not required. Example: 'SP'.
        country: str
            Partner country filter (ComexStat only).
            Field is not required.
        source: str
            Data source filter (e.g. 'BCB/Demab', 'IBGE/DPE').
            Field is not required.
        type: str
            Variation type for PIM/PMC/PMS/GDP: 'yoy' or 'mom'.
            Field is not required.
        limit: int
            Maximum number of observations to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("macro-indicators", {
            "indicator": indicator,
            "start_date": start_date,
            "end_date": end_date,
            "year": year,
            "month": month,
            "period": period,
            "state": state,
            "country": country,
            "source": source,
            "type": type,
            "limit": limit,
            "offset": offset,
        })

    def get_maximum_theoretical_margin(
        self,
        report_date: Optional[str] = None,
        asset: Optional[str] = None,
        instrument_id: Optional[str] = None,
        origin: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_margin: Optional[float] = None,
        max_margin: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        B3 maximum theoretical margin (haircut) reference data.
        Use AlternativeDataMetadata.get_available_assets() first when asset or
        instrument coverage is uncertain. This is a margin reference endpoint,
        not a quote/trade feed and not the investor-categories endpoint.

        Parameters
        ----------------
        report_date: str
            Reference date in YYYY-MM-DD format. Defaults to the latest available snapshot.
            Field is not required.
        asset: str
            Ticker asset filter.
            Field is not required. Example: 'PETR4'.
        instrument_id: str
            B3 instrument identifier filter.
            Field is not required. Example: 'PETR4F'.
        origin: str
            Origin market filter (e.g. 'EQUITIES', 'DERIVATIVES').
            Field is not required.
        start_date: str
            Start date of the query period in YYYY-MM-DD format.
            Field is not required.
        end_date: str
            End date of the query period in YYYY-MM-DD format.
            Field is not required.
        min_margin: float
            Lower bound filter on the discount_margin (haircut) value.
            Field is not required.
        max_margin: float
            Upper bound filter on the discount_margin (haircut) value.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("market-data/maximum-theoretical-margin", {
            "report_date": report_date,
            "asset": asset,
            "instrument_id": instrument_id,
            "origin": origin,
            "start_date": start_date,
            "end_date": end_date,
            "min_margin": min_margin,
            "max_margin": max_margin,
            "limit": limit,
            "offset": offset,
        })

    def get_dpmfi(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: str = "dados_oficiais",
        snapshot_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Monthly time-series of DPMFi (domestic federal public debt) outstanding
        stock broken down by bond type (NTN-B, LFT, NTN-F, LTN, Demais).

        Parameters
        ----------------
        start_date: str
            Start of the query period in YYYY-MM format.
            Field is not required. Example: '2024-01'.
        end_date: str
            End of the query period in YYYY-MM format.
            Field is not required. Example: '2024-12'.
        status: str
            Data status filter: 'dados_oficiais' (official), 'projecao'
            (forecast), or 'estipulado' (PAF target).
            Field is not required. Default: 'dados_oficiais'.
        snapshot_date: str
            Presto partition date in YYYY-MM-DD format. Defaults to the latest
            available weekly snapshot when omitted.
            Field is not required.
        limit: int
            Maximum number of rows to return (max 500).
            Field is not required. Default: 100.
        offset: int
            Number of rows to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("dpmfi", {
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "snapshot_date": snapshot_date,
            "limit": limit,
            "offset": offset,
        })

    def get_dpmfi_composition(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        bond_type: Optional[str] = None,
        snapshot_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Monthly PAF composition by bond category: new issuances (``emissoes``),
        end-of-month outstanding stock (``estoque_final``), and share of total
        DPMFi debt (``perc_divida``) for Prefixado, IPCA, Selic and Total.

        This endpoint covers the forward PAF projection months available in the
        selected snapshot, usually the two months after the latest official
        DPMFi stock observation. Filters outside the available reference-month
        window return an empty but valid result. ``bond_type`` uses PAF
        categories (Prefixado, IPCA, Selic, Total), not security acronyms such
        as LTN, LFT, NTN-B or NTN-F.

        Parameters
        ----------------
        start_date: str
            Start of the query period in YYYY-MM format.
            Field is not required. Example: '2026-04'.
        end_date: str
            End of the query period in YYYY-MM format.
            Field is not required. Example: '2026-06'.
        bond_type: str
            Bond category filter: 'Prefixado', 'IPCA', 'Selic', or 'Total'.
            Returns all categories when omitted.
            Field is not required.
        snapshot_date: str
            Presto partition date in YYYY-MM-DD format. Defaults to the latest
            available weekly snapshot when omitted.
            Field is not required.
        limit: int
            Maximum number of rows to return (max 500).
            Field is not required. Default: 100.
        offset: int
            Number of rows to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("dpmfi/composition", {
            "start_date": start_date,
            "end_date": end_date,
            "bond_type": bond_type,
            "snapshot_date": snapshot_date,
            "limit": limit,
            "offset": offset,
        })
