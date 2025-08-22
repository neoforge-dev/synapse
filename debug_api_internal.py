#!/usr/bin/env python3
"""Debug script to check API internal state via request debug endpoint."""

from fastapi import Request
from fastapi.routing import APIRouter

# We need to add a debug endpoint to the running API
# This script shows what we'd need to add, but we need to modify the API code

async def debug_api_state():
    """Debug the internal state of the running API."""
    print("=" * 50)
    print("DEBUGGING API INTERNAL STATE")
    print("=" * 50)

    # This would need to be added as an endpoint to the API
    debug_info = {
        "message": "This script shows what we need to add to the API",
        "suggestion": "Add a debug endpoint to check GraphRAGEngine vector store state"
    }

    print(json.dumps(debug_info, indent=2))

# Debug endpoint that should be added to the API
def create_debug_router() -> APIRouter:
    """Create debug router to add to API."""
    router = APIRouter()

    @router.get("/debug/engine-state")
    async def debug_engine_state(request: Request):
        """Debug endpoint to check GraphRAGEngine state."""
        try:
            # Get the engine from app state
            engine = request.app.state.graph_rag_engine
            vector_store = engine._vector_store

            # Check vector store state
            await vector_store._ensure_loaded()
            size = await vector_store.get_vector_store_size()

            # Test a direct search
            test_results = await vector_store.search("linkedin", top_k=3)

            return {
                "engine_type": type(engine).__name__,
                "vector_store_type": type(vector_store).__name__,
                "vector_store_size": size,
                "vector_store_path": getattr(vector_store, 'storage_path', 'unknown'),
                "load_attempted": getattr(vector_store, '_load_attempted', 'unknown'),
                "test_search_results": len(test_results),
                "test_search_scores": [r.score for r in test_results[:3]]
            }
        except Exception as e:
            return {"error": str(e), "type": type(e).__name__}

    return router

if __name__ == "__main__":
    print("This script shows debug code that needs to be added to the API.")
    print("We need to add a debug endpoint to inspect the GraphRAGEngine state.")
    print("Let's modify the API directly instead...")
