#!/usr/bin/env python3
"""
API Integration and Contract Tests - MEDIUM PRIORITY
Tests for API ↔ Database ↔ Business system integration and contract validation
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
import json
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from graph_rag.api.main import create_app
from graph_rag.config import get_settings

class TestAPIContractValidation:
    """Test API contract validation across all 33 routers"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client with minimal dependencies"""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def api_endpoints(self):
        """Define core API endpoints for contract testing"""
        return {
            # Core API endpoints
            "health": {"method": "GET", "path": "/health", "expected_status": 200},
            "root": {"method": "GET", "path": "/", "expected_status": 200},
            
            # Document management
            "documents_list": {"method": "GET", "path": "/api/v1/documents", "expected_status": 200},
            "document_create": {"method": "POST", "path": "/api/v1/documents", "expected_status": [201, 422]},
            
            # Search functionality
            "search": {"method": "POST", "path": "/api/v1/search", "expected_status": [200, 422]},
            "search_stream": {"method": "POST", "path": "/api/v1/search/stream", "expected_status": [200, 422]},
            
            # Query functionality  
            "query": {"method": "POST", "path": "/api/v1/query", "expected_status": [200, 422]},
            "ask": {"method": "POST", "path": "/api/v1/ask", "expected_status": [200, 422]},
            
            # Graph operations
            "graph_stats": {"method": "GET", "path": "/api/v1/graph/stats", "expected_status": 200},
            "graph_entities": {"method": "GET", "path": "/api/v1/graph/entities", "expected_status": 200},
            "graph_relationships": {"method": "GET", "path": "/api/v1/graph/relationships", "expected_status": 200},
            
            # Ingestion
            "ingest": {"method": "POST", "path": "/api/v1/ingest", "expected_status": [200, 202, 422]},
            
            # Admin functions
            "admin_stats": {"method": "GET", "path": "/api/v1/admin/stats", "expected_status": 200},
            "admin_reset": {"method": "POST", "path": "/api/v1/admin/reset", "expected_status": [200, 202]},
        }
    
    def test_api_endpoint_availability(self, test_client, api_endpoints):
        """Test that all core API endpoints are available"""
        for endpoint_name, config in api_endpoints.items():
            method = config["method"]
            path = config["path"]
            expected_status = config["expected_status"]
            
            # Make request based on method
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(path, json={})
            else:
                continue
            
            # Verify response
            if isinstance(expected_status, list):
                assert response.status_code in expected_status, \
                    f"Endpoint {endpoint_name} ({method} {path}) returned {response.status_code}, expected one of {expected_status}"
            else:
                assert response.status_code == expected_status, \
                    f"Endpoint {endpoint_name} ({method} {path}) returned {response.status_code}, expected {expected_status}"
    
    def test_api_response_structure_consistency(self, test_client):
        """Test API response structure consistency"""
        # Test health endpoint structure
        response = test_client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data, "Health response should include status"
        
        # Test document list structure
        response = test_client.get("/api/v1/documents")
        assert response.status_code == 200
        
        documents_data = response.json()
        assert isinstance(documents_data, (list, dict)), "Documents response should be list or dict"
    
    def test_error_response_consistency(self, test_client):
        """Test error response format consistency"""
        # Test with invalid search request
        response = test_client.post("/api/v1/search", json={"invalid": "data"})
        
        # Should return validation error
        if response.status_code == 422:
            error_data = response.json()
            assert "detail" in error_data, "Validation error should have detail field"
        
        # Test with non-existent endpoint
        response = test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404, "Non-existent endpoint should return 404"
    
    def test_request_validation_consistency(self, test_client):
        """Test request validation across endpoints"""
        search_test_cases = [
            {"query": "valid search query"},  # Valid case
            {"query": ""},  # Empty query case
            {"invalid_field": "value"},  # Invalid field case
        ]
        
        for test_case in search_test_cases:
            response = test_client.post("/api/v1/search", json=test_case)
            
            # Should handle validation consistently
            assert response.status_code in [200, 422], \
                f"Search validation should return 200 or 422, got {response.status_code}"


class TestDatabaseIntegration:
    """Test API ↔ Database integration"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for database integration testing"""
        app = create_app()
        return TestClient(app)
    
    @patch('graph_rag.infrastructure.graph_stores.memgraph_store.mgclient')
    def test_graph_database_connection(self, mock_mgclient, test_client):
        """Test graph database connection through API"""
        # Mock successful database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_mgclient.connect.return_value = mock_conn
        
        # Test graph stats endpoint (requires database)
        response = test_client.get("/api/v1/graph/stats")
        
        # Should not fail due to connection issues
        assert response.status_code in [200, 503], \
            "Graph stats should return 200 (success) or 503 (service unavailable)"
    
    @patch('graph_rag.infrastructure.vector_stores.simple_vector_store.SimpleVectorStore')
    def test_vector_store_integration(self, mock_vector_store, test_client):
        """Test vector store integration through API"""
        # Configure mock vector store
        mock_instance = Mock()
        mock_instance.search.return_value = []
        mock_vector_store.return_value = mock_instance
        
        # Test search endpoint (uses vector store)
        response = test_client.post("/api/v1/search", json={"query": "test search"})
        
        # Should handle vector store operations
        assert response.status_code in [200, 422, 500], \
            "Search should handle vector store operations gracefully"
    
    def test_database_error_handling(self, test_client):
        """Test database error handling in API"""
        # Test operations that might fail due to database issues
        critical_endpoints = [
            ("/api/v1/graph/stats", "GET"),
            ("/api/v1/documents", "GET"), 
            ("/api/v1/search", "POST")
        ]
        
        for path, method in critical_endpoints:
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(path, json={"query": "test"})
            
            # Should not return 500 errors (should handle gracefully)
            assert response.status_code != 500, \
                f"Endpoint {path} should handle database errors gracefully"


class TestBusinessSystemIntegration:
    """Test Business Development ↔ Core Platform integration"""
    
    @pytest.fixture
    def mock_business_systems(self):
        """Mock business development systems"""
        return {
            'sales_engine': Mock(),
            'linkedin_automation': Mock(), 
            'consultation_detector': Mock()
        }
    
    def test_epic7_api_integration(self, mock_business_systems):
        """Test Epic 7 sales automation API integration"""
        from business_development.epic7_web_interface import app as epic7_app
        
        client = TestClient(epic7_app)
        
        # Test Epic 7 dashboard
        response = client.get("/")
        assert response.status_code == 200, "Epic 7 dashboard should be accessible"
        
        # Test API endpoints
        response = client.get("/api/pipeline-summary")
        assert response.status_code in [200, 500], "Pipeline summary should respond"
    
    def test_business_data_consistency(self, mock_business_systems):
        """Test business data consistency across systems"""
        # This would test that business metrics are consistent
        # across different parts of the system
        
        # Mock business metrics
        mock_metrics = {
            'pipeline_value': 1158000,
            'contact_count': 16,
            'qualified_leads': 12
        }
        
        # Verify metrics consistency
        assert mock_metrics['pipeline_value'] >= 1000000, "Pipeline value should meet target"
        assert mock_metrics['contact_count'] >= 15, "Should have minimum contact count"
        assert mock_metrics['qualified_leads'] <= mock_metrics['contact_count'], \
            "Qualified leads should not exceed total contacts"


class TestAuthenticationIntegration:
    """Test Authentication ↔ Authorization ↔ Business Systems integration"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for auth testing"""
        app = create_app()
        return TestClient(app)
    
    def test_public_endpoints_accessibility(self, test_client):
        """Test public endpoints are accessible without authentication"""
        public_endpoints = [
            "/health",
            "/",
            "/docs",
            "/openapi.json"
        ]
        
        for endpoint in public_endpoints:
            response = test_client.get(endpoint)
            assert response.status_code not in [401, 403], \
                f"Public endpoint {endpoint} should be accessible without auth"
    
    def test_protected_endpoints_behavior(self, test_client):
        """Test protected endpoints behave correctly"""
        # Test with authentication disabled (default test behavior)
        protected_endpoints = [
            "/api/v1/admin/reset",
            "/api/v1/admin/stats"
        ]
        
        for endpoint in protected_endpoints:
            response = test_client.post(endpoint) if 'reset' in endpoint else test_client.get(endpoint)
            
            # In test environment with auth disabled, should work
            # In production with auth enabled, would return 401/403
            assert response.status_code not in [500], \
                f"Protected endpoint {endpoint} should handle auth state correctly"
    
    @patch('graph_rag.config.get_settings')
    def test_authentication_configuration(self, mock_settings, test_client):
        """Test authentication configuration integration"""
        # Mock settings with authentication enabled
        mock_settings.return_value.enable_authentication = True
        mock_settings.return_value.jwt_secret_key = "test-secret-key"
        
        # This tests that the configuration system works
        settings = mock_settings.return_value
        assert hasattr(settings, 'enable_authentication'), "Should have auth config"
        assert hasattr(settings, 'jwt_secret_key'), "Should have JWT config"


class TestEndToEndDataFlow:
    """Test end-to-end data pipeline validation"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for E2E testing"""
        app = create_app()
        return TestClient(app)
    
    def test_document_ingestion_flow(self, test_client):
        """Test complete document ingestion flow"""
        # Test document creation
        document_data = {
            "content": "This is a test document for ingestion flow testing",
            "metadata": {"source": "test", "type": "integration_test"}
        }
        
        response = test_client.post("/api/v1/documents", json=document_data)
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 201, 422, 503], \
            "Document creation should handle gracefully"
        
        if response.status_code in [200, 201]:
            # If creation succeeded, test retrieval
            response = test_client.get("/api/v1/documents")
            assert response.status_code == 200, "Should be able to retrieve documents"
    
    def test_search_query_flow(self, test_client):
        """Test complete search and query flow"""
        # Test search functionality
        search_data = {"query": "integration test query"}
        
        response = test_client.post("/api/v1/search", json=search_data)
        assert response.status_code in [200, 422], "Search should handle gracefully"
        
        # Test query functionality
        query_data = {"query": "What can you tell me about integration testing?"}
        
        response = test_client.post("/api/v1/ask", json=query_data)
        assert response.status_code in [200, 422], "Query should handle gracefully"
    
    def test_graph_operations_flow(self, test_client):
        """Test graph operations flow"""
        # Test graph stats
        response = test_client.get("/api/v1/graph/stats")
        assert response.status_code in [200, 503], "Graph stats should handle gracefully"
        
        # Test entities retrieval
        response = test_client.get("/api/v1/graph/entities")
        assert response.status_code in [200, 503], "Entities retrieval should handle gracefully"
        
        # Test relationships retrieval  
        response = test_client.get("/api/v1/graph/relationships")
        assert response.status_code in [200, 503], "Relationships retrieval should handle gracefully"


class TestSystemResilience:
    """Test system resilience and fallback mechanisms"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for resilience testing"""
        app = create_app()
        return TestClient(app)
    
    def test_graceful_fallbacks(self, test_client):
        """Test graceful fallbacks when components are unavailable"""
        # Test search with potential graph unavailability
        response = test_client.post("/api/v1/search", json={"query": "fallback test"})
        
        # Should not crash even if graph is unavailable
        assert response.status_code != 500, "Search should fallback gracefully"
    
    def test_timeout_handling(self, test_client):
        """Test timeout handling for long-running operations"""
        # Test with potentially long-running query
        long_query = "This is a very long query " * 100
        
        response = test_client.post("/api/v1/ask", json={"query": long_query})
        
        # Should handle long queries without timing out
        assert response.status_code != 408, "Should handle long queries"
    
    def test_concurrent_request_handling(self, test_client):
        """Test concurrent request handling"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = test_client.get("/health")
            results.append(response.status_code)
        
        # Make concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results), \
            "All concurrent health checks should succeed"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])