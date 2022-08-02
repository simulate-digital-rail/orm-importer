from dataclasses import dataclass
from typing import Any
from overpy import Node as OverpyNode
import overpy
import networkx as nx
from planprogenerator.generator import Generator

from rail_types import BoundingBox, Signal
from utils import dist_edge, dist_nodes, get_export_edge, getSignalDirection, is_end_node, is_same_edge, is_signal, is_switch, make_signal_string

from planprogenerator.model.signal import Signal as Gen_Signal
from planprogenerator.model.edge import Edge as Gen_Edge
from planprogenerator.model.node import Node as Gen_Node

class ORMConverter:
    def __init__(self):
        self.graph = None
        self.top_nodes : list[OverpyNode] = []
        self.top_edges : list[tuple[OverpyNode, OverpyNode]] = []
        self.geo_nodes : list[OverpyNode]= []
        self.geo_edges : list[tuple[OverpyNode, OverpyNode]]= []
        self.signals : list[Signal]= []
        self.node_data : dict[str, OverpyNode]= {}
        self.api = overpy.Overpass()

    def _get_track_objects(self, bounding_box: BoundingBox):
        query = f'(way["railway"="rail"]({bounding_box});node(w)({bounding_box}););out body;'
        return self._query_api(query)

    def _query_api(self, query):
        result = self.api.query(query)
        return result

    def _build_graph(self, track_objects):
        G = nx.Graph()
        for way in track_objects.ways:
            previous_node = None
            for idx, node_id in enumerate(way._node_ids):
                try:
                    node = track_objects.get_node(node_id)
                    self.node_data[node_id] = node
                    G.add_node(node.id)
                    if previous_node:
                        G.add_edge(previous_node.id, node.id)
                    previous_node = node
                except overpy.exception.DataIncomplete:
                    continue
        return G

    def _to_export_string(self, include_geo_data=False):
        result_str = ""
        for node in self.top_nodes:
            result_str += f"node {node.id} {node.lat} {node.lon} description\n"

        for edge in self.top_edges:
                result_str += f"edge {edge[0].id} {edge[1].id}\n"

        for signal in self.signals:
            result_str += make_signal_string(signal)

        if include_geo_data:
            for node in self.geo_nodes:
                result_str += f"geo_node {node.id} {node.lat} {node.lon} description\n"
            for edge in self.geo_edges:
                result_str += f"geo_edge {edge[0].id} {edge[1].id}\n"

        
        return result_str

    def _get_next_top_node(self, node, edge: "tuple[str, str]", path):
        node_to_id = edge[1]
        node_to = self.node_data[node_to_id]
        if node_to in self.top_nodes:
            return node_to, path

        path.append(node_to_id)

        if self.graph.degree(node_to_id) == 0:
            return None, path

        distinct_edges = [e for e in self.graph.edges(node_to_id) if not is_same_edge(e, edge)]
        if len(distinct_edges) != 1:
            raise Exception(f"Node: {node_to_id}. \n Geo nodes should have only one other edge, otherwise we don't know where to go")

        next_edge = distinct_edges[0]
        return self._get_next_top_node(node_to, next_edge, path)

    def _add_geo_edges(self, path):
        previous_idx = 0
        for idx, node_id in enumerate(path):
            node = self.node_data[node_id]   
            if idx == 0 or is_signal(node):
                continue
            previous_node = self.node_data[path[previous_idx]]
            self.geo_edges.append((previous_node, node))
            previous_idx = idx

    def _add_signals(self, path, top_edge):
        for idx, node_id in enumerate(path):
            node = self.node_data[node_id]  
            if is_signal(node):
                node_before, node_after = top_edge
                distance_side = dist_edge(node_before, node_after, node)
                distance_node_before = dist_nodes(node_before, node)
                kind = "andere"
                function = "andere"
                direction = getSignalDirection(node.tags["railway:signal:direction"])
                signal = Signal(node, top_edge, distance_side, distance_node_before, kind, function, direction)
                self.signals.append(signal)

    def _to_export_format(self):
        export_nodes: list[Gen_Node] = []
        export_edges: list[Gen_Edge] = []
        export_signals: list[Gen_Signal] = []
        for node in self.top_nodes:
            export_node = Gen_Node(node.id, node.lat, node.lon, "Mock Data - Fill me pls")
            export_nodes.append(export_node)

        for edge in self.top_edges:
            node_a: Gen_Node = [n for n in export_nodes if n.identifier == edge[0].id]
            node_b: Gen_Node = [n for n in export_nodes if n.identifier == edge[1].id]
            if not node_a or not node_b:
                raise Exception("Edge that does not have top nodes, found")
            node_a = node_a[0]
            node_b = node_b[0]
            node_a.connected_nodes.append(node_b)
            node_b.connected_nodes.append(node_a)
            export_edge = Gen_Edge(node_a, node_b)
            export_edges.append(export_edge)

        for signal in self.signals:
            export_edge = get_export_edge(signal.edge, export_edges, export_nodes)
            export_signal = Gen_Signal(export_edge, signal.distance_side, signal.direction, signal.function, signal.kind)
            export_signals.append(export_signal)
        return export_nodes, export_edges, export_signals


    def run(self, x1, y1, x2, y2):
        bounding_box = BoundingBox(x1, y1, x2, y2)
        track_objects = self._get_track_objects(bounding_box)
        self.graph = self._build_graph(track_objects)

        # ToDo: Check whether all edges really link to each other in ORM or if there might be edges missing for nodes that are just a few cm from each other
        # Only nodes with max 1 edge or that are a switch can be top nodes
        for node_id in self.graph.nodes:
            node = self.node_data[node_id]
            if is_end_node(node, self.graph) or is_switch(node):
                self.top_nodes.append(node)
            elif not is_signal(node):
                self.geo_nodes.append(node)

        # DFS-Like to create top and geo edges
        for node in self.top_nodes:
            for edge in self.graph.edges(node.id):
                next_top_node, path = self._get_next_top_node(node, edge, [])
                # Only add geo objects that are on the path between two top nodes
                if next_top_node and next_top_node != node:
                    if not (next_top_node, node) in self.top_edges:
                        new_top_edge = (node, next_top_node)
                        self.top_edges.append(new_top_edge)
                        self._add_geo_edges(path)
                        self._add_signals(path, new_top_edge)

        n, e, s = self._to_export_format()

        gen = Generator()
        gen.generate(n, e, s, "out")
   
if __name__ == '__main__':
    conv = ORMConverter()
    conv.run(x1=52.39503, y1=13.12242, x2=52.3933, y2=13.1421)