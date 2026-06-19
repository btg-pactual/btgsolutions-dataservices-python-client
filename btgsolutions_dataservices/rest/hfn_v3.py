
from typing import Optional, List
from ..exceptions import BadResponse
import requests
from ..config import url_apis_v3
import json
import pandas as pd
from .authenticator import Authenticator


class HighFrequencyNewsV3:
    """
    This class provides latest and historical news through the HFN V3 API,
    with rich filtering by feed, source, language, tags, categories and free text.

    * Main use case:

    >>> from btgsolutions_dataservices import HighFrequencyNewsV3

    >>> hfn = HighFrequencyNewsV3(
    >>>     api_key='YOUR_API_KEY',
    >>> )

    >>> latest = hfn.get_latest_news(
    >>>     feed='economy',
    >>>     limit=10,
    >>> )

    >>> petro_news = hfn.get_latest_news(
    >>>     tags=['PETR4'],
    >>>     text_language='portuguese',
    >>> )

    >>> historical = hfn.get_historical_news(
    >>>     start_date='2025-01-01T00:00:00.000Z',
    >>>     end_date='2025-01-01T23:59:59.999Z',
    >>>     feed='economy',
    >>> )

    >>> filters = hfn.get_available_filters()

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """

    def __init__(
        self,
        api_key: Optional[str],
    ):
        self.api_key = api_key
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"authorization {self.token}"}

    def get_latest_news(
        self,
        countries: Optional[List[str]] = None,
        source_type: Optional[str] = None,
        source: Optional[str] = None,
        feed: Optional[str] = None,
        text_language: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        categories: Optional[List[str]] = None,
        text: Optional[str] = None,
        raw_data: bool = False,
    ):
        """
        Most recent news captured by the HFN Engine.
        By default returns the latest 20 news (max 5000 with ``limit``).
        All filter parameters are optional and can be combined freely.

        Parameters
        ----------------
        countries: list of str
            Filter results by one or more country codes. Matches any provided value.
            Example: ['BR'], ['BR', 'US'].
            Field is not required.
        source_type: str
            Filter results by ingestion source type.
            Accepted values: 'rss', 'html', 'pdf'.
            Field is not required.
        source: str
            Filter results by a specific news source name.
            Example: 'Infomoney', 'Exame - Mercado'.
            Field is not required.
        feed: str
            Filter results by thematic feed category.
            Accepted values: 'politics', 'economy', 'crypto', 'technology',
            'sports', 'health', 'commodities', 'energy', 'general'.
            Field is not required.
        text_language: str
            Filter results by the language of the news content.
            Accepted values: 'portuguese', 'english', 'spanish', 'german', 'french'.
            Field is not required.
        tags: list of str
            Filter results by one or more tags (ticker symbols, index names, etc.).
            Matches any provided value, including substrings.
            Example: ['PETR4'], ['PETR4', 'VALE3'].
            Field is not required.
        start_date: str
            Lower bound for news publishing time.
            Accepted formats: ISO 8601 date-time (``YYYY-MM-DDTHH:MM:SS.sssZ``) or date (``YYYY-MM-DD``).
            Example: '2026-03-13T00:00:00.000Z'.
            Field is not required.
        end_date: str
            Upper bound for news publishing time.
            Accepted formats: ISO 8601 date-time (``YYYY-MM-DDTHH:MM:SS.sssZ``) or date (``YYYY-MM-DD``).
            Example: '2026-03-13T23:59:59.999Z'.
            Field is not required.
        limit: int
            Maximum number of news items to return (max 5000).
            Example: 100.
            Field is not required.
        categories: list of str
            Filter results by one or more category keywords extracted from news content.
            Matches any provided value, including substrings.
            Example: ['Petrobras'], ['Bitcoin', 'Ethereum'].
            Field is not required.
        text: str
            Free text search within news title and body.
            Example: 'trump ira', 'taxa selic'.
            Field is not required.
        raw_data: bool
            If True, returns raw data from API, if False, returns a Pandas DataFrame.
            Default: False.
            Field is not required.
        """
        params = {}
        if countries:
            params['countries'] = ','.join(countries)
        if source_type:
            params['source_type'] = source_type
        if source:
            params['source'] = source
        if feed:
            params['feed'] = feed
        if text_language:
            params['text_language'] = text_language
        if tags:
            params['tags'] = ','.join(tags)
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if limit is not None:
            params['limit'] = limit
        if categories:
            params['categories'] = ','.join(categories)
        if text:
            params['text'] = text

        url = f"{url_apis_v3}/hfn/latest-news"
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            response_data = response.json()
            if raw_data:
                return response_data
            else:
                return pd.DataFrame(response_data)
        else:
            response_data = response.json()
            raise BadResponse(
                f'Error: {response_data.get("ApiClientError", "")}.\n{response_data.get("SuggestedAction", "")}'
            )

    def get_historical_news(
        self,
        countries: Optional[List[str]] = None,
        source_type: Optional[str] = None,
        source: Optional[str] = None,
        feed: Optional[str] = None,
        text_language: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        categories: Optional[List[str]] = None,
        text: Optional[str] = None,
        raw_data: bool = False,
    ):
        """
        Provide a datetime interval and get all news registered in that interval.
        All filter parameters are optional and can be combined freely.

        Parameters
        ----------------
        countries: list of str
            Filter results by one or more country codes. Matches any provided value.
            Example: ['BR'], ['BR', 'US'].
            Field is not required.
        source_type: str
            Filter results by ingestion source type.
            Accepted values: 'rss', 'html', 'pdf'.
            Field is not required.
        source: str
            Filter results by a specific news source name.
            Example: 'Infomoney', 'Exame - Mercado'.
            Field is not required.
        feed: str
            Filter results by thematic feed category.
            Accepted values: 'politics', 'economy', 'crypto', 'technology',
            'sports', 'health', 'commodities', 'energy', 'general'.
            Field is not required.
        text_language: str
            Filter results by the language of the news content.
            Accepted values: 'portuguese', 'english', 'spanish', 'german', 'french'.
            Field is not required.
        tags: list of str
            Filter results by one or more tags (ticker symbols, index names, etc.).
            Matches any provided value.
            Example: ['PETR4'], ['PETR4', 'VALE3'].
            Field is not required.
        start_date: str
            Lower bound for news publishing time.
            Accepted formats: ISO 8601 date-time (``YYYY-MM-DDTHH:MM:SS.sssZ``) or date (``YYYY-MM-DD``).
            Example: '2026-03-13T00:00:00.000Z'.
            Field is not required.
        end_date: str
            Upper bound for news publishing time.
            Accepted formats: ISO 8601 date-time (``YYYY-MM-DDTHH:MM:SS.sssZ``) or date (``YYYY-MM-DD``).
            Example: '2026-03-13T23:59:59.999Z'.
            Field is not required.
        limit: int
            Maximum number of news items to return.
            Example: 100.
            Field is not required.
        categories: list of str
            Filter results by one or more category keywords extracted from news content.
            Matches any provided value.
            Example: ['Petrobras'], ['Bitcoin', 'Ethereum'].
            Field is not required.
        text: str
            Free text search within news title and body.
            Example: 'trump ira', 'taxa selic'.
            Field is not required.
        raw_data: bool
            If True, returns raw data from API, if False, returns a Pandas DataFrame.
            Default: False.
            Field is not required.
        """
        params = {}
        if countries:
            params['countries'] = ','.join(countries)
        if source_type:
            params['source_type'] = source_type
        if source:
            params['source'] = source
        if feed:
            params['feed'] = feed
        if text_language:
            params['text_language'] = text_language
        if tags:
            params['tags'] = ','.join(tags)
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if limit is not None:
            params['limit'] = limit
        if categories:
            params['categories'] = ','.join(categories)
        if text:
            params['text'] = text

        url = f"{url_apis_v3}/hfn/historical-news"
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            response_data = response.json()
            if raw_data:
                return response_data
            else:
                return pd.DataFrame(response_data)
        else:
            response_data = response.json()
            raise BadResponse(
                f'Error: {response_data.get("ApiClientError", "")}.\n{response_data.get("SuggestedAction", "")}'
            )

    def get_available_filters(
        self,
        countries: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        source_types: Optional[List[str]] = None,
        feeds: Optional[List[str]] = None,
        text_languages: Optional[List[str]] = None,
    ):
        """
        Retrieve available filter values for the Latest News and Historical News endpoints.
        Returns available countries, source types, sources, feeds and text languages.
        All parameters are optional and can be used to narrow down the results.

        Parameters
        ----------------
        countries: list of str
            Filter the available results by one or more country codes. Matches any provided value.
            Example: ['BR'].
            Field is not required.
        sources: list of str
            Filter the available results by one or more source names. Matches any provided value.
            Example: ['Bloomberg - Markets'].
            Field is not required.
        source_types: list of str
            Filter the available results by one or more source types. Matches any provided value.
            Accepted values: 'rss', 'html', 'pdf'.
            Field is not required.
        feeds: list of str
            Filter the available results by one or more feeds. Matches any provided value.
            Example: ['economy', 'crypto'].
            Field is not required.
        text_languages: list of str
            Filter the available results by one or more text languages. Matches any provided value.
            Accepted values: 'portuguese', 'english', 'spanish', 'german', 'french'.
            Field is not required.
        """
        params = {}
        if countries:
            params['countries'] = ','.join(countries)
        if sources:
            params['sources'] = ','.join(sources)
        if source_types:
            params['source_types'] = ','.join(source_types)
        if feeds:
            params['feeds'] = ','.join(feeds)
        if text_languages:
            params['text_languages'] = ','.join(text_languages)

        url = f"{url_apis_v3}/hfn/available-filters"
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            response_data = response.json()
            raise BadResponse(
                f'Error: {response_data.get("ApiClientError", "")}.\n{response_data.get("SuggestedAction", "")}'
            )
