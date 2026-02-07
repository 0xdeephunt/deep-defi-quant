# Backtrader Uniswap v3 Offline Backtest

This module builds 1min/5min OHLCV bars from raw Uniswap v3 swaps (via Subgrounds) and runs a Backtrader-based offline simulation with gas, slippage, and impermanent loss (IL) adjustments.

## Run (offline synthetic sample)

```bash
conda activate defi
python src/backtests/run_backtrader_uniswap.py --use-sample --freq 1min
```

## Run (Subgraph)

```bash
conda activate defi
python src/backtests/run_backtrader_uniswap.py --endpoint https://gateway.thegraph.com/api/subgraphs/id/FQ6JYszEKApsBpAmiHesRsd9Ygc6mzmpNRANeVQFYoVX --pool 0xC6962004f452bE9203591991D15f6b388e09E8D0 --api-key=xxx --freq 5min
```

## Outputs

- `src/backtests/results/klines_1min.parquet`
- `src/backtests/results/klines_5min.parquet`
