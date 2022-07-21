from dataclasses import dataclass
from typing import Any
from overpy import Node
import overpy
import networkx as nx

from rail_types import BoundingBox
from utils import is_end_node, is_same_edge, is_signal, is_switch

class ORMConverter:
    def __init__(self):
        self.graph = None
        self.top_nodes : list[Node] = []
        self.top_edges : list[tuple[Node, Node]] = []
        self.geo_nodes : list[Node]= []
        self.geo_edges : list[tuple[Node, Node]]= []
        self.signals : list[Signal]= []
        self.node_data : dict[str, Node]= {}
        self.api = overpy.Overpass()

    def _get_track_objects(self, bounding_box: BoundingBox):
        query = f'(way["railway"="rail"]({bounding_box});node(w););out body;'
        return self._query_api(query)

    def _query_api(self, query):
        result = self.api.query(query)
        return result

    def _build_graph(self, track_objects):
        G = nx.Graph()
        node_data = {}
        for way in track_objects.ways:
            for idx, node in enumerate(way.nodes):
                G.add_node(node.id)
                node_data[node.id] = node
                if idx != 0:
                    G.add_edge(way.nodes[idx-1].id, node.id)
        return G, node_data

    def _to_export_string(self):
        result_str = ""
        for node in self.top_nodes:
            result_str += f"node {node.id} {node.lat} {node.lon} description\n"

        for edge in self.top_edges:
                result_str += f"edge {edge[0].id} {edge[1].id}\n"
        
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
                signal = {node: node, top_edge: top_edge}
                self.signals.append(signal)

    def run(self, x1, y1, x2, y2):
        bounding_box = BoundingBox(x1, y1, x2, y2)
        track_objects = self._get_track_objects(bounding_box)
        self.graph, self.node_data = self._build_graph(track_objects)

        # ToDo: Check whether all edges really link to each other in ORM or if there might be edges missing for nodes that are just a few cm from each other
        # Only nodes with max 1 edge or that are a switch can be top nodes
        for node_id in self.graph.nodes:
            node = self.node_data[node_id]
            print(type(node))
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

        res = self._to_export_string()
        return res

   
if __name__ == '__main__':
    conv = ORMConverter()
    conv.run(x1=52.39503, y1=13.12242, x2=52.3933, y2=13.1421)