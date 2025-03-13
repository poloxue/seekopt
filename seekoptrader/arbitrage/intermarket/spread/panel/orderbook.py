import asyncio
import click

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer, Static

from ..monitor import OrderbookMonitor


class OrderbookPanel(Static):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def _add_or_update_row(self, table: DataTable, index, row):
        row_key = str(index)
        if index < table.row_count:
            table.update_cell(row_key, self.column_keys[0], index)
            table.update_cell(row_key, self.column_keys[1], row["pair_name"])
            table.update_cell(
                row_key, self.column_keys[2], f"{(row['spread_pct'] * 100):4f}%"
            )
            table.update_cell(
                row_key,
                self.column_keys[3],
                f"{(row['buy_a_sell_b_spread_pct'] * 100):4f}%",
            )
            table.update_cell(
                row_key,
                self.column_keys[4],
                f"{(row['buy_b_sell_a_spread_pct'] * 100):4f}%",
            )
            table.update_cell(
                row_key,
                self.column_keys[5],
                f"{row['bid_price_a']}/{row['bid_volume_a']}",
            )
            table.update_cell(
                row_key,
                self.column_keys[6],
                f"{row['ask_price_a']}/{row['ask_volume_a']}",
            )
            table.update_cell(
                row_key,
                self.column_keys[7],
                f"{row['bid_price_b']}/{row['bid_volume_b']}",
            )
            table.update_cell(
                row_key,
                self.column_keys[8],
                f"{row['ask_price_b']}/{row['ask_volume_b']}",
            )
            table.update_cell(
                row_key,
                self.column_keys[9],
                f"{row['elapsed_time_a']:2f}ms/{row['elapsed_time_b']:2f}ms",
            )
        else:
            table.add_row(
                index,
                row["pair_name"],
                f"{row['spread_pct'] * 100:4f}%",
                f"{(row['buy_a_sell_b_spread_pct'] * 100):4f}%",
                f"{(row['buy_b_sell_a_spread_pct'] * 100):4f}%",
                f"{row['bid_price_a']}/{row['bid_volume_a']}",
                f"{row['ask_price_a']}/{row['ask_volume_a']}",
                f"{row['bid_price_b']}/{row['bid_volume_b']}",
                f"{row['ask_price_b']}/{row['ask_volume_b']}",
                f"{row['elapsed_time_a']:2f}ms/{row['elapsed_time_b']:2f}ms",
                key=row_key,
            )

    async def load_data(self):
        top_n = self.app.monitor_params["top_n"]
        params = self.app.monitor_params.copy()
        del params["top_n"]

        monitor = OrderbookMonitor(**params)

        table = self.query_one(DataTable)
        try:
            await monitor.load_markets()
            monitor.start()
            while True:
                await asyncio.sleep(1)
                data = monitor.top(top_n)
                for i, row in enumerate(data):
                    self._add_or_update_row(table, i, row)
                while table.row_count > len(data):
                    table.remove_row(str(table.row_count - 1))
        except BaseException:
            await monitor.stop()

    async def on_mount(self):
        self.column_keys = self.query_one(DataTable).add_columns(
            "序号",
            "交易对",
            "价差",
            "买A卖B",
            "买B卖A",
            "买一价/量（A）",
            "卖一价/量（A）",
            "买一价/量（B）",
            "卖一价/量（B）",
            "实时（A/B）",
        )
        asyncio.create_task(self.load_data())
