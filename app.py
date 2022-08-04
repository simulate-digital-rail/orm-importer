from flask import Flask, request, render_template, url_for

from converter import ORMConverter

app = Flask(__name__)

@app.route("/")
def homepage():
    return render_template('index.html', css_file=url_for('static', filename='pico.min.css'))
    return "<p>Welcome to the ORM - PlanPro Converter</p>"

@app.route("/run")
def run_converter():
    polygon = request.args.get('polygon')
    if not polygon:
        return 'No location specified', 400
    conv = ORMConverter()
    return conv.run(polygon), 200