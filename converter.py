from dataclasses import dataclass
from typing import Any
import uuid
from overpy import Node as OverpyNode
import overpy
import networkx as nx
from planprogenerator.generator import Generator

from rail_types import Signal
from utils import dist_edge, dist_nodes, get_export_edge, get_opposite_edge_pairs, getSignalDirection, is_end_node, is_same_edge, is_signal, is_switch, merge_edges

from planprogenerator.model.signal import Signal as Gen_Signal
from planprogenerator.model.edge import Edge as Gen_Edge
from planprogenerator.model.node import Node as Gen_Node
from planprogenerator.utils import Config
class ORMConverter:
    def __init__(self):
        self.graph = None
        self.top_nodes : list[OverpyNode] = []
        self.top_edges : list[tuple[OverpyNode, OverpyNode]] = []
        self.geo_nodes : list[OverpyNode]= []
        self.geo_edges : list[tuple[OverpyNode, OverpyNode, tuple[OverpyNode, OverpyNode]]]= [] #(node_a, node_b, top_edge)
        self.signals : list[Signal]= []
        self.node_data : dict[str, OverpyNode]= {}
        self.api = overpy.Overpass()

    def _get_track_objects(self, polygon: str):
        query = f'(way["railway"="rail"](poly: "{polygon}");node(w)(poly: "{polygon}"););out body;'
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

    def _add_geo_edges(self, path, top_edge):
        previous_idx = 0
        for idx, node_id in enumerate(path):
            node = self.node_data[node_id]   
            if idx == 0 or is_signal(node):
                continue
            previous_node = self.node_data[path[previous_idx]]
            self.geo_edges.append((previous_node, node, top_edge))
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
        count = 0
        for node in self.top_nodes:
            lat, lon = node.lat, node.lon
            export_node = Gen_Node(node.id, lat, lon, "Mock Data - Fill me pls")
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
            # Currently not using signal.distance_side, since it is to small
            # Probably because in ORM signals are node of the way, therefore only minimal distance to edge
            export_signal = Gen_Signal(export_edge, signal.distance_node_before, signal.direction, signal.function, signal.kind)
            export_signals.append(export_signal)

        # check for crossing-switches
        for node in export_nodes:
            if len(node.connected_nodes) == 4:
                # identfy all 4 edges and merge
                connected_edges = [e for e in export_edges if e.node_a == node or e.node_b == node]
                edge_pair_1, edge_pair_2 = get_opposite_edge_pairs(connected_edges)

                export_edges.append(merge_edges(*edge_pair_1, node))
                export_edges.append(merge_edges(*edge_pair_2, node))
                for e in connected_edges:
                    export_edges.remove(e)
                # create new top nodes - split newly created merged edges by inserting a top node each
                # todo if we want an actual switch here
                # delete crossing node
                for connected_node in node.connected_nodes:
                    connected_node.connected_nodes.remove(node)
                export_nodes.remove(node)
        return export_nodes, export_edges, export_signals


    def run(self, polygon):
        track_objects = self._get_track_objects(polygon)
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
                        self._add_geo_edges(path, new_top_edge)
                        self._add_signals(path, new_top_edge)

        n, e, s = self._to_export_format()

        gen = Generator()
        config = Config(author_name='DRSS-2022', organisation='OSM.HPI', coord_representation='wgs84')
        gen.generate(n, e, s, config, "out")
        return gen.generate(n, e, s, config)
   
   
if __name__ == '__main__':
    conv = ORMConverter()
    conv.run("52.394471570989126 13.12194585800171 52.3955583542288 13.133854866027834 52.39436681938324 13.134176731109621 52.39326691251008 13.122761249542238")
