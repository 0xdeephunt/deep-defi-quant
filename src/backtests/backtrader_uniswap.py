from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import backtrader as bt


class UniswapKlineData(bt.feeds.PandasData):
    params = (
        ("datetime", None),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        ("openinterest", None),
    )


@dataclass
class CostConfig:
    fee_rate: float = 0.0005
    gas_usd: float = 1.5
    slippage_bps: float = 3.0


class CostAwareCommission(bt.CommInfoBase):
    params = (
        ("fee_rate", 0.0005),
        ("gas_usd", 1.5),
        ("slippage_bps", 3.0),
    )

    def getcommission(self, size, price, pseudoexec=False):  # noqa: N802
        """Return commission per unit for a trade.

        Backtrader calls getcommission(size, price, pseudoexec). It expects the
        returned value to be the commission per unit (not total). We compute the
        total cost (fee + slippage + fixed gas) and divide by absolute size.
        """
        notional = abs(size) * price
        fee = notional * float(self.p.fee_rate)
        slippage = notional * (float(self.p.slippage_bps) / 10000.0)
        gas = float(self.p.gas_usd) if size != 0 else 0.0
        total_cost = fee + slippage + gas
        if size == 0:
            return 0.0
        return total_cost / abs(size)


class MeanReversionAlpha(bt.Strategy):
    params = (
        ("lookback", 30),
        ("z_threshold", 1.0),
        ("target_pct", 0.5),
        ("apply_il", True),
        ("il_weight", 1.0),
    )

    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.lookback)
        self.std = bt.indicators.StandardDeviation(self.data.close, period=self.p.lookback)
        self.zscore = (self.data.close - self.sma) / (self.std + 1e-12)
        self.prev_close = None

    def _apply_il(self):
        if not self.p.apply_il:
            return
        if self.prev_close is None:
            self.prev_close = float(self.data.close[0])
            return
        current = float(self.data.close[0])
        if self.position.size == 0 or current <= 0 or self.prev_close <= 0:
            self.prev_close = current
            return

        ratio = current / self.prev_close
        il = (2 * np.sqrt(ratio) / (1 + ratio)) - 1
        if il < 0:
            self.broker.add_cash(self.broker.get_value() * il * self.p.il_weight)
        self.prev_close = current

    def next(self):
        self._apply_il()
        if len(self.data) < self.p.lookback:
            return

        z = self.zscore[0]
        if z > self.p.z_threshold:
            self.order_target_percent(target=-self.p.target_pct)
        elif z < -self.p.z_threshold:
            self.order_target_percent(target=self.p.target_pct)
        else:
            self.order_target_percent(target=0.0)


def run_backtest(
    bars: pd.DataFrame,
    cash: float = 10000.0,
    cost_cfg: Optional[CostConfig] = None,
    strategy_cls=MeanReversionAlpha,
) -> bt.Cerebro:
    if bars is None or bars.empty:
        raise ValueError("Bars dataframe is empty.")

    cerebro = bt.Cerebro()
    data = UniswapKlineData(dataname=bars)
    cerebro.adddata(data)

    cost_cfg = cost_cfg or CostConfig()
    comminfo = CostAwareCommission(
        fee_rate=cost_cfg.fee_rate,
        gas_usd=cost_cfg.gas_usd,
        slippage_bps=cost_cfg.slippage_bps,
    )
    cerebro.broker.addcommissioninfo(comminfo)

    # Ensure strategy lookback does not exceed available data length to avoid
    # indicator "once" initialization IndexError for small samples.
    # Use a conservative default of 30 if data length permits.
    default_lookback = 30
    safe_lookback = max(1, min(default_lookback, len(bars) - 1))
    try:
        cerebro.addstrategy(strategy_cls, lookback=safe_lookback)
    except TypeError:
        # Strategy may not accept lookback kw; fall back to adding without it
        cerebro.addstrategy(strategy_cls)
    cerebro.broker.setcash(cash)
    cerebro.run()
    return cerebro
