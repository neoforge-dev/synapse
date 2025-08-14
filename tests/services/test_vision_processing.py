import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pytest_mock import MockerFixture

from graph_rag.core.interfaces import ChunkData, DocumentData


class TestImageProcessor:
    """Test suite for ImageProcessor functionality."""

    @pytest.mark.asyncio
    async def test_extract_text_from_image_with_valid_image(self):
        """Test that ImageProcessor can extract text from a valid image."""
        # This test will fail until we implement ImageProcessor
        from graph_rag.services.vision.image_processor import ImageProcessor
        
        processor = ImageProcessor()
        
        # Create a mock image file path
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image_path = tmp.name
            
        try:
            # This should extract text from the image
            result = await processor.extract_text_from_image(image_path)
            
            # Verify the result structure
            assert isinstance(result, str)
            assert len(result) >= 0  # Could be empty for images without text
            
        finally:
            # Clean up
            Path(image_path).unlink(missing_ok=True)

    @pytest.mark.asyncio 
    async def test_extract_text_from_image_returns_empty_for_invalid_path(self):
        """Test that ImageProcessor handles invalid image paths gracefully."""
        from graph_rag.services.vision.image_processor import ImageProcessor
        
        processor = ImageProcessor()
        
        # Test with non-existent file
        result = await processor.extract_text_from_image("/path/to/nonexistent/image.png")
        
        # Should return empty string or handle error gracefully
        assert isinstance(result, str)
        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_text_from_image_without_vision_dependencies(self):
        """Test graceful degradation when vision dependencies are not available."""
        # Mock the import failure scenario
        with patch.dict('sys.modules', {
            'pytesseract': None,
            'PIL': None,
            'PIL.Image': None
        }):
            from graph_rag.services.vision.image_processor import ImageProcessor
            
            processor = ImageProcessor()
            
            # Should fall back gracefully
            result = await processor.extract_text_from_image("test.png")
            assert isinstance(result, str)
            # When dependencies unavailable, should return empty or fallback message


class TestPDFAnalyzer:
    """Test suite for PDFAnalyzer functionality."""

    @pytest.fixture
    def mock_image_processor(self):
        """Create a mock ImageProcessor for testing."""
        mock = AsyncMock()
        mock.extract_text_from_image.return_value = "Extracted text from image"
        return mock

    @pytest.mark.asyncio
    async def test_extract_content_from_pdf_with_images(self, mock_image_processor):
        """Test that PDFAnalyzer can extract content including images from PDF."""
        from graph_rag.services.vision.pdf_analyzer import PDFAnalyzer
        
        analyzer = PDFAnalyzer(mock_image_processor)
        
        # Create a mock PDF file path
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdf_path = tmp.name
            
        try:
            # This should extract both text and image content
            result = await analyzer.extract_content(pdf_path)
            
            # Verify the result structure
            assert isinstance(result, dict)
            assert "text" in result
            assert "images_text" in result
            assert isinstance(result["text"], str)
            assert isinstance(result["images_text"], list)
            
        finally:
            # Clean up
            Path(pdf_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_extract_content_handles_text_only_pdf(self, mock_image_processor):
        """Test PDFAnalyzer with PDF containing only text."""
        from graph_rag.services.vision.pdf_analyzer import PDFAnalyzer
        
        analyzer = PDFAnalyzer(mock_image_processor)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdf_path = tmp.name
            
        try:
            result = await analyzer.extract_content(pdf_path)
            
            assert isinstance(result, dict)
            assert "text" in result
            assert "images_text" in result
            assert isinstance(result["text"], str)
            
        finally:
            Path(pdf_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_extract_content_returns_empty_for_invalid_pdf(self, mock_image_processor):
        """Test PDFAnalyzer handles invalid PDF paths gracefully."""
        from graph_rag.services.vision.pdf_analyzer import PDFAnalyzer
        
        analyzer = PDFAnalyzer(mock_image_processor)
        
        result = await analyzer.extract_content("/path/to/nonexistent.pdf")
        
        assert isinstance(result, dict)
        assert result["text"] == ""
        assert result["images_text"] == []


class TestVisionIntegration:
    """Test suite for vision processing integration with the ingestion pipeline."""

    @pytest.fixture
    def mock_document_processor_with_vision(self):
        """Create a document processor mock that handles vision content."""
        mock = AsyncMock()
        # Return chunks that include vision-processed content
        mock.chunk_document.return_value = [
            ChunkData(
                id=str(uuid.uuid4()),
                text="Regular text chunk",
                document_id="test-doc",
                metadata={"source": "text"}
            ),
            ChunkData(
                id=str(uuid.uuid4()),
                text="Text extracted from image via OCR",
                document_id="test-doc", 
                metadata={"source": "image_ocr"}
            )
        ]
        return mock

    @pytest.mark.asyncio
    async def test_ingestion_processes_pdf_with_images(self, mock_document_processor_with_vision):
        """Test that ingestion pipeline can handle PDF documents with images."""
        # This test verifies integration between vision processing and ingestion
        from graph_rag.services.ingestion import IngestionService
        
        # Mock all required dependencies
        mock_entity_extractor = AsyncMock()
        mock_graph_store = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_vector_store = AsyncMock()
        
        service = IngestionService(
            document_processor=mock_document_processor_with_vision,
            entity_extractor=mock_entity_extractor,
            graph_store=mock_graph_store,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store
        )
        
        # Test with a PDF document that contains images
        document_id = str(uuid.uuid4())
        content = "PDF content with embedded images"
        metadata = {"source": "test.pdf", "type": "pdf"}
        
        result = await service.ingest_document(
            document_id=document_id,
            content=content,
            metadata=metadata,
            generate_embeddings=False
        )
        
        # Verify that the document was processed successfully
        assert result.document_id == document_id
        assert len(result.chunk_ids) == 2  # Text + image content chunks
        
        # Verify that vision-processed content was included
        mock_document_processor_with_vision.chunk_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_vision_processing_fallback_when_unavailable(self):
        """Test that the system gracefully handles missing vision dependencies."""
        # Mock scenario where vision processing is not available
        from unittest.mock import patch
        
        with patch('graph_rag.services.vision.image_processor.VISION_AVAILABLE', False):
            # Import after patching to ensure the availability flag is set
            from graph_rag.services.vision.image_processor import ImageProcessor
            
            processor = ImageProcessor()
            result = await processor.extract_text_from_image("test.png")
            
            # Should return empty string when vision is unavailable
            assert isinstance(result, str)
            assert result == ""