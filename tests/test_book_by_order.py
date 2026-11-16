import unittest

import pandas as pd



from btgsolutions_dataservices import BookByOrder
from btgsolutions_dataservices.book_by_order import (
    BID,
    OFFER,
    NEW,
    CHANGE,
    DELETE,
    DELETE_THRU,
    MBO,
    MBP,
    TMPL_SNAPSHOT_ORDERS,
    TMPL_ORDER,
    TMPL_DELETE_ORDER,
    TMPL_MASS_DELETE,
    TMPL_EMPTY_BOOK,
    TMPL_TRADE,
)


def _events_df(rows):
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
    df = pd.DataFrame(rows, columns=columns)
    df["buyer"] = None
    df["seller"] = None
    return df


def _events_with_trades_df(rows):
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
    return pd.DataFrame(rows, columns=columns)


class BookByOrderTests(unittest.TestCase):
    def test_new_change_and_delete(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, OFFER, NEW, 2, 10.5, 50),
                (3, 1, TMPL_ORDER, BID, CHANGE, 1, 10.0, 80),
                (4, 1, TMPL_DELETE_ORDER, BID, DELETE, 2, None, None),
            ]
        )

        book = BookByOrder("TEST3")
        book.replay(events)

        self.assertEqual(len(book), 1)
        self.assertEqual(book.top_of_book(), {
            "best_bid": (1, 10.0, 80, None),
            "best_offer": None,
        })

    def test_no_order_is_simultaneously_bid_and_offer(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, OFFER, NEW, 2, 10.5, 50),
            ]
        )

        book = BookByOrder("TEST3").replay(events)

        bid_ids = {oid for oid, o in book.orders.items() if o[0] == BID}
        offer_ids = {oid for oid, o in book.orders.items() if o[0] == OFFER}
        self.assertEqual(bid_ids & offer_ids, set())

    def test_mass_delete_clears_only_one_side(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, BID, NEW, 2, 9.5, 100),
                (3, 1, TMPL_ORDER, OFFER, NEW, 3, 10.5, 50),
                (4, 1, TMPL_MASS_DELETE, BID, DELETE_THRU, None, None, None),
            ]
        )

        book = BookByOrder("TEST3").replay(events)

        self.assertEqual(book.side_orders(BID), [])
        self.assertEqual(len(book.side_orders(OFFER)), 1)

    def test_empty_book_resets_both_sides(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, OFFER, NEW, 2, 10.5, 50),
                (3, 1, TMPL_EMPTY_BOOK, None, None, None, None, None),
            ]
        )

        book = BookByOrder("TEST3").replay(events)

        self.assertEqual(len(book), 0)

    def test_snapshot_bootstraps_regardless_of_update_action(self):
        events = _events_df(
            [
                (1, 1, TMPL_SNAPSHOT_ORDERS, BID, None, 1, 10.0, 100),
                (1, 2, TMPL_SNAPSHOT_ORDERS, OFFER, None, 2, 10.5, 50),
            ]
        )

        book = BookByOrder("TEST3").replay(events)

        self.assertEqual(len(book), 2)

    def test_delete_action_other_than_new_or_change_is_skipped(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, DELETE, 1, 10.0, 100),
            ]
        )

        book = BookByOrder("TEST3").replay(events)

        self.assertEqual(len(book), 0)
        self.assertEqual(book.events_skipped, 1)

    def test_depth_by_price_aggregates_same_price_level(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, BID, NEW, 2, 10.0, 50),
                (3, 1, TMPL_ORDER, BID, NEW, 3, 9.5, 30),
            ]
        )

        book = BookByOrder("TEST3").replay(events)

        self.assertEqual(book.depth_by_price(BID, n_levels=5), [(10.0, 150), (9.5, 30)])

    def test_replay_stream_matches_replay_across_chunk_boundaries(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, BID, NEW, 2, 9.5, 50),
                (3, 1, TMPL_ORDER, OFFER, NEW, 3, 10.5, 30),
                (4, 1, TMPL_ORDER, BID, CHANGE, 1, 10.0, 80),
                (5, 1, TMPL_DELETE_ORDER, OFFER, DELETE, 3, None, None),
            ]
        )

        # split into chunks of 2 rows, as iter_data(batch_size=2) would yield
        chunks = [events.iloc[i : i + 2] for i in range(0, len(events), 2)]

        book_full = BookByOrder("TEST3").replay(events)
        book_streamed = BookByOrder("TEST3").replay_stream(iter(chunks))

        self.assertEqual(len(book_streamed), len(book_full))
        self.assertEqual(book_streamed.top_of_book(), book_full.top_of_book())
        self.assertEqual(book_streamed.last_seq_num, book_full.last_seq_num)

    def test_replay_classified_mbo_view_yields_one_book_entry_per_book_row(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, OFFER, NEW, 2, 10.5, 50),
            ]
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events], view=MBO, n_levels=5))

        self.assertEqual([kind for kind, _ in results], ["book", "book"])
        self.assertEqual(
            results[0][1],
            {
                "bid": [(1, 10.0, 100, None)],
                "offer": [],
                "order": {
                    "order_id": 1, "side": BID, "price": 10.0, "size": 100, "broker": None,
                    "event_type": "order", "action": "NEW",
                    "seq_num": 1, "rpt_seq": 1, "timestamp": None,
                },
            },
        )
        self.assertEqual(
            results[1][1],
            {
                "bid": [(1, 10.0, 100, None)],
                "offer": [(2, 10.5, 50, None)],
                "order": {
                    "order_id": 2, "side": OFFER, "price": 10.5, "size": 50, "broker": None,
                    "event_type": "order", "action": "NEW",
                    "seq_num": 2, "rpt_seq": 1, "timestamp": None,
                },
            },
        )

    def test_replay_classified_mbp_view_aggregates_by_price(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, BID, NEW, 2, 10.0, 50),
            ]
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events], view=MBP, n_levels=5))

        kind, info = results[-1]
        self.assertEqual(
            (kind, info),
            (
                "book",
                {
                    "bid": [(10.0, 150)],
                    "offer": [],
                    "order": {
                        "order_id": 2, "side": BID, "price": 10.0, "size": 50, "broker": None,
                        "event_type": "order", "action": "NEW",
                        "seq_num": 2, "rpt_seq": 1, "timestamp": None,
                    },
                },
            ),
        )

    def test_replay_classified_classifies_trade_rows_without_mutating_book(self):
        events = _events_with_trades_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100, None, None, None, None, None),
                (2, 1, TMPL_TRADE, None, 0, None, None, None, 999, 10.2, 30, 11, 22),
            ]
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events]))

        self.assertEqual(results[0][0], "book")
        kind, info = results[1]
        self.assertEqual(kind, "trade")
        self.assertEqual(
            info,
            {
                "side": None,
                "trade_id": 999,
                "price": 10.2,
                "size": 30,
                "buyer": 11,
                "seller": 22,
                "event_type": "trade",
                "action": "NEW",
                "seq_num": 2,
                "rpt_seq": 1,
                "timestamp": None,
            },
        )
        # trade row must not have touched the book state
        self.assertEqual(len(book), 1)

    def test_replay_classified_timestamp_is_none_without_md_entry_datetime(self):
        columns = [
            "seq_num",
            "rpt_seq",
            "tmpl_id",
            "md_entry_type",
            "md_update_action",
            "secondary_order_id",
            "md_entry_px",
            "md_entry_size",
            "md_entry_datetime",
            "sending_time",
        ]
        events = pd.DataFrame(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100, pd.NaT, pd.Timestamp("2026-05-15 10:00:00")),
                (2, 1, TMPL_ORDER, BID, NEW, 2, 9.5, 50, pd.Timestamp("2026-05-15 10:00:01.123"), pd.Timestamp("2026-05-15 10:00:01")),
            ],
            columns=columns,
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events]))

        self.assertIsNone(results[0][1]["order"]["timestamp"])
        self.assertEqual(
            results[1][1]["order"]["timestamp"], pd.Timestamp("2026-05-15 10:00:01.123")
        )

    def test_replay_classified_drops_execution_summary_rows(self):
        events = _events_df([(1, 1, 55, BID, 0, None, None, None)])

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events]))

        self.assertEqual(results, [])
        self.assertEqual(book.events_skipped, 1)

    def test_replay_classified_event_type_and_action_per_tmpl_id(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_ORDER, BID, CHANGE, 1, 10.0, 80),
                (3, 1, TMPL_DELETE_ORDER, BID, DELETE, 1, None, None),
                (4, 1, TMPL_MASS_DELETE, OFFER, DELETE_THRU, None, None, None),
                (5, 1, TMPL_EMPTY_BOOK, None, None, None, None, None),
                (6, 1, TMPL_SNAPSHOT_ORDERS, BID, None, 2, 10.0, 100),
            ]
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events]))

        event_types = [info["order"]["event_type"] for _, info in results]
        actions = [info["order"]["action"] for _, info in results]

        self.assertEqual(
            event_types,
            ["order", "order", "delete_order", "mass_delete", "empty_book", "snapshot"],
        )
        self.assertEqual(actions, ["NEW", "CHANGE", "DELETE", "DELETE_THRU", None, None])

    def test_mbo_view_carries_broker_from_buyer_or_seller(self):
        events = _events_with_trades_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100, None, None, None, 11, None),
                (2, 1, TMPL_ORDER, OFFER, NEW, 2, 10.5, 50, None, None, None, None, 22),
            ]
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events], view=MBO, n_levels=5))

        self.assertEqual(
            results[1][1],
            {
                "bid": [(1, 10.0, 100, 11)],
                "offer": [(2, 10.5, 50, 22)],
                "order": {
                    "order_id": 2, "side": OFFER, "price": 10.5, "size": 50, "broker": 22,
                    "event_type": "order", "action": "NEW",
                    "seq_num": 2, "rpt_seq": 1, "timestamp": None,
                },
            },
        )

    def test_mbp_view_has_no_broker(self):
        events = _events_with_trades_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100, None, None, None, 11, None),
            ]
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events], view=MBP, n_levels=5))

        self.assertEqual(
            results[0][1],
            {
                "bid": [(10.0, 100)],
                "offer": [],
                "order": {
                    "order_id": 1, "side": BID, "price": 10.0, "size": 100, "broker": 11,
                    "event_type": "order", "action": "NEW",
                    "seq_num": 1, "rpt_seq": 1, "timestamp": None,
                },
            },
        )

    def test_order_info_is_partial_for_mass_delete_and_empty_book(self):
        events = _events_df(
            [
                (1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100),
                (2, 1, TMPL_DELETE_ORDER, BID, DELETE, 1, None, None),
                (3, 1, TMPL_MASS_DELETE, OFFER, DELETE_THRU, None, None, None),
                (4, 1, TMPL_EMPTY_BOOK, None, None, None, None, None),
            ]
        )

        book = BookByOrder("TEST3")
        results = list(book.replay_classified([events]))

        orders = [info["order"] for _, info in results]
        self.assertEqual(
            orders,
            [
                {
                    "order_id": 1, "side": BID, "price": 10.0, "size": 100, "broker": None,
                    "event_type": "order", "action": "NEW",
                    "seq_num": 1, "rpt_seq": 1, "timestamp": None,
                },
                {
                    "order_id": 1, "side": BID, "price": None, "size": None, "broker": None,
                    "event_type": "delete_order", "action": "DELETE",
                    "seq_num": 2, "rpt_seq": 1, "timestamp": None,
                },
                {
                    "order_id": None, "side": OFFER, "price": None, "size": None, "broker": None,
                    "event_type": "mass_delete", "action": "DELETE_THRU",
                    "seq_num": 3, "rpt_seq": 1, "timestamp": None,
                },
                {
                    "order_id": None, "side": None, "price": None, "size": None, "broker": None,
                    "event_type": "empty_book", "action": None,
                    "seq_num": 4, "rpt_seq": 1, "timestamp": None,
                },
            ],
        )

    def test_replay_classified_invalid_view_raises(self):
        events = _events_df([(1, 1, TMPL_ORDER, BID, NEW, 1, 10.0, 100)])

        book = BookByOrder("TEST3")
        with self.assertRaisesRegex(ValueError, "Invalid 'view'"):
            list(book.replay_classified([events], view="bogus"))

if __name__ == "__main__":
    unittest.main()
