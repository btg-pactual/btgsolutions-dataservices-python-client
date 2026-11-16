import unittest
from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq



from btgsolutions_dataservices import TradesAndBookEvents
from btgsolutions_dataservices.config import url_apis_v3
from btgsolutions_dataservices.exceptions import BadResponse
from btgsolutions_dataservices.rest.trades_and_book_events import DEFAULT_BATCH_SIZE


class FakeAuth:
    @property
    def token(self):
        return "fake-token"


def _parquet_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), buffer)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, status_code, content=b"", text=""):
        self.status_code = status_code
        self.text = text
        self.content = content or text.encode()

    def json(self):
        import json

        return json.loads(self.text)

    def iter_content(self, chunk_size):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i : i + chunk_size]


def _events_parquet(rows):
    columns = [
        "seq_num",
        "rpt_seq",
        "tmpl_id",
        "md_entry_type",
        "md_update_action",
        "secondary_order_id",
        "md_entry_px",
        "md_entry_size",
    ]
    return _parquet_bytes(pd.DataFrame(rows, columns=columns))


def _events_parquet_with_broker(rows):
    columns = [
        "seq_num",
        "rpt_seq",
        "tmpl_id",
        "md_entry_type",
        "md_update_action",
        "secondary_order_id",
        "md_entry_px",
        "md_entry_size",
        "buyer",
        "seller",
    ]
    return _parquet_bytes(pd.DataFrame(rows, columns=columns))


def _events_parquet_with_trades(rows):
    columns = [
        "seq_num",
        "rpt_seq",
        "tmpl_id",
        "md_entry_type",
        "md_update_action",
        "secondary_order_id",
        "md_entry_px",
        "md_entry_size",
        "trade_id",
        "last_px",
        "fill_qty",
        "buyer",
        "seller",
    ]
    return _parquet_bytes(pd.DataFrame(rows, columns=columns))


class TradesAndBookEventsTests(unittest.TestCase):
    def make_client(self):
        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.Authenticator",
            return_value=FakeAuth(),
        ):
            return TradesAndBookEvents(api_key="api-key")

    def test_get_book_does_not_expose_a_raw_dataframe_method(self):
        client = self.make_client()
        self.assertFalse(hasattr(client, "get_data"))
        self.assertFalse(hasattr(client, "iter_data"))

    def test_get_book_is_lazy_until_iterated(self):
        client = self.make_client()

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
        ) as request:
            client.get_book(ticker="PETR4", date="2026-05-15")

        request.assert_not_called()

    def test_get_book_uses_expected_endpoint_and_headers(self):
        client = self.make_client()
        content = _events_parquet(
            [
                (1, 1, 50, "BID", 0, 1, 10.0, 100),
                (2, 1, 50, "OFFER", 0, 2, 10.5, 50),
            ]
        )

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ) as request:
            results = list(client.get_book(ticker="PETR4", date="2026-05-15"))

        request.assert_called_once_with(
            "GET",
            f"{url_apis_v3}/marketdata/bulkdata/events",
            headers={"authorization": "authorization fake-token"},
            params={"ticker": "PETR4", "date": "2026-05-15"},
            stream=True,
        )
        self.assertEqual([kind for kind, _ in results], ["book", "book"])
        self.assertEqual(
            results[-1][1],
            {
                "bid": [(1, 10.0, 100, None)],
                "offer": [(2, 10.5, 50, None)],
                "order": {
                    "order_id": 2, "side": "OFFER", "price": 10.5, "size": 50, "broker": None,
                    "event_type": "order", "action": "NEW",
                    "seq_num": 2, "rpt_seq": 1, "timestamp": None,
                },
            },
        )

    def test_get_book_mbo_view_carries_broker_from_buyer_and_seller_columns(self):
        client = self.make_client()
        content = _events_parquet_with_broker(
            [
                (1, 1, 50, "BID", 0, 1, 10.0, 100, 11, None),
                (2, 1, 50, "OFFER", 0, 2, 10.5, 50, None, 22),
            ]
        )

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ):
            results = list(client.get_book(ticker="PETR4", date="2026-05-15"))

        self.assertEqual(
            results[-1][1],
            {
                "bid": [(1, 10.0, 100, 11)],
                "offer": [(2, 10.5, 50, 22)],
                "order": {
                    "order_id": 2, "side": "OFFER", "price": 10.5, "size": 50, "broker": 22,
                    "event_type": "order", "action": "NEW",
                    "seq_num": 2, "rpt_seq": 1, "timestamp": None,
                },
            },
        )

    def test_get_book_mbp_view_with_n_levels(self):
        client = self.make_client()
        content = _events_parquet(
            [
                (1, 1, 50, "BID", 0, 1, 10.0, 100),
                (2, 1, 50, "BID", 0, 2, 9.5, 50),
                (3, 1, 50, "BID", 0, 3, 9.0, 30),
            ]
        )

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ):
            results = list(
                client.get_book(ticker="PETR4", date="2026-05-15", view="mbp", n_levels=2)
            )

        kind, info = results[-1]
        self.assertEqual(
            (kind, info),
            (
                "book",
                {
                    "bid": [(10.0, 100), (9.5, 50)],
                    "offer": [],
                    "order": {
                        "order_id": 3, "side": "BID", "price": 9.0, "size": 30, "broker": None,
                        "event_type": "order", "action": "NEW",
                        "seq_num": 3, "rpt_seq": 1, "timestamp": None,
                    },
                },
            ),
        )

    def test_get_book_streams_in_chunks_of_batch_size(self):
        client = self.make_client()
        content = _events_parquet(
            [(i, 1, 50, "BID", 0, i, 10.0, 100) for i in range(1, 11)]
        )

        observed_chunk_sizes = []
        original = TradesAndBookEvents._iter_batches

        def spy(self, ticker, date, batch_size):
            for chunk in original(self, ticker, date, batch_size):
                observed_chunk_sizes.append(len(chunk))
                yield chunk

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ), patch.object(TradesAndBookEvents, "_iter_batches", spy):
            results = list(
                client.get_book(ticker="PETR4", date="2026-05-15", batch_size=3)
            )

        self.assertEqual(observed_chunk_sizes, [3, 3, 3, 1])
        self.assertEqual(len(results), 10)

    def test_get_book_boundary_seq_num_on_book_rows(self):
        client = self.make_client()
        content = _events_parquet(
            [(i, 1, 50, "BID", 0, i, 10.0, 100) for i in range(1, 6)]
        )

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ):
            until = list(client.get_book(
                ticker="PETR4", date="2026-05-15",
                boundary={"field": "seq_num", "value": 3, "mode": "until"},
            ))
            after = list(client.get_book(
                ticker="PETR4", date="2026-05-15",
                boundary={"field": "seq_num", "value": 3, "mode": "after"},
            ))

        self.assertEqual([info["order"]["seq_num"] for _, info in until], [1, 2, 3])
        self.assertEqual([info["order"]["seq_num"] for _, info in after], [4, 5])

    def test_get_book_boundary_list_is_a_range(self):
        client = self.make_client()
        content = _events_parquet(
            [(i, 1, 50, "BID", 0, i, 10.0, 100) for i in range(1, 6)]
        )

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ):
            results = list(client.get_book(
                ticker="PETR4", date="2026-05-15",
                boundary=[
                    {"field": "seq_num", "value": 1, "mode": "after"},
                    {"field": "seq_num", "value": 4, "mode": "until"},
                ],
            ))

        self.assertEqual([info["order"]["seq_num"] for _, info in results], [2, 3, 4])

    def test_get_book_boundary_list_mixes_different_fields(self):
        client = self.make_client()
        content = _events_parquet(
            [(i, i * 10, 50, "BID", 0, i, 10.0, 100) for i in range(1, 6)]
        )

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ):
            results = list(client.get_book(
                ticker="PETR4", date="2026-05-15",
                boundary=[
                    {"field": "seq_num", "value": 2, "mode": "after"},
                    {"field": "rpt_seq", "value": 40, "mode": "until"},
                ],
            ))

        self.assertEqual([info["order"]["seq_num"] for _, info in results], [3, 4])

    def test_get_book_boundary_seq_num_on_trade_rows(self):
        client = self.make_client()
        content = _events_parquet_with_trades(
            [
                (1, 1, 50, "BID", 0, 1, 10.0, 100, None, None, None, None, None),
                (2, 1, 53, None, 0, None, None, None, 999, 10.2, 30, 11, 22),
            ]
        )

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(200, content=content),
        ):
            results = list(client.get_book(
                ticker="PETR4", date="2026-05-15",
                boundary={"field": "seq_num", "value": 1, "mode": "after"},
            ))

        self.assertEqual([kind for kind, _ in results], ["trade"])
        self.assertEqual(results[0][1]["seq_num"], 2)

    def test_get_book_default_batch_size(self):
        self.assertEqual(DEFAULT_BATCH_SIZE, 10_000)

    def test_bad_response_uses_server_error_details(self):
        client = self.make_client()

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(
                404,
                text='{"ApiClientError": "Not Found.", "SuggestedAction": "Double check your request."}',
            ),
        ):
            with self.assertRaisesRegex(BadResponse, "Not Found"):
                list(client.get_book(ticker="PETR4", date="2026-05-15"))

    def test_bad_response_uses_server_message_when_there_is_no_client_error(self):
        client = self.make_client()

        with patch(
            "btgsolutions_dataservices.rest.trades_and_book_events.requests.request",
            return_value=FakeResponse(
                404,
                text='{"ApiServerMessage": "Not Found", "SuggestedAction": "Double check your request parameters."}',
            ),
        ):
            with self.assertRaisesRegex(BadResponse, "Error 404: Not Found"):
                list(client.get_book(ticker="FNAM11", date="2026-11-13"))


if __name__ == "__main__":
    unittest.main()
