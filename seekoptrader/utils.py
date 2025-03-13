import os
import ccxt.pro as ccxtpro


params = {
    "enableRateLimit": True,
    "proxies": {
        "http": os.getenv("http_proxy"),
        "https": os.getenv("https_proxy"),
    },
    "aiohttp_proxy": os.getenv("http_proxy"),
    "ws_proxy": os.getenv("http_proxy"),
}


def create_exchange(name):
    return getattr(ccxtpro, name)(params)
