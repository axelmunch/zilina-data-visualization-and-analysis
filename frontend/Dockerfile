# Dashboard Streamlit - Dockerfile
# ----------------------------------------------------
# Build image:   docker build -t esp32-dashboard .
# Run container: docker run -p 8501:8501 esp32-dashboard
# Optionally mount data: -v $(pwd)/data/sensor_data.csv:/app/data/sensor_data.csv
# ----------------------------------------------------

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . frontend/

EXPOSE 8501
CMD ["streamlit", "run", "frontend/streamlit_dashboard.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
