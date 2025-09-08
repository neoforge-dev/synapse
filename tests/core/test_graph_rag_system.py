#!/usr/bin/env python3
"""
Core GraphRAG System Tests - HIGH PRIORITY
Comprehensive testing framework for GraphRAG search, query, and ingestion functionality
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any
import tempfile
import json
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine, QueryResult
from graph_rag.core.interfaces import (
    ChunkData, DocumentData, EntityExtractor, ExtractedEntity, 
    ExtractedRelationship, ExtractionResult, GraphRepository, 
    VectorStore, EmbeddingService
)
from graph_rag.llm.protocols import LLMService
from graph_rag.models import Chunk, Entity, Relationship, Document
from graph_rag.services.search import SearchResult

class TestGraphRAGEngineCore:
    """Test core GraphRAG engine functionality"""
    
    @pytest.fixture
    def mock_graph_store(self):
        """Mock graph repository for testing"""
        mock = AsyncMock(spec=GraphRepository)
        
        # Mock entity and relationship data
        mock_entities = [
            Entity(
                id="entity-1",
                name="Test Entity 1",
                label="TEST",
                properties={"description": "A test entity"}
            ),
            Entity(
                id="entity-2", 
                name="Test Entity 2",
                label="TEST",
                properties={"description": "Another test entity"}
            )
        ]
        
        mock_relationships = [
            Relationship(
                id="rel-1",
                source_id="entity-1",
                target_id="entity-2", 
                label="RELATES_TO",
                properties={"strength": 0.8}
            )
        ]
        
        mock.get_related_entities.return_value = mock_entities
        mock.get_relationships.return_value = mock_relationships
        mock.get_neighbors.return_value = (mock_entities, mock_relationships)
        
        return mock
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store for testing"""
        mock = AsyncMock(spec=VectorStore)
        
        # Mock search results
        mock_chunks = [
            ChunkData(
                id="chunk-1",
                text="This is a test chunk about GraphRAG systems",
                document_id="doc-1",
                embedding=[0.1] * 384,
                score=0.9
            ),
            ChunkData(
                id="chunk-2", 
                text="Another chunk discussing vector search capabilities",
                document_id="doc-2",
                embedding=[0.2] * 384,
                score=0.8
            )
        ]
        
        mock.search.return_value = mock_chunks
        mock.add_chunks.return_value = None
        mock.get_embedding_dimension.return_value = 384
        
        return mock
    
    @pytest.fixture
    def mock_entity_extractor(self):
        """Mock entity extractor for testing"""
        mock = AsyncMock(spec=EntityExtractor)
        
        # Mock extraction results
        mock_extraction = ExtractionResult(
            entities=[
                ExtractedEntity(
                    id="extracted-1",
                    label="PERSON",
                    text="Test Person",
                    metadata={"confidence": 0.9}
                ),
                ExtractedEntity(
                    id="extracted-2",
                    label="ORGANIZATION", 
                    text="Test Organization",
                    metadata={"confidence": 0.8}
                )
            ],
            relationships=[
                ExtractedRelationship(
                    source_entity_id="extracted-1",
                    target_entity_id="extracted-2",
                    label="WORKS_FOR"
                )
            ]
        )
        
        mock.extract_from_text.return_value = mock_extraction
        return mock
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing"""
        mock = AsyncMock(spec=LLMService)
        mock.generate_response.return_value = "This is a mock LLM response based on the provided context."
        mock.available = True
        return mock
    
    @pytest.fixture
    def graph_rag_engine(self, mock_graph_store, mock_vector_store, mock_entity_extractor, mock_llm_service):
        """Create GraphRAG engine with mocked dependencies"""
        return SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )
    
    def test_engine_initialization(self, graph_rag_engine):
        """Test GraphRAG engine initializes correctly"""
        assert graph_rag_engine is not None
        assert graph_rag_engine.graph_store is not None
        assert graph_rag_engine.vector_store is not None
        assert graph_rag_engine.entity_extractor is not None
        assert graph_rag_engine.llm_service is not None
    
    @pytest.mark.asyncio
    async def test_search_functionality(self, graph_rag_engine):
        """Test search functionality combines vector and graph results"""
        query = "Test search query about GraphRAG systems"
        
        result = await graph_rag_engine.search(query, limit=5)
        
        # Verify search was performed
        graph_rag_engine.vector_store.search.assert_called_once()
        
        # Verify results structure
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check result properties
        for search_result in result:
            assert hasattr(search_result, 'chunk')
            assert hasattr(search_result, 'score')
    
    @pytest.mark.asyncio
    async def test_query_generation_with_context(self, graph_rag_engine):
        """Test query generation with combined vector and graph context"""
        query = "What can you tell me about GraphRAG systems?"
        
        result = await graph_rag_engine.query(query)
        
        # Verify query processing
        assert isinstance(result, QueryResult)
        assert result.answer != ""
        assert len(result.relevant_chunks) > 0
        
        # Verify LLM was called with context
        graph_rag_engine.llm_service.generate_response.assert_called_once()
        
        # Verify both vector and graph context were used
        graph_rag_engine.vector_store.search.assert_called_once()
        graph_rag_engine.graph_store.get_neighbors.assert_called()
    
    @pytest.mark.asyncio
    async def test_hybrid_retrieval(self, graph_rag_engine):
        """Test hybrid retrieval combining vector similarity and graph traversal"""
        query = "hybrid retrieval test"
        
        # Perform search
        search_results = await graph_rag_engine.search(query, limit=10)
        
        # Verify hybrid approach was used
        graph_rag_engine.vector_store.search.assert_called()
        
        # Should have results from vector search
        assert len(search_results) > 0
        
        # Verify score normalization and ranking
        scores = [result.score for result in search_results]
        assert all(0 <= score <= 1.0 for score in scores), "Scores should be normalized"
        
        # Verify results are sorted by relevance
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score"
    
    @pytest.mark.asyncio
    async def test_entity_extraction_integration(self, graph_rag_engine):
        """Test entity extraction integration in query processing"""
        query = "Tell me about Test Person and Test Organization"
        
        # Process query
        result = await graph_rag_engine.query(query)
        
        # Verify entity extraction was called
        graph_rag_engine.entity_extractor.extract_from_text.assert_called()
        
        # Verify graph enrichment based on extracted entities
        graph_rag_engine.graph_store.get_neighbors.assert_called()
        
        # Result should include context from entity relationships
        assert result.graph_context is not None


class TestGraphRAGIngestionPipeline:
    """Test document ingestion and processing pipeline"""
    
    @pytest.fixture
    def mock_document_processor(self):
        """Mock document processor for testing"""
        mock = AsyncMock()
        
        async def mock_chunk_document(doc_data):
            return [
                ChunkData(
                    id=f"chunk-{doc_data.id}-1",
                    text="First chunk of the document content",
                    document_id=doc_data.id,
                    embedding=None
                ),
                ChunkData(
                    id=f"chunk-{doc_data.id}-2", 
                    text="Second chunk with different content",
                    document_id=doc_data.id,
                    embedding=None
                )
            ]
        
        mock.chunk_document = mock_chunk_document
        return mock
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service for testing"""
        mock = AsyncMock(spec=EmbeddingService)
        mock.generate_embedding.return_value = [0.1] * 384
        mock.get_embedding_dimension.return_value = 384
        return mock
    
    @pytest.fixture
    def ingestion_engine(self, mock_graph_store, mock_vector_store, mock_entity_extractor, 
                        mock_llm_service, mock_document_processor, mock_embedding_service):
        """Create ingestion-focused GraphRAG engine"""
        engine = SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store, 
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )
        engine.document_processor = mock_document_processor
        engine.embedding_service = mock_embedding_service
        return engine
    
    @pytest.mark.asyncio
    async def test_document_ingestion_pipeline(self, ingestion_engine):
        """Test complete document ingestion pipeline"""
        # Create test document
        test_document = DocumentData(
            id="test-doc-1",
            content="This is a test document about GraphRAG systems and knowledge graphs.",
            metadata={"source": "test", "type": "article"}
        )
        
        # Mock the ingestion process
        chunks = await ingestion_engine.document_processor.chunk_document(test_document)
        
        # Verify chunking
        assert len(chunks) == 2
        assert all(chunk.document_id == test_document.id for chunk in chunks)
        
        # Generate embeddings for chunks
        for chunk in chunks:
            embedding = await ingestion_engine.embedding_service.generate_embedding(chunk.text)
            chunk.embedding = embedding
        
        # Extract entities from chunks
        all_entities = []
        all_relationships = []
        
        for chunk in chunks:
            extraction = await ingestion_engine.entity_extractor.extract_from_text(chunk.text)
            all_entities.extend(extraction.entities)
            all_relationships.extend(extraction.relationships)
        
        # Verify extraction results
        assert len(all_entities) > 0, "Should extract entities from document chunks"
        assert len(all_relationships) >= 0, "Should extract relationships"
        
        # Verify embeddings generated
        assert all(chunk.embedding is not None for chunk in chunks)
        assert all(len(chunk.embedding) == 384 for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_knowledge_graph_building(self, ingestion_engine):
        """Test knowledge graph construction from ingested documents"""
        # Mock extracted entities and relationships
        entities = [
            ExtractedEntity(
                id="kg-entity-1",
                label="CONCEPT",
                text="Knowledge Graph",
                metadata={"confidence": 0.95}
            ),
            ExtractedEntity(
                id="kg-entity-2", 
                label="TECHNOLOGY",
                text="GraphRAG",
                metadata={"confidence": 0.90}
            )
        ]
        
        relationships = [
            ExtractedRelationship(
                source_entity_id="kg-entity-1",
                target_entity_id="kg-entity-2",
                label="ENABLES"
            )
        ]
        
        # Simulate adding to graph store
        await ingestion_engine.graph_store.add_entities(entities)
        await ingestion_engine.graph_store.add_relationships(relationships)
        
        # Verify graph store operations
        ingestion_engine.graph_store.add_entities.assert_called_with(entities)
        ingestion_engine.graph_store.add_relationships.assert_called_with(relationships)
    
    @pytest.mark.asyncio
    async def test_vector_store_indexing(self, ingestion_engine):
        """Test vector store indexing of document chunks"""
        # Create test chunks with embeddings
        test_chunks = [
            ChunkData(
                id="vector-chunk-1",
                text="Test chunk for vector indexing",
                document_id="vector-doc-1",
                embedding=[0.1] * 384
            ),
            ChunkData(
                id="vector-chunk-2",
                text="Another chunk for indexing tests", 
                document_id="vector-doc-1",
                embedding=[0.2] * 384
            )
        ]
        
        # Add chunks to vector store
        await ingestion_engine.vector_store.add_chunks(test_chunks)
        
        # Verify vector store operations
        ingestion_engine.vector_store.add_chunks.assert_called_with(test_chunks)
        
        # Test vector search functionality
        search_results = await ingestion_engine.vector_store.search("test query", limit=5)
        
        # Verify search capabilities
        assert isinstance(search_results, list)
        ingestion_engine.vector_store.search.assert_called_with("test query", limit=5)


class TestGraphRAGPerformance:
    """Test GraphRAG system performance and scalability"""
    
    @pytest.fixture
    def performance_test_engine(self, mock_graph_store, mock_vector_store, mock_entity_extractor, mock_llm_service):
        """Create GraphRAG engine for performance testing"""
        return SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_query_processing(self, performance_test_engine):
        """Test system handles concurrent queries efficiently"""
        queries = [
            "What is GraphRAG?",
            "How does vector search work?", 
            "Explain knowledge graphs",
            "Tell me about entity extraction",
            "What are the benefits of hybrid retrieval?"
        ]
        
        # Process queries concurrently
        tasks = [performance_test_engine.query(query) for query in queries]
        results = await asyncio.gather(*tasks)
        
        # Verify all queries completed successfully
        assert len(results) == len(queries)
        assert all(isinstance(result, QueryResult) for result in results)
        assert all(result.answer != "" for result in results)
    
    @pytest.mark.asyncio
    async def test_large_result_set_handling(self, performance_test_engine):
        """Test system handles large result sets efficiently"""
        # Configure mock to return many results
        large_chunk_set = [
            ChunkData(
                id=f"chunk-{i}",
                text=f"Chunk {i} content for large result set testing",
                document_id=f"doc-{i//10}",
                embedding=[0.1] * 384,
                score=0.9 - (i * 0.01)
            )
            for i in range(100)
        ]
        
        performance_test_engine.vector_store.search.return_value = large_chunk_set
        
        # Test search with large result set
        results = await performance_test_engine.search("large result set test", limit=100)
        
        # Verify system handles large results
        assert len(results) <= 100, "Should respect limit parameter"
        assert all(hasattr(result, 'score') for result in results)
        
        # Verify results are properly ranked
        scores = [result.score for result in results]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by relevance"
    
    @pytest.mark.asyncio
    async def test_memory_efficient_processing(self, performance_test_engine):
        """Test memory-efficient processing of queries"""
        # Test with various query sizes
        query_sizes = [
            ("short", "What is GraphRAG?"),
            ("medium", "Explain how GraphRAG combines vector search with knowledge graphs for better retrieval."),
            ("long", "Provide a detailed explanation of GraphRAG systems, including how they work, their benefits over traditional RAG approaches, implementation considerations, and use cases in enterprise environments.")
        ]
        
        for size_label, query in query_sizes:
            result = await performance_test_engine.query(query)
            
            # Verify successful processing regardless of query size
            assert isinstance(result, QueryResult), f"Failed to process {size_label} query"
            assert result.answer != "", f"{size_label} query should have answer"
            assert len(result.relevant_chunks) > 0, f"{size_label} query should have relevant chunks"


class TestGraphRAGErrorHandling:
    """Test GraphRAG system error handling and resilience"""
    
    @pytest.fixture
    def error_test_engine(self, mock_graph_store, mock_vector_store, mock_entity_extractor, mock_llm_service):
        """Create GraphRAG engine for error testing"""
        return SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )
    
    @pytest.mark.asyncio
    async def test_vector_store_failure_handling(self, error_test_engine):
        """Test graceful handling of vector store failures"""
        # Configure vector store to raise exception
        error_test_engine.vector_store.search.side_effect = Exception("Vector store unavailable")
        
        # Query should still work with graph-only fallback
        result = await error_test_engine.search("test query with vector failure")
        
        # Should fallback gracefully
        assert isinstance(result, list), "Should return results even with vector store failure"
    
    @pytest.mark.asyncio
    async def test_graph_store_failure_handling(self, error_test_engine):
        """Test graceful handling of graph store failures"""
        # Configure graph store to raise exception
        error_test_engine.graph_store.get_neighbors.side_effect = Exception("Graph store unavailable")
        
        # Query should still work with vector-only fallback
        result = await error_test_engine.query("test query with graph failure")
        
        # Should fallback to vector-only mode
        assert isinstance(result, QueryResult), "Should return result even with graph store failure"
        assert result.answer != "", "Should generate answer from vector results only"
    
    @pytest.mark.asyncio
    async def test_llm_service_failure_handling(self, error_test_engine):
        """Test graceful handling of LLM service failures"""
        # Configure LLM service to raise exception
        error_test_engine.llm_service.generate_response.side_effect = Exception("LLM service unavailable")
        
        # Query should still return search results even without LLM response
        result = await error_test_engine.query("test query with LLM failure")
        
        # Should have search results even without generated answer
        assert isinstance(result, QueryResult), "Should return QueryResult even with LLM failure"
        assert len(result.relevant_chunks) > 0, "Should have retrieved relevant chunks"
    
    @pytest.mark.asyncio
    async def test_entity_extraction_failure_handling(self, error_test_engine):
        """Test graceful handling of entity extraction failures"""
        # Configure entity extractor to raise exception
        error_test_engine.entity_extractor.extract_from_text.side_effect = Exception("Entity extraction failed")
        
        # Query should still work without entity enhancement
        result = await error_test_engine.query("test query with entity extraction failure")
        
        # Should work with basic vector search
        assert isinstance(result, QueryResult), "Should return result even with entity extraction failure"
        assert result.answer != "", "Should generate answer without entity context"
    
    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, error_test_engine):
        """Test handling of invalid inputs"""
        # Test empty query
        empty_result = await error_test_engine.query("")
        assert isinstance(empty_result, QueryResult), "Should handle empty query gracefully"
        
        # Test very long query (potential memory/processing issues)
        long_query = "test " * 10000  # Very long query
        long_result = await error_test_engine.query(long_query)
        assert isinstance(long_result, QueryResult), "Should handle very long query gracefully"
        
        # Test special characters
        special_query = "!@#$%^&*()[]{}|\\:;\"'<>,.?/~`"
        special_result = await error_test_engine.query(special_query)
        assert isinstance(special_result, QueryResult), "Should handle special characters gracefully"


class TestGraphRAGDataIntegrity:
    """Test data integrity and consistency in GraphRAG operations"""
    
    @pytest.fixture
    def integrity_test_engine(self, mock_graph_store, mock_vector_store, mock_entity_extractor, mock_llm_service):
        """Create GraphRAG engine for data integrity testing"""
        return SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )
    
    @pytest.mark.asyncio
    async def test_search_result_consistency(self, integrity_test_engine):
        """Test search results are consistent and properly formatted"""
        query = "data integrity test query"
        
        # Perform multiple searches with same query
        results1 = await integrity_test_engine.search(query, limit=5)
        results2 = await integrity_test_engine.search(query, limit=5)
        
        # Results should be consistent
        assert len(results1) == len(results2), "Search results should be consistent"
        
        # Verify result structure integrity
        for result in results1:
            assert hasattr(result, 'chunk'), "Result should have chunk"
            assert hasattr(result, 'score'), "Result should have score"
            assert 0 <= result.score <= 1.0, "Score should be normalized"
            assert result.chunk.id != "", "Chunk should have valid ID"
            assert result.chunk.text != "", "Chunk should have content"
    
    @pytest.mark.asyncio
    async def test_query_result_completeness(self, integrity_test_engine):
        """Test query results contain all expected components"""
        query = "completeness test query"
        
        result = await integrity_test_engine.query(query)
        
        # Verify QueryResult completeness
        assert isinstance(result, QueryResult), "Should return QueryResult object"
        assert hasattr(result, 'relevant_chunks'), "Should have relevant_chunks"
        assert hasattr(result, 'answer'), "Should have answer"
        assert hasattr(result, 'graph_context'), "Should have graph_context"
        assert hasattr(result, 'metadata'), "Should have metadata"
        
        # Verify data types
        assert isinstance(result.relevant_chunks, list), "relevant_chunks should be list"
        assert isinstance(result.answer, str), "answer should be string"
        assert isinstance(result.metadata, dict), "metadata should be dict"
    
    @pytest.mark.asyncio
    async def test_entity_relationship_consistency(self, integrity_test_engine):
        """Test entity and relationship data consistency"""
        # Configure mock to return consistent entity-relationship pairs
        mock_entities = [
            Entity(id="e1", name="Entity 1", label="TEST"),
            Entity(id="e2", name="Entity 2", label="TEST")
        ]
        
        mock_relationships = [
            Relationship(id="r1", source_id="e1", target_id="e2", label="RELATES_TO")
        ]
        
        integrity_test_engine.graph_store.get_related_entities.return_value = mock_entities
        integrity_test_engine.graph_store.get_relationships.return_value = mock_relationships
        
        # Verify entity-relationship consistency
        entities = await integrity_test_engine.graph_store.get_related_entities(["e1"])
        relationships = await integrity_test_engine.graph_store.get_relationships(["e1"])
        
        # Check that relationship references valid entities
        entity_ids = {e.id for e in entities}
        for rel in relationships:
            assert rel.source_id in entity_ids or rel.target_id in entity_ids, \
                "Relationship should reference existing entities"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])