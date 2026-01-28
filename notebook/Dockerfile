# Use an official Python runtime as a parent image
FROM python:3.12.9-slim-bookworm

# Set environment variables
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
# Add /app to PATH
ENV PATH="/app:${PATH}"
# Enable Jupyter Lab by default
ENV JUPYTER_ENABLE_LAB=yes

# Set the working directory in the container
WORKDIR /app

# Install dependencies
# Upgrade pip first, then install packages in a single layer to reduce image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir jupyterlab ipywidgets

RUN pip install --no-cache-dir pandas
RUN pip install --no-cache-dir numpy
RUN pip install --no-cache-dir requests
RUN pip install --no-cache-dir web3
RUN pip install --no-cache-dir pyarrow
RUN pip install --no-cache-dir matplotlib
RUN pip install --no-cache-dir seaborn
RUN pip install --no-cache-dir plotly
RUN pip install --no-cache-dir python-dotenv
RUN pip install --no-cache-dir gql[requests]
RUN pip install --no-cache-dir tqdm

COPY env/key.env /app/.env

# Make port available to the world outside this container
EXPOSE 8888

# Run Jupyter Lab when the container launches
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--allow-root", "--no-browser", "--NotebookApp.token=''"]