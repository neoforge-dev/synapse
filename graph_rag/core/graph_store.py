import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

from graph_rag.models import Entity, Relationship

logger = logging.getLogger(__name__)

class GraphStore(ABC):
    """Abstract base class for storing and retrieving graph data."""

    @abstractmethod
    def add_entity(self, entity: Entity):
        """Adds or updates an entity (node) in the graph."""
        pass

    @abstractmethod
    def add_relationship(self, relationship: Relationship):
        """Adds a relationship (edge) between two entities."""
        pass

    @abstractmethod
    def add_entities_and_relationships(self, entities: List[Entity], relationships: List[Relationship]):
        """Adds multiple entities and relationships, ideally in a single transaction."""
        pass
        
    # Add query methods later as needed, e.g.:
    # @abstractmethod
    # def get_subgraph(self, center_entity_id: str, hops: int = 1) -> Tuple[List[Entity], List[Relationship]]:
    #     pass

    @abstractmethod
    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """Retrieves a single entity by its unique ID."""
        pass
        
    @abstractmethod
    def get_neighbors(self, entity_id: str, relationship_types: Optional[List[str]] = None, direction: str = "both") -> Tuple[List[Entity], List[Relationship]]:
        """Retrieves direct neighbors (entities and relationships) of a given entity.
        
        Args:
            entity_id: The ID of the central entity.
            relationship_types: Optional list of relationship types to filter by.
            direction: 'outgoing', 'incoming', or 'both' (default).
            
        Returns:
            A tuple containing a list of neighbor entities and a list of connecting relationships.
        """
        pass

    @abstractmethod
    def search_entities_by_properties(self, properties: Dict[str, Any], limit: Optional[int] = None) -> List[Entity]:
        """Searches for entities matching specific properties (e.g., name, type).
        
        Args:
            properties: A dictionary of property keys and values to match.
            limit: Optional maximum number of entities to return.
            
        Returns:
            A list of matching Entity objects.
        """
        pass

class MockGraphStore(GraphStore):
    """In-memory mock implementation of GraphStore for testing."""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.nodes: Dict[str, Dict] = {} # Generic node storage
        self.edges: List[Dict] = [] # Generic edge storage
        logger.info("MockGraphStore initialized.")

    def add_entity(self, entity: Entity):
        # Safely access name from properties for logging
        entity_name = entity.properties.get('name', '[name missing]')
        logger.debug(f"MockGraphStore: Adding entity {entity.id} ({entity_name})")
        self.entities[entity.id] = entity
        # Also add to generic nodes
        self.nodes[entity.id] = {
            "id": entity.id, 
            "label": entity.type, # Assuming type maps to label
            "properties": entity.properties
        }

    def add_relationship(self, relationship: Relationship):
        logger.debug(f"MockGraphStore: Adding relationship {relationship.type} from {relationship.source_id} to {relationship.target_id}")
        self.relationships.append(relationship)
        # Also add to generic edges
        self.edges.append({
            "source": relationship.source_id,
            "target": relationship.target_id,
            "type": relationship.type,
            "properties": relationship.properties
        })

    def add_entities_and_relationships(self, entities: List[Entity], relationships: List[Relationship]):
        logger.info(f"MockGraphStore: Bulk adding {len(entities)} entities and {len(relationships)} relationships.")
        for entity in entities:
            self.add_entity(entity)
        for relationship in relationships:
            # In a real bulk operation, relationships might be added even if entities
            # are part of the same batch. Here we add them after entities for simplicity.
            self.add_relationship(relationship)

    def clear(self):
        """Clears the mock store for test isolation."""
        self.entities = {}
        self.relationships = []
        self.nodes = {}
        self.edges = []
        logger.info("MockGraphStore cleared.")

    # --- Mock Query Implementations --- 

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        logger.debug(f"MockGraphStore: Getting entity by id: {entity_id}")
        return self.entities.get(entity_id)
        
    def get_neighbors(self, entity_id: str, relationship_types: Optional[List[str]] = None, direction: str = "both") -> Tuple[List[Entity], List[Relationship]]:
        logger.debug(f"MockGraphStore: Getting neighbors for {entity_id} (types: {relationship_types}, direction: {direction})")
        
        neighbor_entities: Dict[str, Entity] = {}
        connecting_relationships: List[Relationship] = []
        
        for rel in self.relationships:
            is_match = False
            neighbor_id = None
            
            # Check direction and relationship type
            if direction in ["outgoing", "both"] and rel.source.id == entity_id:
                if relationship_types is None or rel.type in relationship_types:
                    is_match = True
                    neighbor_id = rel.target.id
                    
            elif direction in ["incoming", "both"] and rel.target.id == entity_id:
                 if relationship_types is None or rel.type in relationship_types:
                    is_match = True
                    neighbor_id = rel.source.id # The neighbor is the source in this case
            
            # Add neighbor if match found
            if is_match and neighbor_id is not None:
                neighbor = self.entities.get(neighbor_id)
                if neighbor and neighbor_id not in neighbor_entities:
                    neighbor_entities[neighbor_id] = neighbor
                # Add the relationship regardless of whether neighbor exists (matches graph behavior)
                connecting_relationships.append(rel)
        
        logger.debug(f"MockGraphStore: Found {len(neighbor_entities)} neighbors and {len(connecting_relationships)} relationships for {entity_id}.")
        return list(neighbor_entities.values()), connecting_relationships

    def search_entities_by_properties(self, properties: Dict[str, Any], limit: Optional[int] = None) -> List[Entity]:
        logger.debug(f"MockGraphStore: Searching entities by properties: {properties}, limit: {limit}")
        
        matches = []
        for entity in self.entities.values():
            is_match = True
            # Check mandatory properties (like name, type)
            for key, value in properties.items():
                if key == 'type':
                    if entity.type != value:
                        is_match = False
                        break
                elif key == 'name':
                     if entity.name != value:
                        is_match = False
                        break
                # Check metadata properties
                elif key not in entity.metadata or entity.metadata[key] != value:
                    is_match = False
                    break
            
            if is_match:
                matches.append(entity)
                if limit is not None and len(matches) >= limit:
                    break
                    
        logger.debug(f"MockGraphStore: Found {len(matches)} entities matching properties.")
        return matches 

    # Implement other methods as needed for tests, returning mock data
    async def get_neighbors(self, node_id: str, relationship_type: Optional[str] = None, direction: str = "out") -> List[Dict]:
        # Simplified mock implementation
        neighbors = []
        if direction in ["out", "both"]:
            for edge in self.edges:
                if edge["source"] == node_id and (not relationship_type or edge["type"] == relationship_type):
                    target_node = self.nodes.get(edge["target"])
                    if target_node:
                        neighbors.append(target_node) # Return the node dict
        if direction in ["in", "both"]:
            for edge in self.edges:
                 if edge["target"] == node_id and (not relationship_type or edge["type"] == relationship_type):
                    source_node = self.nodes.get(edge["source"])
                    if source_node:
                        neighbors.append(source_node)
        logger.debug(f"MockGraphStore: Found {len(neighbors)} neighbors for {node_id}")
        return neighbors

    async def close(self) -> None:
        logger.info("MockGraphStore: close() called.")
        pass # No-op for mock 