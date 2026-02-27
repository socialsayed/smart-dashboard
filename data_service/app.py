from fastapi import FastAPI
from datetime import datetime
from data_service.cache import TTLCache
from data_service.fetchers.prices import fetch_live_price

app = FastAPI(title="Shared Live Data Service")

price_cache = TTLCache()


@app.get("/price/{symbol}")
def get_price(symbol: str):
    """
    Shared live price endpoint.
    Cached once, served to many users.
    """

    cache_key = f"price:{symbol}"
    cached = price_cache.get(cache_key)

    if cached:
        return cached

    price, src = fetch_live_price(symbol)

    payload = {
        "symbol": symbol,
        "price": price,
        "source": src,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # TTL = 2 seconds (shared live)
    price_cache.set(cache_key, payload, ttl=2)

    return payload