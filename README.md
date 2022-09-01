# ORM-PlanPro-Converter
This converter allows to query Open Railway Maps data and creates a XML File that can be used in PlanPro

## Setup
1. Create a virtual environment with `python3 -m venv .venv` (macOS/Linux) or `py -3 -m venv .venv`
2. Activate the virtual environment with `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate.bat`
3. Run `pip install -r requirements.txt`

## Running the Flask application
1. Run `python3 app.py`
2. Open the url that is display ("Running on http://...")
3. Select coordinates and run

## Live Version
The main branch is automatically deployed to https://orm-planpro-converter.herokuapp.com/