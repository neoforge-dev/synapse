"""PDF analysis service with image extraction capabilities."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import PDF dependencies with graceful fallback
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
    logger.info("PDF processing dependencies available")
except ImportError as e:
    PDF_AVAILABLE = False
    logger.info(f"PDF processing dependencies not available: {e}")
    fitz = None


class PDFAnalyzer:
    """Service for analyzing PDF documents and extracting content including images."""

    def __init__(self, image_processor: Optional['ImageProcessor'] = None):
        """Initialize the PDFAnalyzer.

        Args:
            image_processor: ImageProcessor instance for OCR text extraction
        """
        self.image_processor = image_processor
        self.pdf_available = PDF_AVAILABLE

    async def extract_content(self, pdf_path: str) -> dict[str, any]:
        """Extract content from PDF including text and images.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with keys:
            - 'text': Extracted text content from PDF
            - 'images_text': List of text extracted from images via OCR
            - 'metadata': PDF metadata if available
        """
        result = {
            'text': '',
            'images_text': [],
            'metadata': {}
        }

        if not self.pdf_available:
            logger.debug("PDF processing not available, returning empty result")
            return result

        try:
            # Validate PDF path exists
            path = Path(pdf_path)
            if not path.exists():
                logger.warning(f"PDF file not found: {pdf_path}")
                return result

            if not path.is_file():
                logger.warning(f"Path is not a file: {pdf_path}")
                return result

            # Open PDF document
            doc = fitz.open(pdf_path)

            # Extract metadata
            result['metadata'] = doc.metadata

            # Extract text and images from each page
            all_text = []
            all_images_text = []

            for page_num in range(doc.page_count):
                page = doc[page_num]

                # Extract text from page
                page_text = page.get_text().strip()
                if page_text:
                    all_text.append(page_text)

                # Extract images from page if image processor available
                if self.image_processor:
                    images_text = await self._extract_images_from_page(page, page_num)
                    all_images_text.extend(images_text)

            doc.close()

            # Combine all text
            result['text'] = '\n\n'.join(all_text)
            result['images_text'] = all_images_text

            logger.debug(f"Extracted {len(result['text'])} text characters and {len(all_images_text)} image texts from {pdf_path}")
            return result

        except Exception as e:
            logger.error(f"Failed to extract content from PDF {pdf_path}: {e}")
            return result

    async def _extract_images_from_page(self, page, page_num: int) -> list[str]:
        """Extract images from a PDF page and run OCR on them.

        Args:
            page: PyMuPDF page object
            page_num: Page number for logging

        Returns:
            List of text strings extracted from images
        """
        images_text = []

        if not self.image_processor:
            return images_text

        try:
            # Get images from page
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                try:
                    # Extract image
                    xref = img[0]
                    pix = fitz.Pixmap(page.parent, xref)

                    # Skip if not RGB/RGBA
                    if pix.n - pix.alpha < 4:
                        # Create temporary file for image
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                            temp_path = temp_file.name

                        try:
                            # Save image to temporary file
                            pix.save(temp_path)

                            # Extract text from image using OCR
                            text = await self.image_processor.extract_text_from_image(temp_path)
                            if text.strip():
                                images_text.append(text.strip())
                                logger.debug(f"Extracted text from image {img_index} on page {page_num}")

                        finally:
                            # Clean up temporary file
                            Path(temp_path).unlink(missing_ok=True)

                    pix = None  # Release memory

                except Exception as img_err:
                    logger.debug(f"Failed to process image {img_index} on page {page_num}: {img_err}")
                    continue

        except Exception as e:
            logger.debug(f"Failed to extract images from page {page_num}: {e}")

        return images_text

    def is_pdf_file(self, file_path: str) -> bool:
        """Check if file is a PDF.

        Args:
            file_path: Path to check

        Returns:
            True if file is PDF, False otherwise
        """
        return Path(file_path).suffix.lower() == '.pdf'
