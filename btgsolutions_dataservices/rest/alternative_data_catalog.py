from __future__ import annotations

from copy import deepcopy
from typing import Any


PUBLIC_SOURCES_CONVENTIONS: dict[str, str] = {
    "company_id": (
        "Company identifier accepted by company, governance, ownership, sector, "
        "statement and disclosure endpoints. It can be a B3 ticker, CNPJ, CVM "
        "code, ISIN or company name where endpoint resolution supports names."
    ),
    "fund_id": (
        "Fund identifier accepted by fund endpoints. It can be a fund CNPJ; "
        "holdings, exposures, history and look-through also accept supported "
        "Brazilian ETF tickers such as BOVA11. ETFs and funds are not resolved "
        "through the listed-company directory."
    ),
    "shareholder_id": (
        "Shareholder identifier used for reverse ownership lookup, usually a "
        "CNPJ, CPF, registry id or holder name as available upstream."
    ),
    "asset_identifier": (
        "Asset-holder endpoints default to B3 ticker identifiers when "
        "identifier_type='b3_ticker'."
    ),
    "dates": (
        "Most endpoints use ISO dates in YYYY-MM-DD. DPMFi start_date/end_date "
        "use reference months in YYYY-MM. Financial-statement quarter filters "
        "use Brazilian quarter codes such as 1T24 and 4T24."
    ),
}


PUBLIC_SOURCES_DATA_GAPS: dict[str, str] = {
    "get_macro_indicators": (
        "Macro-indicator rows are heterogeneous across sources. Inspect the "
        "returned indicator, source, type/subseries, unit and date fields before "
        "aggregating or comparing values. The metadata endpoint is discovery "
        "help, but accepted aggregate aliases such as ipca can still return "
        "valid rows even when a related granular code such as "
        "ipca_contributions is also listed. Use the returned row fields to "
        "separate aggregate IPCA/Selic observations from contribution or "
        "category rows."
    ),
    "sector_taxonomy_labels": (
        "B3 sector, subsector and segment labels are upstream taxonomy labels. "
        "Use the exact strings returned by get_taxonomy or get_company_sector "
        "when calling get_sector_companies; punctuation and spelling variations "
        "can change matches."
    ),
    "get_company_board": (
        "For Brazilian companies, body='board' can include Conselho Fiscal rows "
        "alongside Conselho de Administracao rows depending on the filing. For "
        "a board-of-directors answer, filter returned rows by governance_body "
        "or role to keep Conselho de Administracao only. Committee responses "
        "can include broad aggregates such as Outros Comites; do not infer "
        "granular committee names unless they are present in returned fields."
    ),
    "get_financial_statements": (
        "company_id may be omitted only for universe-level screens or rankings. "
        "There is no dedicated latest-quarter discovery field; when a requested "
        "quarter returns zero rows, back off to the latest filed quarter and "
        "state which quarter was used. statement_type is a presentation/filter "
        "such as consolidated or individual when supported; DFP/ITR are filing "
        "source concepts and can appear in returned fields, but they are not "
        "the right filter for cross-company consolidated rankings."
    ),
    "get_fund_exposures": (
        "Fund exposure dimensions are source-dependent. For Brazilian ETFs, "
        "issuer exposure can be based on ticker-like issuer labels and country "
        "exposure can be empty when the source does not classify country. Use "
        "holdings for constituent-level economic exposure and exposures for "
        "aggregate context."
    ),
    "get_fund_lookthrough": (
        "Look-through is useful when a fund holds other funds that can be "
        "expanded. For direct-equity ETFs, look-through can return opaque "
        "asset_key values or zero lookthrough_weight when nested weights cannot "
        "be resolved. In those cases, use get_fund_holdings and "
        "get_fund_exposures for the defensible exposure analysis."
    ),
    "get_top_shareholders": (
        "Top-shareholder snapshots come from the normalized ownership_snapshot "
        "layer. For Brazilian listed companies, CVM/FRE rows are periodic "
        "filing snapshots, often annual or quarterly reference dates. When "
        "reference_date is omitted, the endpoint uses the latest loaded "
        "snapshot per ownership_category; when reference_date is provided, it "
        "must match an exact loaded snapshot date. For Brazilian ownership context, "
        "prefer get_ownership_current, get_ownership_control_group, "
        "get_ownership_free_float and get_ownership_official_notices when this "
        "endpoint returns no rows. "
        "This endpoint does not synthesize top holders from current ownership "
        "or free-float tables. Some responses can include multiple rows for "
        "the same holder across share classes, ownership categories, filings "
        "or source protocols; inspect category, class, protocol/source and "
        "reference date before aggregating percentages."
    ),
    "ownership_reporting_dates": (
        "Brazilian ownership and free-float reference_date fields often come "
        "from CVM/FRE reporting periods, fiscal-year bases or parsed IR "
        "structures. They are reporting/reference dates, not necessarily the "
        "calendar date when the data was loaded or a strict as-of timestamp; a "
        "reference_date can be after the current calendar date when it denotes "
        "a filing year/base period."
    ),
    "get_ownership_history": (
        "Ownership history uses the same normalized ownership_snapshot layer as "
        "top-shareholders and returns only loaded snapshot reference dates. "
        "For Brazilian listed companies, CVM/FRE snapshots are periodic filing "
        "dates rather than guaranteed calendar month-ends. It can return an "
        "empty snapshots list when the snapshot layer has no rows for the "
        "selected company/date/category filter. Use get_ownership_change_events "
        "and get_ownership_official_notices for event/document timelines when "
        "snapshots are empty; this endpoint does not synthesize history from "
        "notice or current-ownership tables."
    ),
    "get_ownership_official_notices": (
        "The response has multiple evidence blocks: official_notices, "
        "ir_page_sources and ir_structures. start_date/end_date filter the "
        "official_notices block; IR page/source metadata or parsed IR "
        "structures can still be returned when that official-notice range is "
        "empty. Use official_notices download_url values with "
        "get_notice_summary; use ir_page_sources/ir_structures as discovery or "
        "parser-status evidence, not as filed notice documents."
    ),
    "get_maximum_theoretical_margin": (
        "discount_margin is the B3 haircut/desagio percentage value from the "
        "maximum-theoretical-margin reference file, not a decimal fraction. "
        "base_value is the B3 reference/base value in that file and should not "
        "be treated as a live quote or a credit decision value. Use quotes and "
        "liquidity endpoints separately when contextualizing the margin data."
    ),
    "get_beneficial_ownership": (
        "Coverage is UK/US oriented: UK Companies House PSC and US SEC proxy "
        "beneficial-owner data. Brazilian listed companies are not available in "
        "this endpoint and can return 404; use ownership-current, control-group "
        "and free-float endpoints for Brazilian ownership context."
    ),
    "get_asset_institutional_holders": (
        "Institutional-holder coverage can be sparse for B3-listed assets and "
        "can return zero rows for tickers that still have fund-holder or ETF "
        "holder coverage. This endpoint reads the precomputed asset-holder "
        "layer and ownership_snapshot fund_holder fallback; it does not run the "
        "live fund-portfolio/ETF holding lookup used by get_asset_fund_holders. "
        "Use get_asset_fund_holders for Brazilian assets when this endpoint is "
        "empty."
    ),
    "get_disclosure_documents_repurchase": (
        "Share-repurchase disclosure coverage can be thin for many companies. "
        "Use document_type='insiders' for Brazilian insider-trading disclosures "
        "when that is the intended question."
    ),
    "get_manager_aggregate_holdings": (
        "Manager aggregation requires a manager CNPJ or exact manager name that "
        "the upstream fund registry/ownership snapshots can attribute to covered "
        "fund holdings. ETF issuer slugs, ETF tickers and fund CNPJs are not "
        "manager identifiers and can return not-found."
    ),
    "get_dpmfi": (
        "DPMFi can be slow when queried without a snapshot or reference-month "
        "filter. Prefer snapshot_date for reproducibility and start_date/end_date "
        "in YYYY-MM when a narrow period is known. When snapshot_date is omitted "
        "the latest available snapshot is used; to discover that snapshot for a "
        "reproducible follow-up call, make a narrow latest query and inspect "
        "the returned snapshot/partition date fields."
    ),
    "get_dpmfi_composition": (
        "DPMFi PAF composition is a forward projection table. The latest "
        "snapshot usually covers only the two reference months after the latest "
        "official DPMFi stock observation; older or outside-window "
        "start_date/end_date filters can return zero rows. bond_type uses PAF "
        "categories Prefixado, IPCA, Selic or Total, not security acronyms such "
        "as LTN, LFT, NTN-B or NTN-F. Use get_dpmfi for official stock by "
        "security acronym/status and get_dpmfi_composition for PAF projection "
        "composition; do not join bond_type values one-to-one across the two."
    ),
}


PUBLIC_SOURCES_EXCLUDED_ENDPOINTS: dict[str, str] = {
    "market-data/investor-categories": (
        "The direct market-data investor-categories endpoint is intentionally "
        "not exposed by the alternative-data package or MCP tool surface."
    )
}


PUBLIC_SOURCES_ENDPOINT_RELATIONSHIPS: dict[str, str] = {
    "company_resolution": (
        "Use AlternativeDataMetadata.get_company_directory or "
        "AlternativeDataCompanies.list_companies to resolve company identifiers "
        "before calling governance, ownership, sector, financial-statement or "
        "disclosure endpoints. Do not use company search for ETFs or investment "
        "funds; use fund endpoints directly with fund CNPJ or supported ETF ticker."
    ),
    "macro_indicator_discovery": (
        "Use AlternativeDataMetadata.get_available_indicators before "
        "AlternativeDataMacroMarkets.get_macro_indicators when the requested "
        "macro series code is uncertain, then inspect the returned rows because "
        "macro endpoints can expose both aggregate and granular series."
    ),
    "asset_discovery": (
        "Use AlternativeDataMetadata.get_available_assets to discover asset or "
        "instrument coverage before requesting maximum theoretical margin data."
    ),
    "financial_statement_discovery": (
        "Use AlternativeDataMetadata.get_financial_statement_types before "
        "AlternativeDataCompanies.get_financial_statements when the statement "
        "name or alias is uncertain."
    ),
    "sector_peer_set": (
        "Use get_taxonomy or get_sectors_summary to understand available B3/CNAE "
        "classification values, get_company_sector to classify one company, and "
        "get_sector_companies to retrieve the peer set for a sector, subsector "
        "or segment. Pass the exact returned taxonomy labels into "
        "get_sector_companies rather than normalized or guessed strings."
    ),
    "document_summary": (
        "Use AlternativeDataCompanies.get_assemblies or "
        "AlternativeDataOwnership.get_ownership_official_notices to discover CVM "
        "RAD URLs, then pass those URLs to get_notice_summary for an AI summary."
    ),
    "br_vs_us_insiders": (
        "AlternativeDataCompanies.get_insider_trades is US SEC only. For "
        "Brazilian insider-trading disclosures use get_disclosures with "
        "document_type='insiders' or the upstream alias 'insider'."
    ),
    "ownership_fallback": (
        "When top-shareholder snapshots are empty, use get_ownership_current, "
        "get_ownership_control_group and get_ownership_free_float for current "
        "ownership, control and investable-float context."
    ),
    "fund_company_bridge": (
        "Use fund holdings/exposures/look-through to connect funds or ETFs to "
        "underlying assets. Use asset fund holders to invert the relationship "
        "and find funds holding a B3 asset."
    ),
    "company_trading_bridge": (
        "Use company directory or list endpoints to resolve a company name, "
        "CNPJ, CVM code or ISIN into the B3 ticker needed by Data Services "
        "market-data endpoints such as ReferenceData, Quotes, HistoricalCandles, "
        "IntradayCandles, IntradayTickData, TickerLastEvent, StockLoan, "
        "BrokerAnalytics and BookScope."
    ),
    "sector_market_peer_bridge": (
        "Use sector taxonomy, company sector and companies-by-sector to create "
        "a peer ticker universe, then use Data Services quotes, historical "
        "candles, liquidity, stock-loan and broker-flow endpoints to compare "
        "market behavior within the sector, subsector or segment."
    ),
    "fund_market_exposure_bridge": (
        "Use fund holdings, exposures, look-through or asset fund holders to "
        "derive underlying tickers, then use Data Services reference data, "
        "quotes, candles and stock-loan endpoints to analyze market exposure, "
        "liquidity and recent price behavior of the fund's assets."
    ),
    "ownership_liquidity_bridge": (
        "Use ownership current, control group and free float with Data Services "
        "quotes, historical volume, stock-loan trades and broker analytics to "
        "contextualize float, liquidity and flow. Treat the join as context, "
        "not causality."
    ),
    "document_market_event_bridge": (
        "Use disclosures, assemblies, official ownership notices and notice "
        "summaries to identify event dates or CVM RAD URLs, then use HFN, "
        "CorporateEvents, HistoricalCandles, IntradayCandles, IntradayTickData "
        "or BookScope for market reaction and event-window analysis."
    ),
    "macro_market_bridge": (
        "Use macro indicators with sector peer sets, company fundamentals and "
        "Data Services historical candles to frame macro exposure, sensitivity "
        "or co-movement. Do not infer causality without a model."
    ),
}


PUBLIC_SOURCES_ENDPOINTS: dict[str, dict[str, Any]] = {
    "AlternativeDataMetadata.get_datasets": {
        "category": "metadata",
        "path": "datasets",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "List public-sources dataset identifiers and basic catalog metadata. "
            "Use this for discovery before selecting a domain-specific endpoint."
        ),
        "parameters": {},
        "relationships": [
            "asset_discovery", "macro_indicator_discovery",
            "financial_statement_discovery", "company_trading_bridge",
            "sector_market_peer_bridge", "macro_market_bridge",
        ],
    },
    "AlternativeDataMetadata.get_available_assets": {
        "category": "metadata",
        "path": "available-assets",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "List available asset or instrument codes covered by public-source "
            "market-data discovery datasets. Use this to discover coverage for "
            "maximum theoretical margin; it is not a price, quote or trade feed."
        ),
        "parameters": {
            "report_date": "Reference date in YYYY-MM-DD; omitted means latest available.",
            "dataset": "Dataset scope, usually 'maximum_theoretical_margin' or 'all'.",
            "prefix": "Optional ticker/code prefix filter such as 'PETR'.",
            "limit": "Maximum number of asset codes to return.",
        },
        "relationships": ["asset_discovery", "company_trading_bridge"],
        "caveats": [PUBLIC_SOURCES_EXCLUDED_ENDPOINTS["market-data/investor-categories"]],
    },
    "AlternativeDataMetadata.get_available_indicators": {
        "category": "metadata",
        "path": "available-indicators",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "List macro and public-source indicator codes accepted by "
            "AlternativeDataMacroMarkets.get_macro_indicators."
        ),
        "parameters": {},
        "relationships": ["macro_indicator_discovery", "macro_market_bridge"],
    },
    "AlternativeDataMetadata.get_company_directory": {
        "category": "metadata",
        "path": "companies/directory",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "Search listed-company metadata by name, ticker, CNPJ, CVM code, "
            "CIK or ISIN. Use this to resolve a company identifier before "
            "governance, ownership, sector, financial-statement or disclosure "
            "endpoints."
        ),
        "parameters": {
            "query": "Free-text query over company name, ticker, CNPJ, CVM code, CIK or ISIN.",
            "jurisdiction": "Optional jurisdiction filter such as 'BR' or 'US'.",
            "limit": "Maximum number of results.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
        "caveats": [
            "CVM funds and ETFs are not indexed here; use fund endpoints with fund CNPJ or supported ETF ticker.",
        ],
    },
    "AlternativeDataMetadata.list_companies": {
        "category": "metadata",
        "path": "companies/list",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "List or search companies available in the public-sources company "
            "directory. Use this for company discovery and identifier resolution."
        ),
        "parameters": {
            "query": "Free-text query over company name, ticker, CNPJ or CIK.",
            "jurisdiction": "Optional jurisdiction filter such as 'BR' or 'US'.",
            "limit": "Maximum number of results.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
        "caveats": [
            "CVM funds and ETFs are not indexed here; use fund endpoints with fund CNPJ or supported ETF ticker.",
        ],
    },
    "AlternativeDataMetadata.list_etfs": {
        "category": "funds",
        "path": "funds/etfs",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "List ETFs available in the public-sources ETF registry. Use this "
            "for ETF discovery because ETFs are not returned by listed-company "
            "search endpoints."
        ),
        "parameters": {
            "query": "Free-text filter over ticker, fund name, CNPJ or issuer.",
            "issuer": "Optional issuer key/name filter.",
            "source": "Holdings source used for reference date and totals: official, approximate or index.",
            "sort_by": "Sort mode: name, ticker, positions_count_desc, total_value_desc or total_value_asc.",
            "min_positions": "Minimum number of positions required.",
            "limit": "Maximum number of ETFs.",
            "offset": "Pagination offset.",
        },
        "relationships": [
            "fund_company_bridge", "company_resolution",
            "fund_market_exposure_bridge",
        ],
    },
    "AlternativeDataMetadata.get_financial_statement_types": {
        "category": "metadata",
        "path": "financial-statements/types",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "List valid financial statement types and aliases accepted by "
            "AlternativeDataCompanies.get_financial_statements."
        ),
        "parameters": {},
        "relationships": ["financial_statement_discovery", "macro_market_bridge"],
    },
    "AlternativeDataMetadata.get_taxonomy": {
        "category": "metadata",
        "path": "taxonomy",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "Get the complete sector/classification taxonomy for B3 or CNAE. "
            "Use B3 for exchange sector, subsector and segment hierarchy; use "
            "CNAE for Brazilian economic activity codes. Reuse returned labels "
            "exactly when filtering peer companies."
        ),
        "parameters": {
            "system": "Classification system, usually 'b3' or 'cnae'.",
            "limit": "Maximum number of taxonomy rows.",
        },
        "relationships": ["sector_peer_set", "sector_market_peer_bridge"],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["sector_taxonomy_labels"]],
    },
    "AlternativeDataMetadata.get_cnae": {
        "category": "metadata",
        "path": "cnae",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "Get official CNAE classification details for a single CNAE code. "
            "Use this when a user provides a CNAE code and asks what it means."
        ),
        "parameters": {"code": "CNAE code."},
        "relationships": ["sector_peer_set", "sector_market_peer_bridge"],
    },
    "AlternativeDataMetadata.get_company_sector": {
        "category": "metadata",
        "path": "companies/sector",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "Get sector classification for a company or listed asset. Rows "
            "include B3 sector, subsector and segment plus registered "
            "headquarters state and municipality when available. Reuse returned "
            "sector labels exactly when building peer sets."
        ),
        "parameters": {"identifier": "Ticker, CNPJ, CVM code, ISIN or company name."},
        "relationships": [
            "sector_peer_set", "company_resolution",
            "company_trading_bridge", "sector_market_peer_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["sector_taxonomy_labels"]],
    },
    "AlternativeDataMetadata.get_sector_companies": {
        "category": "metadata",
        "path": "sectors/companies",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "List companies classified in a B3 sector, optionally filtered by "
            "subsector and segment. Use active_only to restrict to active "
            "companies. For reliable matches, pass exact labels returned by "
            "get_taxonomy or get_company_sector."
        ),
        "parameters": {
            "sector": "B3 sector name.",
            "subsector": "Optional B3 subsector name.",
            "segment": "Optional B3 segment name.",
            "active_only": "If true, return only active companies.",
            "limit": "Maximum number of companies.",
        },
        "relationships": ["sector_peer_set", "sector_market_peer_bridge"],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["sector_taxonomy_labels"]],
    },
    "AlternativeDataMetadata.get_sectors_summary": {
        "category": "metadata",
        "path": "sectors/summary",
        "method": "GET",
        "client": "AlternativeDataMetadata",
        "description": (
            "Get B3 sector summary counts by sector, subsector and segment. Use "
            "this for market composition by sector, not for a company-specific "
            "classification."
        ),
        "parameters": {},
        "relationships": ["sector_peer_set", "sector_market_peer_bridge"],
    },
    "AlternativeDataMacroMarkets.get_macro_indicators": {
        "category": "macro",
        "path": "macro-indicators",
        "method": "GET",
        "client": "AlternativeDataMacroMarkets",
        "description": (
            "Get Brazilian macroeconomic or public fiscal time-series observations. "
            "Indicator values include selic, ipca, ipca_contributions, "
            "ipca_categories, copom, pim, pmc, pms, pnad, gdp, comexstat and "
            "rreo. Returned units, date grains and row fields vary by indicator "
            "and source."
        ),
        "parameters": {
            "indicator": "Macro indicator code.",
            "start_date": "Start date in YYYY-MM-DD when supported by the indicator.",
            "end_date": "End date in YYYY-MM-DD when supported by the indicator.",
            "year": "Four-digit year filter for Comexstat and RREO.",
            "month": "Month filter 1-12 for Comexstat.",
            "period": "Bimester/period filter for RREO.",
            "state": "Brazilian state UF filter for Comexstat or RREO.",
            "country": "Partner country filter for Comexstat.",
            "source": "Optional data-source filter.",
            "type": "Subseries/type filter for PIM, PMC, PMS or GDP, such as industria_geral.",
            "limit": "Maximum number of observations.",
            "offset": "Pagination offset.",
        },
        "relationships": ["macro_indicator_discovery", "macro_market_bridge"],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_macro_indicators"]],
    },
    "AlternativeDataMacroMarkets.get_maximum_theoretical_margin": {
        "category": "market_data_reference",
        "path": "market-data/maximum-theoretical-margin",
        "method": "GET",
        "client": "AlternativeDataMacroMarkets",
        "description": (
            "Get B3 maximum theoretical margin reference data, also known as "
            "haircut or desagio, for assets or instruments. Use this for margin "
            "reference values, not quotes, trades or investor categories."
        ),
        "parameters": {
            "report_date": "Reference date in YYYY-MM-DD; omitted means latest available.",
            "asset": "B3 ticker such as PETR4.",
            "instrument_id": "B3 instrument identifier.",
            "origin": "Optional origin market filter.",
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "min_margin": "Lower bound for discount_margin percentage value.",
            "max_margin": "Upper bound for discount_margin percentage value.",
            "limit": "Maximum number of rows.",
            "offset": "Pagination offset.",
        },
        "relationships": ["asset_discovery", "company_trading_bridge"],
        "caveats": [
            PUBLIC_SOURCES_DATA_GAPS["get_maximum_theoretical_margin"],
            PUBLIC_SOURCES_EXCLUDED_ENDPOINTS["market-data/investor-categories"],
        ],
    },
    "AlternativeDataMacroMarkets.get_dpmfi": {
        "category": "macro",
        "path": "dpmfi",
        "method": "GET",
        "client": "AlternativeDataMacroMarkets",
        "description": (
            "Get monthly stock of DPMFi, Brazilian federal domestic public debt, "
            "by security acronym/indexer such as LTN, LFT, NTN-B, NTN-F and "
            "Demais. This is the official/projection/estimated stock series, "
            "not the PAF composition projection."
        ),
        "parameters": {
            "start_date": "Reference month start in YYYY-MM.",
            "end_date": "Reference month end in YYYY-MM.",
            "status": "Data status: dados_oficiais, projecao or estipulado.",
            "snapshot_date": "Presto partition date in YYYY-MM-DD; omitted means latest available.",
            "limit": "Maximum number of rows.",
            "offset": "Pagination offset.",
        },
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_dpmfi"]],
    },
    "AlternativeDataMacroMarkets.get_dpmfi_composition": {
        "category": "macro",
        "path": "dpmfi/composition",
        "method": "GET",
        "client": "AlternativeDataMacroMarkets",
        "description": (
            "Get DPMFi PAF composition projections: new issuances, "
            "end-of-month outstanding stock and share of total DPMFi debt by "
            "bond category for the forward months available in the selected "
            "snapshot. Returned row fields are reference_date, bond_type, "
            "emissoes, estoque_final and perc_divida."
        ),
        "parameters": {
            "start_date": "Reference month start in YYYY-MM.",
            "end_date": "Reference month end in YYYY-MM.",
            "bond_type": "Bond category: Prefixado, IPCA, Selic or Total; omitted returns all.",
            "snapshot_date": "Presto partition date in YYYY-MM-DD; omitted means latest available.",
            "limit": "Maximum number of rows.",
            "offset": "Pagination offset.",
        },
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_dpmfi_composition"]],
    },
    "AlternativeDataCompanies.get_board": {
        "category": "companies",
        "path": "companies/board",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get members of a company's governance body. body can be board, "
            "executive or committee; committee filters a specific committee when "
            "body='committee'. For Brazilian filings, body='board' can include "
            "Conselho Fiscal rows; filter governance_body/role for Conselho de "
            "Administracao when answering board-of-directors questions."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "reference_date": "Reference date in YYYY-MM-DD; omitted means latest available filing.",
            "body": "Governance body: board, executive or committee.",
            "committee": "Committee name filter when body='committee'.",
            "include_alternates": "Whether to include alternate members.",
            "limit": "Maximum number of members.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_company_board"]],
    },
    "AlternativeDataCompanies.get_governance_summary": {
        "category": "companies",
        "path": "companies/governance-summary",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get a compact latest governance snapshot for a company as a "
            "composite object. It can include board size, committees, CEO and "
            "free-float-related fields when available."
        ),
        "parameters": {"company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"]},
        "relationships": ["company_resolution", "company_trading_bridge"],
    },
    "AlternativeDataCompanies.get_governance_history": {
        "category": "companies",
        "path": "companies/governance-history",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get historical governance snapshots for a company over a date "
            "range. Use this for composition changes over time; use "
            "get_board_changes for event-style appointment and departure changes."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "body": "Optional body filter: board, executive or committee.",
            "limit": "Maximum number of snapshots.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
    },
    "AlternativeDataCompanies.get_governance_documents": {
        "category": "companies",
        "path": "companies/governance-documents",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get CVM governance-related filings for a company. Use category, "
            "governance_topic or event_tag to narrow documents such as "
            "governance forms, elections or committees."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "category": "Optional document category filter.",
            "governance_topic": "Optional governance topic filter.",
            "event_tag": "Optional event tag filter.",
            "limit": "Maximum number of documents.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
        "caveats": [
            "For buybacks or Brazilian insider-trading disclosures, use get_disclosures instead.",
        ],
    },
    "AlternativeDataCompanies.get_governance_compensation": {
        "category": "companies",
        "path": "companies/governance-compensation",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get governance compensation or remuneration records for a company, "
            "optionally filtered by fiscal_year."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "fiscal_year": "Optional four-digit fiscal year.",
            "limit": "Maximum number of records.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
    },
    "AlternativeDataCompanies.get_governance_related_party": {
        "category": "companies",
        "path": "companies/governance-related-party",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get related-party transaction records for a company. Use "
            "relation_category when the relationship or transaction class is known."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "relation_category": "Optional relationship/transaction category filter.",
            "limit": "Maximum number of records.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
    },
    "AlternativeDataCompanies.get_governance_beneficial_ownership": {
        "category": "companies",
        "path": "companies/governance-beneficial-ownership",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get beneficial-owner records from UK Companies House PSC or US SEC "
            "proxy DEF14A data. Brazilian companies are not available here."
        ),
        "parameters": {
            "company_id": (
                "UK company number, SEC ticker/CIK, ISIN, LEI or company name. "
                "Use values such as AAPL or 0000320193 for US coverage."
            ),
            "holder_type": (
                "Optional holder classification such as individual, institution, "
                "director, officer or ten_percent_owner."
            ),
            "limit": "Maximum number of owners.",
            "offset": "Pagination offset.",
        },
        "relationships": [
            "company_resolution", "ownership_fallback",
            "ownership_liquidity_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_beneficial_ownership"]],
    },
    "AlternativeDataCompanies.get_corporate_registry": {
        "category": "companies",
        "path": "companies/corporate-registry",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get official corporate registry relationships for a legal entity. "
            "direction='partners' shows who owns the entity; direction='investees' "
            "shows entities it owns or participates in."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "direction": "partners or investees.",
            "reference_month": "Optional reference month in YYYY-MM.",
            "partner_type": "Optional partner type filter.",
            "qualification": "Optional partner qualification filter.",
            "limit": "Maximum number of records.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
    },
    "AlternativeDataCompanies.get_insider_trades": {
        "category": "companies",
        "path": "companies/insider-trades",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get US SEC insider-trading transactions for a US company ticker or "
            "CIK. This endpoint is not for Brazilian companies."
        ),
        "parameters": {
            "company_id": "US SEC ticker or CIK.",
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "transaction_code": "Optional SEC transaction code such as P or S.",
            "limit": "Maximum number of transactions.",
        },
        "relationships": ["br_vs_us_insiders", "document_market_event_bridge"],
    },
    "AlternativeDataCompanies.get_board_changes": {
        "category": "companies",
        "path": "companies/board-changes",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get board or executive change events for a company, such as "
            "appointments and departures. Use this for event timelines; use "
            "get_board for composition at a date."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "event": "Optional event type filter.",
            "limit": "Maximum number of events.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
    },
    "AlternativeDataCompanies.get_financial_statements": {
        "category": "companies",
        "path": "companies/financial-statements",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get company financial-statement line items from CVM filings. "
            "statement can be income_statement, balance_sheet or cash_flow; "
            "use account_code to retrieve a specific account. Omit company_id "
            "only for universe-level screens or rankings."
        ),
        "parameters": {
            "company_id": (
                PUBLIC_SOURCES_CONVENTIONS["company_id"]
                + " Omit only for universe-level screens or rankings."
            ),
            "statement": "Statement type or alias, for example income_statement, balance_sheet or cash_flow.",
            "quarter": "Brazilian quarter code such as 1T24 or 4T24.",
            "reference_date": "Reference date in YYYY-MM-DD.",
            "statement_type": "Optional presentation/filter such as consolidated or individual when supported.",
            "account_code": "Optional account code filter.",
            "limit": "Maximum number of line items.",
            "offset": "Pagination offset.",
        },
        "relationships": [
            "company_resolution", "financial_statement_discovery",
            "company_trading_bridge", "sector_market_peer_bridge",
            "macro_market_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_financial_statements"]],
    },
    "AlternativeDataCompanies.get_financial_notes": {
        "category": "companies",
        "path": "companies/financial-notes",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get structured explanatory notes, notas explicativas, from CVM "
            "DFP/ITR filings. Use this for note text and parsed note details, "
            "not accounting line-item tables."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "quarter": "Brazilian quarter code such as 1T24 or 4T24.",
            "limit": "Maximum number of notes.",
            "offset": "Pagination offset.",
        },
        "relationships": [
            "company_resolution", "company_trading_bridge",
            "macro_market_bridge",
        ],
    },
    "AlternativeDataCompanies.get_disclosures": {
        "category": "companies",
        "path": "companies/disclosures",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get CVM disclosure documents for Brazilian companies. "
            "document_type='repurchase' returns share-buyback documents; "
            "document_type='insiders' returns Brazilian insider-trading "
            "disclosures; the upstream alias 'insider' is also accepted."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "document_type": "repurchase or insiders; upstream also accepts insider.",
            "asset": "Optional asset ticker filter.",
            "protocol_number": "Optional CVM protocol number filter.",
            "reference_date": "Reference date in YYYY-MM-DD.",
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "transaction": "Optional transaction description filter.",
            "transaction_type": "Optional transaction type filter.",
            "participant_group": "Optional participant group filter.",
            "limit": "Maximum number of documents.",
            "offset": "Pagination offset.",
        },
        "relationships": [
            "company_resolution", "br_vs_us_insiders",
            "company_trading_bridge", "document_market_event_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_disclosure_documents_repurchase"]],
    },
    "AlternativeDataCompanies.get_assemblies": {
        "category": "companies",
        "path": "companies/assemblies",
        "method": "GET",
        "client": "AlternativeDataCompanies",
        "description": (
            "Get the shareholder assembly index, AGO/AGE, for a Brazilian "
            "company. Returned records can include assembly type, parsed agenda "
            "items and CVM RAD URLs for minutes, decision summaries and call notices."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "limit": "Maximum number of assemblies.",
        },
        "relationships": [
            "company_resolution", "document_summary",
            "company_trading_bridge", "document_market_event_bridge",
        ],
    },
    "PublicSources.get_opas": {
        "category": "companies",
        "path": "opas",
        "method": "GET",
        "client": "PublicSources",
        "description": (
            "Get Brazilian tender offers, OPAs, from public-source disclosures. "
            "start_date and end_date are required and filter registration_date."
        ),
        "parameters": {
            "start_date": "Required start date in YYYY-MM-DD.",
            "end_date": "Required end date in YYYY-MM-DD.",
            "asset": "Optional asset ticker filter.",
            "type": "Optional OPA type filter.",
        },
    },
    "AlternativeDataPeople.get_appointments": {
        "category": "people",
        "path": "people/appointments",
        "method": "GET",
        "client": "AlternativeDataPeople",
        "description": (
            "Get a person's appointments, mandates or roles across companies. "
            "Search by person_id when known or by name for fuzzy discovery; "
            "active_only restricts current roles."
        ),
        "parameters": {
            "person_id": "Person id such as CPF, slug:name, cpf:CPF, uk_officer:id or SEC CIK.",
            "name": "Optional fuzzy name search.",
            "active_only": "If true, return only current roles.",
            "body": "Optional governance body filter: board, executive or committee.",
            "group_by": "Use 'company' to aggregate by company when supported.",
            "limit": "Maximum number of appointments.",
            "offset": "Pagination offset.",
        },
        "relationships": ["company_resolution", "company_trading_bridge"],
    },
    "AlternativeDataFunds.get_holdings": {
        "category": "funds",
        "path": "funds/holdings",
        "method": "GET",
        "client": "AlternativeDataFunds",
        "description": (
            "Get a fund or ETF portfolio holdings/positions for a reference date. "
            "Use this for constituent assets and weights or values, not NAV history."
        ),
        "parameters": {
            "fund_id": PUBLIC_SOURCES_CONVENTIONS["fund_id"],
            "reference_date": "Reference date in YYYY-MM-DD; omitted means latest snapshot.",
            "asset_class": "Optional asset class filter.",
            "source": "Holdings source: official, approximate or index.",
            "limit": "Maximum number of holdings.",
            "offset": "Pagination offset.",
        },
        "relationships": ["fund_company_bridge", "fund_market_exposure_bridge"],
    },
    "AlternativeDataFunds.get_exposures": {
        "category": "funds",
        "path": "funds/exposures",
        "method": "GET",
        "client": "AlternativeDataFunds",
        "description": (
            "Get aggregate exposures for a fund or ETF by dimension. "
            "exposure_type can be all, asset_class, issuer, sector, indexer, "
            "maturity or country. Use holdings for constituent-level exposure "
            "when a dimension is sparse or source-dependent."
        ),
        "parameters": {
            "fund_id": PUBLIC_SOURCES_CONVENTIONS["fund_id"],
            "reference_date": "Reference date in YYYY-MM-DD; omitted means latest snapshot.",
            "exposure_type": "Exposure dimension: all, asset_class, issuer, sector, indexer, maturity or country.",
        },
        "relationships": [
            "fund_company_bridge", "sector_peer_set",
            "fund_market_exposure_bridge", "sector_market_peer_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_fund_exposures"]],
    },
    "AlternativeDataFunds.get_history": {
        "category": "funds",
        "path": "funds/history",
        "method": "GET",
        "client": "AlternativeDataFunds",
        "description": (
            "Get a fund's NAV/AUM or portfolio-value history over time. Mutual "
            "funds return net_worth, quota_value and shareholders when available; "
            "ETFs can return total_value and positions_count instead."
        ),
        "parameters": {
            "fund_id": PUBLIC_SOURCES_CONVENTIONS["fund_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "limit": "Maximum number of snapshots.",
        },
        "relationships": ["fund_company_bridge", "fund_market_exposure_bridge"],
        "caveats": [
            "ETF history can use portfolio total_value because ETFs do not have the same daily CVM NAV filing schema as mutual funds.",
        ],
    },
    "AlternativeDataFunds.get_lookthrough": {
        "category": "funds",
        "path": "funds/lookthrough",
        "method": "GET",
        "client": "AlternativeDataFunds",
        "description": (
            "Get recursive look-through exposure for a fund or ETF. Use this to "
            "expand nested fund holdings into underlying assets when available; "
            "for direct-equity ETFs, holdings and exposures can be more useful."
        ),
        "parameters": {
            "fund_id": PUBLIC_SOURCES_CONVENTIONS["fund_id"],
            "reference_date": "Reference date in YYYY-MM-DD; omitted means latest snapshot.",
            "limit": "Maximum number of look-through rows.",
        },
        "relationships": ["fund_company_bridge", "fund_market_exposure_bridge"],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_fund_lookthrough"]],
    },
    "AlternativeDataFunds.get_manager_aggregate_holdings": {
        "category": "funds",
        "path": "managers/aggregate-holdings",
        "method": "GET",
        "client": "AlternativeDataFunds",
        "description": (
            "Get a manager's aggregate holdings across all covered funds managed "
            "by that manager when the upstream registry can attribute funds to "
            "that manager. manager_id accepts a manager CNPJ or exact manager "
            "name, not an ETF ticker, ETF issuer slug or fund CNPJ."
        ),
        "parameters": {
            "manager_id": "Manager CNPJ or exact manager name present in covered fund registry/ownership snapshots.",
            "reference_date": "Reference date in YYYY-MM-DD; omitted means latest snapshot.",
            "limit": "Maximum number of holdings.",
        },
        "relationships": ["fund_company_bridge", "fund_market_exposure_bridge"],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_manager_aggregate_holdings"]],
    },
    "AlternativeDataOwnership.get_top_shareholders": {
        "category": "ownership",
        "path": "companies/shareholders/top",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get top shareholders for a company from the normalized "
            "ownership_snapshot layer when shareholder-level snapshots are "
            "available. Brazilian CVM/FRE rows are periodic filing snapshots."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "reference_date": (
                "Reference date in YYYY-MM-DD; omitted means latest loaded "
                "snapshot per ownership_category. Provided values are exact "
                "loaded snapshot dates, not as-of lookups."
            ),
            "ownership_category": "Ownership category filter when supported.",
            "limit": "Maximum number of shareholders.",
        },
        "relationships": [
            "company_resolution", "ownership_fallback",
            "ownership_liquidity_bridge",
        ],
        "caveats": [
            PUBLIC_SOURCES_DATA_GAPS["get_top_shareholders"],
            PUBLIC_SOURCES_DATA_GAPS["ownership_reporting_dates"],
        ],
    },
    "AlternativeDataOwnership.get_ownership_current": {
        "category": "ownership",
        "path": "companies/ownership-current",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get current ownership structure of a listed company as a composite "
            "object. Use this for latest control, free-float and ownership summary context."
        ),
        "parameters": {"company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"]},
        "relationships": [
            "company_resolution", "ownership_fallback",
            "ownership_liquidity_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["ownership_reporting_dates"]],
    },
    "AlternativeDataOwnership.get_ownership_history": {
        "category": "ownership",
        "path": "companies/ownership-history",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get historical ownership snapshots for a company from the "
            "normalized ownership_snapshot layer. Brazilian CVM/FRE snapshots "
            "are periodic filing dates, not guaranteed month-end series. Use "
            "ownership_category to filter holder categories when supported."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "ownership_category": "Ownership category filter when supported.",
            "limit": "Maximum number of snapshot reference dates.",
        },
        "relationships": [
            "company_resolution", "ownership_fallback",
            "ownership_liquidity_bridge",
        ],
        "caveats": [
            PUBLIC_SOURCES_DATA_GAPS["get_ownership_history"],
            PUBLIC_SOURCES_DATA_GAPS["ownership_reporting_dates"],
        ],
    },
    "AlternativeDataOwnership.get_ownership_change_events": {
        "category": "ownership",
        "path": "companies/ownership-change-events",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get ownership change events for a company, derived from differences "
            "between ownership snapshots. Use this for event timelines instead "
            "of raw snapshots."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "ownership_category": "Ownership category filter when supported.",
            "limit": "Maximum number of events.",
        },
        "relationships": [
            "company_resolution", "ownership_fallback", "document_summary",
            "ownership_liquidity_bridge", "document_market_event_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["ownership_reporting_dates"]],
    },
    "AlternativeDataOwnership.get_ownership_official_notices": {
        "category": "ownership",
        "path": "companies/ownership-official-notices",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get official ownership notices and related IR evidence for a "
            "company. The response can contain official_notices, ir_page_sources "
            "and ir_structures; use official_notices download_url values for "
            "document summaries."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "parser_status": "Parser status filter: parsed, unparsed or all.",
            "limit": "Maximum number of notices.",
        },
        "relationships": [
            "company_resolution", "ownership_fallback", "document_summary",
            "ownership_liquidity_bridge", "document_market_event_bridge",
        ],
        "caveats": [
            PUBLIC_SOURCES_DATA_GAPS["get_ownership_official_notices"],
            PUBLIC_SOURCES_DATA_GAPS["ownership_reporting_dates"],
        ],
    },
    "AlternativeDataOwnership.get_notice_summary": {
        "category": "ownership",
        "path": "companies/notices/summary",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Download a CVM RAD PDF URL and generate a concise AI summary. "
            "Results are cached per URL and language."
        ),
        "parameters": {
            "url": "CVM RAD PDF URL returned by assemblies or official notices.",
            "lang": "Summary language: pt, en or es.",
        },
        "relationships": ["document_summary", "document_market_event_bridge"],
    },
    "AlternativeDataOwnership.get_ownership_control_group": {
        "category": "ownership",
        "path": "companies/ownership-control-group",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get controlling shareholders, shareholder agreements and control "
            "evidence for a company as a composite object. Use this for who "
            "controls the company, not for all holder positions."
        ),
        "parameters": {"company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"]},
        "relationships": [
            "company_resolution", "ownership_fallback",
            "ownership_liquidity_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["ownership_reporting_dates"]],
    },
    "AlternativeDataOwnership.get_ownership_free_float": {
        "category": "ownership",
        "path": "companies/ownership-free-float",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get free-float percentage and share-class details for a company as "
            "a composite object. Use this for investable-float questions."
        ),
        "parameters": {
            "company_id": PUBLIC_SOURCES_CONVENTIONS["company_id"],
            "limit": "Maximum number of share-class/detail rows when returned.",
        },
        "relationships": [
            "company_resolution", "ownership_fallback",
            "ownership_liquidity_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["ownership_reporting_dates"]],
    },
    "AlternativeDataOwnership.get_shareholder_holdings": {
        "category": "ownership",
        "path": "shareholders/holdings",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get one shareholder's holdings across companies. Use this for "
            "portfolio-by-holder questions, not company ownership summaries."
        ),
        "parameters": {
            "shareholder_id": PUBLIC_SOURCES_CONVENTIONS["shareholder_id"],
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "ownership_category": "Ownership category filter when supported.",
            "limit": "Maximum number of holdings.",
            "offset": "Pagination offset.",
        },
        "relationships": ["ownership_fallback", "ownership_liquidity_bridge"],
    },
    "AlternativeDataOwnership.get_institutional_holders": {
        "category": "ownership",
        "path": "assets/institutional-holders",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get institutional holders of an asset from the precomputed "
            "asset-holder layer. identifier defaults to a B3 ticker when "
            "identifier_type='b3_ticker'."
        ),
        "parameters": {
            "identifier": PUBLIC_SOURCES_CONVENTIONS["asset_identifier"],
            "identifier_type": "Identifier type: b3_ticker, isin, cusip or issuer_cnpj.",
            "reference_date": "Reference date in YYYY-MM-DD; omitted means latest snapshot.",
            "limit": "Maximum number of holders.",
        },
        "relationships": ["fund_company_bridge", "fund_market_exposure_bridge"],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_asset_institutional_holders"]],
    },
    "AlternativeDataOwnership.get_fund_holders": {
        "category": "ownership",
        "path": "assets/fund-holders",
        "method": "GET",
        "client": "AlternativeDataOwnership",
        "description": (
            "Get investment funds or ETFs holding a given asset using fund "
            "portfolio and ETF holding snapshots. identifier defaults to a B3 "
            "ticker when identifier_type='b3_ticker'."
        ),
        "parameters": {
            "identifier": PUBLIC_SOURCES_CONVENTIONS["asset_identifier"],
            "identifier_type": "Identifier type: b3_ticker, isin, cusip or issuer_cnpj.",
            "reference_date": "Reference date in YYYY-MM-DD; omitted means latest snapshot.",
            "limit": "Maximum number of funds.",
        },
        "relationships": ["fund_company_bridge", "fund_market_exposure_bridge"],
    },
    "PublicSources.get_share_repurchase": {
        "category": "companies",
        "path": "share-repurchase",
        "method": "GET",
        "client": "PublicSources",
        "description": (
            "Get share-repurchase transactions from public sources filtered by "
            "reference_date range and optional asset."
        ),
        "parameters": {
            "start_date": "Required start date in YYYY-MM-DD.",
            "end_date": "Required end date in YYYY-MM-DD.",
            "asset": "Optional asset ticker filter.",
            "raw_data": "If true, return upstream raw data; otherwise return a DataFrame.",
        },
        "relationships": [
            "company_resolution", "company_trading_bridge",
            "document_market_event_bridge",
        ],
        "caveats": [PUBLIC_SOURCES_DATA_GAPS["get_disclosure_documents_repurchase"]],
    },
}


_PUBLIC_SOURCES_ENDPOINT_ALIASES: dict[str, tuple[str, str]] = {
    "AlternativeDataCompanies.list_companies": (
        "AlternativeDataMetadata.list_companies",
        "AlternativeDataCompanies",
    ),
    "AlternativeDataFunds.list_etfs": (
        "AlternativeDataMetadata.list_etfs",
        "AlternativeDataFunds",
    ),
}

for _alias, (_target, _client) in _PUBLIC_SOURCES_ENDPOINT_ALIASES.items():
    PUBLIC_SOURCES_ENDPOINTS[_alias] = deepcopy(PUBLIC_SOURCES_ENDPOINTS[_target])
    PUBLIC_SOURCES_ENDPOINTS[_alias]["client"] = _client


PUBLIC_SOURCES_TOOL_ENDPOINTS: dict[str, str] = {
    "search_companies": "AlternativeDataMetadata.get_company_directory",
    "list_available_indicators": "AlternativeDataMetadata.get_available_indicators",
    "get_macro_observations": "AlternativeDataMacroMarkets.get_macro_indicators",
    "get_maximum_theoretical_margin": "AlternativeDataMacroMarkets.get_maximum_theoretical_margin",
    "get_dpmfi": "AlternativeDataMacroMarkets.get_dpmfi",
    "get_dpmfi_composition": "AlternativeDataMacroMarkets.get_dpmfi_composition",
    "get_financial_notes": "AlternativeDataCompanies.get_financial_notes",
    "list_available_assets": "AlternativeDataMetadata.get_available_assets",
    "list_datasets": "AlternativeDataMetadata.get_datasets",
    "list_financial_statement_types": "AlternativeDataMetadata.get_financial_statement_types",
    "get_sector_taxonomy": "AlternativeDataMetadata.get_taxonomy",
    "get_cnae": "AlternativeDataMetadata.get_cnae",
    "get_sector_summary": "AlternativeDataMetadata.get_sectors_summary",
    "get_company_board": "AlternativeDataCompanies.get_board",
    "get_governance_summary": "AlternativeDataCompanies.get_governance_summary",
    "get_governance_history": "AlternativeDataCompanies.get_governance_history",
    "get_governance_documents": "AlternativeDataCompanies.get_governance_documents",
    "get_governance_compensation": "AlternativeDataCompanies.get_governance_compensation",
    "get_related_party": "AlternativeDataCompanies.get_governance_related_party",
    "get_beneficial_ownership": "AlternativeDataCompanies.get_governance_beneficial_ownership",
    "get_corporate_registry": "AlternativeDataCompanies.get_corporate_registry",
    "get_insider_trades": "AlternativeDataCompanies.get_insider_trades",
    "get_board_changes": "AlternativeDataCompanies.get_board_changes",
    "get_company_assemblies": "AlternativeDataCompanies.get_assemblies",
    "get_company_sector": "AlternativeDataMetadata.get_company_sector",
    "get_companies_by_sector": "AlternativeDataMetadata.get_sector_companies",
    "get_financial_statements": "AlternativeDataCompanies.get_financial_statements",
    "get_disclosure_documents": "AlternativeDataCompanies.get_disclosures",
    "get_opas": "PublicSources.get_opas",
    "get_share_repurchase": "PublicSources.get_share_repurchase",
    "get_person_appointments": "AlternativeDataPeople.get_appointments",
    "list_etfs": "AlternativeDataFunds.list_etfs",
    "get_fund_holdings": "AlternativeDataFunds.get_holdings",
    "get_fund_exposures": "AlternativeDataFunds.get_exposures",
    "get_fund_history": "AlternativeDataFunds.get_history",
    "get_fund_lookthrough": "AlternativeDataFunds.get_lookthrough",
    "get_manager_aggregate_holdings": "AlternativeDataFunds.get_manager_aggregate_holdings",
    "get_top_shareholders": "AlternativeDataOwnership.get_top_shareholders",
    "get_ownership_current": "AlternativeDataOwnership.get_ownership_current",
    "get_ownership_history": "AlternativeDataOwnership.get_ownership_history",
    "get_ownership_change_events": "AlternativeDataOwnership.get_ownership_change_events",
    "get_ownership_official_notices": "AlternativeDataOwnership.get_ownership_official_notices",
    "get_notice_summary": "AlternativeDataOwnership.get_notice_summary",
    "get_control_group": "AlternativeDataOwnership.get_ownership_control_group",
    "get_free_float": "AlternativeDataOwnership.get_ownership_free_float",
    "get_shareholder_holdings": "AlternativeDataOwnership.get_shareholder_holdings",
    "get_asset_institutional_holders": "AlternativeDataOwnership.get_institutional_holders",
    "get_asset_fund_holders": "AlternativeDataOwnership.get_fund_holders",
}


def _format_mapping(mapping: dict[str, str]) -> str:
    return "; ".join(f"{key}: {value}" for key, value in mapping.items())


def _build_endpoint_description(endpoint: dict[str, Any]) -> str:
    pieces = [endpoint["description"]]
    parameters = endpoint.get("parameters") or {}
    if parameters:
        pieces.append("Parameters: " + _format_mapping(parameters) + ".")
    relation_keys = endpoint.get("relationships") or []
    if relation_keys:
        relations = [PUBLIC_SOURCES_ENDPOINT_RELATIONSHIPS[key] for key in relation_keys]
        pieces.append("Endpoint relationships: " + " ".join(relations))
    caveats = endpoint.get("caveats") or []
    if caveats:
        pieces.append("Caveats: " + " ".join(caveats))
    return " ".join(pieces)


PUBLIC_SOURCES_ENDPOINT_DESCRIPTIONS: dict[str, str] = {
    key: _build_endpoint_description(endpoint)
    for key, endpoint in PUBLIC_SOURCES_ENDPOINTS.items()
}


PUBLIC_SOURCES_TOOL_DESCRIPTIONS: dict[str, str] = {
    tool_name: PUBLIC_SOURCES_ENDPOINT_DESCRIPTIONS[endpoint_key]
    for tool_name, endpoint_key in PUBLIC_SOURCES_TOOL_ENDPOINTS.items()
}


def get_public_sources_endpoint(name: str) -> dict[str, Any]:
    """Return technical endpoint metadata by endpoint key or MCP-style tool name."""
    endpoint_key = PUBLIC_SOURCES_TOOL_ENDPOINTS.get(name, name)
    if endpoint_key not in PUBLIC_SOURCES_ENDPOINTS:
        raise KeyError(f"Unknown public-sources endpoint or tool: {name}")
    return deepcopy(PUBLIC_SOURCES_ENDPOINTS[endpoint_key])


def get_public_sources_endpoint_description(name: str) -> str:
    """Return the technical description for an endpoint key or MCP-style tool name."""
    endpoint_key = PUBLIC_SOURCES_TOOL_ENDPOINTS.get(name, name)
    if endpoint_key not in PUBLIC_SOURCES_ENDPOINT_DESCRIPTIONS:
        raise KeyError(f"Unknown public-sources endpoint or tool: {name}")
    return PUBLIC_SOURCES_ENDPOINT_DESCRIPTIONS[endpoint_key]


def get_public_sources_tool_description(tool_name: str) -> str:
    """Return the technical description for an MCP-style public-sources tool name."""
    if tool_name not in PUBLIC_SOURCES_TOOL_DESCRIPTIONS:
        raise KeyError(f"Unknown public-sources tool: {tool_name}")
    return PUBLIC_SOURCES_TOOL_DESCRIPTIONS[tool_name]


def get_public_sources_tool_manifest() -> list[dict[str, Any]]:
    """Return endpoint metadata arranged by MCP-style tool name."""
    manifest = []
    for tool_name, endpoint_key in PUBLIC_SOURCES_TOOL_ENDPOINTS.items():
        endpoint = get_public_sources_endpoint(endpoint_key)
        endpoint["tool_name"] = tool_name
        endpoint["endpoint_key"] = endpoint_key
        endpoint["description"] = PUBLIC_SOURCES_TOOL_DESCRIPTIONS[tool_name]
        manifest.append(endpoint)
    return manifest
