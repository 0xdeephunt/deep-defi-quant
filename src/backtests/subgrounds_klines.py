from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional
import requests

import numpy as np
import pandas as pd

try:
    from subgrounds import Subgrounds
except ImportError as exc:  # pragma: no cover - handled in runtime
    raise ImportError("subgrounds is required. Install with `pip install subgrounds`.") from exc


@dataclass
class SwapQueryConfig:
    endpoint: str
    pool_address: str
    page_size: int = 1000
    max_pages: int = 5
    order_direction: str = "desc"
    headers: Optional[Dict[str, str]] = None


def fetch_swaps_subgrounds(cfg: SwapQueryConfig) -> pd.DataFrame:
    """Fetch swaps from a Uniswap v3 subgraph using Subgrounds.

    Returns a dataframe with swap fields and a `datetime` column.
    """
    # If headers are provided (e.g. API key / Authorization), use requests
    # to query the Graph endpoint directly since some Subgrounds versions
    # do not expose a headers parameter for load_subgraph.
    if cfg.headers:
        query = """
        query($pool: String!, $first: Int!, $skip: Int!) {
          swaps(
            first: $first,
            skip: $skip,
            orderBy: timestamp,
            orderDirection: desc,
            where: { pool: $pool }
          ) {
            id
            timestamp
            amountIn
            amountOut
            amountInUSD
            amountOutUSD
            tick
            tokenIn { id symbol }
            tokenOut { id symbol }
            hash
            gasLimit
            gasUsed
            gasPrice
          }
        }
        """

        swaps_all = []
        headers = cfg.headers or {}
        for page in range(cfg.max_pages):
            variables = {"pool": cfg.pool_address.lower(), "first": cfg.page_size, "skip": page * cfg.page_size}
            resp = requests.post(cfg.endpoint, json={"query": query, "variables": variables}, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                raise RuntimeError(f"GraphQL errors: {data['errors']}")
            rows = data.get("data", {}).get("swaps", [])
            if not rows:
                break
            swaps_all.append(pd.DataFrame(rows))
    else:
        sg = Subgrounds()
        subgraph = sg.load_subgraph(cfg.endpoint)

        swaps_all = []
        for page in range(cfg.max_pages):
            swaps = subgraph.Query.swaps(
                first=cfg.page_size,
                skip=page * cfg.page_size,
                where={"pool": cfg.pool_address.lower()},
                orderBy=subgraph.Swap.timestamp,
                orderDirection=cfg.order_direction,
            )

            df = sg.query_df(
                [
                    swaps.id,
                    swaps.timestamp,
                    swaps.amountIn,
                    swaps.amountOut,
                    swaps.amountInUSD,
                    swaps.amountOutUSD,
                    swaps.tick,
                    swaps.tokenIn.id,
                    swaps.tokenIn.symbol,
                    swaps.tokenOut.id,
                    swaps.tokenOut.symbol,
                    swaps.hash,
                    swaps.gasLimit,
                    swaps.gasUsed,
                    swaps.gasPrice,
                ]
            )
            if df.empty:
                break
            swaps_all.append(df)

    if not swaps_all:
        return pd.DataFrame()

    swaps_df = pd.concat(swaps_all, ignore_index=True)
    swaps_df["timestamp"] = pd.to_numeric(swaps_df["timestamp"], errors="coerce")
    swaps_df["datetime"] = pd.to_datetime(swaps_df["timestamp"], unit="s", utc=True)
    return swaps_df


def build_klines(swaps_df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Aggregate raw swaps into OHLCV bars for a given frequency."""
    if swaps_df is None or swaps_df.empty:
        return pd.DataFrame()

    df = swaps_df.copy()
    if "datetime" not in df.columns:
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)

    df = df.sort_values("datetime").set_index("datetime")

    df["amountIn"] = pd.to_numeric(df.get("amountIn"), errors="coerce")
    df["amountOut"] = pd.to_numeric(df.get("amountOut"), errors="coerce")
    df["amountInUSD"] = pd.to_numeric(df.get("amountInUSD"), errors="coerce")
    df["amountOutUSD"] = pd.to_numeric(df.get("amountOutUSD"), errors="coerce")

    df["price"] = df["amountOut"] / df["amountIn"].replace(0, np.nan)

    ohlc = df["price"].resample(freq).ohlc()
    volume = df["amountOut"].resample(freq).sum().rename("volume")

    volume_usd = df["amountOutUSD"].resample(freq).sum().rename("volume_usd")
    if volume_usd.isna().all():
        volume_usd = df["amountInUSD"].resample(freq).sum().rename("volume_usd")

    bars = pd.concat([ohlc, volume, volume_usd], axis=1).dropna()
    return bars


def make_sample_swaps(n: int = 5000, seed: int = 7) -> pd.DataFrame:
    """Generate synthetic swap-like data for offline testing."""
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="s", tz="UTC")
    amount_in = rng.lognormal(mean=5.0, sigma=0.5, size=n)
    price = rng.lognormal(mean=0.0, sigma=0.02, size=n).cumprod()
    amount_out = amount_in * price
    amount_in_usd = amount_in * rng.uniform(0.95, 1.05, size=n)
    amount_out_usd = amount_out * rng.uniform(0.95, 1.05, size=n)

    return pd.DataFrame(
        {
            "id": [f"swap_{i}" for i in range(n)],
            "timestamp": (timestamps.view("int64") // 10**9).astype(int),
            "datetime": timestamps,
            "amountIn": amount_in,
            "amountOut": amount_out,
            "amountInUSD": amount_in_usd,
            "amountOutUSD": amount_out_usd,
            "tick": rng.integers(-200000, 200000, size=n),
        }
    )
