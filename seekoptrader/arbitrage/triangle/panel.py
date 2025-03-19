import asyncio
import click

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer, Static

from .monitor import Monitor


class Panel(Static):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def _add_or_update_row(self, table: DataTable, index, row):
        row_key = str(index)
        if index < table.row_count:
            table.update_cell(row_key, self.column_keys[0], index)
            table.update_cell(row_key, self.column_keys[1], row["name"])
            table.update_cell(
                row_key, self.column_keys[2], f"{row['exchange_rate']:4f}"
            )
            table.update_cell(
                row_key, self.column_keys[3], f"{row['exchange_rate_abc']:4f}"
            )
            table.update_cell(
                row_key, self.column_keys[4], f"{row['exchange_rate_acb']:4f}"
            )
            table.update_cell(
                row_key, self.column_keys[5], f"{row['exchange_rate_bac']:4f}"
            )
            table.update_cell(
                row_key, self.column_keys[6], f"{row['exchange_rate_bca']:4f}"
            )
            table.update_cell(
                row_key, self.column_keys[7], f"{row['exchange_rate_cab']:4f}"
            )
            table.update_cell(
                row_key, self.column_keys[8], f"{row['exchange_rate_cba']:4f}"
            )
            table.update_cell(
                row_key,
                self.column_keys[9],
                f"{row['bid_price_a']}/{row['ask_price_a']}",
            )
            table.update_cell(
                row_key,
                self.column_keys[10],
                f"{row['bid_price_b']}/{row['ask_price_b']}",
            )
            table.update_cell(
                row_key,
                self.column_keys[11],
                f"{row['bid_price_c']}/{row['ask_price_c']}",
            )
            table.update_cell(
                row_key,
                self.column_keys[12],
                f"{row['elapsed_time']:2f}ms",
            )
        else:
            table.add_row(
                index,
                row["name"],
                f"{row['exchange_rate']:4f}",
                f"{row['exchange_rate_abc']:4f}",
                f"{row['exchange_rate_acb']:4f}",
                f"{row['exchange_rate_bac']:4f}",
                f"{row['exchange_rate_bca']:4f}",
                f"{row['exchange_rate_cab']:4f}",
                f"{row['exchange_rate_cba']:4f}",
                f"{row['bid_price_a']}/{row['ask_price_a']}",
                f"{row['bid_price_b']}/{row['ask_price_b']}",
                f"{row['bid_price_c']}/{row['ask_price_c']}",
                f"{row['elapsed_time']:2f}ms",
                key=row_key,
            )

    async def load_data(self):
        top_n = self.app.monitor_params["top_n"]
        params = self.app.monitor_params.copy()
        del params["top_n"]

        monitor = Monitor(**params)

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
        except Exception as e:
            print(e)
            pass
        finally:
            await monitor.stop()

    async def on_mount(self):
        self.column_keys = self.query_one(DataTable).add_columns(
            "序号",
            "交易对",
            "汇率",
            "汇率（ABC）",
            "汇率（ACB）",
            "汇率（BAC）",
            "汇率（BCA）",
            "汇率（CAB）",
            "汇率（CBA）",
            "买/卖一价（A）",
            "买/卖一价（B）",
            "买/卖一价（C）",
            "实时",
        )
        asyncio.create_task(self.load_data())
