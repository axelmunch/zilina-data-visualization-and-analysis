# Dashboard Streamlit — Dockerfile
# ----------------------------------------------------
# Build image:   docker build -t esp32-dashboard .
# Run container: docker run -p 8501:8501 esp32-dashboard
# Optionally mount data: -v $(pwd)/data/sensor_data.csv:/app/data/sensor_data.csv
# ----------------------------------------------------

# 1. Base image (slim Python)
FROM python:3.11-slim

# 3. Workdir
WORKDIR /app

COPY requirements.txt .

# 5. Install Python deps (freeze for reproducibility)
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy code
COPY . frontend/

# 6. Expose default Streamlit port
EXPOSE 8501

# 7. Environment (less verbose logs)
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS="false"

# 8. Launch app
CMD ["streamlit", "run", "frontend/main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
