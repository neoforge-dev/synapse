"""Image processing service with OCR capabilities."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import vision dependencies with graceful fallback
try:
    import pytesseract
    from PIL import Image
    
    VISION_AVAILABLE = True
    logger.info("Vision processing dependencies available")
except ImportError as e:
    VISION_AVAILABLE = False
    logger.info(f"Vision processing dependencies not available: {e}")
    pytesseract = None
    Image = None


class ImageProcessor:
    """Service for extracting text from images using OCR."""

    def __init__(self):
        """Initialize the ImageProcessor."""
        self.vision_available = VISION_AVAILABLE
        
    async def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image file using OCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text as string, empty string if extraction fails or vision unavailable
        """
        if not self.vision_available:
            logger.debug("Vision processing not available, returning empty string")
            return ""
            
        try:
            # Validate image path exists
            path = Path(image_path)
            if not path.exists():
                logger.warning(f"Image file not found: {image_path}")
                return ""
                
            if not path.is_file():
                logger.warning(f"Path is not a file: {image_path}")
                return ""
                
            # Open and process image
            with Image.open(image_path) as img:
                # Extract text using pytesseract
                text = pytesseract.image_to_string(img).strip()
                logger.debug(f"Extracted {len(text)} characters from {image_path}")
                return text
                
        except Exception as e:
            logger.error(f"Failed to extract text from image {image_path}: {e}")
            return ""
            
    def is_supported_format(self, file_path: str) -> bool:
        """Check if the image format is supported.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            True if format is supported, False otherwise
        """
        if not self.vision_available:
            return False
            
        supported_extensions = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif'}
        return Path(file_path).suffix.lower() in supported_extensions
        
    async def extract_text_from_multiple_images(self, image_paths: list[str]) -> list[str]:
        """Extract text from multiple images.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            List of extracted text strings
        """
        results = []
        for image_path in image_paths:
            text = await self.extract_text_from_image(image_path)
            results.append(text)
        return results