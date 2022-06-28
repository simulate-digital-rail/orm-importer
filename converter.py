import overpy

def build_query(x1,y1,x2,y2):
    x1,x2 = min(x1,x2), max(x1,x2)
    y1,y2 = min(y1,y2), max(y1,y2)
    query = f'(way["railway"="rail"]({x1},{y1},{x2},{y2});node(w););out body;'
    print(query)
    return query

def query_orm(query):
    api = overpy.Overpass()
    result = api.query(query)
    return result

def run_converter(x1, y1, x2, y2):
    orm_objects = query_orm(build_query(x1,y1,x2,y2))
    
    result_str = ""

    for node in orm_objects.nodes:
        result_str += f"node {node.id} {node.lat} {node.lon} description\n"

    for way in orm_objects.ways:
        for idx, el in enumerate(way._node_ids):
            if idx==0:
                continue
            
            result_str += f"edge {way._node_ids[idx-1]} {el}\n"
        first_node = way._node_ids[0]

    return result_str
        



    