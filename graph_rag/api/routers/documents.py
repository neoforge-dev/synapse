from fastapi import APIRouter, HTTPException, status, Response, Depends
from typing import List, Dict, Any # Added Dict, Any
import logging # Import logging
import uuid

from graph_rag.api import schemas
from graph_rag.domain.models import Document
from graph_rag.api.dependencies import GraphRepositoryDep

router = APIRouter()
logger = logging.getLogger(__name__) # Logger for this module

@router.post(
    "/", 
    response_model=schemas.CreateResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_document(
    document_in: schemas.DocumentCreate,
    repo: GraphRepositoryDep
):
    """Create a new document node in the graph."""
    doc_id = document_in.id or str(uuid.uuid4()) # Ensure ID exists
    logger.info(f"Attempting to create document with proposed ID: {doc_id}")
    document = Document(
        id=doc_id,
        content=document_in.content,
        metadata=document_in.metadata
    )
    try:
        created_doc_id = await repo.save_document(document)
        logger.info(f"Successfully created document {created_doc_id}")
        return schemas.CreateResponse(id=created_doc_id)
    except Exception as e:
        # Logger in repository already logged details
        logger.error(f"API Error: Failed to save document (proposed ID: {doc_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document. Check logs for details."
        )

@router.get("/{document_id}", response_model=schemas.DocumentResponse)
async def get_document(
    document_id: str,
    repo: GraphRepositoryDep
):
    """Retrieve a document by its ID."""
    logger.info(f"Attempting to retrieve document {document_id}")
    try:
        document = await repo.get_document(document_id)
        if document is None:
            logger.warning(f"Document {document_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found"
            )
        
        logger.info(f"Successfully retrieved document {document_id}")
        # Map domain model to response schema
        return schemas.DocumentResponse(
            id=document.id,
            type=document.type,
            content=document.content,
            metadata=document.metadata,
            created_at=document.created_at,
            updated_at=document.updated_at,
            properties={} 
        )
    except HTTPException: # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Logger in repository already logged details
        logger.error(f"API Error: Failed to retrieve document {document_id}. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document. Check logs for details."
        )

@router.delete(
    "/{document_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Document and Associated Chunks"
)
async def delete_document(
    document_id: str,
    repo: GraphRepositoryDep,
    response: Response # Inject Response object for status code setting
):
    """
    Delete a document and all chunks directly associated with it.
    
    Returns:
    - 204 No Content: If deletion is successful.
    - 404 Not Found: If the document ID does not exist.
    - 500 Internal Server Error: If a database error occurs.
    """
    logger.info(f"Attempting to delete document {document_id} and its chunks.")
    try:
        deleted = await repo.delete_document(document_id)
        if not deleted:
            logger.warning(f"Document {document_id} not found for deletion.")
            # Raise 404, but set status code on response as well for clarity
            response.status_code = status.HTTP_404_NOT_FOUND 
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found or could not be deleted."
            )
        
        logger.info(f"Successfully deleted document {document_id}")
        # Status code 204 already set by decorator, no return body needed.
        return 
        
    except HTTPException: # Re-raise HTTP exceptions (like the 404 above)
        raise
    except Exception as e:
        # Logger in repository likely logged specifics
        logger.error(f"API Error: Failed to delete document {document_id}. Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document {document_id}. Check logs for details."
        )

@router.patch(
    "/{document_id}",
    response_model=schemas.DocumentResponse, # Corrected response model
    summary="Update Document Metadata",
    description="Updates the metadata of a specific document by its ID.",
    responses={
        404: {"description": "Document not found"},
        500: {"description": "Internal server error during update"},
    },
    tags=["Documents"]
)
async def update_document_metadata(
    document_id: str,
    update_data: schemas.DocumentUpdateMetadataRequest, # Corrected request schema type hint
    graph_repo: GraphRepositoryDep, # Removed '= Depends()'
    # entity_extractor: EntityExtractorDep = Depends(), # Keep if needed for updates
) -> schemas.DocumentResponse:
    """Updates the metadata for a document identified by `document_id`.

    Args:
        document_id (str): The unique ID of the document to update.
        update_data (schemas.DocumentUpdateMetadataRequest): The new metadata to apply.
        graph_repo (GraphRepository): Injected graph repository dependency.

    Returns:
        schemas.DocumentResponse: The updated document representation.

    Raises:
        HTTPException: 404 if the document is not found.
        HTTPException: 500 if there's an error during the update.
    """
    logger.info(f"Attempting to update metadata for document ID: {document_id}")
    try:
        # Fetch the existing document first to ensure it exists
        existing_node = await graph_repo.get_node(document_id)
        if not existing_node or existing_node.get("_label") != "Document":
            logger.warning(f"Update failed: Document ID {document_id} not found.")
            raise HTTPException(status_code=404, detail="Document not found")

        # Update the metadata
        updated_node_data = await graph_repo.update_node_properties(
            document_id,
            update_data.metadata
        )

        if not updated_node_data:
             # Should not happen if get_node succeeded, but handle defensively
            logger.error(f"Update failed unexpectedly for document ID: {document_id} after verifying existence.")
            raise HTTPException(status_code=500, detail="Failed to update document metadata after finding it")

        logger.info(f"Successfully updated metadata for document ID: {document_id}")
        # Return the updated document using DocumentResponse schema
        return schemas.DocumentResponse(
            id=updated_node_data["id"],
            type=updated_node_data["_label"], # Assuming type is stored in _label
            content=updated_node_data["content"], # Assuming content is stored
            metadata=updated_node_data["metadata"],
            created_at=updated_node_data.get("created_at"), # Use .get for optional fields
            updated_at=updated_node_data.get("updated_at")
        )

    except HTTPException as http_exc: # Re-raise HTTP exceptions
        raise http_exc
    except Exception as e:
        logger.error(f"Error updating metadata for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error updating document: {e}")

# TODO: Consider PUT endpoint for full document replacement?

# TODO: Add endpoints for updating documents 