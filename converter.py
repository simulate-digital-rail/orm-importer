import overpy

def build_query(location):
    return location

def query_orm(location):
    query = build_query(location)
    api = overpy.Overpass()
    result = api.query(query)
    return result

def run_converter(location):
    orm_objects = query_orm(location)
    