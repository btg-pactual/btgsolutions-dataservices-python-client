4.2.0 (2026-06-25)


Added

- Technical REST endpoint catalogs for Public Sources / Alternative Data and
  Data Services, exposed from ``btgsolutions_dataservices.rest`` for MCPs and
  other AI clients to reuse endpoint descriptions, parameters, caveats and
  endpoint relationships.
- Catalog coverage for company metadata, governance, ownership, funds, people,
  macro/DPMFi, B3 maximum theoretical margin, quotes, candles, intraday trades,
  last-event snapshots, reference data, corporate events, company fundamental
  data, HFN news, stock-loan, bulk market data, broker analytics and BookScope.
- Documentation of cross-endpoint relationships such as company-to-market-data
  identifier resolution, sector peer analysis, fund-to-underlying exposure,
  ownership/free-float-to-liquidity context, document/event-market workflows and
  macro-to-sector/company context.

Changed

- Clarified that the direct market-data ``investor-categories`` endpoint remains
  intentionally excluded from the alternative-data package surface.
- Clarified that ``get_governance_beneficial_ownership`` is UK/US oriented
  (Companies House PSC / SEC proxy data) and should not be used as Brazilian
  listed-company ownership coverage.
- Clarified that ``get_manager_aggregate_holdings`` requires a covered manager
  CNPJ or exact manager name, not ETF tickers, ETF issuer slugs or fund CNPJs.
- Clarified DPMFi query semantics and recommended ``snapshot_date`` or narrow
  reference-month filters for reproducible interactive usage.
- Updated README examples to point Brazilian ownership questions to ownership
  endpoints and ETF questions to ETF/fund discovery and holdings workflows.

Fixed

- Improved non-JSON upstream error handling in ``PublicSources.get_opas``,
  ``PublicSources.get_share_repurchase`` and
  ``BulkData.get_available_tickers`` so callers receive a clear ``BadResponse``
  instead of a raw JSON parsing exception.


4.1.1 (2026-06-23)


Added

- Alternative data examples for ``list_companies``, ``list_etfs``, ``get_assemblies`` and ``get_notice_summary`` in the package README.
- Documented B3 maximum theoretical margin under ``AlternativeDataMacroMarkets`` and kept the direct market-data ``investor-categories`` endpoint out of the package surface.
- ``AlternativeDataOwnership.get_notice_summary`` for AI summaries of CVM RAD documents.

Changed

- Corrected financial-statement/financial-notes quarter examples to the live ``1T24``/``4T24`` format.
- Clarified that ETF-aware fund methods accept BR ETF tickers such as ``BOVA11`` in addition to fund CNPJs.


4.0.0 (2026-06-22)


Removed

- ``HFNV3WebSocketClient`` — merged into ``HFNWebSocketClient`` (#1)
- ``HighFrequencyNewsV3`` — merged into ``HighFrequencyNews`` (#2)


Changed

- ``HFNWebSocketClient`` now connects to the HFN V3 WebSocket with subscribe/unsubscribe, on-demand ``latest_news``, ``available_filters``, ``post_metrics`` and ``watch_metrics`` (#1)
- ``HighFrequencyNews`` now uses the HFN V3 REST API with ``get_latest_news``, ``get_historical_news`` and ``get_available_filters`` (#2)


Migration guide
---------------

The class names ``HFNWebSocketClient`` and ``HighFrequencyNews`` are unchanged, but their
method signatures changed completely. Update your calls as shown below.


WebSocket — HFNWebSocketClient
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The constructor no longer accepts ``stream_type`` or ``country``. The connection model
changed from a receive-only stream to a bidirectional protocol where you subscribe with
filter settings after connecting.

Before (≤ v3.2)::

    ws = HFNWebSocketClient(api_key='YOUR_API_KEY', stream_type='realtime', country='brazil')
    ws.run()
    ws.get_latest_news()
    ws.close()

After (v4.0)::

    ws = HFNWebSocketClient(api_key='YOUR_API_KEY')
    ws.run()
    ws.subscribe(settings={'countries': ['BR']})  # replaces stream_type + country in the constructor
    ws.latest_news(settings={'limit': '10'})      # replaces get_latest_news()
    ws.close()

Parameter mapping:

+------------------------------+----------------------------------------------------+
| Before                       | After                                              |
+==============================+====================================================+
| ``country='brazil'``         | ``ws.subscribe(settings={'countries': ['BR']})``   |
+------------------------------+----------------------------------------------------+
| ``country='chile'``          | ``ws.subscribe(settings={'countries': ['CL']})``   |
+------------------------------+----------------------------------------------------+
| ``stream_type='realtime'``   | default — all subscriptions are real-time          |
+------------------------------+----------------------------------------------------+
| ``ws.get_latest_news()``     | ``ws.latest_news(settings={})``                    |
+------------------------------+----------------------------------------------------+


REST — HighFrequencyNews
~~~~~~~~~~~~~~~~~~~~~~~~

All method names were replaced. Country names also changed from full strings to ISO codes
inside a list.

Method mapping:

+------------------------------------------------------------------+--------------------------------------------------------------------+
| Before (≤ v3.2)                                                  | After (v4.0)                                                       |
+==================================================================+====================================================================+
| ``hfn.latest_news(feed='economy', country='brazil', n=10)``      | ``hfn.get_latest_news(feed='economy', countries=['BR'], limit=10)``|
+------------------------------------------------------------------+--------------------------------------------------------------------+
| ``hfn.filter_news(ticker='PETR4')``                              | ``hfn.get_latest_news(tags=['PETR4'])``                            |
+------------------------------------------------------------------+--------------------------------------------------------------------+
| ``hfn.filter_news(tag='IBOV')``                                  | ``hfn.get_latest_news(tags=['IBOV'])``                             |
+------------------------------------------------------------------+--------------------------------------------------------------------+
| ``hfn.historical_news(start_date=..., end_date=..., feed=...)``  | ``hfn.get_historical_news(start_date=..., end_date=..., feed=...)``|
+------------------------------------------------------------------+--------------------------------------------------------------------+
| ``hfn.get_available_feeds()``                                    | ``hfn.get_available_filters()`` → key ``feeds``                    |
+------------------------------------------------------------------+--------------------------------------------------------------------+
| ``hfn.get_available_sources()``                                  | ``hfn.get_available_filters()`` → key ``sources``                  |
+------------------------------------------------------------------+--------------------------------------------------------------------+
| ``hfn.get_available_tickers()``                                  | ``hfn.get_available_filters()`` → inspect returned data            |
+------------------------------------------------------------------+--------------------------------------------------------------------+
| ``hfn.get_available_tags()``                                     | ``hfn.get_available_filters()`` → inspect returned data            |
+------------------------------------------------------------------+--------------------------------------------------------------------+

Side-by-side example:

Before (≤ v3.2)::

    hfn = HighFrequencyNews(api_key='YOUR_API_KEY')

    latest    = hfn.latest_news(feed='economy', country='brazil', n=15)
    by_ticker = hfn.filter_news(ticker='PETR4', country='brazil')
    by_tag    = hfn.filter_news(tag='IBOV')
    history   = hfn.historical_news(start_date='2026-05-21', end_date='2026-05-28', feed='raw')
    feeds     = hfn.get_available_feeds()
    sources   = hfn.get_available_sources()

After (v4.0)::

    hfn = HighFrequencyNews(api_key='YOUR_API_KEY')

    latest    = hfn.get_latest_news(feed='economy', countries=['BR'], limit=15)
    by_ticker = hfn.get_latest_news(tags=['PETR4'], countries=['BR'])
    by_tag    = hfn.get_latest_news(tags=['IBOV'])
    history   = hfn.get_historical_news(start_date='2026-05-21', end_date='2026-05-28', feed='economy')
    filters   = hfn.get_available_filters()  # feeds, sources, countries and more in a single call

.. note::
   ``feed='raw'`` no longer exists. Call ``get_latest_news()`` without a ``feed`` argument
   to receive unfiltered news.


3.3.0 (2026-06-19)


Added

- High Frequency News V3 REST API (``HighFrequencyNewsV3``) with ``get_latest_news``, ``get_historical_news`` and ``get_available_filters`` (#1)
- High Frequency News V3 WebSocket client (``HFNV3WebSocketClient``) with subscribe/unsubscribe, on-demand ``latest_news``, ``available_filters``, ``post_metrics`` and ``watch_metrics`` (#2)
- Alternative Data endpoints (#3)



3.2.12 (2026-05-28)


Added


- Added broker Analytics API (#1)


3.2.11 (2026-05-26)


Added


- Adding book scope (#1)


3.2.9 (2026-05-18)


Added


- Added BrokerAnalyticsWebSocketClient (#1)


3.2.8 (2026-05-11)


Added


- Added crypto API (#1)
- Added round parameter to historical candles API (#2)
- Added broker reference API (#3)


2.12.0 (2025-07-21)


Added


- Added new method 'get_tobs' to TickerLastEvent module (#1)


2.11.0 (2025-05-21)


Added


- MarketDataFeed (#1)


2.7.0 (2025-02-26)


Added


- Websocket instrument status subscription and history
- Changed example of top of book dashboard, adding some fields and improving performance. Added a specific print function for default logs.
- Added an example of a dashboard that uses WS Books to update asset top of book in realtime

2.4.0 (2025-01-29)


Added


- Public Sources API (#1)


2.3.0 (2024-12-02)


Added


- Allowing filtering of books by maximun level. (#1)


2.2.0 (2024-11-08)


Added


- Add compatibility with Python 3.12.X (#1)


2.1.2 (2024-11-07)


Changed


- Updated Intraday Candles API to version 3 (#1)


2.1.1 (2024-10-14)


Added


- Company Data API (#1)


2.0.0 (2024-07-03)


Changed


- Updated Bulk Data API to version 2 (#1)


1.1.0 (2024-06-03)


Added


- Corporate Events API (#1)


1.0.14 (2024-05-16)


Added


- Bulk Data API 'trades-and-book-events' data type (#1)


Changed


- WebSocketClient on_message callback function is now spawning a new thread (#2)
