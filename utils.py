from platform import node
import numpy as np
from planprogenerator.model.node import Node as Gen_Node
from planprogenerator.model.edge import Edge as Gen_Edge

from rail_types import Signal
from overpy import Node

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
    # identify end nodes first, as a signal might also be an end node respective to the bounding box
    if graph.degree(node.id) == 1 or graph.degree(node.id) == 0:
        return True

    if is_signal(node):
        return False

def is_signal(node):
    return is_x(node, 'signal')

def is_switch(node):
    return is_x(node, 'switch')

def is_x(node, x: str):
    return 'railway' in node.tags.keys() and node.tags['railway'] == x

def make_signal_string(signal: Signal):
    node_before, node_after = signal.edge
    # ToDo extend arnes planpro generator to take dist_side as input, only then pos of signal is unambigous
    signal_str = f"signal {node_before.id} {node_after.id} {signal.distance_node_before} {signal.function} {signal.kind}\n"
    return signal_str

def is_same_edge(e1: tuple, e2: tuple):
    if e1 == e2:
        return True
    if e1[0] == e2[1] and e1[1] == e2[0]:
        return True
    return False

def get_export_edge(edge: "tuple[Node, Node]", gen_edges: "list[Gen_Edge]", gen_nodes: "list[Gen_Node]"):
    node_a: Gen_Node = [n for n in gen_nodes if n.identifier == edge[0].id]
    node_b: Gen_Node = [n for n in gen_nodes if n.identifier == edge[1].id]
    if not node_a or not node_b:
        raise Exception("Edge that does not have top nodes, found")
    node_a = node_a[0]
    node_b = node_b[0]
    for gen_edge in gen_edges:
        if gen_edge.node_a == node_a and gen_edge.node_b == node_b:
            return gen_edge
    raise Exception("No generator edge found for converter edge")

def getSignalDirection(direction: str):
    if direction == "forward":
        return "in"
    if direction == "backward":
        return "gegen"
    raise Exception("Unknown signal direction encountered")