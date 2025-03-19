import time
import traceback
import asyncio
import itertools

from typing import Tuple, Dict
from collections import defaultdict

from seekoptrader.utils import create_exchange


class MonitorBase:
    def __init__(self, market_a, market_b, symbols=None, quote_currency="USDT"):
        self.exchange_a_name, self.type_a, self.subtype_a = self.parse_market(market_a)
        self.exchange_b_name, self.type_b, self.subtype_b = self.parse_market(market_b)

        self.exchange_a = create_exchange(self.exchange_a_name)
        self.exchange_b = create_exchange(self.exchange_b_name)

        if symbols is not None:
            self.symbols = symbols
            self.quote_currency = None
        else:
            self.quote_currency = quote_currency

        self.symbol_map = defaultdict(dict)
        self.pair_data: Dict[Tuple[str, str], dict] = {}
        self.monitor_tasks = []
        self.running = False

        self.latencies = defaultdict(dict)

    async def sync_time(self, exchange):
        while self.running:
            try:
                start_time = time.time() * 1000
                server_time = await exchange.fetch_time()
                end_time = time.time() * 1000

                rtt = end_time - start_time
                latency = rtt / 2
                time_diff = end_time - (server_time + latency)

                self.latencies[exchange.name.lower()] = {
                    "latency": latency,
                    "time_diff": time_diff,
                }
            except Exception as e:
                print(f"Excpetion: {traceback.format_exc()}")
            await asyncio.sleep(10)

    def parse_market(self, market):
        market_params = market.split(".")
        if len(market_params) == 2:
            exchange_name, type_ = market_params
            return exchange_name, type_, None
        elif len(market_params) == 3:
            exchange_name, type_, subtype = market_params
            return exchange_name, type_, subtype
        else:
            raise ValueError(
                "Market parameter must match format as follows:"
                "\t- <exchange>.<type> (e.g. binance.spot)"
                "\t- <exchange>.<type>.<subtype> (e.g. okx.swap.linear)"
            )

    async def load_markets(self):
        await self.exchange_a.load_markets()
        await self.exchange_b.load_markets()

        def format_markets(markets, type_, subtype):
            new_markets = defaultdict(list)
            for m in markets.values():
                if (
                    m["type"] == type_
                    and (subtype is None or m[subtype])
                    and (
                        m["quote"] == self.quote_currency
                        or (
                            self.quote_currency is None
                            and f"{m['base']}-{m['quote']}" in self.symbols
                        )
                    )
                ):
                    new_markets[m["base"], m["quote"]].append(m["symbol"])
            return new_markets

        markets_a = format_markets(self.exchange_a.markets, self.type_a, self.subtype_a)
        markets_b = format_markets(self.exchange_b.markets, self.type_b, self.subtype_b)

        keys = set(markets_a.keys()).intersection(set(markets_b.keys()))
        pairs = [
            {
                "base": base,
                "quote": quote,
                "symbols_a": markets_a[(base, quote)],
                "symbols_b": markets_b[(base, quote)],
            }
            for base, quote in keys
        ]
        self.symbol_map = self._build_symbol_map(pairs)

    def _build_symbol_map(self, pairs):
        symbol_map = defaultdict(dict)
        for pair in pairs:
            for symbol_a, symbol_b in itertools.product(
                pair["symbols_a"], pair["symbols_b"]
            ):
                pair_name = f"{symbol_a}-{symbol_b}"
                if symbol_a not in symbol_map["a"]:
                    symbol_map["a"][symbol_a] = {
                        "index": "a",
                        "pair_names": [pair_name],
                    }
                else:
                    symbol_map["a"][symbol_a]["pair_names"].append(pair_name)
                if symbol_b not in symbol_map["b"]:
                    symbol_map["b"][symbol_b] = {
                        "index": "b",
                        "pair_names": [pair_name],
                    }
                else:
                    symbol_map["b"][symbol_b]["pair_names"].append(pair_name)
        return symbol_map

    async def monitor(self, exchange, index, symbols):
        raise NotImplementedError("Method is not implemented")

    def top(self, n):
        data = list(self.pair_data.values())
        return sorted(data, key=lambda x: x["spread_pct"], reverse=True)[
            : min(n, len(data))
        ]

    def start(self):
        self.running = True

        batch_size = 50
        a_symbols = list(self.symbol_map["a"].keys())
        b_symbols = list(self.symbol_map["b"].keys())
        self.monitor_tasks = [
            asyncio.create_task(self.sync_time(self.exchange_a)),
            asyncio.create_task(self.sync_time(self.exchange_b)),
            *[
                asyncio.create_task(
                    self.monitor(self.exchange_a, "a", a_symbols[i : i + batch_size])
                )
                for i in range(0, len(a_symbols), batch_size)
            ],
            *[
                asyncio.create_task(
                    self.monitor(self.exchange_b, "b", b_symbols[i : i + batch_size])
                )
                for i in range(0, len(b_symbols), batch_size)
            ],
        ]

    async def stop(self):
        """优雅关闭"""
        self.running = False
        for task in self.monitor_tasks:
            task.cancel()
        try:
            await asyncio.gather(*self.monitor_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        await self.exchange_a.close()
        await self.exchange_b.close()
