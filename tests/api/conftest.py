# import pytest
# import pytest_asyncio # For async fixtures
# from typing import AsyncGenerator

# from httpx import AsyncClient, ASGITransport

# # Import the FastAPI app instance
# # Adjust path as needed
# from graph_rag.api.main import app 

# @pytest_asyncio.fixture(scope="function")
# async def test_client() -> AsyncGenerator[AsyncClient, None]:
#     """Provides an asynchronous test client for the FastAPI app."""
#     # Use base_url="http://test" as recommended by FastAPI docs for testing
#     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
#         # You could potentially override dependencies here for testing if needed
#         # e.g., mock the MemgraphStore or EmbeddingService
#         # See FastAPI documentation on testing dependencies: 
#         # https://fastapi.tiangolo.com/advanced/testing-dependencies/
        
#         yield client
        
#         # Cleanup after tests if needed

# This file can be used to define fixtures specific to API tests.
# Currently empty as the main test_client is defined in the root conftest.py 