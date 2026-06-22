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
