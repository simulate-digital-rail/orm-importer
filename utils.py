from platform import node
from decimal import Decimal
from typing import List
import numpy as np
from planprogenerator.model.node import Node as Gen_Node
from planprogenerator.model.edge import Edge as Gen_Edge

from rail_types import Signal
from overpy import Node
from haversine import haversine


def dist_nodes(n1, n2):
    # Calculate distance between two nodes
    p1 = (n1.lat, n1.lon)
    p2 = (n2.lat, n2.lon)
    return haversine(p1, p2)

def dist_edge(node_before, node_after, signal):
    # Calculate distance from point(signal) to edge between node before and after
    # TODO: Validate that this is really correct!
    p1 = np.array((node_before.lat, node_before.lon))
    p2 = np.array((node_after.lat, node_after.lon))
    p3 = np.array((signal.lat, signal.lon))
    return np.abs(np.cross(p2-p1, p1-p3)) / Decimal(haversine((node_before.lat, node_before.lon), (node_after.lat, node_after.lon)))

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

def get_opposite_edge_pairs(edges: List[Gen_Edge]):
    if len(edges) != 4:
        raise Exception("Opposite edge pairs can only be identified for a list of 4 edged. Only " +  str(len(edges)) + " edges given")
    node_map = []
    for e in edges:
        if e.node_a != node:
            node_map.append((e.node_a, e))
        else:
            node_map.append((e.node_b, e))

    node_map.sort(key=lambda t: t[0].geo_node.x)
    top_left = max(node_map[:2], key=lambda t: t[0].geo_node.y)[1]
    bottom_left = min(node_map[:2], key=lambda t: t[0].geo_node.y)[1]
    top_right = max(node_map[2:], key=lambda t: t[0].geo_node.y)[1]
    bottom_right = min(node_map[2:], key=lambda t: t[0].geo_node.y)[1]

    return (top_left, bottom_right), (bottom_left, top_right)
            
    
def merge_edges(e1: Gen_Edge, e2: Gen_Edge, node_to_remove: Gen_Node):
    if e1.node_a == node_to_remove:
        if e2.node_a == node_to_remove:
            return Gen_Edge(e1.node_b, e2.node_b)
        if e2.node_b == node_to_remove:
            return Gen_Edge(e1.node_b, e2.node_a)
        else:
            raise Exception("Could not merge edges")
    if e1.node_b == node_to_remove:
        if e2.node_a == node_to_remove:
            return Gen_Edge(e1.node_a, e2.node_b)
        if e2.node_b == node_to_remove:
            return Gen_Edge(e1.node_a, e2.node_a)
        else:
            raise Exception("Could not merge edges")
    else:
        raise Exception("Could not merge edges")