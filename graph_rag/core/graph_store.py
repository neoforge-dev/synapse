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

class MockGraphStore(GraphStore):
    """In-memory mock implementation of GraphStore for testing."""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.calls: Dict[str, List[Any]] = {
            "add_entity": [],
            "add_relationship": [],
            "add_entities_and_relationships": [],
            "get_entity_by_id": [],
            "get_neighbors": []
        }
        logger.info("MockGraphStore initialized.")

    def add_entity(self, entity: Entity):
        logger.debug(f"MockGraphStore: Adding entity {entity.id} ({entity.name})")
        self.entities[entity.id] = entity
        self.calls["add_entity"].append(entity)

    def add_relationship(self, relationship: Relationship):
        logger.debug(f"MockGraphStore: Adding relationship {relationship.source.id} -> {relationship.target.id} ({relationship.type})")
        # Basic check if entities exist (in a real store, this might be handled by constraints)
        if relationship.source.id not in self.entities:
            logger.warning(f"Source entity {relationship.source.id} not found for relationship.")
            # Decide on behavior: raise error or just log?
        if relationship.target.id not in self.entities:
            logger.warning(f"Target entity {relationship.target.id} not found for relationship.")
            
        self.relationships.append(relationship)
        self.calls["add_relationship"].append(relationship)

    def add_entities_and_relationships(self, entities: List[Entity], relationships: List[Relationship]):
        logger.info(f"MockGraphStore: Bulk adding {len(entities)} entities and {len(relationships)} relationships.")
        self.calls["add_entities_and_relationships"].append((entities, relationships))
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
        self.calls = {
            "add_entity": [], 
            "add_relationship": [], 
            "add_entities_and_relationships": [],
            "get_entity_by_id": [],
            "get_neighbors": []
            }
        logger.info("MockGraphStore cleared.")

    # --- Mock Query Implementations --- 

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        logger.debug(f"MockGraphStore: Getting entity by id: {entity_id}")
        self.calls["get_entity_by_id"].append(entity_id)
        return self.entities.get(entity_id)
        
    def get_neighbors(self, entity_id: str, relationship_types: Optional[List[str]] = None, direction: str = "both") -> Tuple[List[Entity], List[Relationship]]:
        logger.debug(f"MockGraphStore: Getting neighbors for {entity_id} (types: {relationship_types}, direction: {direction})")
        self.calls["get_neighbors"].append((entity_id, relationship_types, direction))
        
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