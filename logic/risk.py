def risk_ok(trades, max_trades, pnl, max_loss):
    if trades >= max_trades:
        return False, "Max trades reached"
    if pnl <= -max_loss:
        return False, "Max loss reached"
    return True, None
