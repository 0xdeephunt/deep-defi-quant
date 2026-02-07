from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backtrader_uniswap import CostConfig, run_backtest
from subgrounds_klines import SwapQueryConfig, build_klines, fetch_swaps_subgrounds, make_sample_swaps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Uniswap v3 backtest with Backtrader")
    parser.add_argument("--endpoint", type=str, default="", help="Subgraph endpoint URL")
    parser.add_argument("--pool", type=str, default="", help="Uniswap v3 pool address")
    parser.add_argument("--api-key", type=str, default="", help="API key for subgraph endpoint (if required)")
    parser.add_argument("--use-sample", action="store_true", help="Use synthetic swaps")
    parser.add_argument("--freq", type=str, default="1min", choices=["1min", "5min"], help="Bar frequency")
    parser.add_argument("--cash", type=float, default=10000.0)
    parser.add_argument("--fee", type=float, default=0.0005)
    parser.add_argument("--gas", type=float, default=1.5)
    parser.add_argument("--slippage", type=float, default=3.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.use_sample:
        swaps_df = make_sample_swaps()
    else:
        if not args.endpoint or not args.pool:
            raise SystemExit("Provide --endpoint and --pool, or use --use-sample")
        headers = {"Authorization": f"Bearer {args.api_key}"} if args.api_key else None
        cfg = SwapQueryConfig(endpoint=args.endpoint, pool_address=args.pool, headers=headers)
        swaps_df = fetch_swaps_subgrounds(cfg)

    bars = build_klines(swaps_df, args.freq)
    if bars.empty:
        raise SystemExit("No bars produced. Check swaps data.")

    cerebro = run_backtest(
        bars,
        cash=args.cash,
        cost_cfg=CostConfig(fee_rate=args.fee, gas_usd=args.gas, slippage_bps=args.slippage),
    )

    final_value = cerebro.broker.getvalue()
    print(f"Final equity: {final_value:.2f}")

    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    bars.to_parquet(out_dir / f"klines_{args.freq}.parquet")


if __name__ == "__main__":
    main()
