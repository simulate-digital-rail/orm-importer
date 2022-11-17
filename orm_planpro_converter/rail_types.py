from dataclasses import dataclass
from overpy import Node

@dataclass
class Signal:
    node: Node
    edge: "tuple[Node, Node]"
    distance_side: float
    distance_node_before: float
    kind: str
    function: str
    direction: str
    element_name: str
