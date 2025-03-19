# seekoptrader

***特别注意：本项目是作者研究学习中逐步具象的监控工具，还在不断开发完善中，会有不少 bug 和体验不佳的地方。***

***免责声明：本软件仅用于教育目的，不构成任何投资建议！请勿投入您无法承受损失的资金。使用本软件产生的所有交易风险由您自行承担，软件开发者及相关方概不负责。***

SeekOpTrader，一个帮助寻找交易机会的监控工具，当前版本主要集中在加密货币套利机会的监控实现。

当前仅支持三个监控看板：

- 跨市场的 ticker 价差看板；
- 跨市场的 orderbook 价差看板；
- 现货三角套利监控看板；

注：ticker 级别交易价差机会的实际滑点较大，最初实现主要是为了学习目的。

使用案例：

监控 binance 与 okx 现货 ticker 级别的价差机会。

```bash
python seekoptrader/__main__.py spread --panel ticker \
                                       --market-a binance.spot \
                                       --market-b okx.spot
```

![](https://cdn.jsdelivr.net/gh/poloxue/images@seekoptrader/01.jpg)

监控 binance 与 okx 的正向永续 orderbook 级别的价差机会。通过 Orderbook 监控，建议通过 `--symbols` 指定交易对列表，防止监控品种过多，导致过多的延迟。

```bash
python seekoptrader/__main__.py spread --panel orderbook \
                                       --market-a binance.swap.linear \
                                       --market-b okx.swap.linear \
                                       --symbols TRUMP-USDT,XRP-USDT,ADA-USDT,STX-USDT
```

![](https://cdn.jsdelivr.net/gh/poloxue/images@seekoptrader/02.png)

监控同交易所现货和正向交割 orderbook 级别的价差机会，期现的配对数量有限。

```bash
python seekoptrader/__main__.py spread --panel orderbook \
                                       --market-a okx.spot \
                                       --market-b okx.future.linear
```

![](https://cdn.jsdelivr.net/gh/poloxue/images@seekoptrader/03.png)

三角套利机会监控：

```python
python seekoptrader/__main__.py triangle --exchange-name okx \
                                         --topn 20
```

![](https://cdn.jsdelivr.net/gh/poloxue/images@seekoptrader/04.png)

由于 `binance` 现货合约过多，暂不建议在 binance 上使用，后续会逐步优化。
