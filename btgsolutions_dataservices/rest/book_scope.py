from datetime import datetime, timedelta, timezone
from typing import Optional, List
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator
from io import BytesIO
import pyarrow as pa
import pyarrow.parquet as pq

VALID_SELECT_OPTIONS = {"trades", "book_snapshot", "book_incremental"}
MAX_MARKET_SCOPE_WINDOW = timedelta(minutes=10)
ROW_LIMIT = 10000


class BookScope:
    """
    This class provides market scope data (trades, book snapshots, book incremental)
    for a given symbol and time window.

    * Main use case:

    >>> from btgsolutions_dataservices import BookScope
    >>> book_scope = BookScope(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> book_scope.get(
    >>>     symbol='PETR4',
    >>>     market_type='Equities',
    >>>     start_time='2026-05-22T12:00:00Z',
    >>>     end_time='2026-05-22T12:10:00Z',
    >>> )

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
        self.base_url = url_api_v1

    def _fetch_all_pages(self, endpoint_url: str, params: dict) -> bytes:
        """Fetches all pages via rpt_seq cursor and returns a single combined parquet."""
        tables = []
        rpt_seq = None

        while True:
            page_params = {**params}
            if rpt_seq is not None:
                page_params["rpt_seq"] = rpt_seq

            response = requests.get(endpoint_url, params=page_params, headers=self.headers)
            if response.status_code != 200:
                try:
                    error_body = response.json()
                    detail = error_body.get("detail", error_body.get("error", response.text))
                except Exception:
                    detail = response.text
                raise BadResponse(f"Error: {detail}")

            table = pq.read_table(BytesIO(response.content))
            tables.append(table)

            if table.num_rows < ROW_LIMIT:
                break
            rpt_seq = table.column("rpt_seq")[-1].as_py()

        combined = pa.concat_tables(tables)
        buffer = BytesIO()
        pq.write_table(combined, buffer)
        return buffer.getvalue()

    @staticmethod
    def _combine_parquets(parquet_payloads: List[bytes]) -> bytes:
        """Combines multiple parquet payloads into a single parquet file."""
        tables = [BookScope._normalize_timestamps(pq.read_table(BytesIO(payload))) for payload in parquet_payloads]
        combined = pa.concat_tables(tables, promote_options="default")
        buffer = BytesIO()
        pq.write_table(combined, buffer)
        return buffer.getvalue()

    @staticmethod
    def _normalize_timestamps(table: pa.Table) -> pa.Table:
        """Normalizes timestamp columns so tables can be concatenated safely."""
        normalized = table

        for field in table.schema:
            if pa.types.is_timestamp(field.type):
                target_type = pa.timestamp("us", tz=field.type.tz)
                column_index = normalized.schema.get_field_index(field.name)
                normalized = normalized.set_column(
                    column_index,
                    field.name,
                    normalized[field.name].cast(target_type),
                )

        return normalized

    @staticmethod
    def _parse_iso8601(value: str, field_name: str) -> datetime:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a valid ISO-8601 datetime string.") from exc

    @staticmethod
    def _resolve_scope(end_time: datetime) -> str:
        """Determines whether the request is 'intraday' or 'historical' based on end_time."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if end_time >= today_start:
            return "intraday"
        return "historical"

    def get(
        self,
        symbol: str,
        market_type: str,
        start_time: str,
        end_time: str,
        select: List[str] = ["trades", "book_snapshot", "book_incremental"],
        aggregate_info: bool = False,
    ):
        """
        Returns trades, book snapshot and book incremental data for the given symbol and time window.

        Pagination is handled automatically: if the API returns the maximum number of rows
        (10 000), additional pages are fetched using the rpt_seq cursor until all events
        in the requested horizon are retrieved. The caller always receives a single,
        complete parquet file per dataset.

        Parameters
        ----------------
        symbol: str
            The ticker symbol to query.
            Field is required. Example: 'PETR4', 'DOLM26'.
        market_type: str
            Market type.
            Field is required. Allowed values: 'Equities', 'Derivatives'.
        start_time: str
            Start of the analysis window in ISO-8601 format.
            Field is required. Example: '2026-05-22T15:50:00Z'.
        end_time: str
            End of the analysis window in ISO-8601 format.
            Field is required. Example: '2026-05-22T12:10:00Z'.
        select: list of str
            Which datasets to return.
            Field is optional. Default: ['trades', 'book_snapshot', 'book_incremental'].
            Allowed values: 'trades', 'book_snapshot', 'book_incremental'.
        aggregate_info: bool
            When True, returns a single parquet file containing the selected datasets.
            Field is optional. Default: False.

        Returns
        ----------------
        dict
            Dictionary with the selected keys, each containing:
            - 'data': raw parquet bytes with all rows for the requested time window
            When aggregate_info is True, returns a single key:
            - 'data': raw parquet bytes with all selected datasets combined into one parquet file
        """
        invalid = set(select) - VALID_SELECT_OPTIONS
        if invalid:
            raise ValueError(f"Invalid select options: {invalid}. Valid options are: {VALID_SELECT_OPTIONS}")

        parsed_start_time = self._parse_iso8601(start_time, "start_time")
        parsed_end_time = self._parse_iso8601(end_time, "end_time")

        if parsed_start_time >= parsed_end_time:
            raise ValueError("start_time must be earlier than end_time.")

        if parsed_end_time - parsed_start_time > MAX_MARKET_SCOPE_WINDOW:
            raise ValueError("The maximum allowed range between start_time and end_time is 10 minutes.")

        base_params = dict(symbol=symbol, start_time=start_time, end_time=end_time, limit=ROW_LIMIT)

        scope = self._resolve_scope(parsed_end_time)

        endpoint_map = {
            "trades": f"{self.base_url}/marketdata/br/b3/book-scope/{scope}/{market_type}/trades",
            "book_snapshot": f"{self.base_url}/marketdata/br/b3/book-scope/{scope}/{market_type}/book-snapshot",
            "book_incremental": f"{self.base_url}/marketdata/br/b3/book-scope/{scope}/{market_type}/book-incremental",
        }

        result = {}
        parquet_payloads = []
        for key in select:
            data = self._fetch_all_pages(endpoint_map[key], base_params)
            if aggregate_info:
                parquet_payloads.append(data)
            else:
                result[key] = {"data": data}

        if aggregate_info:
            result["data"] = self._combine_parquets(parquet_payloads)

        return result
