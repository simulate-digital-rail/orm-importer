from dataclasses import dataclass
import overpy
import numpy as np

from rail_types import BoundingBox, Signal
api = overpy.Overpass()

def get_track_objects(bounding_box: BoundingBox):
    query = f'(way["railway"="rail"]({bounding_box});node(w););out body;'
    return query_old_api(query)

def query_old_api(query):
    result = api.query(query)
    return result

def dist_nodes(n1, n2):
    # Calculate distance between two nodes
    p1 = np.array((n1.lat, n1.lon))
    p2 = np.array((n2.lat, n2.lon))
    return np.linalg.norm(p2-p1)

def dist_edge(node_before, node_after, signal):
    # Calculate distance from point(signal) to edge between node before and after
    p1 = np.array((node_before.lat, node_before.lon))
    p2 = np.array((node_after.lat, node_after.lon))
    p3 = np.array((signal.lat, signal.lon))
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def make_signal_string(signal, node_before, node_after):
    distance_side = dist_edge(node_before, node_after, signal)
    distance_node_before = dist_nodes(node_before, signal)
    kind = "andere"
    function = "andere"
    # ToDo extend arnes planpro generator to take dist_side as input, only then pos of signal is unambigous
    signal_str = f"signal signal {node_before.id} {node_after.id} {distance_node_before} {function} {kind}]\n"
    return signal_str

def find_next_rail_node(index, way):
    # Not used anymore
    print([{"id": n.id, "tags": n.tags} for n in way.nodes] )
    for i in range(index, len(way.nodes)):
        if 'railway' in way.nodes[i].tags.keys() and way.nodes[i].tags['railway'] == 'rail':
            print("found")
            return way.nodes[i]
    raise Exception("No rail node after signal was found")

def get_previous_non_signal_node(index, way):
    for i in reversed(range(0, index)):
        if 'railway' in way.nodes[i].tags.keys() and not way.nodes[i].tags['railway'] == 'signal':
            return way.nodes[i]
    raise Exception("No previous rail node was found")

def get_next_non_signal_node(index, way):
    for i in range(index + 1, len(way.nodes)):
        if 'railway' in way.nodes[i].tags.keys() and not way.nodes[i].tags['railway'] == 'signal':
            return way.nodes[i]
    raise Exception("No next rail node was found")

def run_converter(x1, y1, x2, y2):
    bounding_box = BoundingBox(x1, y1, x2, y2)
    track_objects = get_track_objects(bounding_box)

    result_str = ""

    for node in track_objects.nodes:
        if 'railway' in node.tags.keys() and node.tags['railway'] == 'signal':
            continue
        result_str += f"node {node.id} {node.lat} {node.lon} description\n"

    for way in track_objects.ways:
        for idx, node in enumerate(way.nodes):
            if idx==0 or ('railway' in node.tags.keys() and node.tags['railway'] == 'signal'):
                continue
            previous_node = get_previous_non_signal_node(idx, way)
            result_str += f"edge {previous_node.id} {node.id}\n"

    for way in track_objects.ways:

        for idx, node in enumerate(way.nodes):
            if 'railway' in node.tags.keys() and  node.tags['railway'] == 'signal':
                if idx == 0 or idx == len(way.nodes) - 1:
                    print("Signal node id: ", node.id)
                    print([{"id": n.id, "tags": n.tags} for n in way.nodes] )
                    raise Exception("Signal is first or last node")
                node_before = get_previous_non_signal_node(idx, way)
                node_after = get_next_non_signal_node(idx, way)
                result_str += make_signal_string(signal=node, node_before=node_before,
                                                 node_after=node_after)

    return result_str
        



    