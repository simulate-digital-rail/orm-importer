from dataclasses import dataclass
import overpy

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __repr__(self):
        x1,x2 = min(self.x1,self.x2), max(self.x1,self.x2)
        y1,y2 = min(self.y1,self.y2), max(self.y1,self.y2)
        return f'{x1},{y1},{x2},{y2}'

def get_track_objects(bounding_box: BoundingBox):
    query = f'(way["railway"="rail"]({bounding_box});node(w););out body;'
    return query_orm(query)

def get_signal_objects(bounding_box: BoundingBox):
    query = f'(node["railway"="signal"]({bounding_box}););out;'
    return query_orm(query)

def query_orm(query):
    api = overpy.Overpass()
    result = api.query(query)
    return result

def run_converter(x1, y1, x2, y2):
    bounding_box = BoundingBox(x1, y1, x2, y2)
    track_objects = get_track_objects(bounding_box)
    signal_objects = get_signal_objects(bounding_box)

    result_str = ""

    for node in track_objects.nodes:
        result_str += f"node {node.id} {node.lat} {node.lon} description\n"

    for way in track_objects.ways:
        for idx, el in enumerate(way._node_ids):
            if idx==0:
                continue
            
            result_str += f"edge {way._node_ids[idx-1]} {el}\n"
        first_node = way._node_ids[0]

    return result_str
        



    