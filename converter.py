from dataclasses import dataclass
from typing import Any
import overpy
import networkx as nx

from rail_types import BoundingBox
from utils import is_end_node, is_signal, is_switch
api = overpy.Overpass()

class ORMConverter:
    def __init__(self):
        self.graph = None
        self.top_nodes = []
        self.top_edges = []
        self.geo_nodes = []
        self.geo_edges = []
        self.signals = []

    def _get_track_objects(self, bounding_box: BoundingBox):
        query = f'(way["railway"="rail"]({bounding_box});node(w););out body;'
        return self.query_api(query)

    def _query_api(self, query):
        result = api.query(query)
        return result

    def _build_graph(self, track_objects):
        G = nx.DiGraph()
        for way in track_objects.ways:
            for idx, node in enumerate(way.nodes):
                G.add_node(node)
                if idx != 0:
                    G.add_edge(way.nodes[idx-1].id, node.id)
        return G

    def _to_export_string(self):
        result_str = ""
        for node in self.top_nodes:
            result_str += f"node {node.id} {node.lat} {node.lon} description\n"

        for edge in self.top_edges:
                result_str += f"edge {edge[0].id} {edge[1].id}\n"
        
        return result_str

    def _get_next_top_node(self, node, out_edge: "tuple[Any, Any]", path):
        node_to = out_edge[1]
        if node_to in self.top_nodes:
            return node_to

        path.append(node)

        if self.graph.degree(node_to) == 0:
            return None
        
        if self.graph.degree(node_to) != 1:
            raise Exception("Geo nodes should have only one out, otherwise we don't know where to go")

        return self._get_next_top_node(self, node_to, self.graph.edges[node_to], path)

    def _add_geo_edges(self, path):
        for idx, node in enumerate(path):
            if idx == 0:
                continue
            self.geo_edges.append(path[idx - 1], node)
        return 

    def run( self, x1, y1, x2, y2):
        bounding_box = BoundingBox(x1, y1, x2, y2)
        track_objects = self._get_track_objects(bounding_box)
        # ToDo: Currently building a directed graph. Does this make sense based on the ORM data?
        self.graph = self._build_graph(track_objects)

        # ToDo: Check whether all edges really link to each other in ORM or if there might be edges missing for nodes that are just a few cm from each other
        # Only nodes with max 1 edge or that are a switch can be top nodes
        for node in self.graph.nodes:
            if is_end_node(node) or is_switch(node):
                self.top_nodes.append(node)
            elif not is_signal(node):
                self.geo_nodes.append(node)
            else:
                self.signals.append(node)

        # DFS-Like to create top and geo edges
        for node in self.top_nodes:
            if self.graph.degree(node) > 2:
                raise Exception("Top nodes should have max two out edges (would be the case for a switch)")
            for edge in self.graph.out_edges(node):
                next_top_node, path = self._get_next_top_node(node, edge, [])
                # Only add geo objects that are on the path between two top nodes
                if next_top_node and next_top_node != node:
                    self.top_edges.append((node, next_top_node))
                    self._add_geo_edges(path)

        res = self._to_export_string()
        return res

   
if __name__ == '__main__':
    conv = ORMConverter()
    conv.run(x1=52.39503, y1=13.12242, x2=52.3933, y2=13.1421)