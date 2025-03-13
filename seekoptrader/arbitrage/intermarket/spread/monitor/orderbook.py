import time
import traceback
import asyncio
import ccxt.pro as ccxtpro

from seekoptrader.arbitrage.intermarket.spread.monitor.base import MonitorBase


class OrderbookMonitor(MonitorBase):
    support_depths = {
        "binance": [5],
        "bybit": [1, 50],
        "okx": [1, 50],
    }

    async def monitor(self, exchange: ccxtpro.Exchange, index: str, symbols):
        """
        统一监控方法
        :param exchange: 交易所实例
        :param index: 来源索引 ('a'或'b')
        """
        exchange_name = exchange.name.lower()
        limit = self.support_depths.get(exchange_name, [None])[0]
        while self.running:
            try:
                order_book = await exchange.watch_order_book_for_symbols(
                    symbols, limit=limit
                )
                await self.process_order_book(
                    order_book, index, self.latencies[exchange_name].get("time_diff", 0)
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Excpetion({index}): {traceback.format_exc()}")
                await asyncio.sleep(5)

    async def process_order_book(self, order_book, index, time_diff):
        symbol = order_book["symbol"]
        if symbol not in self.symbol_map[index]:
            return

        pair_map = self.symbol_map[index][symbol]
        pair_names = pair_map["pair_names"]
        for pair_name in pair_names:
            if pair_name not in self.pair_data:
                self.pair_data[pair_name] = {
                    "pair_name": pair_name,
                    "spread_pct": 0,
                    "buy_a_sell_b_spread_pct": 0,
                    "buy_b_sell_a_spread_pct": 0,
                    "bid_price_a": 0,
                    "bid_volume_a": 0,
                    "ask_price_a": 0,
                    "ask_volume_a": 0,
                    "bid_price_b": 0,
                    "bid_volume_b": 0,
                    "ask_price_b": 0,
                    "ask_volume_b": 0,
                    "elapsed_time_a": 0,
                    "elapsed_time_b": 0,
                }

            if len(order_book["bids"]):
                self.pair_data[pair_name][f"bid_price_{index}"] = order_book["bids"][0][
                    0
                ]
                self.pair_data[pair_name][f"bid_volume_{index}"] = order_book["bids"][
                    0
                ][1]

            if len(order_book["asks"]):
                self.pair_data[pair_name][f"ask_price_{index}"] = order_book["asks"][0][
                    0
                ]
                self.pair_data[pair_name][f"ask_volume_{index}"] = order_book["asks"][
                    0
                ][1]

            self.pair_data[pair_name][f"elapsed_time_{index}"] = time.time() * 1e3 - (
                order_book["timestamp"] + time_diff
            )
            await self.calculate_spread(pair_name)

    async def calculate_spread(self, pair_name):
        data = self.pair_data[pair_name]
        try:
            if (
                data["ask_price_a"]
                and data["bid_price_a"]
                and data["ask_price_b"]
                and data["bid_price_b"]
            ):
                data["buy_b_sell_a_spread"] = data["bid_price_a"] - data["ask_price_b"]
                data["buy_b_sell_a_spread_pct"] = (
                    data["buy_b_sell_a_spread"] / data["ask_price_b"]
                )
                data["buy_a_sell_b_spread"] = data["bid_price_b"] - data["ask_price_a"]
                data["buy_a_sell_b_spread_pct"] = (
                    data["buy_a_sell_b_spread"] / data["ask_price_a"]
                )
                data["spread_pct"] = max(
                    data["buy_b_sell_a_spread_pct"], data["buy_a_sell_b_spread_pct"]
                )
        except (TypeError, ZeroDivisionError) as e:
            print(f"Calculate spread error for {pair_name}: {str(e)}")


async def run_monitor(market_a, market_b, symbols=None):
    monitor = OrderbookMonitor(market_a, market_b, symbols=symbols)

    try:
        await monitor.load_markets()
        monitor.start()
        while True:
            print(monitor.top(5))
            await asyncio.sleep(10)
    except BaseException as e:
        print(f"监控已停止: {e}")
        await monitor.stop()


if __name__ == "__main__":
    try:
        asyncio.run(
            run_monitor("binance.swap.inverse", "okx.swap.inverse", symbols=["BTC-USD"])
        )
    except KeyboardInterrupt:
        print("程序已终止")
