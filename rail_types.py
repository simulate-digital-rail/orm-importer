from dataclasses import dataclass
from overpy import Node

@dataclass
class Signal:
    node: Node
    edge: "tuple[Node, Node]"