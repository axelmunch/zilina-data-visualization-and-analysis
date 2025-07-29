FROM python:3.12-slim

WORKDIR /app
COPY data_gen.py /app/

RUN pip install influxdb-client

CMD ["python", "data_gen.py"]
