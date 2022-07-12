from dataclasses import dataclass
from typing import Any
import overpy
import networkx as nx

from rail_types import BoundingBox
from utils import is_end_node, is_signal, is_switch

class ORMConverter:
    def __init__(self):
        self.graph = None
        self.top_nodes = []
        self.top_edges = []
        self.geo_node_ids = []
        self.geo_edges = []
        self.signals = []
        self.node_data = {}
        self.api = overpy.Overpass()

    def _get_track_objects(self, bounding_box: BoundingBox):
        query = f'(way["railway"="rail"]({bounding_box});node(w););out body;'
        return self._query_api(query)

    def _query_api(self, query):
        result = self.api.query(query)
        return result

    def _build_graph(self, track_objects):
        G = nx.DiGraph()
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
                result_str += f"edge {edge[0]} {edge[1]}\n"
        
        return result_str

    def _get_next_top_node(self, node, out_edge: "tuple[str, str]", path):
        node_to_id = out_edge[1]
        node_to = self.node_data[node_to_id]
        if node_to in self.top_nodes:
            return node_to

        path.append(node_to_id)

        if self.graph.degree(node_to_id) == 0:
            return None
        
        if self.graph.degree(node_to_id) != 1:
            print(type(self.graph.out_edges[node_to_id]))
            #print([f"In: {edge[0]}, {edge[1]}" for edge in self.graph.in_edges[node_to_id]])
            print([f"Out: {edge[0]}, {edge[1]}" for edge in self.graph.out_edges[node_to_id]])
            raise Exception(f"Node: {node_to_id}. \n Geo nodes should have only one out, otherwise we don't know where to go")

        return self._get_next_top_node(self, node_to, self.graph.edges[node_to_id][0], path)

    def _add_geo_edges(self, path):
        for idx, node_id in enumerate(path):
            if idx == 0:
                continue
            node = self.node_data[node_id]   
            previous_node = self.node_data[path[idx - 1]]
            self.geo_edges.append(previous_node, node)

    def run( self, x1, y1, x2, y2):
        bounding_box = BoundingBox(x1, y1, x2, y2)
        track_objects = self._get_track_objects(bounding_box)
        # ToDo: Currently building a directed graph. Does this make sense based on the ORM data?
        self.graph, self.node_data = self._build_graph(track_objects)

        # ToDo: Check whether all edges really link to each other in ORM or if there might be edges missing for nodes that are just a few cm from each other
        # Only nodes with max 1 edge or that are a switch can be top nodes
        for node_id in self.graph.nodes:
            node = self.node_data[node_id]
            if is_end_node(node, self.graph) or is_switch(node):
                self.top_nodes.append(node)
            elif not is_signal(node):
                self.geo_node_ids.append(node)
            else:
                self.signals.append(node)

        # DFS-Like to create top and geo edges
        for node in self.top_nodes:
            if self.graph.degree(node.id) > 2:
                raise Exception("Top nodes should have max two out edges (would be the case for a switch)")
            for edge in self.graph.out_edges(node.id):
                print(edge)
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