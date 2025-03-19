import asyncio

from textual.app import ComposeResult
from textual.widgets import DataTable, Static

from ..monitor import TickerMonitor


class TickerPanel(Static):
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
            table.update_cell(row_key, self.column_keys[3], str(row["spread"]))
            table.update_cell(row_key, self.column_keys[4], str(row["price_a"]))
            table.update_cell(row_key, self.column_keys[5], str(row["price_b"]))
            table.update_cell(
                row_key, self.column_keys[6], f"{row['elapsed_time_a']:2f}ms"
            )
            table.update_cell(
                row_key, self.column_keys[7], f"{row['elapsed_time_b']:2f}ms"
            )
        else:
            table.add_row(
                index,
                row["pair_name"],
                f"{(row['spread_pct'] * 100):4f}%",
                str(row["spread"]),
                str(row["price_a"]),
                str(row["price_b"]),
                f"{row['elapsed_time_a']:2f}ms",
                f"{row['elapsed_time_b']:2f}ms",
                key=row_key,
            )

    async def load_data(self):
        top_n = self.app.monitor_params["top_n"]
        params = self.app.monitor_params.copy()
        del params["top_n"]

        monitor = TickerMonitor(**params)

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
        except Exception:
            pass
        finally:
            await monitor.stop()

    async def on_mount(self):
        self.column_keys = self.query_one(DataTable).add_columns(
            "序号",
            "交易对",
            "价差（%）",
            "价差",
            "最新价（A）",
            "最新价（B）",
            "实时（A）",
            "实时（B）",
        )

        asyncio.create_task(self.load_data())
