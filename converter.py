from dataclasses import dataclass
import overpy
import numpy as np

from rail_types import BoundingBox, Signal
api = overpy.Overpass()

def get_all_rail_objects(bounding_box: BoundingBox):
    query = f'(way["railway"]({bounding_box});node(w););out body;'
    return query_old_api(query)

def get_track_objects(bounding_box: BoundingBox):
    query = f'(way["railway"="rail"]({bounding_box});node(w););out body;'
    return query_old_api(query)

def get_signals_objects(bounding_box: BoundingBox):
    query = f'(way["railway"="signal"]({bounding_box});node(w););out body;'
    return query_old_api(query)

def query_old_api(query):
    result = api.query(query)
    return result

def dist_nodes(n1, n2):
    # Calculate distance between two nodes
    p1 = (n1.lat, n1.lon)
    p2 = (n2.lat, n2.lon)
    return np.linalg.norm(p2-p1)

def make_signal_string(signal, node_before, node_after):
    distance_side = dist_side(node_before, signal)
    distance_node_before = dist_nodes(node_before, signal)
    kind = "andere"
    function = "andere"
    # ToDo extend arnes planpro generator to take dist_side as input, only then pos of signal is unambigous
    signal_str = f"signal signal {node_before.id} {node_after.id} {distance_node_before} {function} {kind}]\n"
    return signal_str


def dist_side(node_before, node_after, signal):
    # Calculate distance from point(signal) to edge between node before and after
    p1 = (node_before.lat, node_before.lon)
    p2 = (node_after.lat, node_after.lon)
    p3 = (signal.lat, signal.lon)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def find_next_rail_node(index, way):
    for i in range(index, len(way.nodes)):
        if 'railway' in way.nodes[i].tags.keys() and way.nodes[i].tags['railway'] == 'rail':
            return way.nodes[i]
    raise Exception("No rail node after signal was found")

def run_converter(x1, y1, x2, y2):
    bounding_box = BoundingBox(x1, y1, x2, y2)
    all_objects = get_all_rail_objects(bounding_box)
    track_objects = get_track_objects(bounding_box)

    result_str = ""

    for node in track_objects.nodes:
        result_str += f"node {node.id} {node.lat} {node.lon} description\n"

    for way in track_objects.ways:
        for idx, el in enumerate(way._node_ids):
            if idx==0:
                continue
            
            result_str += f"edge {way._node_ids[idx-1]} {el}\n"

    for way in all_objects.ways:
        node_before = None
        for idx, node in enumerate(way.nodes):
            if 'railway' in node.tags.keys() and  node.tags['railway'] == 'rail':
                node_before = node
            if 'railway' in node.tags.keys() and  node.tags['railway'] == 'signal':
                node_after = find_next_rail_node(idx, way)
                if not node_before:
                    raise Exception("No rail node before signal was found")
                result_str += make_signal_string(signal=node, node_before=node_before,
                                                 node_after=node_after)

    return result_str
        



    