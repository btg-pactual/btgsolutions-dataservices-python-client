from datetime import datetime, timedelta, timezone
from typing import Optional, List
from ..exceptions import BadResponse
import requests
from ..config import url_api_v1
from .authenticator import Authenticator
from io import BytesIO
import pyarrow as pa
import pyarrow.parquet as pq

VALID_MARKET_TYPES = {"derivatives", "options", "stocks"}
MAX_MARKET_SCOPE_WINDOW = timedelta(minutes=10)
DEFAULT_ROW_LIMIT = 10000

# One entry per exchange covered by the book-scope service. "path_prefix" is the
# "/marketdata/<prefix>/book-scope" segment; "datasets" maps each select option to
# its URL dataset segment. B3 is the only market with a market_type path segment
# and a 3-way split between trades, book_snapshot and book_incremental. NUAM
# Colombia, NUAM Chile, BIVA (Mexico) and BMV (Mexico) share the same shape: no
# market_type segment, and a single "book" dataset instead of a snapshot/incremental
# split (every row from those exchanges already carries the full bid/ask state).
_MARKET_CONFIGS = {
    "b3": {
        "path_prefix": "br/b3",
        "requires_market_type": True,
        "datasets": {
            "trades": "trades",
            "book_snapshot": "book-snapshot",
            "book_incremental": "book-incremental",
        },
    },
    "nuam_colombia": {
        "path_prefix": "co/nuam",
        "requires_market_type": False,
        "datasets": {"trades": "trades", "book": "book"},
    },
    "nuam_chile": {
        "path_prefix": "cl/nuam",
        "requires_market_type": False,
        "datasets": {"trades": "trades", "book": "book"},
    },
    "biva_mexico": {
        "path_prefix": "mx/biva",
        "requires_market_type": False,
        "datasets": {"trades": "trades", "book": "book"},
    },
    "bmv_mexico": {
        "path_prefix": "mx/bmv",
        "requires_market_type": False,
        "datasets": {"trades": "trades", "book": "book"},
    },
}


class BookScope:
    """
    This class provides market scope data (trades and book state) for a given
    symbol and time window, across B3 (Brazil), NUAM Colombia, NUAM Chile,
    BIVA (Mexico) and BMV (Mexico).

    * Main use case (B3):

    >>> from btgsolutions_dataservices import BookScope
    >>> book_scope = BookScope(
    >>>     api_key='YOUR_API_KEY',
    >>> )
    >>> book_scope.get(
    >>>     symbol='DOLM26',
    >>>     market_type='derivatives',
    >>>     start_time='2026-05-28T14:12:00Z',
    >>>     end_time='2026-05-28T14:15:00Z',
    >>> )

    * NUAM Colombia / NUAM Chile / BIVA (Mexico) / BMV (Mexico):

    >>> book_scope.get(
    >>>     symbol='PFDAVIGRP',
    >>>     market='nuam_colombia',
    >>>     start_time='2026-05-28T14:12:00Z',
    >>>     end_time='2026-05-28T14:15:00Z',
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
        """Sends a single request with the default row limit; the server paginates internally."""
        page_params = {**params, "limit": DEFAULT_ROW_LIMIT}
        response = requests.get(endpoint_url, params=page_params, headers=self.headers)
        if response.status_code != 200:
            try:
                error_body = response.json()
                detail = error_body.get("detail", error_body.get("error", response.text))
            except Exception:
                detail = response.text
            raise BadResponse(f"Error: {detail}")
        return response.content

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
        start_time: str,
        end_time: str,
        market: str = "b3",
        market_type: Optional[str] = None,
        select: Optional[List[str]] = None,
        aggregate_info: bool = False,
    ):
        """
        Returns trades and book state data for the given symbol and time window,
        on the requested market/exchange.

        Pagination is handled automatically by the API. The caller always receives
        a single, complete parquet file per dataset.

        Parameters
        ----------------
        symbol: str
            The ticker symbol to query.
            Field is required. Example: 'PETR4', 'DOLM26' (B3), 'PFDAVIGRP' (NUAM Colombia).
        start_time: str
            Start of the analysis window in ISO-8601 UTC format.
            Field is required. Example: '2026-05-28T14:12:00Z'.
        end_time: str
            End of the analysis window in ISO-8601 UTC format.
            Field is required. Example: '2026-05-28T14:15:00Z'.
        market: str
            Exchange to query.
            Field is optional. Default: 'b3'.
            Allowed values: 'b3' (Brazil), 'nuam_colombia', 'nuam_chile',
            'biva_mexico', 'bmv_mexico'.
        market_type: str
            Market type. Only used (and required) when market='b3'; ignored for
            every other market.
            Allowed values: 'derivatives', 'options', 'stocks'.
        select: list of str
            Which datasets to return.
            Field is optional. Default: for market='b3', ['trades', 'book_snapshot',
            'book_incremental']; for every other market, ['trades', 'book'].
            Allowed values: 'trades', 'book_snapshot', 'book_incremental' (market='b3'
            only) or 'trades', 'book' (every other market).
        aggregate_info: bool
            When True, returns a single pandas.DataFrame containing the selected datasets.
            Field is optional. Default: False.

        Returns
        ----------------
        dict or pandas.DataFrame
            When aggregate_info is False (default): dictionary with the selected keys,
            each mapping directly to a pandas.DataFrame with all rows for the requested
            time window.
            When aggregate_info is True: returns a single pandas.DataFrame with all
            selected datasets combined.
        """
        normalized_market = market.lower()
        if normalized_market not in _MARKET_CONFIGS:
            raise ValueError(
                f"Invalid market: {market}. Valid options are: {sorted(_MARKET_CONFIGS)}"
            )
        config = _MARKET_CONFIGS[normalized_market]

        if config["requires_market_type"]:
            if not market_type:
                raise ValueError(f"market_type is required when market='{normalized_market}'.")
            normalized_market_type = market_type.lower()
            if normalized_market_type not in VALID_MARKET_TYPES:
                raise ValueError(
                    f"Invalid market_type: {market_type}. Valid options are: {VALID_MARKET_TYPES}"
                )
            path_prefix = f"{config['path_prefix']}/book-scope/{{scope}}/{normalized_market_type}"
        else:
            path_prefix = f"{config['path_prefix']}/book-scope/{{scope}}"

        valid_select_options = set(config["datasets"])
        if select is None:
            select = list(config["datasets"])
        invalid = set(select) - valid_select_options
        if invalid:
            raise ValueError(f"Invalid select options: {invalid}. Valid options are: {valid_select_options}")

        parsed_start_time = self._parse_iso8601(start_time, "start_time")
        parsed_end_time = self._parse_iso8601(end_time, "end_time")

        if parsed_start_time >= parsed_end_time:
            raise ValueError("start_time must be earlier than end_time.")

        if parsed_end_time - parsed_start_time > MAX_MARKET_SCOPE_WINDOW:
            raise ValueError("The maximum allowed range between start_time and end_time is 10 minutes.")

        base_params = dict(symbol=symbol, start_time=start_time, end_time=end_time)

        scope = self._resolve_scope(parsed_end_time)

        endpoint_map = {
            key: f"{self.base_url}/marketdata/{path_prefix.format(scope=scope)}/{dataset}"
            for key, dataset in config["datasets"].items()
        }

        result = {}
        parquet_payloads = []
        for key in select:
            data = self._fetch_all_pages(endpoint_map[key], base_params)
            if aggregate_info:
                parquet_payloads.append(data)
            else:
                result[key] = pq.read_table(BytesIO(data)).to_pandas()

        if aggregate_info:
            return pq.read_table(BytesIO(self._combine_parquets(parquet_payloads))).to_pandas()

        return result
