import time
import asyncio

from .base import MonitorBase


class TickerMonitor(MonitorBase):
    async def monitor(self, exchange, index: str, symbols):
        """
        统一监控方法
        :param exchange: 交易所实例
        :param index: 来源索引 ('a'或'b')
        """
        exchange_name = exchange.name.lower()
        while self.running:
            try:
                tickers = await exchange.watch_tickers(symbols)
                for symbol, ticker in tickers.items():
                    await self.process_ticker(
                        symbol,
                        ticker,
                        index,
                        self.latencies[exchange_name].get("time_diff", 0),
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Excpetion({index}): {str(e)}")
                await asyncio.sleep(5)

    async def process_ticker(self, symbol, ticker, index, time_diff):
        if symbol not in self.symbol_map[index]:
            return

        pair_map = self.symbol_map[index][symbol]
        pair_names = pair_map["pair_names"]
        for pair_name in pair_names:
            if pair_name not in self.pair_data:
                self.pair_data[pair_name] = {
                    "pair_name": pair_name,
                    "spread": 0,
                    "spread_pct": 0,
                    "price_a": 0,
                    "price_b": 0,
                    "elapsed_time_a": 0,
                    "elapsed_time_b": 0,
                }
            self.pair_data[pair_name][f"price_{index}"] = ticker["last"]
            self.pair_data[pair_name][f"elapsed_time_{index}"] = time.time() * 1e3 - (
                ticker["timestamp"] + time_diff
            )

            await self.calculate_spread(pair_name)

    async def calculate_spread(self, pair_key):
        data = self.pair_data[pair_key]
        try:
            if data["price_a"] and data["price_b"]:
                min_price = min(data["price_a"], data["price_b"])
                spread = abs(data["price_a"] - data["price_b"])
                spread_pct = spread / min_price
                data["spread"] = spread
                data["spread_pct"] = spread_pct
        except (TypeError, ZeroDivisionError) as e:
            print(f"Calculate spread error for {pair_key}: {str(e)}")
