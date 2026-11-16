# BTG Solutions - Data Services

Real time and historical Financial Market Data, News, Corporate Events and more.
More information at https://dataservices.btgpactualsolutions.com/.

## Installation

```bash
pip3 install btgsolutions-dataservices-python-client
```

## Documentation

The official documentation is hosted at https://python-client-docs.dataservices.btgpactualsolutions.com/

## Examples

### Real Time Data

#### Market Data Stream (optimized for performance)

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataFeed(api_key='YOUR_API_KEY', data_type='books', data_subtype='stocks')
ws.run()
ws.subscribe(['PETR4'])

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

#### Market Data Stream

##### Books

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', data_type='books', instruments=['PETR4', 'VALE3'])
ws.run(on_message=lambda message: print(message))

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Books, Top Of Book (n=1)

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', data_type='books')
ws.run(on_message=lambda message: print(message))
ws.subscribe(['PETR4', 'VALE3'], n=1)

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Trades

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', data_type='trades', instruments=['PETR4', 'VALE3'])
ws.run(on_message=lambda message: print(message))

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Trades, delayed (15 minutes delay)

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', data_type='trades', stream_type='delayed', instruments=['PETR4', 'VALE3'])
ws.run(on_message=lambda message: print(message))

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Books, throttle (1 second throttle)

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', data_type='books', stream_type='throttle', instruments=['PETR4', 'VALE3'])
ws.run(on_message=lambda message: print(message))

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Trades, NASDAQ (US)

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', exchange='nasdaq', data_type='trades')
ws.run(on_message=lambda message: print(message))
ws.subscribe(['AMZN', 'GOOG', 'TSLA'])

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Trades, BMV (MX)

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', exchange='bmv', data_type='trades')
ws.run(on_message=lambda message: print(message))

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Security Status

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', data_type='instrument_status', data_subtype='stocks')
ws.run(on_message=lambda message: print(message))
ws.instrument_status('PETR4')
ws.instrument_status_history('PETR4')

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```
##### Settlement Price 

```python
import btgsolutions_dataservices as btg
ws = btg.MarketDataWebSocketClient(api_key='YOUR_API_KEY', data_type='settlement-price', instruments=['ABEVOU25', 'WINV25'])
ws.run(on_message=lambda message: print(message))

## Getting the last event (settlement-price) of ABEVOU25:
# ws.get_last_event(['ABEVOU25'])

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Broker Analytics

```python
import btgsolutions_dataservices as btg

ws = btg.BrokerAnalyticsWebSocketClient(api_key='YOUR_API_KEY')
ws.run(on_message=lambda message: print(message))

ws.available_tickers()
ws.available_brokers()
ws.subscribe_top_tickers(n=10, brokers=['85'])
ws.subscribe_top_brokers(n=5, tickers=['SNFF11'])
ws.subscribed_to()
ws.get_last_event(analytics_type='top_tickers', n=3, brokers=['85', '3'])
ws.get_last_event(analytics_type='top_brokers', n=100, tickers=['SNFF11'])
ws.unsubscribe_top_tickers(brokers=['85'])
ws.unsubscribe_top_brokers(tickers=['SNFF11'])

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

##### Book Events (order-by-order book)

The B3 order-by-order book (market-by-order) with the broker of each order: a `book_snapshot` of each subscribed ticker (every resting order, in priority order), then one `book_event` per order change. Realtime only, at most 10 tickers per connection, for `stocks`, `options` and `derivatives`.

```python
import btgsolutions_dataservices as btg

ws = btg.MarketDataWebSocketClient(
    api_key='YOUR_API_KEY',
    data_type='book-events',
    data_subtype='derivatives',
    instruments=['WINZ26'],
)
ws.run(on_message=lambda message: print(message))  # book_snapshot, then book_event / book_status

ws.get_last_event('WINZ26')  # current book of a subscribed ticker (a book_snapshot)

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

For `book-events`, messages are handled in a single thread (book changes must be applied in order), the server certificate is always verified, `run()` waits at most `connect_timeout` seconds (default 10) for the connection to open and a dropped connection only calls `on_close` (no automatic reconnection at this level).

##### Realtime Book by Order

`RealtimeBookEvents` keeps each ticker's book in memory (`BookByOrder`) from the `book-events` stream and yields one entry per change, in the same shape as the historical `TradesAndBookEvents.get_book()` (book only, no trades).

```python
import btgsolutions_dataservices as btg

books = btg.RealtimeBookEvents(api_key='YOUR_API_KEY', data_subtype='derivatives')

for kind, info in books.get_book(['WINZ26', 'WDOZ26'], view='mbo', n_levels=5):
    if kind == 'book':
        print(info['symbol'], info['bid'][:1], info['offer'][:1], info['order']['event_type'], info['order']['action'])
    else:
        print('status:', info)  # suspect / ok / waiting_snapshot / resyncing / disconnected / reconnected / reconnect_failed

    # books.book('WINZ26') is the whole BookByOrder, always up to date
```

- `view='mbo'` (default): top `n_levels` orders per side as `(order_id, price, size, broker)`; `view='mbp'`: top price levels as `(price, total_size)`.
- `info['order']`: the order that changed (`order_id`, `side`, `price`, `size`, `broker`, `event_type`, `action`, `seq_num`, `rpt_seq`, `timestamp` = order entry time) plus `transact_time` (exchange time of the change), `end_of_event` (last change of an exchange event; always `True` on a snapshot) and `prev_size` (on a `CHANGE`).
- `info['queued']`: messages already waiting behind this one. Near 0, the loop keeps up; if it keeps growing, the code inside the loop is slower than the feed. The book in memory is always current, so skipping work on an entry never skips the event in the book:

```python
if not info['order']['end_of_event']:
    continue                 # mid exchange event: an intermediate book
if info['queued'] > 0:
    continue                 # something newer is already queued
heavy_work(books.book('WINZ26'))
```

- A gap in a ticker's `seq_num` yields `('status', {'status': 'resyncing', 'reason': 'seq_gap'})`, asks the server for the current book and skips that ticker's events until it comes.
- Connection drops yield `disconnected` (with the server's close code and reason when it sends one), then `reconnected` (every book comes again as a snapshot) or, after `max_reconnects` consecutive failures, `reconnect_failed` and the generator ends. `reconnect=False` ends the generator right after `disconnected`.
- `timeout=` stops after that many seconds without messages; `break` or `books.close()` (also from another thread) closes the connection.
- Orders without price (market orders in auctions) come with `price=None`, ahead of every price level. During auctions the book can be crossed (best bid >= best offer), as on the exchange.

#### Intraday Candles

```python
import btgsolutions_dataservices as btg
int_candles = btg.IntradayCandles(api_key='YOUR_API_KEY')
int_candles.get_intraday_candles(market_type='stocks', tickers=['PETR4', 'VALE3'], candle_period='1m', delay='delayed', mode='relative', timezone='UTC', market_status='regular', raw_data=True)
```

#### Intraday Tick Data

```python
import btgsolutions_dataservices as btg
intra_tickdata = btg.IntradayTickData(api_key='YOUR_API_KEY')
intra_tickdata.get_trades(ticker='PETR4')
```

#### Quotes

```python
import btgsolutions_dataservices as btg
quotes = btg.Quotes(api_key='YOUR_API_KEY')
quotes.get_quote(market_type = 'stocks', tickers = ['PETR4', 'VALE3'])
```

#### Ticker Last Trade

```python
import btgsolutions_dataservices as btg
last_event = btg.TickerLastEvent(api_key='YOUR_API_KEY')
last_event.get_trades(data_type='equities', ticker='VALE3')
```

#### Ticker Last Top of Book

```python
import btgsolutions_dataservices as btg
last_event = btg.TickerLastEvent(api_key='YOUR_API_KEY')
last_event.get_tobs(data_type='equities')
```

#### Ticker Last Trading Status

```python
import btgsolutions_dataservices as btg
last_event = btg.TickerLastEvent(api_key='YOUR_API_KEY')
last_event.get_status(tickers=['PETR4','VALE3'])
```

#### Ticker Last Polling - Top of Books

```python
import btgsolutions_dataservices as btg
last_event = btg.TickerLastEventPolling(api_key='YOUR_API_KEY', data_type='top-of-books', data_subtype='stocks')
last_event.get()
```


### Historical Data

#### Historical Candles

##### Interday

```python
import btgsolutions_dataservices as btg
hist_candles = btg.HistoricalCandles(api_key='YOUR_API_KEY')
hist_candles.get_interday_history_candles(ticker='PETR4',  market_type='stocks', corporate_events_adj=True, start_date='2023-10-01', end_date='2023-10-13', rmv_after_market=True, timezone='UTC', raw_data=False, round=False)
```

##### Intraday

```python
import btgsolutions_dataservices as btg
hist_candles = btg.HistoricalCandles(api_key='YOUR_API_KEY')
hist_candles.get_intraday_history_candles(ticker='PETR4',  market_type='stocks', corporate_events_adj=True, date='2023-10-06', candle='1m', rmv_after_market=True, timezone='UTC', raw_data=False, round=True)
```

##### Interday Batch

```python
import btgsolutions_dataservices as btg
hist_candles = btg.HistoricalCandles(api_key='YOUR_API_KEY')
hist_candles.get_interday_history_candles_batch(market_type='stocks', tickers=['PETR4', 'VALE3'], start_date='2023-10-01', end_date='2023-10-13', corporate_events_adj=True, rmv_after_market=True, timezone='UTC', raw_data=False, round=True)
```

##### Available Tickers

```python
import btgsolutions_dataservices as btg
hist_candles = btg.HistoricalCandles(api_key='YOUR_API_KEY')
hist_candles.get_available_tickers(market_type='stocks', date='2025-05-29')
```

##### Plot Candles

```python
import btgsolutions_dataservices as btg
hist_candles = btg.HistoricalCandles(api_key='YOUR_API_KEY')
hist_candles.get_intraday_history_candles(ticker='PETR4',  market_type='stocks', corporate_events_adj=True, date='2023-10-06', candle='1m', rmv_after_market=True, timezone='UTC', raw_data=False).plot(x='candle_time', y='close_price', kind='scatter')
```

#### Historical Candles Crypto

##### Interday

```python
import btgsolutions_dataservices as btg
hist_candles_crypto = btg.HistoricalCandlesCrypto(api_key='YOUR_API_KEY')
hist_candles_crypto.get_interday_history_candles(ticker='BTC', currency='BRL', exchange='consolidated', start_date='2025-06-01', end_date='2025-07-01', timezone='UTC', raw_data=False)
```

##### Intraday

```python
import btgsolutions_dataservices as btg
hist_candles_crypto = btg.HistoricalCandlesCrypto(api_key='YOUR_API_KEY')
hist_candles_crypto.get_intraday_history_candles(ticker='BTC', currency='BRL', exchange='consolidated', date='2025-06-01', candle='1h', timezone='America/Sao_Paulo', raw_data=False)
```

##### Available Tickers

```python
import btgsolutions_dataservices as btg
hist_candles_crypto = btg.HistoricalCandlesCrypto(api_key='YOUR_API_KEY')
hist_candles_crypto.get_available_tickers(exchange='coinbase', date='2023-01-13')
```

#### Historical Tick Data (Bulk Data)

##### Available Tickers

```python
import btgsolutions_dataservices as btg
bulk_data = btg.BulkData(api_key='YOUR_API_KEY')
bulk_data.get_available_tickers(date='2023-07-03', data_type='trades', prefix='PETR')
```

##### Get Data

```python
import btgsolutions_dataservices as btg
bulk_data = btg.BulkData(api_key='YOUR_API_KEY')
bulk_data.get_data(ticker='DI1F18', date='2017-01-02', data_type='trades')
# bulk_data.get_data(ticker='PETR4', date='2024-01-22', data_type='books')
# bulk_data.get_data(ticker='VALE3', date='2024-04-01', data_type='trades-and-book-events')
# bulk_data.get_data(ticker='PETR4', date='2025-05-07', data_type='instrument-status')
# bulk_data.get_data(ticker='PETR4', date='2025-05-07', data_type='execution-summary')
# bulk_data.get_data(ticker='PETR4', date='2025-05-07', data_type='execution-statistics')
```

##### Get Data With Billing Headers

```python
import btgsolutions_dataservices as btg
bulk_data = btg.BulkData(api_key='YOUR_API_KEY')
df, billing_headers = bulk_data.get_data(ticker='PETR4', date='2025-06-20', data_type='trades', return_billing_headers=True)
# billing_headers = bulk_data.get_data(ticker='PETR4', date='2025-06-20', data_type='trades', dry_run=True)
```

##### Security List

```python
import btgsolutions_dataservices as btg
bulk_data = btg.BulkData(api_key='YOUR_API_KEY')
bulk_data.get_security_list(date='2025-05-07')
```

##### Market Data Channels

```python
import btgsolutions_dataservices as btg
bulk_data = btg.BulkData(api_key='YOUR_API_KEY')
bulk_data.get_market_data_channels(date='2026-01-30')
```

##### Compressed Data (PCAP files)

```python
import btgsolutions_dataservices as btg
bulk_data = btg.BulkData(api_key='YOUR_API_KEY')
bulk_data.get_compressed_data(channel='98', date='2026-01-30', data_type='instruments')
# bulk_data.get_compressed_data(channel='98', date='2026-01-30', data_type='incremental', feed='feedA')
# bulk_data.get_compressed_data(channel='98', date='2026-01-30', data_type='snapshot')
```

#### Historical Book by Order

Rebuild the order-by-order book of a past day from the trades-and-book-events stream, as a generator of `(kind, info)` pairs: `"book"` for each book change (with the `bid`/`offer` after it and the `order` that changed) and `"trade"` for trades. The day is streamed in bounded chunks (`batch_size`), so memory stays low.

```python
import btgsolutions_dataservices as btg

events = btg.TradesAndBookEvents(api_key='YOUR_API_KEY')

for kind, info in events.get_book(ticker='PETR4', date='2026-05-15', view='mbo', n_levels=5):
    if kind == 'trade':
        print('trade:', info)
    else:
        print('book:', info['bid'][:1], info['offer'][:1], info['order']['action'])

# only a time window (the book is still replayed from the start of the day):
for kind, info in events.get_book(
    ticker='PETR4', date='2026-05-15',
    boundary=[
        {'field': 'timestamp', 'value': '2026-05-15 14:00:00', 'mode': 'after'},
        {'field': 'timestamp', 'value': '2026-05-15 14:30:00', 'mode': 'until'},
    ],
):
    ...
```

#### Market Events

##### Available Tickers

```python
import btgsolutions_dataservices as btg
market_events = btg.MarketEvents(api_key='YOUR_API_KEY')
market_events.get_available_tickers(date='2026-09-17', data_type='price-events', prefix='PETR')
```

##### Get Data

```python
import btgsolutions_dataservices as btg
market_events = btg.MarketEvents(api_key='YOUR_API_KEY')
market_events.get_data(ticker='PETR4', date='2026-09-17', data_type='price-events')
# market_events.get_data(ticker='AURE3T', date='2026-09-17', data_type='open-interest')
# market_events.get_data(ticker='PETR4', date='2026-09-17', data_type='auction-imbalance')
# market_events.get_data(ticker='PETR4', date='2026-09-17', data_type='price-quantity-bands')
```

### Alternative Data

#### High Frequency News Stream

```python
import btgsolutions_dataservices as btg
ws = btg.HFNWebSocketClient(api_key='YOUR_API_KEY')
ws.run(on_message=lambda message: print(message))

# Subscribe to live economy news in Portuguese
ws.subscribe(settings={'feed': 'economy', 'text_language': 'portuguese'})

# Request latest news on demand (without subscribing to the live stream)
ws.latest_news(settings={'feed': 'crypto', 'limit': '10'})

# Get available filter values
ws.available_filters(settings={})

# Stop receiving broadcasts (keeps connection open)
ws.unsubscribe()

ws.close()

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

#### High Frequency News

```python
import btgsolutions_dataservices as btg
hfn = btg.HighFrequencyNews(api_key='YOUR_API_KEY')

# Latest news with filters
hfn.get_latest_news(feed='economy', text_language='portuguese', limit=10)

# Latest news by ticker tags
hfn.get_latest_news(tags=['PETR4', 'VALE3'])

# Historical news for a date range
hfn.get_historical_news(
    start_date='2026-05-01T00:00:00.000Z',
    end_date='2026-05-08T23:59:59.999Z',
    feed='economy',
)

# Available filter values
hfn.get_available_filters()
```

#### OPA

```python
import btgsolutions_dataservices as btg
public_sources = btg.PublicSources(api_key='YOUR_API_KEY')
public_sources.get_opas(start_date='2022-10-01', end_date='2024-10-01')
```

#### STOCK LOAN

```python
import btgsolutions_dataservices as btg
stock_loan = btg.StockLoan(api_key='YOUR_API_KEY')
stock_loan.get_trades()
stock_loan.get_paginated_trades(page=1, limit=1000, ticker ='PETR4')
stock_loan.get_available_tickers()
```

#### Company Fundamentals

##### Company General Information

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.general_info(ticker='PETR4')
```

##### Income Statement

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.income_statement(ticker='PETR4')
```

##### Balance Sheet

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.balance_sheet(ticker='PETR4')
```

##### Cash Flow

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.cash_flow(ticker='PETR4')
```

##### Valuation

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.valuation(ticker='PETR4')
```

##### Ratios

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.ratios(ticker='PETR4')
```

##### Growth

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.growth(ticker='PETR4')
```

##### Interims

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.interims(ticker='PETR4')
```

##### All Financial Tables

```python
import btgsolutions_dataservices as btg
company_data = btg.CompanyData(api_key='YOUR_API_KEY')
company_data.all_financial_tables(ticker='PETR4')
```

#### REST Technical Catalogs

Technical endpoint descriptions for REST APIs are exported by the package so
MCPs and other connectors can reuse the same source of truth instead of
duplicating endpoint semantics locally.

```python
from btgsolutions_dataservices.rest import (
    DATASERVICES_ENDPOINTS,
    DATASERVICES_ENDPOINT_RELATIONSHIPS,
    get_dataservices_tool_description,
)

print(get_dataservices_tool_description("get_quotes"))
print(get_dataservices_tool_description("get_book_scope"))
```

The Data Services catalog covers quotes, candles, intraday trades, last events,
reference data, corporate events, company fundamental data, HFN news,
stock-loan data, bulk market data, broker reference, broker analytics and
book-scope endpoints. It documents parameters, endpoint relationships such as
available-ticker discovery before market-data calls, broker-reference discovery
before broker analytics, HFN filter discovery before news queries, corporate
events before adjusted price analysis, and book-scope constraints for
microstructure analysis.

The REST catalogs also document cross-domain relationships between Public
Sources and market-data services: company directory resolution feeds ticker
reference, quotes, candles, stock-loan, broker analytics and book-scope tools;
sector classification feeds peer-market comparisons; fund holdings feed
underlying ticker market analysis; ownership/free-float feeds liquidity context;
and disclosures, official notices, HFN news and corporate events feed event
window analysis.

#### Alternative Data - Metadata

Technical endpoint descriptions for the public-sources alternative-data APIs are
exported by the package so MCPs and other connectors can reuse the same source
of truth:

```python
from btgsolutions_dataservices.rest import (
    PUBLIC_SOURCES_ENDPOINTS,
    PUBLIC_SOURCES_ENDPOINT_RELATIONSHIPS,
    get_public_sources_tool_description,
)

print(get_public_sources_tool_description("get_company_board"))
```

The catalog documents endpoint parameters, known data gaps, excluded endpoints,
and relationships such as: company metadata resolving identifiers for governance
and ownership calls; macro indicator metadata feeding macro observations; asset
metadata feeding maximum-theoretical-margin calls; financial statement type
metadata feeding statement queries; assemblies and ownership notices feeding
notice summaries; and fund holdings/asset fund holders linking funds with
company tickers.

```python
import btgsolutions_dataservices as btg
meta = btg.AlternativeDataMetadata(api_key='YOUR_API_KEY')
meta.get_company_directory(query='PETROBRAS', jurisdiction='BR')
meta.list_companies(query='PETROBRAS', jurisdiction='BR')
meta.list_etfs(query='BOVA')
meta.get_company_sector(identifier='PETR4')
meta.get_taxonomy(system='b3')
meta.get_cnae(code='6422100')
meta.get_sector_companies(sector='Petróleo, Gás e Biocombustíveis')
meta.get_sectors_summary()
meta.get_financial_statement_types()
meta.get_datasets()
meta.get_available_assets(dataset='maximum_theoretical_margin', prefix='PETR')
meta.get_available_indicators()
```

#### Alternative Data - Companies

```python
import btgsolutions_dataservices as btg
companies = btg.AlternativeDataCompanies(api_key='YOUR_API_KEY')
companies.list_companies(query='PETROBRAS', jurisdiction='BR')
companies.get_board(company_id='VALE3', body='board')
companies.get_governance_summary(company_id='ITUB4')
companies.get_governance_history(company_id='PETR4', start_date='2023-01-01', end_date='2024-12-31')
companies.get_governance_documents(company_id='PETR4', start_date='2024-01-01', end_date='2024-12-31')
companies.get_governance_compensation(company_id='VALE3', fiscal_year='2024')
companies.get_governance_related_party(company_id='ITUB4')
companies.get_governance_beneficial_ownership(company_id='AAPL')  # UK PSC / US SEC proxy data; not BR listed-company ownership
companies.get_corporate_registry(company_id='PETR4', direction='partners')
companies.get_corporate_registry(company_id='PETR4', direction='investees')
companies.get_insider_trades(company_id='AAPL', start_date='2024-01-01', end_date='2024-12-31')
companies.get_board_changes(company_id='VALE3', event='elected')
companies.get_assemblies(company_id='PINE4')
companies.get_financial_statements(company_id='PETR4', statement='income_statement', quarter='4T24')
companies.get_financial_notes(company_id='VALE3', quarter='4T24')
companies.get_disclosures(company_id='PETR4', document_type='repurchase')
companies.get_disclosures(company_id='PETR4', document_type='insider')
```

For Brazilian governance endpoints, current board and summary responses prefer
the latest raw FRE filing when available. Returned governance summaries can
include `latest_reference_date`, `latest_version`, `latest_document_id` and
`structure_source`; alternate B3 tickers/units such as `BPAC11` can resolve to
the underlying listed company when covered by the source metadata.

#### Alternative Data - People

```python
import btgsolutions_dataservices as btg
people = btg.AlternativeDataPeople(api_key='YOUR_API_KEY')
people.get_appointments(person_id='slug:Jean Paul Lemann', active_only=True)
people.get_appointments(person_id='slug:Jean Paul Lemann', group_by='company')
```

#### Alternative Data - Funds

```python
import btgsolutions_dataservices as btg
funds = btg.AlternativeDataFunds(api_key='YOUR_API_KEY')
funds.list_etfs(query='BOVA')
funds.get_holdings(fund_id='BOVA11', reference_date='2024-12-31')
funds.get_exposures(fund_id='BOVA11', exposure_type='asset_class')
funds.get_history(fund_id='BOVA11', start_date='2024-01-01', end_date='2024-12-31')
funds.get_lookthrough(fund_id='BOVA11')
# Manager aggregation requires an exact covered manager CNPJ/name, not ETF issuer slugs, ETF tickers or fund CNPJs.
# funds.get_manager_aggregate_holdings(manager_id='...')
```

#### Alternative Data - Ownership

```python
import btgsolutions_dataservices as btg
ownership = btg.AlternativeDataOwnership(api_key='YOUR_API_KEY')
ownership.get_top_shareholders(company_id='VALE3', limit=10)
ownership.get_ownership_current(company_id='ITUB4')
ownership.get_ownership_history(company_id='PETR4', start_date='2023-01-01', end_date='2024-12-31')
ownership.get_ownership_change_events(company_id='VALE3', start_date='2024-01-01', end_date='2024-12-31')
ownership.get_ownership_official_notices(company_id='PETR4')
ownership.get_notice_summary(url='https://www.rad.cvm.gov.br/ENETWEB/frmGerenciaPastaDeArquivos.aspx?numProtocolo=1234567')
ownership.get_ownership_control_group(company_id='VALE3')
ownership.get_ownership_free_float(company_id='PETR4')
ownership.get_shareholder_holdings(shareholder_id='00.000.000/0001-91')
ownership.get_institutional_holders(identifier='VALE3')
ownership.get_fund_holders(identifier='PETR4', identifier_type='b3_ticker')
```

For Brazilian ownership/free-float endpoints, current control and free-float
responses use the latest FRE source document/version for the selected reference
date when available. Repeated older source documents are deduplicated where
possible, while distinct rows for the same holder across classes, roles or
ownership categories are preserved. Zero free-float or independence percentages
can be valid source values, not missing data.

#### Alternative Data - Macro & Markets

```python
import btgsolutions_dataservices as btg
macro = btg.AlternativeDataMacroMarkets(api_key='YOUR_API_KEY')
macro.get_macro_indicators(indicator='selic')
macro.get_macro_indicators(indicator='ipca_contributions', start_date='2024-01', end_date='2024-12')
macro.get_macro_indicators(indicator='gdp', type='yoy')
macro.get_macro_indicators(indicator='comexstat', year='2024', state='SP')
macro.get_macro_indicators(indicator='comexstat', aggregate='states', start_date='2024-01', end_date='2024-12')
macro.get_macro_indicators(indicator='comexstat', aggregate='timeline', group_by='country', state='SP')
macro.get_macro_indicators(indicator='rreo', year='2024', period='6')
macro.get_maximum_theoretical_margin(asset='PETR4', report_date='2024-12-31')
macro.get_dpmfi(start_date='2024-01', end_date='2024-12', status='dados_oficiais')
macro.get_dpmfi(snapshot_date='2026-06-24', limit=10)  # reproducible scoped snapshot
macro.get_dpmfi_composition(bond_type='IPCA')
```

`AlternativeDataMacroMarkets` exposes the public-sources market-data endpoint for B3 maximum theoretical margin. The direct market-data `investor-categories` endpoint is intentionally not exposed in this package.

### Reference Data

#### Corporate Events

```python
import btgsolutions_dataservices as btg
corporate_events = btg.CorporateEvents(api_key='YOUR_API_KEY')
corporate_events.get(start_date='2024-05-01', end_date='2024-05-31')
# corporate_events.get(start_date='2024-05-01', end_date='2024-05-31', tickers=['VALE3'])
```

#### Broker Reference

```python
import btgsolutions_dataservices as btg
broker_reference = btg.BrokerReference(api_key='YOUR_API_KEY')
broker_reference.get()
```

#### Book Scope

```python
import btgsolutions_dataservices as btg
book_scope = btg.BookScope(api_key='YOUR_API_KEY')

result = book_scope.get(
    symbol='DOLM26',
    market_type='derivatives',
    start_time='2026-05-28T14:12:00Z',
    end_time='2026-05-28T14:15:00Z',
    select=['trades', 'book_snapshot', 'book_incremental'],  # choose one, two, or all three
)

single_file_result = book_scope.get(
    symbol='DOLM26',
    market_type='derivatives',
    start_time='2026-05-28T14:12:00Z',
    end_time='2026-05-28T14:15:00Z',
    select=['trades', 'book_snapshot', 'book_incremental'],
    aggregate_info=True,
)
```

#### Broker Analytics

```python
import btgsolutions_dataservices as btg
broker_analytics = btg.BrokerAnalytics(api_key='YOUR_API_KEY', market_type='stocks')
summary = broker_analytics.get_summary(brokers=['85', '3'], tickers=['PETR4', 'ABCB4'])
top_brokers = broker_analytics.get_top_brokers(n=10)
top_tickers = broker_analytics.get_top_tickers(n=10, brokers=['85', '3'])
```

#### Ticker Reference Data

```python
import btgsolutions_dataservices as btg
ref = btg.ReferenceData(api_key='YOUR_API_KEY')
ref.ticker_reference(tickers=['VALE3','PETR4'])
```

#### Algo Hunter

```python
import btgsolutions_dataservices as btg
algohunter = AlgoHunter(api_key='YOUR_API_KEY')
algohunter.get_thermometer()
algohunter.get_recently_detected(ticker='PETR4')
```


