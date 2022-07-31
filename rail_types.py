from dataclasses import dataclass
from overpy import Node

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __repr__(self):
        x1,x2 = min(self.x1,self.x2), max(self.x1,self.x2)
        y1,y2 = min(self.y1,self.y2), max(self.y1,self.y2)
        return f'{x1},{y1},{x2},{y2}'

@dataclass
class Signal:
    node: Node
    edge: "tuple[Node, Node]"
    distance_side: float
    distance_node_before: float
    kind: str
    function: str
