from flask import Flask, abort, request

app = Flask(__name__)


@app.post("/")
def receive_data():
    data = request.get_json()

    match data:
        case dict():
            print("Dictionary")
        case list():
            print("List")
        case _:
            abort(400)

    return ""
