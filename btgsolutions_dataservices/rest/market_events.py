from typing import Optional
from ..exceptions import BadResponse
import requests
from ..config import url_apis
from .authenticator import Authenticator
from .bulk_data import extract_billing_headers
import json
from io import BytesIO
import pyarrow.parquet as pq


class MarketEvents:
    """
    This class provides B3 market events data (price events, open interest, auction imbalance,
    price & quantity bands) by ticker and date.

    * Main use case:

    >>> from btgsolutions_dataservices import MarketEvents
    >>> market_events = MarketEvents(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> market_events.get_data(
    >>>     ticker = 'PETR4',
    >>>     date = '2025-05-07',
    >>>     data_type = 'price-events',
    >>>     raw_data = False
    >>> )

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """
    def __init__(
        self,
        api_key:Optional[str]
    ):
        self.api_key = api_key
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"authorization {self.token}"}

    def get_available_tickers(
        self,
        date:str,
        data_type:str,
        prefix:str=''
    ):
        """
        This method provides all tickers available for query, for the provided market events data type.

        Parameters
        ----------------
        date: str
            Date period.
            Field is required.
            Format: 'YYYY-MM-DD'.
            Example: '2025-05-07'.
        data_type: str
            Market events data type.
            Field is required.
            Example: 'price-events', 'open-interest', 'auction-imbalance' or 'price-quantity-bands'.
        prefix: str
            Filters tickers starting with the prefix.
            Field is optional.
            Example: 'PETR'.
        """
        url = f"{url_apis}/marketdata/market-events/available-tickers?date={date}&data_type={data_type}&prefix={prefix}"
        response = requests.request("GET", url,  headers=self.headers)

        try:
            response_json = response.json()
        except ValueError as exc:
            body = (response.text or "").strip()
            raise BadResponse(
                f"Error {response.status_code}: non-JSON response from market events available-tickers. "
                f"{body[:500]}"
            ) from exc
        if response.status_code == 200: return response_json['tickers']
        raise BadResponse(f'Error: {response_json.get("ApiClientError", "")}.\n{response_json.get("SuggestedAction", "")}')

    def get_data(
        self,
        ticker:str,
        date:str,
        data_type:str='price-events',
        raw_data:bool=False,
        dry_run:bool=False,
    ):
        """
        This method provides B3 market events data (price events, open interest, auction imbalance,
        price & quantity bands) for a given ticker and date.

        Parameters
        ----------------
        ticker: str
            Ticker that needs to be returned.
            Field is required. Example: 'PETR4'.
        date: str
            Date period.
            Field is required.
            Format: 'YYYY-MM-DD'. Example: '2025-05-07'.
        data_type: str
            Market events data type.
            Field is required. Available types: 'price-events', 'open-interest',
            'auction-imbalance', 'price-quantity-bands'.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        dry_run: bool
            If true, checks request validity without downloading data and returns informative headers.
            Field is not required. Default: False.
        """

        url = f"{url_apis}/marketdata/market-events/{data_type}?ticker={ticker}&date={date}"
        if dry_run:
            url = f"{url}&dry_run=true"

        response = requests.request("GET", url,  headers=self.headers)

        if response.status_code == 204 and dry_run:
            return extract_billing_headers(response.headers)

        if response.status_code == 200:

            try:

                if raw_data == False:
                    parquet_buffer = BytesIO(response.content)
                    parquet_file = pq.ParquetFile(parquet_buffer)
                    df = parquet_file.read().to_pandas()
                    return df

                else:
                    content_disposition = response.headers.get('Content-Disposition', '')
                    filename = content_disposition.split('filename=')[1]

                    # Write the content to a file
                    with open(filename, 'wb') as file:
                        file.write(response.content)
                    return None

            except Exception as e:
                print(f'error while trying to retrieve file:\n{e}')
                return None

        response = json.loads(response.text)
        raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')
