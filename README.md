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

### Alternative Data

#### High Frequency News Stream

```python
import btgsolutions_dataservices as btg
ws = btg.HFNWebSocketClient(api_key='YOUR_API_KEY', country='brazil')
ws.run(on_message=lambda message: print(message))

## The following is optional to keep the program running in a .py file:
# from time import sleep
# while True:
#   sleep(1)
```

#### High Frequency News

```python
import btgsolutions_dataservices as btg
hfn = btg.HighFrequencyNews(api_key='YOUR_API_KEY')
hfn.latest_news()
```

#### High Frequency News V3 Stream

```python
import btgsolutions_dataservices as btg
ws = btg.HFNV3WebSocketClient(api_key='YOUR_API_KEY')
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
```

#### High Frequency News V3

```python
import btgsolutions_dataservices as btg
hfn = btg.HighFrequencyNewsV3(api_key='YOUR_API_KEY')

# Latest news with filters
hfn.get_latest_news(feed='economy', text_language='portuguese', limit=10)

# Latest news by ticker tags
hfn.get_latest_news(tags=['PETR4', 'VALE3'])

# Historical news for a date range
hfn.get_historical_news(
    start_date='2026-05-01T00:00:00.000Z',
    end_date='2026-05-01T23:59:59.999Z',
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

