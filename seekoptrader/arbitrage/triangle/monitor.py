import time
import click
import networkx as nx
import asyncio
import traceback

from collections import defaultdict
from seekoptrader.utils import create_exchange


FIAT_CURRENCIES = [
    "USD",
    "EUR",
    "JPY",
    "GBP",
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "HKD",
    "SGD",
    "KRW",
    "RUB",
    "TRY",
    "MXN",
    "AED",
    "BRL",
    "ZAR",
    "PLN",
    "ARS",
]
STABLE_CURRENCIES = [
    "USDT",
    "USDC",
    "TUSD",
    "BUSD",
    "DAI",
    "EURI",
    "FDUSD",
    "USDE",
]


class Monitor:
    def __init__(self, exchange_name):
        self.symbol_map = defaultdict(list)
        self.triangles = {}
        self.triangle_data = {}

        self.exchange = create_exchange(exchange_name)
        self.monitor_tasks = []
        self.server_timediff = 0

    def valid_currencies(self, currencies):
        return (
            len(set(currencies) & set(STABLE_CURRENCIES)) <= 1
            and len(set(currencies).intersection(FIAT_CURRENCIES)) == 0
        )

    def find_triangles(self, markets):
        G = nx.DiGraph()
        for m in markets:
            base, quote, symbol = m["base"], m["quote"], m["symbol"]
            G.add_edge(base, quote, symbol=symbol)

        triangles = {}
        currencies = G.nodes()
        for b in currencies:
            for a in G[b]:
                for c in currencies:
                    if c == b or c == a:
                        continue
                    if c in G and b in G[c]:
                        if a in G[c]:
                            if self.valid_currencies([b, a, c]):
                                triangles[f"{a}-{b}-{c}"] = (
                                    G[b][a]["symbol"],
                                    G[c][b]["symbol"],
                                    G[c][a]["symbol"],
                                )
        return triangles

    def init_data(self, triangles):
        for name, triangle in triangles.items():
            self.symbol_map[triangle[0]].append({"name": name, "index": "a"})
            self.symbol_map[triangle[1]].append({"name": name, "index": "b"})
            self.symbol_map[triangle[2]].append({"name": name, "index": "c"})
            self.triangle_data[name] = {
                "name": name,
                "exchange_rate": 0,
                "exchange_rate_abc": 0,
                "exchange_rate_acb": 0,
                "exchange_rate_bac": 0,
                "exchange_rate_bca": 0,
                "exchange_rate_cba": 0,
                "exchange_rate_cab": 0,
                "bid_price_a": 0,
                "ask_price_a": 0,
                "bid_price_b": 0,
                "ask_price_b": 0,
                "bid_price_c": 0,
                "ask_price_c": 0,
                "elapsed_time": 0,
            }

    async def load_markets(self):
        markets = await self.exchange.load_markets()
        markets = [m for m in markets.values() if m["spot"] and m["active"]]
        triangles = self.find_triangles(markets)
        self.init_data(triangles)

    async def sync_time(self):
        while self.running:
            try:
                start_time = time.time() * 1000
                server_time = await self.exchange.fetch_time()
                end_time = time.time() * 1000

                rtt = end_time - start_time
                latency = rtt / 2

                self.server_timediff = end_time - (server_time + latency)
            except Exception:
                print(f"Excpetion: {traceback.format_exc()}")
            await asyncio.sleep(10)

    async def watch(self, symbols):
        while self.is_running:
            try:
                order_book = await self.exchange.watch_order_book_for_symbols(symbols)
                self.process_order_book(order_book)
            except Exception as e:
                print("异常：", e)
                await asyncio.sleep(5)

    def process_order_book(self, order_book):
        symbol = order_book["symbol"]
        triangle_infos = self.symbol_map[symbol]
        for info in triangle_infos:
            index, name = info["index"], info["name"]

            self.triangle_data[name][f"ask_price_{index}"] = order_book["asks"][0][0]
            self.triangle_data[name][f"bid_price_{index}"] = order_book["bids"][0][0]

            self.calculate_exchange_rate(name, order_book["timestamp"])

    def calculate_exchange_rate(self, name, timestamp):
        data = self.triangle_data[name]
        if (
            data["ask_price_a"]
            and data["bid_price_a"]
            and data["ask_price_b"]
            and data["bid_price_b"]
            and data["ask_price_c"]
            and data["bid_price_c"]
        ):
            data["exchange_rate_abc"] = (
                1 / data["ask_price_a"] / data["ask_price_b"] * data["bid_price_c"]
            )
            data["exchange_rate_acb"] = (
                1 / data["ask_price_c"] * data["bid_price_b"] * data["bid_price_a"]
            )
            data["exchange_rate_bca"] = (
                1 / data["ask_price_b"] * data["bid_price_c"] / data["ask_price_a"]
            )
            data["exchange_rate_bac"] = (
                1 * data["bid_price_a"] / data["ask_price_c"] * data["bid_price_b"]
            )
            data["exchange_rate_cab"] = (
                1 * data["bid_price_c"] / data["ask_price_a"] / data["ask_price_b"]
            )
            data["exchange_rate_cba"] = (
                1 * data["bid_price_b"] * data["bid_price_a"] / data["ask_price_c"]
            )

            data["exchange_rate"] = max(
                data["exchange_rate_abc"],
                data["exchange_rate_acb"],
                data["exchange_rate_bca"],
                data["exchange_rate_bac"],
                data["exchange_rate_cab"],
                data["exchange_rate_cba"],
            )
            data["elapsed_time"] = time.time() * 1e3 - (
                timestamp + self.server_timediff
            )

    def top(self, n):
        data = list(self.triangle_data.values())
        return sorted(data, key=lambda x: x["exchange_rate"], reverse=True)[
            : min(n, len(data))
        ]

    def start(self):
        self.is_running = True
        symbols = list(self.symbol_map.keys())

        batch_size = 20
        self.monitor_tasks = [
            asyncio.create_task(self.watch(symbols[i : i + batch_size]))
            for i in range(0, len(symbols), batch_size)
        ]
        self.monitor_tasks.append(asyncio.create_task(self.sync_time()))

    async def stop(self):
        self.running = False
        for task in self.monitor_tasks:
            task.cancel()

        try:
            await asyncio.gather(*self.monitor_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        await self.exchange.close()


async def run_monitor(exchange_name):
    monitor = Monitor(exchange_name=exchange_name)
    await monitor.load_markets()
    try:
        monitor.start()
        while True:
            print(monitor.top(5))
            await asyncio.sleep(1)
    except Exception:
        pass
    finally:
        await monitor.stop()


@click.command()
@click.option("--exchange-name", default="okx", help="Name of the exchange")
def main(exchange_name):
    asyncio.run(run_monitor(exchange_name))


if __name__ == "__main__":
    main()
