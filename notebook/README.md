# Jupyter Notebook

## Build docker

```shell
cd notebook
docker build -t defi-quant-notebook:latest .
```

### Run docker

```shell
docker run -d -p 8888:8888 -v .:/app/notebook -w /app/notebook --name defi-quant-notebook defi-quant-notebook:latest
```

### Run Jupyter Notebook with your web brower

Open web brower and input: <http://127.0.0.1:8888/lab>