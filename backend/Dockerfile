# API - Dockerfile
# ----------------------------------------------------
# Build image:   docker build -t esp32-api .
# Run container: docker run -p 5000:5000 esp32-api
# ----------------------------------------------------

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["flask", "--app", "api", "run", "--host=0.0.0.0"]
