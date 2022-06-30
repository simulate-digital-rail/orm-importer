from flask import Flask, request

import converter

app = Flask(__name__)

@app.route("/")
def homepage():
    return "<p>Welcome to the ORM - PlanPro Converter</p>"

@app.route("/run")
def run_converter():
    x1 = request.args.get('x1')
    y1 = request.args.get('y1')
    x2 = request.args.get('x2')
    y2 = request.args.get('y2')
    if not x1 or not x2 or not y1 or not y2:
        return 'No location specified', 400
    return converter.run_converter(x1, y1, x2, y2), 200

@app.route("/get_ppxml")
def get_ppxml():
    x1 = request.args.get('x1')
    y1 = request.args.get('y1')
    x2 = request.args.get('x2')
    y2 = request.args.get('y2')
    if not x1 or not x2 or not y1 or not y2:
        return 'No location specified', 400

    return converter.to_ppxml(x1, y1, x2, y2)