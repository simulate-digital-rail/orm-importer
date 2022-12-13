from typing import Tuple
from overpy import Node as OverpyNode
import overpy
import networkx as nx
from planprogenerator import Generator, Config
from railwayroutegenerator.generator import generate_from_topology
from yaramo import model
from yaramo.topology import Topology

from orm_importer.rail_types import Signal
from orm_importer.utils import dist_edge, dist_nodes, get_export_edge, get_opposite_edge_pairs, get_signal_function, get_signal_kind, getSignalDirection, is_end_node, is_same_edge, is_signal, is_switch, merge_edges


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
        self.topology = Topology()

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

    def _add_geo_edges(self, path, start_node, end_node):
        previous_idx = 0
        for idx, node_id in enumerate(path):
            node = self.node_data[node_id]   
            if idx == 0 or is_signal(node):
                continue
            previous_node = self.node_data[path[previous_idx]]
            self.geo_edges.append((previous_node, node, (start_node, end_node)))
            previous_idx = idx

    def _add_signals(self, path, edge: model.Edge, node_before, node_after):
        for idx, node_id in enumerate(path):
            node = self.node_data[node_id]  
            if is_signal(node):
                signal = model.Signal(
                    edge=edge,
                    distance_previous_node=dist_nodes(node_before, node),
                    side_distance=dist_edge(node_before, node_after, node),
                    direction=getSignalDirection(node.tags["railway:signal:direction"]),
                    function=get_signal_function(node) ,
                    kind=get_signal_kind(node),
                    name=str(node.tags.get("ref", node_id))[:6]
                )
                self.topology.add_signal(signal)


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

        for node in self.top_nodes:
            lat, lon = node.lat, node.lon
            export_node = model.Node(name=node.id, geo_node=model.GeoNode(lat, lon))
            self.topology.add_node(export_node)


        # DFS-Like to create top and geo edges
        for node in self.top_nodes:
            for edge in self.graph.edges(node.id):
                next_top_node, path = self._get_next_top_node(node, edge, [])
                # Only add geo objects that are on the path between two top nodes
                if next_top_node and next_top_node != node:
                    node_a = next((n for n in self.topology.nodes.values() if n.name == node.id), None)
                    node_b = next((n for n in self.topology.nodes.values() if n.name == next_top_node.id), None)
                    if (node_a and node_b) and not self.topology.get_edge_by_nodes(node_a, node_b):
                        current_edge = model.Edge(node_a, node_b)
                        self.topology.add_edge(current_edge)
                        self._add_geo_edges(path, node, next_top_node)
                        self._add_signals(path, current_edge, node, next_top_node)

        count = 0

        replaced_edges = {}
        replaced_n = {}

        for node in self.topology.nodes.values():
            # check for crossing-switches
            if len(node.connected_nodes) == 4:
                # identfy all 4 edges and merge
                connected_edges = [e for e in self.topology.edges.values() if e.node_a == node or e.node_b == node]
                edge_pair_1, edge_pair_2 = get_opposite_edge_pairs(connected_edges, node)
                new_edge_1 = merge_edges(*edge_pair_1, node)
                new_edge_2 = merge_edges(*edge_pair_2, node)

                # ToDo add to mapping which actual nodes were replaced
                '''replaced_edges[(node.connected_nodes[0].identifier, node.identifier)] = new_edge
                replaced_edges[(node.connected_nodes[1].identifier, node.identifier)] = new_edge
                replaced_edges[(node.connected_nodes[2].identifier, node.identifier)] = new_edge
                replaced_edges[(node.connected_nodes[3].identifier, node.identifier)] = new_edge'''
                export_edges.append(new_edge_1)
                export_edges.append(new_edge_2)
                for e in connected_edges:
                    export_edges.remove(e)
                # create new top nodes - split newly created merged edges by inserting a top node each
                # todo if we want an actual switch here
                # delete crossing node
                export_nodes.remove(node)

            # checking for switches with missing connection
            if len(node.connected_nodes) == 2:
                connected_edges = [e for e in export_edges if e.node_a == node or e.node_b == node]
                new_edge = merge_edges(connected_edges[0], connected_edges[1], node)
                export_edges.append(new_edge)
                replaced_edges[(node.connected_nodes[0].identifier, node.identifier)] = new_edge
                replaced_edges[(node.connected_nodes[1].identifier, node.identifier)] = new_edge
                for e in connected_edges:
                    export_edges.remove(e)
                export_nodes.remove(node)

        for geo_edge in self.geo_edges:
            top_edge: Tuple[OverpyNode, OverpyNode] = geo_edge[2]
            # check if top_edge that the geo edge is associated with still exists, if not find the replaced edge
            if (top_edge[0].id, top_edge[1].id) in replaced_edges.keys():
                export_top_edge = replaced_edges[(top_edge[0].id, top_edge[1].id)]
            elif (top_edge[1].id, top_edge[0].id) in replaced_edges.keys():
                export_top_edge = replaced_edges[(top_edge[1].id, top_edge[0].id)]
            else:
                node_a = next((n for n in self.topology.nodes.values() if n.name == top_edge[0].id), None)
                node_b = next((n for n in self.topology.nodes.values() if n.name == top_edge[1].id), None)
                export_top_edge = self.topology.get_edge_by_nodes(node_a, node_b)
            geo_node = model.GeoNode(geo_edge[1].lat, geo_edge[1].lon)
            export_top_edge.intermediate_geo_nodes.append(geo_node)

        return self.topology
   
   
if __name__ == '__main__':
    conv = ORMConverter()
    topology = conv.run("52.39385615174401 13.049869537353517 52.3902158368756 13.049440383911135 52.38821222613622 13.073966503143312 52.392153883603726 13.074588775634767")
    routes = generate_from_topology(topology)
    print(routes)
    pp = Generator().generate(topology.nodes.values(), topology.edges.values(), topology.signals.values(), Config(author_name="b", coord_representation="wgs84", organisation="b"), filename="out")

