#!/usr/bin/env python3
"""
Debug script to test the API query flow and see where it breaks.
"""
import logging

import requests

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_api_query():
    """Test the API query endpoint step by step."""

    # Test 1: Health check
    logger.info("=== Testing API health ===")
    try:
        response = requests.get("http://localhost:8000/health")
        logger.info(f"Health status: {response.status_code}")
        logger.info(f"Health response: {response.json()}")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return

    # Test 2: Vector store stats via admin endpoint
    logger.info("=== Testing vector store stats ===")
    try:
        response = requests.get("http://localhost:8000/api/v1/admin/vector/stats")
        logger.info(f"Vector stats status: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Vector stats: {response.json()}")
        else:
            logger.error(f"Vector stats error: {response.text}")
    except Exception as e:
        logger.error(f"Vector stats failed: {e}")

    # Test 3: Simple search query
    logger.info("=== Testing search query ===")
    try:
        search_payload = {
            "query": "LinkedIn development practices",
            "limit": 3
        }
        response = requests.post(
            "http://localhost:8000/api/v1/search/query",
            headers={"Content-Type": "application/json"},
            json=search_payload
        )
        logger.info(f"Search status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Search returned {len(result.get('results', []))} results")
            if result.get('results'):
                first_result = result['results'][0]
                logger.info(f"First result score: {first_result.get('score')}")
                logger.info(f"First result chunk ID: {first_result['chunk']['id']}")
        else:
            logger.error(f"Search error: {response.text}")
    except Exception as e:
        logger.error(f"Search failed: {e}")

    # Test 4: GraphRAG query (the failing one)
    logger.info("=== Testing GraphRAG query ===")
    try:
        query_payload = {
            "text": "What are some LinkedIn development practices?",
            "max_chunks": 5,
            "include_graph": False
        }
        response = requests.post(
            "http://localhost:8000/api/v1/query/ask",
            headers={"Content-Type": "application/json"},
            json=query_payload
        )
        logger.info(f"GraphRAG query status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"GraphRAG query response keys: {result.keys()}")
            logger.info(f"Answer: {result.get('answer', 'No answer')[:200]}...")
            logger.info(f"Retrieved chunks: {len(result.get('retrieved_chunks', []))}")
        else:
            logger.error(f"GraphRAG query error: {response.text}")
    except Exception as e:
        logger.error(f"GraphRAG query failed: {e}")

    # Test 5: Check if the issue is in the GraphRAGEngine retrieval
    logger.info("=== Testing vector store retrieval directly ===")
    try:
        search_payload = {
            "query": "LinkedIn development practices",
            "limit": 3,
            "search_type": "vector"
        }
        response = requests.post(
            "http://localhost:8000/api/v1/search/query",
            headers={"Content-Type": "application/json"},
            json=search_payload
        )
        logger.info(f"Direct vector search status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Direct vector search returned {len(result.get('results', []))} results")
            for i, result_item in enumerate(result.get('results', [])[:2]):
                chunk = result_item.get('chunk', {})
                logger.info(f"Result {i}: score={result_item.get('score')}, text_preview='{chunk.get('text', '')[:100]}...'")
    except Exception as e:
        logger.error(f"Direct vector search failed: {e}")

if __name__ == "__main__":
    test_api_query()
