from ccxt.pro import Exchange
import click

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

from arbitrage.spread.panel import TickerPanel, OrderbookPanel
from arbitrage.triangle.panel import Panel as TrianglePanel


class MonitorApp(App):
    CSS = """
        #content {
            overflow-x: auto;
            overflow-y: auto;
        }
        """

    def __init__(self, title, monitor_panel, monitor_params):
        self.TITLE = title

        super().__init__()

        self.monitor_panel = monitor_panel
        self.monitor_params = monitor_params

    def create_monitor_panel(self, id):
        if self.monitor_panel == "ticker":
            return TickerPanel(id=id)
        elif self.monitor_panel == "orderbook":
            return OrderbookPanel(id=id)
        elif self.monitor_panel == "triangle":
            return TrianglePanel(id=id)
        else:
            raise ValueError(f"Unsupported panel type: {self.monitor_panel}")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield self.create_monitor_panel(id="content")


@click.group()
def cli():
    pass


@cli.command("triangle")
@click.option(
    "--exchange-name",
    default="okx",
    help="Name of the exchange",
)
@click.option(
    "--topn",
    type=int,
    default=20,
    show_default=True,
    help="Number of top items to monitor",
)
def triangle(exchange_name, topn):
    title = f"三角套利监控: {exchange_name}"
    monitor_parmas = {"exchange_name": exchange_name, "top_n": topn}
    MonitorApp(title, "triangle", monitor_params=monitor_parmas).run()


@cli.command("spread")
@click.option(
    "--panel",
    type=click.Choice(["orderbook", "ticker"], case_sensitive=False),
    default="ticker",
    required=True,
    help="Monitoring panel type (orderbook/ticker)",
)
@click.option(
    "--market-a",
    type=click.STRING,
    default="binance.spot",
    required=True,
    help="Market A structure: exchange.type[.subtype], e.g. binance.spot, okx.future.linear",
)
@click.option(
    "--market-b",
    type=click.STRING,
    default="okx.swap.linear",
    required=True,
    help="Market A structure: exchange.type[.subtype], e.g. binance.spot, okx.future.linear",
)
@click.option(
    "--quote-currency", default="USDT", show_default=True, help="Base quote currency"
)
@click.option(
    "--symbols",
    default=None,
    help="Filter symbols, comma-separated (e.g. BTC-USDT,ETH-USDT)",
)
@click.option(
    "--topn",
    type=int,
    default=20,
    show_default=True,
    help="Number of top items to monitor",
)
def spread(panel, market_a, market_b, quote_currency, symbols, topn):
    symbols = set(symbols.split(",")) if symbols else None
    monitor_params = {
        "market_a": market_a,
        "market_b": market_b,
        "quote_currency": quote_currency,
        "symbols": symbols,
        "top_n": topn,
    }
    title = f"交易监控: A-{market_a} B-{market_b}"
    MonitorApp(title, panel, monitor_params=monitor_params).run()


def main():
    cli()


if __name__ == "__main__":
    main()
