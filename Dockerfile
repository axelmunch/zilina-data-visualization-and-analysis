# Dashboard Streamlit — Dockerfile
# ----------------------------------------------------
# Build image:   docker build -t esp32-dashboard .
# Run container: docker run -p 8501:8501 esp32-dashboard
# Optionally mount data: -v $(pwd)/sensor_data.csv:/app/sensor_data.csv
# ----------------------------------------------------

# 1. Base image (slim Python)
FROM python:3.11-slim AS base

# 2. Install system deps (gcc, libpq for psycopg2)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 3. Workdir
WORKDIR /app

# 4. Copy code
COPY streamlit_dashboard.py /app/

# 5. Install Python deps (freeze for reproducibility)
RUN pip install --no-cache-dir \
    streamlit==1.35.0 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    plotly==5.22.0 \
    influxdb-client==1.42.0 \
    psycopg2-binary==2.9.9


# 6. Expose default Streamlit port
EXPOSE 8501

# 7. Environment (less verbose logs)
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS="false"

# 8. Launch app
CMD ["streamlit", "run", "streamlit_dashboard.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
