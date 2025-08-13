"""Saved query management system for complex query persistence."""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class SavedQueryManager:
    """Manages saved queries for users."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else Path.cwd() / "saved_queries.json"
        self.queries = self._load_queries()
        logger.info("SavedQueryManager initialized")
    
    def save_query(self, query_data: Dict[str, Any]) -> str:
        """Save a query and return its ID."""
        # Generate unique ID
        query_id = str(uuid.uuid4())
        
        # Add metadata
        query_with_metadata = {
            "id": query_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **query_data
        }
        
        # Validate query structure
        if not self._validate_query(query_with_metadata):
            raise ValueError("Invalid query structure")
        
        self.queries[query_id] = query_with_metadata
        self._persist_queries()
        
        logger.info(f"Saved query: {query_data.get('name', 'unnamed')} with ID {query_id}")
        return query_id
    
    def get_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a query by ID."""
        return self.queries.get(query_id)
    
    def update_query(self, query_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing query."""
        if query_id not in self.queries:
            return False
        
        self.queries[query_id].update(updates)
        self.queries[query_id]["updated_at"] = datetime.now().isoformat()
        self._persist_queries()
        
        logger.info(f"Updated query {query_id}")
        return True
    
    def delete_query(self, query_id: str) -> bool:
        """Delete a query."""
        if query_id in self.queries:
            del self.queries[query_id]
            self._persist_queries()
            logger.info(f"Deleted query {query_id}")
            return True
        return False
    
    def list_user_queries(self, user_id: str) -> List[Dict[str, Any]]:
        """List all queries for a specific user."""
        user_queries = [
            query for query in self.queries.values()
            if query.get("created_by") == user_id
        ]
        
        # Sort by creation date (newest first)
        user_queries.sort(
            key=lambda q: q.get("created_at", ""), 
            reverse=True
        )
        
        return user_queries
    
    def list_public_queries(self) -> List[Dict[str, Any]]:
        """List all public queries."""
        public_queries = [
            query for query in self.queries.values()
            if query.get("is_public", False)
        ]
        
        # Sort by popularity/usage
        public_queries.sort(
            key=lambda q: q.get("usage_count", 0),
            reverse=True
        )
        
        return public_queries
    
    def search_queries(self, search_term: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search queries by name or description."""
        search_term_lower = search_term.lower()
        matching_queries = []
        
        for query in self.queries.values():
            # Check if user has access to this query
            if user_id and not self._user_can_access_query(query, user_id):
                continue
            
            # Search in name and description
            name = query.get("name", "").lower()
            description = query.get("description", "").lower()
            
            if search_term_lower in name or search_term_lower in description:
                matching_queries.append(query)
        
        return matching_queries
    
    def get_query_stats(self, query_id: str) -> Dict[str, Any]:
        """Get usage statistics for a query."""
        query = self.get_query(query_id)
        if not query:
            return {}
        
        return {
            "usage_count": query.get("usage_count", 0),
            "last_used": query.get("last_used"),
            "created_at": query.get("created_at"),
            "updated_at": query.get("updated_at"),
            "is_public": query.get("is_public", False),
            "created_by": query.get("created_by")
        }
    
    def increment_usage(self, query_id: str):
        """Increment usage count for a query."""
        if query_id in self.queries:
            query = self.queries[query_id]
            query["usage_count"] = query.get("usage_count", 0) + 1
            query["last_used"] = datetime.now().isoformat()
            self._persist_queries()
    
    def duplicate_query(self, query_id: str, new_name: str, user_id: str) -> Optional[str]:
        """Duplicate an existing query for a user."""
        original_query = self.get_query(query_id)
        if not original_query:
            return None
        
        # Create new query based on original
        new_query = {
            "name": new_name,
            "description": f"Copy of {original_query.get('name', 'unnamed query')}",
            "query": original_query["query"].copy(),
            "created_by": user_id,
            "is_public": False  # Copies are private by default
        }
        
        return self.save_query(new_query)
    
    def export_queries(self, user_id: str) -> Dict[str, Any]:
        """Export all queries for a user."""
        user_queries = self.list_user_queries(user_id)
        
        export_data = {
            "export_date": datetime.now().isoformat(),
            "user_id": user_id,
            "query_count": len(user_queries),
            "queries": user_queries
        }
        
        return export_data
    
    def import_queries(self, import_data: Dict[str, Any], user_id: str) -> List[str]:
        """Import queries from export data."""
        imported_ids = []
        
        queries_to_import = import_data.get("queries", [])
        for query_data in queries_to_import:
            # Update metadata for import
            import_query = query_data.copy()
            import_query["created_by"] = user_id
            import_query["is_public"] = False  # Imported queries are private
            
            # Remove ID to generate new one
            import_query.pop("id", None)
            
            try:
                new_id = self.save_query(import_query)
                imported_ids.append(new_id)
            except ValueError as e:
                logger.warning(f"Skipped invalid query during import: {e}")
        
        logger.info(f"Imported {len(imported_ids)} queries for user {user_id}")
        return imported_ids
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular public queries."""
        public_queries = self.list_public_queries()
        
        # Sort by usage count
        popular_queries = sorted(
            public_queries,
            key=lambda q: q.get("usage_count", 0),
            reverse=True
        )
        
        return popular_queries[:limit]
    
    def _validate_query(self, query_data: Dict[str, Any]) -> bool:
        """Validate query structure."""
        required_fields = ["name", "query"]
        return all(field in query_data for field in required_fields)
    
    def _user_can_access_query(self, query: Dict[str, Any], user_id: str) -> bool:
        """Check if user can access a query."""
        # User can access their own queries or public queries
        return (query.get("created_by") == user_id or 
                query.get("is_public", False))
    
    def _load_queries(self) -> Dict[str, Dict[str, Any]]:
        """Load queries from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Could not load saved queries: {e}")
        
        return {}
    
    def _persist_queries(self):
        """Persist queries to storage."""
        try:
            # Create directory if it doesn't exist
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_path, 'w') as f:
                json.dump(self.queries, f, indent=2)
        except IOError as e:
            logger.error(f"Could not persist saved queries: {e}")
    
    def cleanup_old_queries(self, days_old: int = 365):
        """Clean up old unused queries."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cutoff_iso = cutoff_date.isoformat()
        
        queries_to_delete = []
        for query_id, query in self.queries.items():
            # Skip public queries and recently used queries
            if query.get("is_public", False):
                continue
            
            last_used = query.get("last_used", query.get("created_at", ""))
            if last_used < cutoff_iso:
                queries_to_delete.append(query_id)
        
        # Delete old queries
        for query_id in queries_to_delete:
            del self.queries[query_id]
        
        if queries_to_delete:
            self._persist_queries()
            logger.info(f"Cleaned up {len(queries_to_delete)} old queries")
        
        return len(queries_to_delete)