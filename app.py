from flask import Flask, request, render_template, url_for

from converter import ORMConverter

app = Flask(__name__)

@app.route("/")
def homepage():
    return render_template('index.html', css_file=url_for('static', filename='pico.min.css'))
    return "<p>Welcome to the ORM - PlanPro Converter</p>"

@app.route("/run")
def run_converter():
    x1 = request.args.get('x1')
    y1 = request.args.get('y1')
    x2 = request.args.get('x2')
    y2 = request.args.get('y2')
    if not x1 or not x2 or not y1 or not y2:
        return 'No location specified', 400
    conv = ORMConverter()
    return conv.run(x1, y1, x2, y2), 200