# deep-defi-quant

## Create DeFi Conda

```shell
conda create -c conda-forge -n defi python=3.12
conda activate defi
conda install -y -c conda-forge pandas numpy requests web3 pyarrow matplotlib seaborn plotly python-dotenv gql[requests] tqdm requests-toolbelt

pip install "subgrounds[all]" backtrader
```
