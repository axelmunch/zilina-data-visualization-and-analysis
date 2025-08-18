from api_types import Data
from flask import Flask, abort, request

app = Flask(__name__)


def insert_data(data: Data):
    print(data)


@app.post("/")
def receive_data():
    data = request.get_json()

    match data:
        case dict():
            print("Dictionary")
            insert_data(data)
        case list():
            print("List")
            for e in data:
                insert_data(e)
        case _:
            abort(400)

    return ""
