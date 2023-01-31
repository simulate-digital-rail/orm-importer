# orm-importer
This importer uses railway data from OpenStreetMap (visible e.g. on https://openrailwaymap.org) to create a corresponding topology with [yaramo](https://github.com/simulate-digital-rail/yaramo) objects.

## Setup
1. Create a virtual environment with `python3 -m venv .venv` (macOS/Linux) or `py -3 -m venv .venv`
2. Activate the virtual environment with `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate.bat`
3. Run `poetry install`

## Usage
```` python
from orm_importer.importer import ORMImporter

# any number of points (each being a pair of coordinates separated by a space) representing a polygon
polygon = ""  
topology = ORMImporter().run(polygon)
````
Examples for how to use the orm-importer can be found in the [demo](https://github.com/simulate-digital-rail/demo) repository.
