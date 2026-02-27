from services.prices import live_price


def fetch_live_price(symbol: str):
    """
    Fetch live price from existing services.prices
    Returns (price, source)
    """
    price, src = live_price(symbol)
    return price, src