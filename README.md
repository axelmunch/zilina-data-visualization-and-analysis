# Web-Based Visualization and Analysis Platform for Multi-Sensor Structural Monitoring Using ESP32

## Developer start

Install [Docker](https://www.docker.com/) and [Python](https://www.python.org/).

(Optional) Create a [Python virtual environment](https://docs.python.org/3/library/venv.html).

### Database

```sh
docker compose up -d influxdb
```

The database will run on port **8086**.

### Frontend application

```sh
pip install -r frontend/requirements.txt

streamlit run frontend/streamlit_dashboard.py
```

The application will run on port **8501**.

### Backend API (no hot reload with Flask)

```sh
pip install -r backend/requirements.txt

flask --app backend/api run
```

The API will run on port **5000**.

## Production start

Install [Docker](https://www.docker.com/).

```sh
docker compose up -d --build
```
