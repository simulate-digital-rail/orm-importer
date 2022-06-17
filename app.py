from flask import Flask, request
from converter import run_converter

app = Flask(__name__)

@app.route("/")
def homepage():
    return "<p>Welcome to the ORM - PlanPro Converter</p>"

@app.route("/run/")
def run_converter():
    location = request.args.get('location')
    if not location:
        return 'No location specified', 400
    run_converter(location)