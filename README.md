# ORM-PlanPro-Converter
This converter allows to query Open Railway Maps data and creates a XML File that can be used in PlanPro

## Setup
1. Create a virtual environment with `python3 -m venv .venv` (macOS/Linux) or `py -3 -m venv .venv`
2. Activate the virtual environment with `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate.bat`
3. Run `pip install -r requirements.txt`
4. Run `build_ppg.sh` (macOS/Linux) or `build_ppg.bat` to build the PlanPro Generator JAR

## Running the Flask application
1. Run `flask run`
2. Use this request to query Bhf. Griebnitzsee `localhost:5000/run?x1=52.39503&y1=13.12242&x2=52.3933&y2=13.1421`
3. Use the same format with route `/get_ppxml` to get the result in PlanPro XML format