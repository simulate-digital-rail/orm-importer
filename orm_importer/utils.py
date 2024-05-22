import re
from decimal import Decimal
from typing import List

import numpy as np
import overpy.exception
from haversine import haversine
from overpy import Node, Way
from yaramo import model
from yaramo.additional_signal import (
    AdditionalSignal,
    AdditionalSignalZs2,
    AdditionalSignalZs2v,
    AdditionalSignalZs3,
    AdditionalSignalZs3v,
)
from yaramo.edge import Edge
from yaramo.signal import SignalState


def dist_edge(node_before, node_after, signal):
    # Calculate distance from point(signal) to edge between node before and after
    # TODO: Validate that this is really correct!
    return 3.95
    p1 = np.array((node_before.lat, node_before.lon))
    p2 = np.array((node_after.lat, node_after.lon))
    p3 = np.array((signal.lat, signal.lon))
    return np.abs(np.cross(p2 - p1, p1 - p3)) / Decimal(
        haversine((node_before.lat, node_before.lon), (node_after.lat, node_after.lon))
    )


def is_end_node(node, graph):
    # identify end nodes first, as a signal might also be an end node respective to the bounding box
    if graph.degree(node.id) == 1 or graph.degree(node.id) == 0:
        return True

    if is_signal(node):
        return False


def is_signal(node):
    # we cannot use railway=signal as a condition, as buffer stops violate this assumption.
    # Instead, we check for the signal direction as we cannot create a signal without a direction anyway
    return "railway:signal:direction" in node.tags.keys()


def is_switch(node, graph):
    return is_x(node, "switch") and graph.degree(node.id) == 3


def is_x(node, x: str):
    return "railway" in node.tags.keys() and node.tags["railway"] == x


def is_same_edge(e1: tuple, e2: tuple):
    if e1 == e2:
        return True
    if e1[0] == e2[1] and e1[1] == e2[0]:
        return True
    return False


def getSignalDirection(edge: Edge, ways: dict[str, List[Way]], path, signal_direction_tag: str):
    edge_is_forward = None
    for way in ways[edge.node_a.name]:
        node_a = int(edge.node_a.name)
        node_b = int(edge.node_b.name)
        try:
            if node_a in way._node_ids and node_b in way._node_ids:
                edge_is_forward = way._node_ids.index(node_a) < way._node_ids.index(node_b)
                break
            elif node_a in way._node_ids and len(path) > 0 and path[0] in way._node_ids:
                edge_is_forward = way._node_ids.index(node_a) < way._node_ids.index(path[0])
                break
            else:
                for i in range(len(path) - 1):
                    if path[i] in way._node_ids and path[i + 1] in way._node_ids:
                        edge_is_forward = way._node_ids.index(path[i]) < way._node_ids.index(
                            path[i + 1]
                        )
                        break
        except overpy.exception.DataIncomplete:
            continue

    if edge_is_forward is None:
        raise Exception("Could not determine direction of edge")

    if (edge_is_forward and signal_direction_tag == "forward") or (
        not edge_is_forward and signal_direction_tag == "backward"
    ):
        return "in"
    else:
        return "gegen"


def get_signal_states(signal_tags: dict):
    # Sh0 is tagged as Hp0 in OSM since a few years, but not all tags have been replaced so we convert them
    raw_states = []
    raw_states += signal_tags.get("railway:signal:main:states", "").split(";")
    raw_states += signal_tags.get("railway:signal:combined:states", "").split(";")
    raw_states += (
        signal_tags.get("railway:signal:minor:states", "").replace("sh0", "hp0").split(";")
    )
    raw_states.append(signal_tags.get("railway:signal:minor", "").replace("sh0", "hp0"))
    states = set()
    for raw_state in raw_states:
        if raw_state.startswith("DE-ESO:"):
            try:
                states.add(SignalState[raw_state.split(":")[1]])
            except KeyError:
                continue
    return states


def get_opposite_edge_pairs(edges: List[model.Edge], node_to_remove: model.Node):
    if len(edges) != 4:
        raise Exception(
            "Opposite edge pairs can only be identified for a list of 4 edged. Only "
            + str(len(edges))
            + " edges given"
        )
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
    if not "railway:signal:direction" in signal.tags.keys():
        raise Exception("Expected signal node")
    try:
        tag = next(t for t in signal.tags.keys() if t.endswith(":function"))
        if signal.tags[tag] == "entry":
            return "Einfahr_Signal"
        elif signal.tags[tag] == "exit":
            return "Ausfahr_Signal"
        elif signal.tags[tag] == "block":
            return "Block_Signal"
        else:
            return "andere"
    except StopIteration:
        return "andere"


def get_signal_kind(signal: Node) -> str:
    if not "railway:signal:direction" in signal.tags.keys():
        raise Exception("Expected signal node")
    # ORM Reference: https://wiki.openstreetmap.org/wiki/OpenRailwayMap/Tagging/Signal
    if "railway:signal:main" in signal.tags.keys():
        return "Hauptsignal"
    elif "railway:signal:distant" in signal.tags.keys():
        return "Vorsignal"
    elif "railway:signal:combined" in signal.tags.keys():
        return "Mehrabschnittssignal"
    elif "railway:signal:shunting" in signal.tags.keys() or (
        "railway:signal:minor" in signal.tags.keys()
        and (
            signal.tags["railway:signal:minor"] == "DE-ESO:sh0"
            or signal.tags["railway:signal:minor"] == "DE-ESO:sh2"
        )
    ):
        return "Sperrsignal"
    elif (
        "railway:signal:main" in signal.tags.keys() and "railway:signal:minor" in signal.tags.keys()
    ):
        return "Hauptsperrsignal"
    # Names in comment are not yet supported by PlanPro generator
    elif "railway:signal:main_repeated" in signal.tags.keys():
        return "andere"  # 'Vorsignalwiederholer'
    elif "railway:signal:minor" in signal.tags.keys():
        return "andere"  # 'Zugdeckungssignal'
    elif "railway:signal:crossing" in signal.tags.keys():
        return "andere"  # 'Überwachungssignal'
    elif (
        "railway:signal:combined" in signal.tags.keys()
        and "railway:signal:minor" in signal.tags.keys()
    ):
        return "andere"  # 'Mehrabschnittssperrsignal'
    else:
        return "andere"


def get_signal_name(node: Node):
    ref = str(node.tags.get("ref", node.id))
    if result := re.findall(r"\d{1,2}\s?([a-zA-Z]+\d*)", ref):
        return result[0]
    return ref


def get_signal_classification_number(node: Node):
    ref = str(node.tags.get("ref", None))
    if result := re.findall(r"(\d{1,2})\s?[a-zA-Z]+\d*", ref):
        number = result[0]
        return str(number) if len(number) > 1 else f"0{number}"
    return "60"


def is_signal_type(tags: dict, signal_type: str, eso_value: str):
    return signal_type in tags.keys() and tags[signal_type] == eso_value


def get_zs_values(osm_tags: dict, key: str):
    value_str = osm_tags.get(key, None)
    if value_str is None or value_str == "none":
        return []
    values = value_str.split(";")
    invalid_values = [None, "", "?"]
    return filter(lambda value: value not in invalid_values, values)


def get_additional_signals(signal: Node) -> List[AdditionalSignal]:
    additional_signals = []
    if is_signal_type(signal.tags, "railway:signal:route_distant", "DE-ESO:zs2v"):
        additional_signal = AdditionalSignalZs2v(
            [
                AdditionalSignalZs2v.AdditionalSignalSymbolZs2v[s]
                for s in get_zs_values(signal.tags, "railway:signal:route_distant:states")
            ]
        )
        additional_signals.append(additional_signal)
    if is_signal_type(signal.tags, "railway:signal:route", "DE-ESO:zs2"):
        additional_signal = AdditionalSignalZs2(
            [
                AdditionalSignalZs2.AdditionalSignalSymbolZs2[s]
                for s in get_zs_values(
                    signal.tags,
                    "railway:signal:route:states",
                )
            ]
        )
        additional_signals.append(additional_signal)
    if is_signal_type(signal.tags, "railway:signal:speed_limit_distant", "DE-ESO:zs3v"):
        additional_signal = AdditionalSignalZs3v(
            [
                AdditionalSignalZs3v.AdditionalSignalSymbolZs3v(0 if s == "off" else int(s) / 10)
                for s in get_zs_values(
                    signal.tags,
                    "railway:signal:speed_limit_distant:speed",
                )
            ]
        )
        additional_signals.append(additional_signal)
    if is_signal_type(signal.tags, "railway:signal:speed_limit", "DE-ESO:zs3"):
        additional_signal = AdditionalSignalZs3(
            [
                AdditionalSignalZs3.AdditionalSignalSymbolZs3(0 if s == "off" else int(s) / 10)
                for s in get_zs_values(signal.tags, "railway:signal:speed_limit:speed")
            ]
        )
        additional_signals.append(additional_signal)
    return additional_signals
