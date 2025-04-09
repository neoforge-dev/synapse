from typing import Protocol, List, Dict, Any, Optional, Tuple
from pydantic import BaseModel

class NodeData(BaseModel):
    label: str
    properties: Dict[str, Any]
    # Expect 'id' property within properties for uniqueness

class RelationshipData(BaseModel):
    type: str
    properties: Dict[str, Any]

class GraphStore(Protocol):
    """Interface for interacting with a graph database."""

    async def connect(self) -> None:
        """Establish connection to the database."""
        ...

    async def close(self) -> None:
        """Close connection to the database."""
        ...

    async def add_node(self, label: str, properties: Dict[str, Any]) -> str:
        """Adds or merges a node. Assumes 'id' in properties for merging.
           Returns the node ID."""
        ...

    async def add_relationship(
        self, 
        source_node_id: str, 
        target_node_id: str, 
        rel_type: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Adds a relationship between two existing nodes (matched by 'id')."""
        ...

    async def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a node's properties by its ID."""
        ...
        
    async def query_subgraph(
        self, 
        start_node_id: str, 
        max_depth: int = 1,
        relationship_types: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Queries a subgraph starting from a node. 
           Returns a tuple: (list_of_nodes, list_of_relationships)."""
        ...

    async def detect_communities(
        self, 
        algorithm: str = "louvain", 
        write_property: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Runs a community detection algorithm (requires MAGE).
           Returns list of nodes with their community IDs.
           Optionally writes community ID back to nodes.
        """
        ...
        
    async def execute_read(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Executes a read-only Cypher query."""
        ...
        
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Executes a write Cypher query."""
        ...
        
    async def apply_schema_constraints(self) -> None:
        """Applies predefined schema constraints (e.g., uniqueness)."""
        ... 