from platform import node
from decimal import Decimal
from typing import List
import numpy as np

from overpy import Node
from haversine import haversine
from yaramo import model
from yaramo.edge import Edge


def dist_nodes(n1, n2):
    # Calculate distance between two nodes
    p1 = (n1.lat, n1.lon)
    p2 = (n2.lat, n2.lon)
    return haversine(p1, p2)


def dist_edge(node_before, node_after, signal):
    # Calculate distance from point(signal) to edge between node before and after
    # TODO: Validate that this is really correct!
    return 3.95
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


def getSignalDirection(direction: str):
    if direction == "forward":
        return "in"
    if direction == "backward":
        return "gegen"
    raise Exception("Unknown signal direction encountered")


def get_opposite_edge_pairs(edges: List[model.Edge], node_to_remove: model.Node):
    if len(edges) != 4:
        raise Exception("Opposite edge pairs can only be identified for a list of 4 edged. Only " +  str(len(edges)) + " edges given")
    node_map = []
    for e in edges:
        if e.node_a != node_to_remove:
            node_map.append((e.node_a, e))
        else:
            node_map.append((e.node_b, e))

    node_map.sort(key=lambda t: t[0].geo_node.geo_point.x)
    top_left = max(node_map[:2], key=lambda t: t[0].geo_node.geo_point.y)[1]
    bottom_left = min(node_map[:2], key=lambda t: t[0].geo_node.geo_point.y)[1]
    top_right = max(node_map[2:], key=lambda t: t[0].geo_node.geo_point.y)[1]
    bottom_right = min(node_map[2:], key=lambda t: t[0].geo_node.geo_point.y)[1]

    return (top_left, bottom_right), (bottom_left, top_right)


def merge_edges(e1: model.Edge, e2: model.Edge, node_to_remove: model.Node):
    print(node_to_remove.uuid)
    print(str(e1.node_a.uuid) + " " + str(e1.node_b.uuid))
    print(str(e2.node_a.uuid) + " " + str(e2.node_b.uuid))
    first_node = e1.node_a if e1.node_b == node_to_remove else e1.node_b
    second_node = e2.node_a if e2.node_b == node_to_remove else e2.node_b
    first_node.connected_nodes.remove(node_to_remove)
    first_node.connected_nodes.append(second_node)
    second_node.connected_nodes.remove(node_to_remove)
    second_node.connected_nodes.append(first_node)
    edge = Edge(first_node, second_node)
    edge.signals = e1.signals + e2.signals
    edge.intermediate_geo_nodes = e1.intermediate_geo_nodes + e2.intermediate_geo_nodes
    edge.update_length()
    return edge


def get_signal_function(signal: Node) -> str:
    if not signal.tags['railway'] == 'signal':
        raise Exception('Expected signal node')
    try:
        tag = next(t for t in signal.tags.keys() if t.endswith(':function'))
        if signal.tags[tag] == 'entry':
            return 'Einfahr_Signal'
        elif signal.tags[tag] == 'exit':
            return 'Ausfahr_Signal'
        else:
            return 'andere'
    except StopIteration:
        return 'andere'


def get_signal_kind(signal: Node) -> str:
    if not signal.tags['railway'] == 'signal':
        raise Exception('Expected signal node')
    # ORM Reference: https://wiki.openstreetmap.org/wiki/OpenRailwayMap/Tagging/Signal
    if 'railway:signal:main' in signal.tags.keys():
        return 'Hauptsignal'
    elif 'railway:signal:distant' in signal.tags.keys():
        return 'Vorsignal'
    elif 'railway:signal:combined' in signal.tags.keys():
        return 'Mehrabschnittssignal'
    elif 'railway:signal:shunting' in signal.tags.keys():
        return 'Sperrsignal'
    elif 'railway:signal:main' in signal.tags.keys() and 'railway:signal:minor' in signal.tags.keys():
        return 'Hauptsperrsignal'
    # Names in comment are not yet supported by PlanPro generator
    elif 'railway:signal:main_repeated' in signal.tags.keys():
        return 'andere'  # 'Vorsignalwiederholer'
    elif 'railway:signal:minor' in signal.tags.keys():
        return 'andere'  # 'Zugdeckungssignal'
    elif 'railway:signal:crossing' in signal.tags.keys():
        return 'andere'  # 'Überwachungssignal'
    elif 'railway:signal:combined' in signal.tags.keys() and 'railway:signal:minor' in signal.tags.keys():
        return 'andere'  # 'Mehrabschnittssperrsignal'
    else:
        return 'andere'