import hashlib

def daily_watchlist(stocks, date, size=5):
    seed = f"{date}_{'_'.join(sorted(stocks))}"
    h = hashlib.sha256(seed.encode()).hexdigest()

    picks = []
    for i in range(0, len(h), 2):
        s = stocks[int(h[i:i+2], 16) % len(stocks)]
        if s not in picks:
            picks.append(s)
        if len(picks) == size:
            break

    return picks
