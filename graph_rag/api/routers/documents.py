from fastapi import APIRouter, HTTPException, status, Response
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

@router.get("/{document_id}", response_model=schemas.DocumentRead)
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
        return schemas.DocumentRead(
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
    response_model=schemas.DocumentRead, 
    summary="Update Document Metadata"
)
async def update_document_metadata(
    document_id: str,
    update_data: schemas.DocumentUpdateMetadata,
    repo: GraphRepositoryDep
):
    """
    Update specific properties of a document (currently only metadata).
    Uses PATCH semantics - only updates fields provided in the request body.
    """
    logger.info(f"Attempting to update metadata for document {document_id}")
    
    properties_to_update: Dict[str, Any] = update_data.model_dump(exclude_unset=True)
    
    if not properties_to_update:
         logger.warning(f"PATCH request for document {document_id} received with no fields to update.")
         # Fetch and return the current document state if no update fields are provided
         current_doc = await repo.get_document(document_id)
         if current_doc is None:
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail=f"Document with id {document_id} not found."
             )
         # Return current doc using the response model
         return schemas.DocumentRead(
             id=current_doc.id, type=current_doc.type, content=current_doc.content,
             metadata=current_doc.metadata, created_at=current_doc.created_at,
             updated_at=current_doc.updated_at, properties={}
         )

    # Currently, only metadata is allowed. If other fields were sent, 
    # update_data schema validation (if strict) or this check would handle it.
    if "metadata" not in properties_to_update:
         logger.warning(f"PATCH request for document {document_id} contained non-updatable fields: {properties_to_update.keys()}")
         raise HTTPException(
             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
             detail="Only 'metadata' field can be updated via PATCH."
         )
         
    try:
        updated_document = await repo.update_document_properties(document_id, properties_to_update)
        
        if updated_document is None:
            logger.warning(f"Document {document_id} not found during update attempt.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found."
            )
        
        logger.info(f"Successfully updated metadata for document {document_id}")
        # Map domain model to response schema
        return schemas.DocumentRead(
            id=updated_document.id,
            type=updated_document.type,
            content=updated_document.content,
            metadata=updated_document.metadata,
            created_at=updated_document.created_at,
            updated_at=updated_document.updated_at,
            properties={}
        )

    except HTTPException: # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"API Error: Failed to update document {document_id}. Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document {document_id}. Check logs for details."
        )

# TODO: Consider PUT endpoint for full document replacement?

# TODO: Add endpoints for updating documents 