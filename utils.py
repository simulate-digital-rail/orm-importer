import numpy as np

from rail_types import Signal

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

def is_end_node(node, graph):
    if is_signal(node):
        return False
    
    if graph.degree(node.id) == 1 or graph.degree(node.id) == 0:
        return True

def is_signal(node):
    return is_x(node, 'signal')

def is_switch(node):
    return is_x(node, 'switch')

def is_x(node, x: str):
    return 'railway' in node.tags.keys() and node.tags['railway'] == x

def make_signal_string(signal: Signal):
    node_before, node_after = signal.edge
    distance_side = dist_edge(node_before, node_after, signal)
    distance_node_before = dist_nodes(node_before, signal)
    kind = "andere"
    function = "andere"
    # ToDo extend arnes planpro generator to take dist_side as input, only then pos of signal is unambigous
    signal_str = f"signal {node_before.id} {node_after.id} {distance_node_before} {function} {kind}]\n"
    return signal_str

def is_same_edge(e1: tuple, e2: tuple):
    if e1 == e2:
        return True
    if e1[0] == e2[1] and e1[1] == e2[0]:
        return True
    return False
