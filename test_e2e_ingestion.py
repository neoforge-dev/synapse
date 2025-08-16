#!/usr/bin/env python3
"""
End-to-end test of the ingestion pipeline with entity extraction and real embeddings.
This script tests the complete flow: document -> chunks -> entities -> embeddings -> storage.
"""

import sys
import os
import asyncio
import tempfile
import shutil
sys.path.insert(0, os.path.abspath('.'))

from graph_rag.core.document_processor import DocumentProcessor
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.services.embedding import SentenceTransformerEmbeddingService
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
from graph_rag.models import Document

async def test_e2e_ingestion_pipeline():
    """Test complete ingestion pipeline with entities and embeddings"""
    print("Testing end-to-end ingestion pipeline...")
    
    # Create temporary directory for vector store
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize services
        document_processor = DocumentProcessor()
        entity_extractor = SpacyEntityExtractor()
        embedding_service = SentenceTransformerEmbeddingService()
        
        # Create mock repositories (avoid real Memgraph dependency)
        class MockGraphRepository:
            def __init__(self):
                self.documents = {}
                self.chunks = {}
                self.entities = {}
                self.relationships = {}
                
            async def add_document(self, document):
                self.documents[document.id] = document
                
            async def add_chunk(self, chunk):
                self.chunks[chunk.id] = chunk
                
            async def add_entity(self, entity):
                self.entities[entity.id] = entity
                
            async def add_relationship(self, relationship):
                self.relationships[relationship.id] = relationship
                
            async def get_chunks_by_document_id(self, doc_id):
                return [chunk for chunk in self.chunks.values() if chunk.document_id == doc_id]
                
            async def delete_document(self, doc_id, id_source=None):
                if doc_id in self.documents:
                    del self.documents[doc_id]
                # Delete associated chunks
                chunks_to_delete = [chunk_id for chunk_id, chunk in self.chunks.items() 
                                  if chunk.document_id == doc_id]
                for chunk_id in chunks_to_delete:
                    del self.chunks[chunk_id]
                return len(chunks_to_delete)
        
        graph_repository = MockGraphRepository()
        
        # Initialize vector store
        vector_store = SimpleVectorStore(persist_dir=temp_dir)
        
        # Create test document with rich content
        test_content = """
        Apple Inc. is a technology company founded by Steve Jobs, Steve Wozniak, and Ronald Wayne.
        The company is headquartered in Cupertino, California, and has become one of the world's most 
        valuable companies. Tim Cook currently serves as the CEO, succeeding Steve Jobs.
        
        Microsoft Corporation, led by Satya Nadella, is another major technology company based in 
        Redmond, Washington. The company was founded by Bill Gates and Paul Allen in 1975.
        
        Both companies have revolutionized the technology industry and continue to innovate in areas
        like artificial intelligence, cloud computing, and consumer electronics.
        """
        
        document = Document(
            id="test-e2e-doc",
            content=test_content,
            metadata={"source": "e2e_test", "title": "Tech Companies Overview"}
        )
        
        print("Starting pipeline testing...")
        
        # Test components individually instead of using IngestionService to avoid circular imports
        
        # 1. Process document into chunks
        processed_doc = await document_processor.process_document(document)
        print(f"✓ Document processed into {len(processed_doc.chunks)} chunks")
        
        # 2. Extract entities
        extracted_doc = await entity_extractor.extract(processed_doc)
        print(f"✓ Extracted {len(extracted_doc.entities)} entities")
        
        # 3. Store document and chunks in graph
        await graph_repository.add_document(extracted_doc)
        for chunk in extracted_doc.chunks:
            await graph_repository.add_chunk(chunk)
        for entity in extracted_doc.entities:
            await graph_repository.add_entity(entity)
        for relationship in extracted_doc.relationships:
            await graph_repository.add_relationship(relationship)
        
        # 4. Generate embeddings
        chunk_texts = [chunk.text for chunk in extracted_doc.chunks]
        embeddings = []
        for text in chunk_texts:
            embedding = await embedding_service.generate_embedding(text)
            embeddings.append(embedding)
        print(f"✓ Generated {len(embeddings)} embeddings")
        
        # 5. Store embeddings in vector store
        for i, (chunk, embedding) in enumerate(zip(extracted_doc.chunks, embeddings)):
            await vector_store.add_chunk(chunk, embedding)
        
        print(f"✓ Pipeline completed successfully")
        
        # Verify document was stored
        assert extracted_doc.id in graph_repository.documents
        stored_doc = graph_repository.documents[extracted_doc.id]
        assert stored_doc.content == document.content
        print("✓ Document stored correctly")
        
        # Verify chunks were created and stored
        stored_chunks = await graph_repository.get_chunks_by_document_id(extracted_doc.id)
        assert len(stored_chunks) > 0
        print(f"✓ {len(stored_chunks)} chunks stored")
        
        # Verify entities were extracted and stored
        assert len(graph_repository.entities) > 0
        print(f"✓ {len(graph_repository.entities)} entities extracted")
        
        # Print extracted entities
        for entity_id, entity in graph_repository.entities.items():
            print(f"  - {entity.name} ({entity.type})")
        
        # Verify embeddings were created
        vector_stats = vector_store.get_stats()
        assert vector_stats['total_vectors'] > 0
        print(f"✓ {vector_stats['total_vectors']} embeddings created")
        
        # Test semantic search works with real embeddings
        search_results = await vector_store.similarity_search(
            query="Apple technology company",
            k=3
        )
        assert len(search_results) > 0
        print(f"✓ Semantic search returned {len(search_results)} results")
        
        # Verify embeddings have correct dimensions  
        # Check if we can access embedding data from search results
        first_chunk_id = list(vector_store._chunks.keys())[0] if vector_store._chunks else None
        if first_chunk_id:
            chunk_data = vector_store._chunks[first_chunk_id]
            if hasattr(chunk_data, 'embedding'):
                embedding_dim = len(chunk_data.embedding)
                assert embedding_dim == 384, f"Expected 384 dimensions, got {embedding_dim}"
                print(f"✓ Embeddings have correct dimensions: {embedding_dim}")
        
        # Test that we can find relevant chunks
        relevant_chunks = [result for result in search_results if "Apple" in result.text]
        assert len(relevant_chunks) > 0
        print(f"✓ Found {len(relevant_chunks)} relevant chunks about Apple")
        
        print("🎉 End-to-end ingestion pipeline test passed!")
        
        return {
            "document_stored": True,
            "chunks_created": len(stored_chunks),
            "entities_extracted": len(graph_repository.entities),
            "embeddings_created": vector_stats['total_vectors'],
            "search_results": len(search_results)
        }
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    result = asyncio.run(test_e2e_ingestion_pipeline())
    print(f"\nTest Results: {result}")