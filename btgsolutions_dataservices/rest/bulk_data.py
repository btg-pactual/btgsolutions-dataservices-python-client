import os
from typing import Optional
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1, url_apis, url_apis_v3
from .authenticator import Authenticator
import json
import pandas as pd
from io import BytesIO
import pyarrow.parquet as pq

def download_compressed_file(url, headers):
    
    with requests.get(url, headers=headers, stream=True) as response:
        if response.status_code != 200:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')

        try:
            file_name = response.headers.get('content-disposition').split('filename=')[1]
        except:
            file_name = "compressed_file.tar.gz"
        
        total_length = response.headers.get('content-length')
        if total_length is not None:
            total_length = int(total_length)
            bytes_downloaded = 0

        with open(file_name, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    if total_length is not None:
                        bytes_downloaded += len(chunk)
                        print(f"Downloaded: {bytes_downloaded / total_length * 100:.2f}%", end='\r')

    current_dir_name = os.getcwd()
    print(f"\nDownload completed. File path: '{current_dir_name}/{file_name}'")

class BulkData:
    """
    This class provides market data by ticker and date, in .csv format

    * Main use case:

    >>> from btgsolutions_dataservices import BulkData
    >>> bulk_data = BulkData(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> bulk_data.get_data(
    >>>     ticker = 'DI1F18',
    >>>     date = '2017-01-02',
    >>>     data_type = 'trades',
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
        This method provides all tickers available for query, for the provided market data type.

        Parameters
        ----------------
        date: str
            Date period.
            Field is required.
            Format: 'YYYY-MM-DD'.
            Example: '2023-07-03'.
        data_type: str
            Market data type.
            Field is required.
            Example: 'trades', 'books' or 'trades-and-book-events'.
        prefix: str
            Filters tickers starting with the prefix.
            Field is optional.
            Example: 'DOL'.
        """
        url = f"{url_apis}/marketdata/bulkdata/available-tickers?date={date}&data_type={data_type}&prefix={prefix}"
        response = requests.request("GET", url,  headers=self.headers)

        response_json = response.json()
        if response.status_code == 200: return response_json['tickers']
        raise BadResponse(f'Error: {response_json.get("ApiClientError", "")}.\n{response_json.get("SuggestedAction", "")}')

    def get_market_data_channels(
        self,
        date:str,
    ):
        """
        This method provides all the available market data channels for a given date. For more detailed information about market data channels, please consult our documentation, at https://dataservicesdocs.btgpactualsolutions.com/home > Data Specs > Market Data channel definition.

        Parameters
        ----------------
        date: str
            Date period.
            Field is required.
            Format: 'YYYY-MM-DD'. Example: '2026-01-30'.
        """
        url = f"{url_apis_v3}/marketdata/bulkdata/compressed/available-channels?date={date}"

        response = requests.request("GET", url,  headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("ApiClientError", "")}.\n{response.get("SuggestedAction", "")}')

    def get_compressed_data(
        self,
        channel:str,
        date:str,
        data_type:str='instruments',
        feed:str='',
    ):
        """
        This method provides market data via compressed files (instruments, snapshot, incremental) for a given market data channel and date. Function get_market_data_channels provides all the available channels for a given date.

        Parameters
        ----------------
        channel: str
            Market Data channel.
            Field is required. Example: '72'.
        date: str
            Date period.
            Field is required.
            Format: 'YYYY-MM-DD'. Example: '2026-01-30'.
        data_type: str
            Market data type.
            Field is required. Example: 'instruments', 'snapshot', 'incremental'.
        feed: str
            Available only for 'incremental' data type. Allowed values: 'feedA' or 'feedB'
            Field is not required.
        """
        url = f"{url_apis_v3}/marketdata/bulkdata/compressed/{data_type}?channel={channel}&date={date}&feed={feed}"
        download_compressed_file(url, headers=self.headers)

    def get_data(
        self,
        ticker:str,
        date:str,
        data_type:str='trades',
        raw_data:bool=False
    ):
        """
        This method provides tick-by-tick market data (trades, book events, book snapshots) for a given ticker and date.

        Parameters
        ----------------
        ticker: str
            Ticker that needs to be returned.
            Field is required. Example: 'DI1F18'.
        date: str
            Date period.
            Field is required.
            Format: 'YYYY-MM-DD'. Example: '2023-07-03', '2023-07-28'.
        data_type: str
            Market data type.
            Field is required. Available types: 'trades', 'books', 'trades-and-book-events'
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Field is not required. Default: False.
        """

        url = f"{url_apis}/marketdata/bulkdata/{data_type}?ticker={ticker}&date={date}"

        response = requests.request("GET", url,  headers=self.headers)
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

    def get_security_list(
        self,
        date:str,
        raw_data:bool=False
    ):
        """
        This method returns the security list for a given date.

        Parameters
        ----------------
        date: str
            Date period.
            Field is required.
            Format: 'YYYY-MM-DD'. Example: '2025-05-12'.
        raw_data: bool
            If false, returns data in a dataframe. If true, returns raw data.
            Default: False.
        """

        url = f"{url_apis}/marketdata/bulkdata/security-list?date={date}"

        response = requests.request("GET", url,  headers=self.headers)
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
        raise BadResponse(f'Error: {response.get("ApiClientError", "") or response.get("ApiServerMessage", "")}.\n{response.get("SuggestedAction", "")}')
