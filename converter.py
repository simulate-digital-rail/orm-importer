import overpy

def build_query(x1,y1,x2,y2):
    x1,x2 = min(x1,x2), max(x1,x2)
    y1,y2 = min(y1,y2), max(y1,y2)
    query = f'node["railway"]({x1},{y1},{x2},{y2});out;'
    print(query)
    return query

def query_orm(query):
    api = overpy.Overpass()
    result = api.query(query)
    return result

def run_converter(x1, y1, x2, y2):
    orm_objects = query_orm(build_query(x1,y1,x2,y2))
    