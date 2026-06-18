from enum import Enum
from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    CASE = "case"
    SUSPECT = "suspect"


class EdgeKind(str, Enum):
    MENTIONS = "mentions"            # case → suspect
    CO_SUSPECT = "co_suspect"        # suspect ↔ suspect (via shared case)


class NetworkNode(BaseModel):
    id: str
    label: str
    kind: NodeKind
    properties: dict[str, str | int | None] = Field(default_factory=dict)


class NetworkEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: EdgeKind
    weight: int = 1                  # for CO_SUSPECT, the count of shared cases


class NetworkResponse(BaseModel):
    center_id: str                   # the node the graph is centered on
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    depth: int                       # number of hops expanded from center
