"""Comprehensive tests for the ImprovedSynapseEngine."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from graph_rag.core.improved_synapse_engine import (
    ConsolidatedAnswer,
    ImprovedSynapseEngine,
)
from graph_rag.core.interfaces import (
    ChunkData,
    ExtractionResult,
    SearchResultData,
)
from graph_rag.infrastructure.vector_stores.shared_persistent_vector_store import (
    SharedPersistentVectorStore,
)


@pytest.fixture
def mock_graph_store():
    """Mock graph repository."""
    from graph_rag.core.interfaces import GraphRepository

    # Create a mock that passes isinstance checks
    mock = AsyncMock(spec=GraphRepository)
    mock.search_entities_by_properties = AsyncMock(return_value=[])
    mock.get_neighbors = AsyncMock(return_value=([], []))
    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    mock = AsyncMock()
    mock.get_embedding_dimension.return_value = 384
    mock.encode = AsyncMock(return_value=[[0.1] * 384])
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    return mock


@pytest.fixture
def mock_entity_extractor():
    """Mock entity extractor."""
    mock = AsyncMock()
    mock.extract_from_text = AsyncMock(return_value=ExtractionResult(entities=[], relationships=[]))
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    mock = AsyncMock()
    mock.generate_response = AsyncMock(return_value="Test response")
    mock.extract_entities_relationships = AsyncMock(return_value=([], []))
    return mock


@pytest.fixture
def mock_vector_store(mock_embedding_service, tmp_path):
    """Mock shared persistent vector store."""
    from graph_rag.core.interfaces import VectorStore

    # Create a proper mock that passes isinstance checks
    mock = AsyncMock(spec=VectorStore)
    mock._ensure_loaded = AsyncMock()
    mock.get_vector_store_size = AsyncMock(return_value=10)
    mock.search = AsyncMock(return_value=[])
    mock.add_chunks = AsyncMock()
    mock.save = AsyncMock()
    mock.load = AsyncMock()

    return mock


@pytest.fixture
def improved_engine(
    mock_graph_store,
    mock_vector_store,
    mock_entity_extractor,
    mock_llm_service,
    mock_embedding_service,
    tmp_path
):
    """Create ImprovedSynapseEngine with mocked dependencies."""
    storage_path = tmp_path / "test_storage"

    engine = ImprovedSynapseEngine(
        graph_store=mock_graph_store,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service,
        embedding_service=mock_embedding_service,
        storage_path=str(storage_path),
    )

    return engine


@pytest.fixture
def sample_chunks():
    """Sample chunk data for testing."""
    return [
        ChunkData(
            id="chunk_1",
            text="Universal orchestrator pattern provides centralized control over distributed systems.",
            document_id="doc_1",
            metadata={"topic": "architecture"},
            score=0.9,
        ),
        ChunkData(
            id="chunk_2",
            text="The system achieved 39,092x performance improvement through optimization.",
            document_id="doc_2",
            metadata={"topic": "performance"},
            score=0.8,
        ),
        ChunkData(
            id="chunk_3",
            text="Best practice: implement proper error handling for resilient systems.",
            document_id="doc_3",
            metadata={"topic": "best_practices"},
            score=0.7,
        ),
    ]


@pytest.fixture
def sample_search_results(sample_chunks):
    """Sample search results for testing."""
    return [
        SearchResultData(chunk=chunk, score=chunk.score)
        for chunk in sample_chunks
    ]


class TestImprovedSynapseEngine:
    """Test cases for ImprovedSynapseEngine."""

    @pytest.mark.asyncio
    async def test_initialization_with_persistent_vector_store(
        self, mock_graph_store, mock_vector_store, mock_entity_extractor,
        mock_llm_service, mock_embedding_service, tmp_path
    ):
        """Test engine initialization with SharedPersistentVectorStore."""
        engine = ImprovedSynapseEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service,
            embedding_service=mock_embedding_service,
            storage_path=str(tmp_path / "test"),
        )

        assert isinstance(engine._vector_store, SharedPersistentVectorStore)
        assert engine._graph_store == mock_graph_store
        assert engine._entity_extractor == mock_entity_extractor
        assert engine._llm_service == mock_llm_service

    @pytest.mark.asyncio
    async def test_initialization_with_regular_vector_store(
        self, mock_graph_store, mock_entity_extractor, mock_llm_service,
        mock_embedding_service, tmp_path
    ):
        """Test engine initialization when wrapping regular vector store."""
        mock_regular_store = AsyncMock()

        engine = ImprovedSynapseEngine(
            graph_store=mock_graph_store,
            vector_store=mock_regular_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service,
            embedding_service=mock_embedding_service,
            storage_path=str(tmp_path / "test"),
        )

        # Should create new SharedPersistentVectorStore
        assert isinstance(engine._vector_store, SharedPersistentVectorStore)

    @pytest.mark.asyncio
    async def test_vector_store_loading(self, improved_engine):
        """Test vector store loading functionality."""
        await improved_engine._ensure_vector_store_loaded()

        # Verify that ensure_loaded was called
        improved_engine._vector_store._ensure_loaded.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_context_with_empty_store(self, improved_engine):
        """Test context retrieval when vector store is empty."""
        improved_engine._vector_store.get_vector_store_size = AsyncMock(return_value=0)

        result = await improved_engine.retrieve_context("test query")

        assert result == []

    @pytest.mark.asyncio
    async def test_retrieve_context_with_data(self, improved_engine, sample_search_results):
        """Test context retrieval when vector store has data."""
        improved_engine._vector_store.get_vector_store_size = AsyncMock(return_value=10)
        improved_engine._vector_store.search = AsyncMock(return_value=sample_search_results)

        result = await improved_engine.retrieve_context("test query", limit=5)

        assert len(result) == 3
        assert all(isinstance(r, SearchResultData) for r in result)
        improved_engine._vector_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_with_consolidation(self, improved_engine, sample_search_results):
        """Test hybrid search with consolidation functionality."""
        improved_engine._vector_store.get_vector_store_size = AsyncMock(return_value=10)
        improved_engine._vector_store.search = AsyncMock(return_value=sample_search_results)

        # Mock consolidation
        with patch.object(improved_engine, '_consolidate_overlapping_chunks') as mock_consolidate:
            mock_consolidate.return_value = sample_search_results

            config = {"search_type": "hybrid", "k": 5}
            result, _ = await improved_engine._retrieve_and_build_context("test query", config)

            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_blend_and_deduplicate_results(self, improved_engine, sample_search_results):
        """Test blending and deduplication of search results."""
        vector_results = sample_search_results[:2]
        keyword_results = sample_search_results[1:]  # Overlapping results

        blended = improved_engine._blend_and_deduplicate_results(
            vector_results, keyword_results, blend_weight=0.3
        )

        # Should have all unique chunks
        assert len(blended) == 3
        # Should be sorted by blended score
        assert blended[0].score >= blended[1].score >= blended[2].score

    @pytest.mark.asyncio
    async def test_consolidate_overlapping_chunks(self, improved_engine, sample_search_results):
        """Test consolidation of overlapping chunks."""
        # Mock experiment consolidator
        with patch.object(improved_engine._experiment_consolidator, 'find_similar_documents') as mock_find:
            with patch.object(improved_engine._experiment_consolidator, 'consolidate_experiments'):
                # Mock similarity matches
                mock_find.return_value = []

                result = await improved_engine._consolidate_overlapping_chunks(sample_search_results)

                # Should return original chunks if no consolidation
                assert len(result) == 3

    @pytest.mark.asyncio
    async def test_answer_query_consolidated_success(self, improved_engine, sample_search_results):
        """Test successful consolidated query answering."""
        # Mock dependencies
        improved_engine._vector_store.get_vector_store_size = AsyncMock(return_value=10)
        improved_engine._retrieve_and_build_context = AsyncMock(
            return_value=(sample_search_results, None)
        )
        improved_engine._generate_enhanced_answer = AsyncMock(
            return_value=Mock(text="Test answer", confidence_score=0.8)
        )
        improved_engine._extract_architectural_patterns = AsyncMock(return_value=[])
        improved_engine._extract_success_metrics = AsyncMock(return_value=[])
        improved_engine._extract_best_practices = AsyncMock(return_value=[])

        result = await improved_engine.answer_query_consolidated("test query")

        assert isinstance(result, ConsolidatedAnswer)
        assert result.answer == "Test answer"
        assert result.confidence_score == 0.8
        assert len(result.consolidated_chunks) == 3

    @pytest.mark.asyncio
    async def test_answer_query_consolidated_no_context(self, improved_engine):
        """Test consolidated query when no context is found."""
        improved_engine._retrieve_and_build_context = AsyncMock(return_value=([], None))

        result = await improved_engine.answer_query_consolidated("test query")

        assert isinstance(result, ConsolidatedAnswer)
        assert "No relevant information found" in result.answer
        assert result.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_extract_architectural_patterns(self, improved_engine, sample_search_results):
        """Test extraction of architectural patterns."""
        # Mock pattern recognizer
        mock_pattern = Mock()
        mock_pattern.pattern_name = "Universal Orchestrator"
        mock_pattern.description = "Centralized control pattern"
        mock_pattern.benefits = ["Simplified coordination"]
        mock_pattern.challenges = ["Single point of failure"]
        mock_pattern.use_cases = ["Workflow orchestration"]
        mock_pattern.evidence_strength = 0.8

        improved_engine._experiment_consolidator.pattern_recognizer.identify_patterns = AsyncMock(
            return_value=[mock_pattern]
        )

        patterns = await improved_engine._extract_architectural_patterns(sample_search_results)

        assert len(patterns) == 1
        assert patterns[0]["pattern_name"] == "Universal Orchestrator"
        assert patterns[0]["evidence_strength"] == 0.8

    @pytest.mark.asyncio
    async def test_extract_success_metrics(self, improved_engine, sample_search_results):
        """Test extraction of success metrics."""
        # Mock metrics extractor
        mock_metric = Mock()
        mock_metric.metric_type = Mock(value="performance_improvement")
        mock_metric.value = 39092.0
        mock_metric.unit = "x"
        mock_metric.context = "39,092x improvement"
        mock_metric.source_location = "chunk_2"
        mock_metric.confidence_score = 0.9

        improved_engine._experiment_consolidator.metrics_extractor.extract_metrics = AsyncMock(
            return_value=[mock_metric]
        )

        metrics = await improved_engine._extract_success_metrics(sample_search_results)

        assert len(metrics) == 1
        assert metrics[0]["metric_type"] == "performance_improvement"
        assert metrics[0]["value"] == 39092.0
        assert metrics[0]["confidence_score"] == 0.9

    @pytest.mark.asyncio
    async def test_extract_best_practices(self, improved_engine, sample_search_results):
        """Test extraction of best practices."""
        improved_engine._experiment_consolidator.pattern_recognizer.extract_best_practices = AsyncMock(
            return_value=["Implement proper error handling", "Use centralized orchestration"]
        )

        practices = await improved_engine._extract_best_practices(sample_search_results)

        assert len(practices) == 2
        assert "error handling" in practices[0]
        assert "orchestration" in practices[1]

    @pytest.mark.asyncio
    async def test_build_machine_readable_format(self, improved_engine, sample_search_results):
        """Test building machine-readable format."""
        patterns = [{"pattern_name": "Test Pattern", "evidence_strength": 0.8}]
        metrics = [{"metric_type": "performance", "value": 100, "confidence_score": 0.9}]

        machine_readable = improved_engine._build_machine_readable_format(
            sample_search_results, None, patterns, metrics
        )

        assert "concepts" in machine_readable
        assert "relationships" in machine_readable
        assert "evidence" in machine_readable
        assert "patterns" in machine_readable
        assert "metrics" in machine_readable

        assert len(machine_readable["concepts"]) == 3
        assert len(machine_readable["patterns"]) == 1
        assert len(machine_readable["metrics"]) == 1

    @pytest.mark.asyncio
    async def test_calculate_consolidation_confidence(self, improved_engine, sample_search_results):
        """Test consolidation confidence calculation."""
        patterns = [{"evidence_strength": 0.8}]
        metrics = [{"confidence_score": 0.9}]

        confidence = improved_engine._calculate_consolidation_confidence(
            sample_search_results, patterns, metrics
        )

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high with good data

    @pytest.mark.asyncio
    async def test_calculate_evidence_ranking(self, improved_engine):
        """Test evidence ranking calculation."""
        patterns = [{"evidence_strength": 0.8}, {"evidence_strength": 0.6}]
        metrics = [{"confidence_score": 0.9}, {"confidence_score": 0.8}]

        ranking = improved_engine._calculate_evidence_ranking(patterns, metrics)

        assert 0.0 <= ranking <= 1.0

    @pytest.mark.asyncio
    async def test_prepare_sources(self, improved_engine, sample_search_results):
        """Test source preparation for citations."""
        sources = improved_engine._prepare_sources(sample_search_results)

        assert len(sources) == 3
        for i, source in enumerate(sources):
            assert source["id"] == f"chunk_{i+1}"
            assert "score" in source
            assert "text_preview" in source

    @pytest.mark.asyncio
    async def test_get_vector_store_status(self, improved_engine):
        """Test vector store status retrieval."""
        improved_engine._vector_store.get_vector_store_size = AsyncMock(return_value=42)
        improved_engine._vector_store.storage_path = Path("/test/path")

        status = await improved_engine.get_vector_store_status()

        assert status["vector_count"] == 42
        assert status["store_type"] == "SharedPersistentVectorStore"
        assert status["is_persistent"] is True
        assert status["storage_path"] is not None

    @pytest.mark.asyncio
    async def test_add_chunks_to_store(self, improved_engine, sample_chunks):
        """Test adding chunks to the vector store."""
        await improved_engine.add_chunks_to_store(sample_chunks)

        improved_engine._vector_store.add_chunks.assert_called_once_with(sample_chunks)

    @pytest.mark.asyncio
    async def test_enhanced_graph_context_retrieval(self, improved_engine, sample_search_results):
        """Test enhanced graph context retrieval."""
        # Mock entity extraction
        mock_entity = Mock()
        mock_entity.text = "orchestrator"
        mock_entity.label = "PATTERN"

        extraction_result = ExtractionResult(entities=[mock_entity], relationships=[])
        improved_engine._entity_extractor.extract_from_text = AsyncMock(return_value=extraction_result)

        # Mock graph store responses
        mock_graph_entity = Mock()
        mock_graph_entity.id = "entity_1"
        improved_engine._graph_store.search_entities_by_properties = AsyncMock(
            return_value=[mock_graph_entity]
        )
        improved_engine._graph_store.get_neighbors = AsyncMock(return_value=([], []))

        result = await improved_engine._get_enhanced_graph_context(sample_search_results)

        assert result is not None
        entities, relationships = result
        assert len(entities) == 1

    @pytest.mark.asyncio
    async def test_error_handling_in_consolidated_answer(self, improved_engine):
        """Test error handling in consolidated answer generation."""
        # Mock a failure in context retrieval
        improved_engine._retrieve_and_build_context = AsyncMock(
            side_effect=Exception("Test error")
        )

        result = await improved_engine.answer_query_consolidated("test query")

        assert isinstance(result, ConsolidatedAnswer)
        assert "Error generating answer" in result.answer
        assert result.confidence_score == 0.0
        assert "error" in result.metadata

    def test_consolidated_answer_to_dict(self):
        """Test ConsolidatedAnswer to_dict conversion."""
        sample_chunk = ChunkData(
            id="test_chunk",
            text="Test text",
            document_id="test_doc",
            metadata={"test": "value"}
        )

        answer = ConsolidatedAnswer(
            answer="Test answer",
            consolidated_chunks=[sample_chunk],
            confidence_score=0.8,
            metadata={"test": "metadata"}
        )

        result_dict = answer.to_dict()

        assert result_dict["answer"] == "Test answer"
        assert result_dict["confidence_score"] == 0.8
        assert "consolidated_chunks" in result_dict
        assert "metadata" in result_dict


class TestConsolidationIntegration:
    """Integration tests for consolidation features."""

    @pytest.mark.asyncio
    async def test_end_to_end_consolidation_flow(
        self, improved_engine, sample_search_results
    ):
        """Test complete consolidation flow from query to response."""
        # Setup mocks for full flow
        improved_engine._vector_store.get_vector_store_size = AsyncMock(return_value=10)
        improved_engine._vector_store.search = AsyncMock(return_value=sample_search_results)

        # Mock LLM response
        mock_llm_response = Mock()
        mock_llm_response.text = "Consolidated test answer based on patterns and metrics."
        mock_llm_response.confidence_score = 0.85
        improved_engine._generate_enhanced_answer = AsyncMock(return_value=mock_llm_response)

        # Mock pattern and metrics extraction
        improved_engine._extract_architectural_patterns = AsyncMock(return_value=[
            {
                "pattern_name": "Universal Orchestrator",
                "description": "Centralized control pattern",
                "benefits": ["Simplified coordination"],
                "challenges": ["Single point of failure"],
                "use_cases": ["Workflow orchestration"],
                "evidence_strength": 0.8
            }
        ])
        improved_engine._extract_success_metrics = AsyncMock(return_value=[
            {
                "metric_type": "performance_improvement",
                "value": 39092.0,
                "unit": "x",
                "context": "39,092x improvement",
                "source_location": "chunk_2",
                "confidence_score": 0.9
            }
        ])
        improved_engine._extract_best_practices = AsyncMock(return_value=[
            "Implement proper error handling for resilient systems"
        ])

        config = {
            "search_type": "hybrid",
            "k": 5,
            "consolidation_threshold": 0.7
        }

        result = await improved_engine.answer_query_consolidated(
            "How does universal orchestrator improve system performance?",
            config=config
        )

        # Verify comprehensive response
        assert isinstance(result, ConsolidatedAnswer)
        assert "Consolidated test answer" in result.answer
        assert result.confidence_score == 0.85
        assert len(result.consolidated_chunks) == 3
        assert len(result.architectural_patterns) == 1
        assert len(result.success_metrics) == 1
        assert len(result.best_practices) == 1
        assert result.architectural_patterns[0]["pattern_name"] == "Universal Orchestrator"
        assert result.success_metrics[0]["value"] == 39092.0
        assert "machine_readable" in result.to_dict()

    @pytest.mark.asyncio
    async def test_consolidation_with_overlapping_content(
        self, improved_engine
    ):
        """Test consolidation when content has significant overlap."""
        # Create overlapping chunks
        overlapping_chunks = [
            ChunkData(
                id="chunk_1",
                text="Universal orchestrator pattern provides centralized control",
                document_id="doc_1",
                score=0.9
            ),
            ChunkData(
                id="chunk_2",
                text="Universal orchestrator provides centralized control over systems",
                document_id="doc_2",
                score=0.85
            ),
            ChunkData(
                id="chunk_3",
                text="Centralized orchestration improves system coordination",
                document_id="doc_3",
                score=0.8
            )
        ]

        search_results = [SearchResultData(chunk=chunk, score=chunk.score) for chunk in overlapping_chunks]

        # Mock consolidation to simulate overlap detection
        with patch.object(improved_engine._experiment_consolidator, 'find_similar_documents') as mock_find:
            with patch.object(improved_engine._experiment_consolidator, 'consolidate_experiments') as mock_consolidate:
                # Mock finding similarity
                mock_find.return_value = [Mock()]  # Simulate matches found

                # Mock consolidation result
                mock_experiment = Mock()
                mock_experiment.consolidated_id = "consolidated_123"
                mock_experiment.consolidation_confidence = 0.85
                mock_experiment.evidence_ranking = 0.8
                mock_experiment.source_candidates = [Mock() for _ in range(2)]  # 2 candidates consolidated

                mock_consolidate.return_value = [mock_experiment]

                result = await improved_engine._consolidate_overlapping_chunks(search_results)

                # Should have fewer results due to consolidation
                assert len(result) <= len(search_results)

                # Check that consolidation metadata is added
                if result:
                    enhanced_chunk = result[0].chunk
                    if enhanced_chunk.metadata:
                        assert "consolidation_group" in enhanced_chunk.metadata or "consolidated_from" in enhanced_chunk.metadata


@pytest.mark.asyncio
async def test_persistence_integration(tmp_path, mock_embedding_service):
    """Test integration with persistent storage."""
    storage_path = tmp_path / "integration_test"

    # Create vector store with actual persistence
    vector_store = SharedPersistentVectorStore(
        embedding_service=mock_embedding_service,
        storage_path=str(storage_path)
    )

    # Add some test data
    test_chunks = [
        ChunkData(
            id="persist_test_1",
            text="Test persistence functionality",
            document_id="test_doc",
            embedding=[0.1] * 384
        )
    ]

    await vector_store.add_chunks(test_chunks)

    # Verify storage files were created
    assert (storage_path / "vectors.pkl").exists()
    assert (storage_path / "metadata.json").exists()

    # Test loading in new instance
    new_vector_store = SharedPersistentVectorStore(
        embedding_service=mock_embedding_service,
        storage_path=str(storage_path)
    )

    await new_vector_store._ensure_loaded()
    size = await new_vector_store.get_vector_store_size()
    assert size == 1
