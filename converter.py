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
    print([{"id": n.id, "tags": n.tags} for n in way.nodes] )
    raise Exception("No previous rail node was found")

def get_next_non_signal_node(index, way):
    for i in range(index + 1, len(way.nodes)):
        if 'railway' in way.nodes[i].tags.keys() and not way.nodes[i].tags['railway'] == 'signal':
            return way.nodes[i]
    print([{"id": n.id, "tags": n.tags} for n in way.nodes] )
    raise Exception("No next rail node was found")

def is_signal(node):
    return is_x(node, 'signal')

def is_switch(node):
    return is_x(node, 'switch')

def is_x(node, x: str):
    return 'railway' in node.tags.keys() and node.tags['railway'] == x

def find_next_non_signal_on_way(way):
    for node in way.nodes:
        if not is_signal(node) and node != way.nodes[-1]:
            return node
    return None

def find_previous_non_signal_on_way(way, first_node_on_way):
    for node in reversed(way.nodes[:-1]):
        if not is_signal(node) and node != first_node_on_way:
            return node
    return None

def is_part_of_other_way(node, way_a, all_ways):
    # assumption: node should be part of exactly 0 or 1 other ways if it is not a switch
    for way_b in all_ways:
        if way_b != way_a and node in way_b.nodes:
            return True
    return False

def find_next_top_node(node, way_a, all_ways):
    for way_b in all_ways:
        if way_b != way_a and node in way_b.nodes:
            last_node = way_b[-1]
            if is_signal(last_node):
                find_previous_non_signal_on_way(way_b, way_b[0])
                if not is_part_of_other_way(last_node, way_b, all_ways) or  is_switch(last_node):
                    return last_node
                return find_next_top_node(last_node, way_b, all_ways)

def find_first_non_signal_node(nodes):
    for node in nodes:
        if not is_signal(node):
            return node

def find_last_non_signal_node(nodes):
    for node in reversed(nodes):
        if not is_signal(node):
            return node

def run_converter(x1, y1, x2, y2):
    bounding_box = BoundingBox(x1, y1, x2, y2)
    track_objects = get_track_objects(bounding_box)

    result_str = ""

    # nodes for topologie
    top_nodes = {}
    top_edges = []

    # Neuer pseudo code extrem unoptimiert und wird vermutlich duplikate enthalten
    # Wollen über alle nodes die potentielle kandidaten für top_nodes sind iterieren
    for way in track_objects.ways:
        # Only the first and last non_signal nodes of a ORM way can be candidates for a PP node
        # All nodes in between in a ORM way that are not switches can only be geo nodes
        first_way_node = find_first_non_signal_node(way.nodes)
         # ToDo: need to think about how to handle this case
        if not first_way_node:
            pass

        # node will be added to topology if it is a switch or if it is a real beginning node
        # ToDo: remove double call to find part of other way and to get that way
        if is_part_of_other_way(first_way_node, way, track_objects.ways) or not is_switch(first_way_node):
            first_way_node = find_next_top_node(first_way_node, way, track_objects.ways)
        

        last_way_node = find_last_non_signal_node(way.nodes)
        if not last_way_node:
            pass

        if is_part_of_other_way(last_way_node, way, track_objects.ways) or not is_switch(last_way_node):
            last_way_node = find_next_top_node(last_way_node, way, track_objects.ways)

        # add first and last node to topology
        if not first_way_node.id in top_nodes:
            top_nodes[first_way_node.id] = node
        if not last_way_node.id in top_nodes:
                top_nodes[last_way_node.id] = node

        # ToDo: generate nodes and edges for all switches in between first and last non_signal node on this way

        # adapt this if there is a switch inbetween
        if first_way_node and last_way_node:
            top_edges.append((first_way_node, last_way_node))

    # ToDo: generate geo nodes&edges
        

    for node in top_nodes:
        result_str += f"node {node.id} {node.lat} {node.lon} description\n"

    for edge in top_edges:
            result_str += f"edge {edge[0].id} {edge[1].id}\n"
    
    # ToDo add point objects (signals) and geoobjects to pp output

    return result_str
        



    