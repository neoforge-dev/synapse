#!/usr/bin/env python3
"""Debug script to test API endpoint configuration."""

import asyncio
import logging
import requests
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_api_query():
    """Test API query with different configurations."""
    print("=" * 50)
    print("DEBUGGING API QUERY CONFIGURATION")
    print("=" * 50)
    
    base_url = "http://localhost:8004/api/v1/query/ask"
    
    # Test 1: Basic request (using defaults)
    print("1. Testing basic request (defaults)...")
    basic_request = {
        "text": "What are some LinkedIn development practices?"
    }
    
    try:
        response = requests.post(base_url, json=basic_request, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Answer preview: {result.get('answer', '')[:200]}...")
            print(f"Chunks found: {len(result.get('relevant_chunks', []))}")
            print(f"Config in metadata: {result.get('metadata', {}).get('config', {})}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Explicit vector search
    print("\n2. Testing explicit vector search...")
    vector_request = {
        "text": "What are some LinkedIn development practices?",
        "search_type": "vector",
        "k": 3,
        "include_graph": False
    }
    
    try:
        response = requests.post(base_url, json=vector_request, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Answer preview: {result.get('answer', '')[:200]}...")
            print(f"Chunks found: {len(result.get('relevant_chunks', []))}")
            print(f"Config in metadata: {result.get('metadata', {}).get('config', {})}")
            if result.get('relevant_chunks'):
                print(f"First chunk preview: {result['relevant_chunks'][0].get('text', '')[:100]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Different query text
    print("\n3. Testing with simpler query...")
    simple_request = {
        "text": "linkedin",
        "search_type": "vector",
        "k": 3
    }
    
    try:
        response = requests.post(base_url, json=simple_request, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Answer preview: {result.get('answer', '')[:200]}...")
            print(f"Chunks found: {len(result.get('relevant_chunks', []))}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_query()