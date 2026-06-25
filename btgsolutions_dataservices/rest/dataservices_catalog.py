from __future__ import annotations

from copy import deepcopy
from typing import Any


DATASERVICES_CONVENTIONS: dict[str, str] = {
    "ticker": (
        "Exchange ticker or symbol accepted by the requested market-data domain. "
        "Use the corresponding available-tickers endpoint when coverage or "
        "market type is uncertain."
    ),
    "tickers": (
        "List of exchange tickers. Most REST endpoints serialize this as a "
        "comma-separated query parameter."
    ),
    "market_type": (
        "Brazilian B3 market segment. Common values are stocks, derivatives, "
        "options and indices; each endpoint documents its allowed subset."
    ),
    "mode": (
        "Quote mode. Use realtime for live data when the key is entitled; use "
        "delayed for 15-minute delayed data where supported."
    ),
    "delay": (
        "Intraday-candle delay selector. Allowed values are realtime and delayed."
    ),
    "date": "ISO date in YYYY-MM-DD.",
    "datetime": (
        "ISO-8601 datetime. Book-scope endpoints expect UTC timestamps such as "
        "2026-05-28T14:12:00Z and enforce a 10-minute maximum window."
    ),
    "raw_data": (
        "Python-client switch that returns raw API JSON or file payloads instead "
        "of pandas objects. MCP tools normally persist normalized results as "
        "dataset handles."
    ),
}


DATASERVICES_ENDPOINT_RELATIONSHIPS: dict[str, str] = {
    "ticker_discovery": (
        "Use the available-tickers endpoint for the target domain before "
        "requesting quotes, candles, last events, bulk data or stock-loan data "
        "when the ticker universe is uncertain."
    ),
    "crypto_ticker_discovery": (
        "Use the crypto available-tickers endpoint for the target exchange/date "
        "before requesting crypto candles when the supported crypto universe is "
        "uncertain. This discovery is separate from B3 equity/derivatives "
        "coverage."
    ),
    "reference_enrichment": (
        "Use get_ticker_reference to enrich tickers with instrument "
        "metadata such as security id, currency, lot size and tick size before "
        "joining market-data results across tools."
    ),
    "events_price_context": (
        "Use get_corporate_events to identify ex-date corporate events and then "
        "compare with historical candles or quotes. If corporate_events_adj is "
        "true, historical candle prices are adjusted for events."
    ),
    "hfn_filter_discovery": (
        "Use get_news_filters to discover countries, sources, feeds and "
        "languages before calling latest or historical news with narrow filters."
    ),
    "broker_reference": (
        "Use get_broker_reference to map broker codes and names before broker "
        "analytics. Broker analytics is D0 realtime data and should not be read "
        "as historical broker flow."
    ),
    "bulk_data_discovery": (
        "Use list_bulk_data_tickers and list_bulk_market_data_channels before "
        "requesting ticker/date bulk data or compressed market-data files."
    ),
    "book_scope_microstructure": (
        "get_book_scope combines trades, book snapshots and incremental book "
        "events for one symbol and a short time window. Use it for microstructure "
        "questions after a ticker, market_type and event window are known."
    ),
    "company_identifier_bridge": (
        "Use search_companies or resolve_company_identifier to translate company "
        "names, CNPJ, CVM code or ISIN into B3 tickers before requesting quotes, "
        "candles, intraday trades, last events, stock-loan, broker analytics or "
        "book-scope data. Use company, governance, ownership and statement "
        "endpoints after market data when business context is needed."
    ),
    "sector_peer_market_bridge": (
        "Use get_company_sector and get_companies_by_sector to build a peer "
        "ticker universe, then compare "
        "quotes, historical candle returns, liquidity, stock-loan data or "
        "broker-flow metrics across the peer set."
    ),
    "fund_market_exposure_bridge": (
        "Use get_fund_holdings, get_fund_exposures, get_fund_lookthrough or "
        "get_asset_fund_holders to derive underlying tickers, then use "
        "get_ticker_reference, quotes, candles and stock-loan tools to analyze "
        "the market behavior and liquidity of those exposures."
    ),
    "ownership_liquidity_bridge": (
        "Use get_ownership_current, get_control_group and get_free_float with "
        "quotes, historical volume, stock-loan trades and broker analytics to "
        "contextualize float, liquidity and flow. These joins provide context "
        "and should not be treated as proof of causality."
    ),
    "public_document_event_bridge": (
        "Use Public Sources disclosures, assemblies, official notices, HFN news "
        "and CorporateEvents to identify event dates or timestamps before "
        "requesting historical candles, intraday candles, tick trades or "
        "BookScope windows for event analysis."
    ),
    "macro_market_bridge": (
        "Use get_macro_observations with sector peer sets, company fundamentals "
        "and historical candles to frame macro exposure, sensitivity or "
        "co-movement. This is analytical context, not a causal model by itself."
    ),
}


DATASERVICES_RESULT_CONTRACTS: dict[str, str] = {
    "quotes": (
        "MCP result is a dataset handle whose rows are current quote snapshots, "
        "typically one row per ticker. Common fields include ticker, price "
        "fields, financial volume, traded volume, variation fields, "
        "last_close_time and currency."
    ),
    "candles": (
        "MCP result is a dataset handle with one row per candle. Common fields "
        "include symbol or ticker, candle_time or date, open_time, close_time, "
        "open_price, close_price, high_price, low_price, number_of_trades, "
        "financial_volume and volume. Datetime fields follow the requested "
        "timezone parameter."
    ),
    "crypto_candles": (
        "MCP result is a dataset handle with crypto OHLCV time-series rows. "
        "These rows are market-data time series only and do not join naturally "
        "to B3 company, CVM filing, ownership, sector or governance endpoints."
    ),
    "intraday_candles": (
        "MCP result is a dataset handle with current-session candle rows, often "
        "grouped by ticker. Use the requested timezone and candle_period when "
        "joining or aggregating."
    ),
    "tick_data": (
        "MCP result is a dataset handle with current-day tick trade rows. Use "
        "trade timestamps for ordering and compare with intraday candles or "
        "book-scope data only after aligning timezones."
    ),
    "last_event": (
        "MCP result is a dataset handle with the latest snapshot rows for the "
        "requested event family. It is a current snapshot, not a historical "
        "time series."
    ),
    "reference_data": (
        "MCP result is a dataset handle with instrument reference rows. Common "
        "fields include ticker or symbol, security identifiers, market type, "
        "currency, lot size and tick size."
    ),
    "corporate_events": (
        "MCP result is a dataset handle with corporate-event rows by ex-date "
        "and ticker when available. Use it to explain price adjustment context "
        "and then confirm issuer identity before joining with disclosures or "
        "news."
    ),
    "company_data": (
        "MCP result is a dataset handle. General-info output usually has one "
        "row per ticker with identity, sector and description fields. "
        "Financial-table output is table-specific and can be wide; columns may "
        "represent periods or financial line items, so inspect the dataset "
        "schema before ranking or comparing values. Valuation tables commonly "
        "include fields such as EV/Revenues, EV/EBITDA, P/E, Price/BV, Dividend "
        "Yield (%), EBITDA, EBIT, market capitalization and net debt when "
        "available. Income-statement, balance-sheet, cash-flow, ratios, growth "
        "and interims tables have different shapes. Values, units and currency "
        "must be read from the returned table fields."
    ),
    "news": (
        "MCP result is a dataset handle with HFN item rows. Common fields "
        "include _id, title, url, published_at, ingested_at, metadata, tags or "
        "processed content fields. Use published_at for event windows, inspect "
        "metadata/tags before assigning a company, and deduplicate by _id or "
        "url when combining latest and historical queries."
    ),
    "stock_loan": (
        "MCP result is a dataset handle with stock-loan trade rows or ticker "
        "coverage rows. Common fields include ticker, trade date, quantity and "
        "rate, but inspect the returned schema before calculations."
    ),
    "bulk_data": (
        "MCP result is a dataset handle for large tick, book or security-list "
        "files. For data_type='trades', expect trade-level rows; for "
        "data_type='books', expect book snapshot/order-book rows; for "
        "data_type='trades-and-book-events', expect a mix of trade and book "
        "event records; the security-list endpoint returns one row per listed "
        "instrument. Exact columns depend on source file, so inspect the schema "
        "before filtering, joining or exporting."
    ),
    "broker_reference": (
        "MCP result is a dataset handle mapping broker codes and names. Use "
        "this before broker analytics when users provide broker names."
    ),
    "broker_analytics": (
        "MCP result is a dataset handle with D0 broker-flow analytics rows or "
        "named blocks. It is current-trading-day data, not a historical broker "
        "position or inventory database."
    ),
    "book_scope": (
        "MCP result is a dataset handle with selected book-scope datasets such "
        "as trades, book_snapshot and book_incremental. Timestamps are UTC ISO "
        "datetimes and the request window is capped at 10 minutes."
    ),
}


DATASERVICES_ENDPOINTS: dict[str, dict[str, Any]] = {
    "Quotes.get_quote": {
        "category": "quotes",
        "path": "/api/v1/marketdata/br/b3/{mode}/quotes/{market_type}/tickers",
        "method": "GET",
        "client": "Quotes",
        "description": (
            "Return realtime or delayed B3 quote snapshots for one or more "
            "tickers in a market segment. Use for current price, variation, bid, "
            "ask and quote fields, not for historical bars."
        ),
        "parameters": {
            "tickers": "List of tickers such as ['PETR4', 'VALE3'].",
            "market_type": "Market segment: stocks, options, derivatives or indices.",
            "mode": "Quote mode: realtime or delayed.",
        },
        "relationships": [
            "ticker_discovery", "reference_enrichment",
            "company_identifier_bridge", "sector_peer_market_bridge",
            "fund_market_exposure_bridge",
        ],
    },
    "Quotes.get_top_bottom": {
        "category": "quotes",
        "path": "/api/v1/marketdata/br/b3/{mode}/quotes/{market_type}/top-bottom",
        "method": "GET",
        "client": "Quotes",
        "description": (
            "Return top and bottom quote movers for a B3 market segment, ranked "
            "by intraday or interday variation and optionally filtered by ticker "
            "type such as IBOV, SHARE, BDR, FII, ETF or UNIT."
        ),
        "parameters": {
            "market_type": "Market segment: stocks, options, derivatives or indices.",
            "mode": "Quote mode: realtime or delayed.",
            "ticker_type": "Ticker universe filter such as IBOV, SHARE, BDR, FII, ETF or UNIT.",
            "variation": "Variation basis: intraday or interday.",
            "n": "Number of top and bottom rows to return.",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "sector_peer_market_bridge",
        ],
    },
    "Quotes.get_available_tickers": {
        "category": "quotes",
        "path": "/api/v1/marketdata/br/b3/{mode}/quotes/{market_type}/available-tickers",
        "method": "GET",
        "client": "Quotes",
        "description": (
            "List tickers available for quote queries for a given market segment "
            "and realtime/delayed mode."
        ),
        "parameters": {
            "market_type": "Market segment: stocks, options, derivatives or indices.",
            "mode": "Quote mode: realtime or delayed.",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "sector_peer_market_bridge",
        ],
        "result_contract": (
            "MCP result is a dataset handle with quote-coverage tickers for the "
            "requested market_type and mode. It is a discovery result, not a "
            "price snapshot."
        ),
    },
    "HistoricalCandles.get_intraday_history_candles": {
        "category": "candles",
        "path": "/v3/marketdata/history/candles/intraday/{market_type}",
        "method": "GET",
        "client": "HistoricalCandles",
        "description": (
            "Return historical intraday OHLCV candles for a B3 ticker on one "
            "date. Supports candle intervals from seconds to hours and optional "
            "corporate-event price adjustment."
        ),
        "parameters": {
            "market_type": "Allowed values: stocks, derivatives or indices.",
            "ticker": "Ticker such as PETR4.",
            "date": "Trading date in YYYY-MM-DD.",
            "candle": "Candle interval such as 1s, 1m, 5m, 15m, 30m or 1h.",
            "corporate_events_adj": "Whether to adjust prices for corporate events.",
            "rmv_after_market": "Whether to remove after-market trades.",
            "timezone": "Datetime timezone: America/Sao_Paulo or UTC.",
            "round": "Whether to round adjusted prices.",
        },
        "relationships": [
            "ticker_discovery", "events_price_context",
            "company_identifier_bridge", "public_document_event_bridge",
            "sector_peer_market_bridge",
        ],
    },
    "HistoricalCandles.get_interday_history_candles": {
        "category": "candles",
        "path": "/v3/marketdata/history/candles/interday/{market_type}",
        "method": "GET",
        "client": "HistoricalCandles",
        "description": (
            "Return daily historical OHLCV candles for one B3 ticker between "
            "start_date and end_date, with optional corporate-event adjustment."
        ),
        "parameters": {
            "market_type": "Allowed values: stocks, derivatives or indices.",
            "ticker": "Ticker such as PETR4.",
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "corporate_events_adj": "Whether to adjust prices for corporate events.",
            "rmv_after_market": "Whether to remove after-market trades.",
            "timezone": "Datetime timezone: America/Sao_Paulo or UTC.",
            "round": "Whether to round adjusted prices.",
        },
        "relationships": [
            "ticker_discovery", "events_price_context",
            "company_identifier_bridge", "public_document_event_bridge",
            "sector_peer_market_bridge", "macro_market_bridge",
        ],
    },
    "HistoricalCandles.get_interday_history_candles_batch": {
        "category": "candles",
        "path": "/v3/marketdata/history/candles/interday/{market_type}/batch",
        "method": "POST",
        "client": "HistoricalCandles",
        "description": (
            "Return daily historical OHLCV candles for multiple B3 tickers in "
            "one request. Use when comparing several assets over the same date "
            "range."
        ),
        "parameters": {
            "market_type": "Allowed values: stocks or derivatives.",
            "tickers": "List of tickers such as ['PETR4', 'VALE3'].",
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "corporate_events_adj": "Whether to adjust prices for corporate events.",
            "rmv_after_market": "Whether to remove after-market trades.",
            "timezone": "Datetime timezone: America/Sao_Paulo or UTC.",
            "round": "Whether to round adjusted prices.",
        },
        "relationships": [
            "ticker_discovery", "events_price_context",
            "company_identifier_bridge", "public_document_event_bridge",
            "sector_peer_market_bridge", "macro_market_bridge",
        ],
    },
    "HistoricalCandles.get_available_tickers": {
        "category": "candles",
        "path": "/v3/marketdata/history/candles/available-tickers/{market_type}",
        "method": "GET",
        "client": "HistoricalCandles",
        "description": (
            "List tickers with historical candle coverage for a market segment "
            "on a given date."
        ),
        "parameters": {
            "market_type": "Allowed values: stocks, derivatives or indices.",
            "date": "Coverage date in YYYY-MM-DD.",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "sector_peer_market_bridge",
        ],
        "result_contract": (
            "MCP result is a dataset handle with tickers that have historical "
            "candle coverage for the requested market_type and date. It is a "
            "discovery result, not candle OHLCV data."
        ),
    },
    "HistoricalCandlesCrypto.get_intraday_history_candles": {
        "category": "crypto_candles",
        "path": "/v3/marketdata/history/candles/intraday/crypto",
        "method": "GET",
        "client": "HistoricalCandlesCrypto",
        "description": (
            "Return historical intraday OHLCV candles for supported crypto "
            "assets by currency and exchange."
        ),
        "parameters": {
            "ticker": "Crypto ticker: BTC, ETH or SOL.",
            "currency": "Currency: BRL or USD.",
            "exchange": "Exchange: coinbase, mercado_bitcoin or consolidated.",
            "date": "Trading date in YYYY-MM-DD.",
            "candle": "Candle interval such as 1s, 30s, 1m, 5m, 15m, 30m or 1h.",
            "timezone": "Datetime timezone: America/Sao_Paulo or UTC.",
        },
        "relationships": ["crypto_ticker_discovery"],
        "caveats": [
            "Crypto candles are standalone crypto time series; do not route them "
            "through B3 company, CVM, ownership, sector or governance joins "
            "unless the user explicitly asks for cross-asset context."
        ],
    },
    "HistoricalCandlesCrypto.get_interday_history_candles": {
        "category": "crypto_candles",
        "path": "/v3/marketdata/history/candles/interday/crypto",
        "method": "GET",
        "client": "HistoricalCandlesCrypto",
        "description": (
            "Return daily historical OHLCV candles for supported crypto assets "
            "by currency and exchange."
        ),
        "parameters": {
            "ticker": "Crypto ticker: BTC, ETH or SOL.",
            "currency": "Currency: BRL or USD.",
            "exchange": "Exchange: coinbase, mercado_bitcoin or consolidated.",
            "start_date": "Start date in YYYY-MM-DD.",
            "end_date": "End date in YYYY-MM-DD.",
            "timezone": "Datetime timezone: America/Sao_Paulo or UTC.",
        },
        "relationships": ["crypto_ticker_discovery"],
        "caveats": [
            "Crypto candles are standalone crypto time series; do not route them "
            "through B3 company, CVM, ownership, sector or governance joins "
            "unless the user explicitly asks for cross-asset context."
        ],
    },
    "HistoricalCandlesCrypto.get_available_tickers": {
        "category": "crypto_candles",
        "path": "/v3/marketdata/history/candles/available-tickers/crypto",
        "method": "GET",
        "client": "HistoricalCandlesCrypto",
        "description": "List crypto tickers available for historical candle queries by exchange and date.",
        "parameters": {
            "exchange": "Exchange: coinbase, mercado_bitcoin or consolidated.",
            "date": "Coverage date in YYYY-MM-DD.",
        },
        "relationships": ["crypto_ticker_discovery"],
        "result_contract": (
            "MCP result is a dataset handle with crypto ticker coverage for the "
            "requested exchange/date. It is a discovery result, not candle OHLCV "
            "data."
        ),
        "caveats": [
            "Crypto coverage discovery is separate from B3 ticker discovery."
        ],
    },
    "IntradayCandles.get_intraday_candles": {
        "category": "intraday_candles",
        "path": "/api/v1/marketdata/br/b3/{delay}/intraday-candles/{market_type}",
        "method": "GET",
        "client": "IntradayCandles",
        "description": (
            "Return current-session intraday candles for one or more B3 tickers. "
            "Use for live or delayed intraday monitoring, not for historical "
            "multi-day bars."
        ),
        "parameters": {
            "market_type": "Market segment: stocks, derivatives, options or indices.",
            "tickers": "List of tickers such as ['PETR4', 'ABEV3'].",
            "delay": "Data delay: realtime or delayed.",
            "timezone": "Datetime timezone: America/Sao_Paulo or UTC.",
            "candle_period": "Grouping interval such as 1m, 5m, 30m, 1h or 1d.",
            "start": "Optional Unix timestamp lower bound.",
            "end": "Optional Unix timestamp upper bound.",
            "mode": "Candle mode: absolute, relative or spark.",
            "cross_filter": "Trade cross filter: all, only_cross or without_cross.",
            "market_status": "Market-status filter: all or regular; not available for indices.",
        },
        "relationships": ["ticker_discovery"],
    },
    "IntradayCandles.get_available_tickers": {
        "category": "intraday_candles",
        "path": "/api/v1/marketdata/br/b3/{delay}/intraday-candles/{market_type}/available_tickers",
        "method": "GET",
        "client": "IntradayCandles",
        "description": "List tickers available for current-session intraday candle queries.",
        "parameters": {
            "market_type": "Market segment: stocks, derivatives, options or indices.",
            "delay": "Data delay: realtime or delayed.",
        },
        "relationships": ["ticker_discovery"],
        "result_contract": (
            "MCP result is a dataset handle with tickers that have current-session "
            "intraday-candle coverage for the requested market_type and delay. "
            "It is a discovery result, not candle OHLCV data."
        ),
    },
    "IntradayTickData.get_trades": {
        "category": "tick_data",
        "path": "/v1/marketdata/tick/intraday/trades/{ticker}",
        "method": "GET",
        "client": "IntradayTickData",
        "description": (
            "Return current-day tick-by-tick trades for one ticker, optionally "
            "bounded by ISO datetime start and end filters."
        ),
        "parameters": {
            "ticker": "Ticker such as PETR4.",
            "start": "Optional start datetime or date in UTC ISO format.",
            "end": "Optional end datetime or date in UTC ISO format.",
        },
        "relationships": [
            "ticker_discovery", "book_scope_microstructure",
            "company_identifier_bridge", "public_document_event_bridge",
        ],
    },
    "TickerLastEvent.get_trades": {
        "category": "last_event",
        "path": "/api/v1/marketdata/br/b3/snapshot/trades/{data_type}",
        "method": "GET",
        "client": "TickerLastEvent",
        "description": (
            "Return the latest trade snapshot for one B3 ticker in equities or "
            "derivatives."
        ),
        "parameters": {
            "data_type": "Snapshot data type: equities or derivatives.",
            "ticker": "Ticker such as PETR4 or DOLM26.",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "public_document_event_bridge",
        ],
    },
    "TickerLastEvent.get_tobs": {
        "category": "last_event",
        "path": "/api/v1/marketdata/br/b3/snapshot/book/tob/{data_type}/batch",
        "method": "GET",
        "client": "TickerLastEvent",
        "description": "Return latest top-of-book snapshots for all tickers in equities or derivatives.",
        "parameters": {
            "data_type": "Book data type: equities or derivatives.",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "public_document_event_bridge",
        ],
    },
    "TickerLastEvent.get_status": {
        "category": "last_event",
        "path": "/api/v1/marketdata/br/b3/snapshot/status/batch",
        "method": "GET",
        "client": "TickerLastEvent",
        "description": (
            "Return current trading status for selected B3 tickers, or for all "
            "available tickers when no list is supplied."
        ),
        "parameters": {
            "tickers": "Optional list of tickers such as ['PETR4', 'VALE3', 'DOLM25'].",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "public_document_event_bridge",
        ],
    },
    "TickerLastEvent.get_available_tickers": {
        "category": "last_event",
        "path": "/api/v1/marketdata/br/b3/snapshot/{type}/{data_type}/available-tickers",
        "method": "GET",
        "client": "TickerLastEvent",
        "description": "List tickers available for last trade or top-of-book snapshot queries.",
        "parameters": {
            "type": "Event family: trades or books.",
            "data_type": "Market data type: equities or derivatives.",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
        ],
        "result_contract": (
            "MCP result is a dataset handle with tickers available for the "
            "requested last-event family and data_type. It is a discovery result, "
            "not a last trade or top-of-book snapshot."
        ),
    },
    "ReferenceData.ticker_reference": {
        "category": "reference_data",
        "path": "/api/v1/marketdata/br/b3/snapshot/instruments/batch",
        "method": "GET",
        "client": "ReferenceData",
        "description": (
            "Return current-day instrument reference data for tickers, including "
            "fields such as security id, currency, minimum lot size and minimum "
            "tick size."
        ),
        "parameters": {
            "tickers": "Required non-empty ticker list.",
        },
        "relationships": [
            "reference_enrichment", "ticker_discovery",
            "company_identifier_bridge", "sector_peer_market_bridge",
            "fund_market_exposure_bridge",
        ],
    },
    "CorporateEvents.get": {
        "category": "corporate_events",
        "path": "/v2/marketdata/corporate-events",
        "method": "GET",
        "client": "CorporateEvents",
        "description": (
            "Return market-data corporate events filtered by ex-date range and "
            "optional tickers. Use to contextualize price moves and adjustment "
            "decisions."
        ),
        "parameters": {
            "start_date": "Lower ex-date bound in YYYY-MM-DD.",
            "end_date": "Upper ex-date bound in YYYY-MM-DD.",
            "tickers": "Optional ticker list.",
        },
        "relationships": [
            "events_price_context", "ticker_discovery",
            "company_identifier_bridge", "public_document_event_bridge",
        ],
    },
    "CompanyData.general_info": {
        "category": "company_data",
        "path": "/v2/company_indicators/company_info/{ticker}",
        "method": "GET",
        "client": "CompanyData",
        "description": (
            "Return company general information for a ticker, including identity, "
            "sector and descriptive fields where available."
        ),
        "parameters": {
            "ticker": "Company ticker such as PETR4.",
        },
        "relationships": [
            "reference_enrichment", "company_identifier_bridge",
            "sector_peer_market_bridge", "macro_market_bridge",
        ],
    },
    "CompanyData.all_financial_tables": {
        "category": "company_data",
        "path": "/v2/fundamentalist_data/financial_tables/{ticker}",
        "method": "GET",
        "client": "CompanyData",
        "description": (
            "Return all available fundamental financial tables for a company "
            "ticker, including valuation, income statement, balance sheet, cash "
            "flow, ratios, growth and interim tables when present."
        ),
        "parameters": {
            "ticker": "Company ticker or ticker root such as PETR4 or PETR.",
        },
        "relationships": [
            "events_price_context", "reference_enrichment",
            "company_identifier_bridge", "sector_peer_market_bridge",
            "macro_market_bridge",
        ],
    },
    "CompanyData.financial_table": {
        "category": "company_data",
        "path": "/v2/fundamentalist_data/financial_tables/{ticker}",
        "method": "GET",
        "client": "CompanyData",
        "description": (
            "Return one selected fundamental financial table for a company "
            "ticker. Valid table names map to the Python-client helpers: "
            "income_statement, balance_sheet, cash_flow, valuation, ratios, "
            "growth and interims."
        ),
        "parameters": {
            "ticker": "Company ticker or ticker root such as PETR4 or PETR.",
            "table": "Financial table selector.",
        },
        "relationships": [
            "events_price_context", "reference_enrichment",
            "company_identifier_bridge", "sector_peer_market_bridge",
            "macro_market_bridge",
        ],
    },
    "HighFrequencyNews.get_latest_news": {
        "category": "news",
        "path": "/v3/hfn/latest-news",
        "method": "GET",
        "client": "HighFrequencyNews",
        "description": (
            "Return the most recent High Frequency News items captured by the "
            "HFN engine. Filters can be combined by country, source, feed, "
            "language, tags, categories, date window and free text."
        ),
        "parameters": {
            "countries": "Optional list of country codes such as ['BR'] or ['BR', 'US'].",
            "source_type": "Optional source type: rss, html or pdf.",
            "source": "Optional source name.",
            "feed": "Optional feed such as politics, economy, crypto, technology, sports, health, commodities, energy or general.",
            "text_language": "Optional language such as portuguese, english, spanish, german or french.",
            "tags": "Optional tag list such as ticker symbols.",
            "start_date": "Optional lower publishing-time bound as date or ISO datetime.",
            "end_date": "Optional upper publishing-time bound as date or ISO datetime.",
            "limit": "Optional result limit; latest-news supports up to 5000.",
            "categories": "Optional category keywords extracted from content.",
            "text": "Optional free-text query over title and body.",
        },
        "relationships": [
            "hfn_filter_discovery", "reference_enrichment",
            "company_identifier_bridge", "public_document_event_bridge",
            "macro_market_bridge",
        ],
    },
    "HighFrequencyNews.get_historical_news": {
        "category": "news",
        "path": "/v3/hfn/historical-news",
        "method": "GET",
        "client": "HighFrequencyNews",
        "description": (
            "Return HFN news over an explicit historical datetime interval with "
            "the same filters as latest news."
        ),
        "parameters": {
            "countries": "Optional list of country codes.",
            "source_type": "Optional source type: rss, html or pdf.",
            "source": "Optional source name.",
            "feed": "Optional thematic feed.",
            "text_language": "Optional content language.",
            "tags": "Optional tag list such as ticker symbols.",
            "start_date": "Optional lower publishing-time bound as date or ISO datetime.",
            "end_date": "Optional upper publishing-time bound as date or ISO datetime.",
            "limit": "Optional result limit.",
            "categories": "Optional category keywords extracted from content.",
            "text": "Optional free-text query over title and body.",
        },
        "relationships": [
            "hfn_filter_discovery", "reference_enrichment",
            "company_identifier_bridge", "public_document_event_bridge",
            "macro_market_bridge",
        ],
    },
    "HighFrequencyNews.get_available_filters": {
        "category": "news",
        "path": "/v3/hfn/available-filters",
        "method": "GET",
        "client": "HighFrequencyNews",
        "description": (
            "Return available HFN filter values for countries, sources, source "
            "types, feeds and text languages. Use this before narrow news "
            "queries when valid values are unknown."
        ),
        "parameters": {
            "countries": "Optional country-code filter list.",
            "sources": "Optional source-name filter list.",
            "source_types": "Optional source-type filter list.",
            "feeds": "Optional feed filter list.",
            "text_languages": "Optional language filter list.",
        },
        "relationships": ["hfn_filter_discovery"],
        "result_contract": (
            "MCP result is a dataset handle containing "
            "available HFN filter values such as countries, sources, source "
            "types, feeds and text languages. It is discovery metadata, not news "
            "items."
        ),
    },
    "StockLoan.get_paginated_trades": {
        "category": "stock_loan",
        "path": "/v1/marketdata/stock-loan/daily-trades",
        "method": "GET",
        "client": "StockLoan",
        "description": (
            "Return paginated daily stock-loan trades, optionally filtered by "
            "ticker. Use pagination to avoid very large responses."
        ),
        "parameters": {
            "page": "Page number starting at 1.",
            "limit": "Maximum rows per page.",
            "ticker": "Optional ticker such as PETR4.",
        },
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "ownership_liquidity_bridge", "fund_market_exposure_bridge",
        ],
    },
    "StockLoan.get_available_tickers": {
        "category": "stock_loan",
        "path": "/v1/marketdata/stock-loan/available-tickers",
        "method": "GET",
        "client": "StockLoan",
        "description": "List tickers available for stock-loan daily-trade queries.",
        "parameters": {},
        "relationships": [
            "ticker_discovery", "company_identifier_bridge",
            "ownership_liquidity_bridge", "fund_market_exposure_bridge",
        ],
        "result_contract": (
            "MCP result is a dataset handle with tickers covered by stock-loan "
            "daily-trade queries. It is a discovery result, not stock-loan trade "
            "data."
        ),
    },
    "BulkData.get_available_tickers": {
        "category": "bulk_data",
        "path": "/v2/marketdata/bulkdata/available-tickers",
        "method": "GET",
        "client": "BulkData",
        "description": (
            "List tickers available for ticker/date bulk market-data files by "
            "date, data type and optional prefix."
        ),
        "parameters": {
            "date": "Coverage date in YYYY-MM-DD.",
            "data_type": "Bulk data type such as trades, books or trades-and-book-events.",
            "prefix": "Optional ticker prefix filter such as DOL.",
        },
        "relationships": [
            "bulk_data_discovery", "ticker_discovery",
            "company_identifier_bridge", "book_scope_microstructure",
        ],
        "result_contract": (
            "MCP result is a dataset handle with bulk-data ticker coverage for "
            "the requested date, data_type and optional prefix. It is a discovery "
            "result, not the bulk file contents."
        ),
        "caveats": [
            "Use a narrow prefix when possible. Broad prefixes or highly active "
            "B3 roots can be slow or time out upstream; a precise prefix such as "
            "AAPL for AAPL34 is a safer discovery probe than a broad root."
        ],
    },
    "BulkData.get_market_data_channels": {
        "category": "bulk_data",
        "path": "/v3/marketdata/bulkdata/compressed/available-channels",
        "method": "GET",
        "client": "BulkData",
        "description": (
            "List market-data channels available for compressed instruments, "
            "snapshot or incremental files on a date."
        ),
        "parameters": {
            "date": "Coverage date in YYYY-MM-DD.",
        },
        "relationships": ["bulk_data_discovery"],
        "result_contract": (
            "MCP result is a dataset handle with available compressed market-data "
            "channels for the requested date. It is discovery metadata for bulk "
            "downloads."
        ),
    },
    "BulkData.get_data": {
        "category": "bulk_data",
        "path": "/v2/marketdata/bulkdata/{data_type}",
        "method": "GET",
        "client": "BulkData",
        "description": (
            "Return tick-by-tick bulk market data for one ticker and date as a "
            "Parquet-backed dataset. Data types include trades, books and "
            "trades-and-book-events."
        ),
        "parameters": {
            "ticker": "Ticker such as DI1F18 or PETR4.",
            "date": "Coverage date in YYYY-MM-DD.",
            "data_type": "Bulk data type such as trades, books or trades-and-book-events.",
        },
        "relationships": [
            "bulk_data_discovery", "book_scope_microstructure",
            "company_identifier_bridge", "public_document_event_bridge",
        ],
        "caveats": [
            "Responses may be large; prefer available-tickers discovery and narrow ticker/date filters."
        ],
    },
    "BulkData.get_security_list": {
        "category": "bulk_data",
        "path": "/v2/marketdata/bulkdata/security-list",
        "method": "GET",
        "client": "BulkData",
        "description": "Return the B3 security list for a date as a Parquet-backed dataset.",
        "parameters": {
            "date": "Coverage date in YYYY-MM-DD.",
        },
        "relationships": ["bulk_data_discovery", "reference_enrichment"],
        "caveats": ["The security list can be large."],
    },
    "BrokerReference.get": {
        "category": "broker_reference",
        "path": "/v1/marketdata/broker/info/all-brokers",
        "method": "GET",
        "client": "BrokerReference",
        "description": (
            "Return the broker reference dataset with B3 broker codes and names. "
            "Use before broker analytics when the user supplied a broker name "
            "instead of a code."
        ),
        "parameters": {},
        "relationships": ["broker_reference"],
    },
    "BrokerAnalytics.get_summary": {
        "category": "broker_analytics",
        "path": "/v1/marketdata/br/b3/realtime/broker-analytics/{market_type}/summary",
        "method": "GET",
        "client": "BrokerAnalytics",
        "description": (
            "Return D0 realtime broker analytics summary for selected broker "
            "codes and tickers in one market segment."
        ),
        "parameters": {
            "market_type": "Market segment: stocks, derivatives or options.",
            "brokers": "List of broker codes.",
            "tickers": "List of ticker symbols.",
            "side": "Optional side filter: buy or sell.",
        },
        "relationships": [
            "broker_reference", "ticker_discovery",
            "company_identifier_bridge", "ownership_liquidity_bridge",
        ],
        "caveats": ["This is current-trading-day data, not historical broker flow."],
    },
    "BrokerAnalytics.get_top_brokers": {
        "category": "broker_analytics",
        "path": "/v1/marketdata/br/b3/realtime/broker-analytics/{market_type}/top-brokers",
        "method": "GET",
        "client": "BrokerAnalytics",
        "description": (
            "Return top N brokers ranked by D0 financial volume, optionally "
            "filtered by tickers and side, with ticker breakdown."
        ),
        "parameters": {
            "market_type": "Market segment: stocks, derivatives or options.",
            "n": "Number of brokers to return.",
            "tickers": "Optional ticker filter list.",
            "side": "Optional side filter: buy or sell.",
        },
        "relationships": [
            "broker_reference", "ticker_discovery",
            "company_identifier_bridge", "ownership_liquidity_bridge",
            "sector_peer_market_bridge",
        ],
        "caveats": ["This is current-trading-day data, not historical broker flow."],
    },
    "BrokerAnalytics.get_top_tickers": {
        "category": "broker_analytics",
        "path": "/v1/marketdata/br/b3/realtime/broker-analytics/{market_type}/top-tickers",
        "method": "GET",
        "client": "BrokerAnalytics",
        "description": (
            "Return top N tickers ranked by D0 financial volume, optionally "
            "filtered by broker codes and side, with broker breakdown."
        ),
        "parameters": {
            "market_type": "Market segment: stocks, derivatives or options.",
            "n": "Number of tickers to return.",
            "brokers": "Optional broker-code filter list.",
            "side": "Optional side filter: buy or sell.",
        },
        "relationships": [
            "broker_reference", "ticker_discovery",
            "company_identifier_bridge", "ownership_liquidity_bridge",
            "sector_peer_market_bridge",
        ],
        "caveats": ["This is current-trading-day data, not historical broker flow."],
    },
    "BookScope.get": {
        "category": "book_scope",
        "path": "/v1/marketdata/br/b3/book-scope/{scope}/{market_type}/{dataset}",
        "method": "GET",
        "client": "BookScope",
        "description": (
            "Return trades, book snapshots and/or incremental book events for "
            "one B3 symbol over a short ISO datetime window. The Python client "
            "chooses intraday or historical scope from end_time and paginates "
            "by rpt_seq."
        ),
        "parameters": {
            "symbol": "Ticker or symbol such as PETR4 or DOLM26.",
            "market_type": "Market segment: stocks, derivatives or options.",
            "start_time": "UTC ISO datetime such as 2026-05-28T14:12:00Z.",
            "end_time": "UTC ISO datetime such as 2026-05-28T14:15:00Z.",
            "select": "Datasets to return: trades, book_snapshot and/or book_incremental.",
            "aggregate_info": "If true, combine selected datasets into one table.",
        },
        "relationships": [
            "book_scope_microstructure", "broker_reference",
            "company_identifier_bridge", "public_document_event_bridge",
            "ownership_liquidity_bridge",
        ],
        "caveats": ["The maximum allowed window is 10 minutes."],
    },
}


DATASERVICES_TOOL_ENDPOINTS: dict[str, str] = {
    "get_quotes": "Quotes.get_quote",
    "get_top_bottom_quotes": "Quotes.get_top_bottom",
    "list_quote_tickers": "Quotes.get_available_tickers",
    "get_historical_intraday_candles": "HistoricalCandles.get_intraday_history_candles",
    "get_historical_interday_candles": "HistoricalCandles.get_interday_history_candles",
    "get_historical_interday_candles_batch": "HistoricalCandles.get_interday_history_candles_batch",
    "list_historical_candle_tickers": "HistoricalCandles.get_available_tickers",
    "get_crypto_intraday_candles": "HistoricalCandlesCrypto.get_intraday_history_candles",
    "get_crypto_interday_candles": "HistoricalCandlesCrypto.get_interday_history_candles",
    "list_crypto_candle_tickers": "HistoricalCandlesCrypto.get_available_tickers",
    "get_intraday_candles": "IntradayCandles.get_intraday_candles",
    "list_intraday_candle_tickers": "IntradayCandles.get_available_tickers",
    "get_intraday_trades": "IntradayTickData.get_trades",
    "get_last_trade": "TickerLastEvent.get_trades",
    "get_last_top_of_book": "TickerLastEvent.get_tobs",
    "get_trading_status": "TickerLastEvent.get_status",
    "list_last_event_tickers": "TickerLastEvent.get_available_tickers",
    "get_ticker_reference": "ReferenceData.ticker_reference",
    "get_corporate_events": "CorporateEvents.get",
    "get_company_general_info": "CompanyData.general_info",
    "get_company_financial_table": "CompanyData.financial_table",
    "get_company_all_financial_tables": "CompanyData.all_financial_tables",
    "get_latest_news": "HighFrequencyNews.get_latest_news",
    "get_historical_news": "HighFrequencyNews.get_historical_news",
    "get_news_filters": "HighFrequencyNews.get_available_filters",
    "get_stock_loan_trades": "StockLoan.get_paginated_trades",
    "list_stock_loan_tickers": "StockLoan.get_available_tickers",
    "list_bulk_data_tickers": "BulkData.get_available_tickers",
    "list_bulk_market_data_channels": "BulkData.get_market_data_channels",
    "get_bulk_market_data": "BulkData.get_data",
    "get_bulk_security_list": "BulkData.get_security_list",
    "get_broker_reference": "BrokerReference.get",
    "get_broker_analytics_summary": "BrokerAnalytics.get_summary",
    "get_top_brokers": "BrokerAnalytics.get_top_brokers",
    "get_top_tickers_by_broker_flow": "BrokerAnalytics.get_top_tickers",
    "get_book_scope": "BookScope.get",
}


def _compose_endpoint_description(endpoint: dict[str, Any]) -> str:
    parts: list[str] = [endpoint["description"]]
    parameters = endpoint.get("parameters") or {}
    if parameters:
        parts.append(
            "Parameters: "
            + "; ".join(f"{name}: {description}" for name, description in parameters.items())
            + "."
        )
    relationships = endpoint.get("relationships") or []
    if relationships:
        parts.append(
            "Related workflow: "
            + " ".join(DATASERVICES_ENDPOINT_RELATIONSHIPS[key] for key in relationships)
        )
    result_contract = endpoint.get("result_contract") or DATASERVICES_RESULT_CONTRACTS.get(endpoint.get("category", ""))
    if result_contract:
        parts.append("Result contract: " + result_contract)
    caveats = endpoint.get("caveats") or []
    if caveats:
        parts.append("Caveats: " + " ".join(caveats))
    return " ".join(parts)


DATASERVICES_ENDPOINT_DESCRIPTIONS: dict[str, str] = {
    endpoint_key: _compose_endpoint_description(endpoint)
    for endpoint_key, endpoint in DATASERVICES_ENDPOINTS.items()
}


DATASERVICES_TOOL_DESCRIPTIONS: dict[str, str] = {
    tool_name: DATASERVICES_ENDPOINT_DESCRIPTIONS[endpoint_key]
    for tool_name, endpoint_key in DATASERVICES_TOOL_ENDPOINTS.items()
}


def get_dataservices_endpoint(name: str) -> dict[str, Any]:
    endpoint_key = DATASERVICES_TOOL_ENDPOINTS.get(name, name)
    try:
        endpoint = deepcopy(DATASERVICES_ENDPOINTS[endpoint_key])
        result_contract = endpoint.get("result_contract") or DATASERVICES_RESULT_CONTRACTS.get(endpoint.get("category", ""))
        if result_contract:
            endpoint["result_contract"] = result_contract
        return endpoint
    except KeyError:
        raise KeyError(f"Unknown Data Services endpoint or MCP tool: {name}") from None


def get_dataservices_endpoint_description(name: str) -> str:
    endpoint_key = DATASERVICES_TOOL_ENDPOINTS.get(name, name)
    try:
        return DATASERVICES_ENDPOINT_DESCRIPTIONS[endpoint_key]
    except KeyError:
        raise KeyError(f"Unknown Data Services endpoint or MCP tool: {name}") from None


def get_dataservices_tool_description(name: str) -> str:
    try:
        return DATASERVICES_TOOL_DESCRIPTIONS[name]
    except KeyError:
        raise KeyError(f"Unknown Data Services MCP tool: {name}") from None


def get_dataservices_tool_manifest() -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for tool_name, endpoint_key in DATASERVICES_TOOL_ENDPOINTS.items():
        endpoint = get_dataservices_endpoint(endpoint_key)
        endpoint["tool_name"] = tool_name
        endpoint["endpoint_key"] = endpoint_key
        endpoint["description"] = DATASERVICES_TOOL_DESCRIPTIONS[tool_name]
        manifest.append(endpoint)
    return manifest
