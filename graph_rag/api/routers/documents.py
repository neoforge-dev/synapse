import logging  # Import logging
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

# Defer schema import
# from graph_rag.api import schemas
from graph_rag.api import schemas  # Restore top-level import
from fastapi import Request


# Lazy wrappers to avoid circular import with app factory
def _state_get_graph_repository(request: Request) -> "GraphRepository":
    from graph_rag.api.main import get_graph_repository as _getter

    return _getter(request)


def _state_get_vector_store(request: Request) -> "VectorStore":
    from graph_rag.api.main import get_vector_store as _getter

    return _getter(request)


# Import GraphRepository interface for type hinting
from graph_rag.core.interfaces import GraphRepository, VectorStore
from graph_rag.domain.models import (
    Entity,
)

# from graph_rag.core.graph_store import GraphStore # Remove incorrect import
# from graph_rag.core.vector_store import VectorStore # Incorrect import

# router = APIRouter(prefix="/documents", tags=["Documents"]) # REMOVE direct creation
logger = logging.getLogger(__name__)  # Logger for this module


def create_documents_router() -> APIRouter:
    """Factory function to create the documents router with its endpoints."""
    router = APIRouter()  # Create router inside factory

    @router.post(
        "",
        # response_model=schemas.CreateResponse, # Deferred
        response_model=schemas.CreateResponse,  # Restore
        status_code=status.HTTP_201_CREATED,
        summary="Add a single document",
        description="Adds a new document node to the graph.",
    )
    async def add_document(
        doc_in: schemas.DocumentCreate,  # Restore type hint
        repo: Annotated[
            GraphRepository, Depends(_state_get_graph_repository)
        ],  # Depend on state-aware getter
    ):
        """Creates a new document entity in the graph. Uses provided ID if available, otherwise generates one."""
        try:
            # Use provided ID or generate a new one
            document_id = doc_in.id if doc_in.id else str(uuid.uuid4())

            # Ensure metadata is a dict, even if None was provided
            doc_metadata = doc_in.metadata or {}

            # document_entity = Entity(id=doc_in.id, type="Document", properties=doc_in.metadata or {}) # Original has error if metadata is None
            # document_id = str(uuid.uuid4()) # Generate ID if not provided or handle optionality - REVERT TO ORIGINAL INTENT (use ID from request if available, or define how it's generated)
            # For now, assume DocumentCreate schema requires an ID or handles generation
            # Let's assume doc_in MUST provide metadata, or handle None
            # document_id = str(uuid.uuid4()) # Temporarily keep ID generation
            document_entity = Entity(
                id=document_id, type="Document", properties=doc_metadata
            )
            await repo.add_entity(document_entity)
            logger.info(f"Document added with ID: {document_id}")
            # Ensure response model matches the actual return type after local import
            return schemas.CreateResponse(id=document_id)
        except Exception as e:
            logger.error(
                f"Error adding document: {e}", exc_info=True
            )  # Removed potentially non-existent doc_in.id from log
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add document",
            )

    @router.get(
        "",
        # response_model=List[schemas.DocumentResponse], # Deferred
        response_model=list[schemas.DocumentResponse],  # Restore
        summary="List all documents",
        description="Retrieves all document nodes from the graph. Warning: potentially large response.",
    )
    async def list_all_documents(
        repo: Annotated[
            GraphRepository, Depends(_state_get_graph_repository)
        ],  # Depend on state-aware getter
        limit: Optional[int] = Query(
            100, description="Limit the number of documents returned", ge=1, le=1000
        ),
        # ) -> List['schemas.DocumentResponse']: # Use forward reference string in type hint - REMOVE
    ):
        # from graph_rag.api import schemas # Import locally - REMOVE
        """Fetches all documents, potentially limited."""
        try:
            # Assuming search_entities_by_properties exists and works as intended
            # The original implementation had 'type' hardcoded, let's keep that for now
            doc_entities = await repo.search_entities_by_properties(
                {"type": "Document"}, limit=limit
            )
            # Manually construct DocumentResponse objects to map Entity.properties to DocumentResponse.metadata
            return [
                schemas.DocumentResponse(
                    id=entity.id,
                    metadata=entity.properties.get(
                        "metadata", {}
                    ),  # Extract only the metadata field
                    type=entity.type,
                    created_at=entity.properties.get(
                        "created_at"
                    ),  # Extract from properties
                    updated_at=entity.properties.get(
                        "updated_at"
                    ),  # Extract from properties
                )
                for entity in doc_entities
            ]
        except Exception as e:
            logger.error(f"Error listing documents: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents",
            )

    @router.get(
        "/{document_id}",
        # response_model=schemas.DocumentResponse, # Deferred
        response_model=schemas.DocumentResponse,  # Restore
        summary="Get document by ID",
        # responses={ # Deferred
        #     404: {"model": schemas.ErrorDetail, "description": "Document not found"},
        #     500: {"model": schemas.ErrorDetail}
        # }
        responses={  # Restore
            404: {"model": schemas.ErrorDetail, "description": "Document not found"},
            500: {"model": schemas.ErrorDetail},
        },
    )
    async def get_document(
        document_id: str,
        repo: Annotated[
            GraphRepository, Depends(_state_get_graph_repository)
        ],  # Depend on state-aware getter
        # ) -> 'schemas.DocumentResponse': # Use forward reference string in type hint - REMOVE
    ):
        # from graph_rag.api import schemas # Import locally - REMOVE
        """Retrieve a specific document by its unique ID."""
        # Ensure get_entity_by_id exists and returns expected structure or None
        doc_entity = await repo.get_entity_by_id(document_id)
        if not doc_entity or doc_entity.type != "Document":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id '{document_id}' not found",
            )
        # Map properties to metadata in the response, include type and timestamps if present
        return schemas.DocumentResponse(
            id=doc_entity.id,
            metadata=doc_entity.properties.get(
                "metadata", {}
            ),  # Extract only the metadata field
            type=doc_entity.type,
            created_at=doc_entity.properties.get(
                "created_at"
            ),  # Extract from properties
            updated_at=doc_entity.properties.get(
                "updated_at"
            ),  # Extract from properties
        )

    @router.delete(
        "/{document_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Delete Document and Associated Chunks",
    )
    async def delete_document(
        document_id: str,
        repo: Annotated[
            GraphRepository, Depends(_state_get_graph_repository)
        ],  # Depend on state-aware getter
        vector_store: Annotated[
            VectorStore, Depends(_state_get_vector_store)
        ],  # Depend on state-aware getter
        response: Response,  # Inject Response object for status code setting
    ):
        """
        Delete a document and all chunks directly associated with it from both the graph and vector store.

        Returns:
        - 204 No Content: If deletion is successful.
        - 404 Not Found: If the document ID does not exist.
        - 500 Internal Server Error: If a database error occurs.
        """
        logger.info(
            f"--- ENTERING delete_document HANDLER for doc_id: {document_id} ---"
        )  # ADDED LOG
        logger.info(f"Attempting to delete document {document_id} and its chunks.")
        try:
            # First, get all chunks belonging to this document
            try:
                chunks = await repo.get_chunks_by_document_id(document_id)
                chunk_ids = [chunk.id for chunk in chunks]
                logger.info(
                    f"Found {len(chunk_ids)} chunks to delete from vector store for document {document_id}"
                )

                # Remove chunks from vector store
                if chunk_ids:
                    try:
                        await vector_store.delete_chunks(chunk_ids)
                        logger.info(
                            f"Deleted {len(chunk_ids)} chunks from vector store"
                        )
                    except Exception as vs_e:
                        logger.warning(
                            f"Failed to delete chunks from vector store: {vs_e}. Continuing with graph deletion."
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve chunks for document {document_id}: {e}. Continuing with document deletion."
                )

            # Then delete the document (and its chunks) from the graph
            deleted = await repo.delete_document(document_id)
            if not deleted:
                logger.warning(f"Document {document_id} not found for deletion.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with id {document_id} not found or could not be deleted.",
                )

            logger.info(f"Successfully deleted document {document_id}")
            # Status code 204 already set by decorator, no return body needed.
            return

        except HTTPException:  # Re-raise HTTP exceptions (like the 404 above)
            raise
        except Exception as e:
            # Logger in repository likely logged specifics
            logger.error(
                f"API Error: Failed to delete document {document_id}. Error: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document {document_id}. Check logs for details.",
            )

    @router.patch(
        "/{document_id}/metadata",
        # response_model=schemas.DocumentResponse, # Deferred
        response_model=schemas.DocumentResponse,  # Restore
        summary="Update document metadata",
        description="Updates the metadata properties of an existing document node.",
        # responses={ # Deferred
        #     404: {"model": schemas.ErrorDetail, "description": "Document not found"},
        #     500: {"model": schemas.ErrorDetail}
        # }
        responses={  # Restore
            404: {"model": schemas.ErrorDetail, "description": "Document not found"},
            500: {"model": schemas.ErrorDetail},
        },
    )
    async def update_document_metadata(
        document_id: str,
        metadata_update: schemas.DocumentMetadataUpdate,
        graph_repo: Annotated[
            GraphRepository, Depends(_state_get_graph_repository)
        ],  # Depend on state-aware getter
    ):
        try:
            existing_entity = await graph_repo.get_entity_by_id(document_id)
            if not existing_entity or existing_entity.type != "Document":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with id '{document_id}' not found",
                )
            updated_properties = existing_entity.properties.copy()
            update_data = metadata_update.model_dump(exclude_unset=True).get(
                "properties", {}
            )
            updated_properties.update(update_data)
            updated_entity = Entity(
                id=document_id, type="Document", properties=updated_properties
            )
            await graph_repo.add_entity(updated_entity)
            logger.info(f"Updated metadata for document {document_id}")
            # Return the merged/updated entity directly (do not re-fetch)
            return schemas.DocumentResponse(
                id=updated_entity.id,
                metadata=updated_entity.properties,
                type=updated_entity.type,
                created_at=getattr(updated_entity, "created_at", None),
                updated_at=getattr(updated_entity, "updated_at", None),
            )
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(
                f"Error updating metadata for document {document_id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update document metadata",
            )

    # TODO: Consider PUT endpoint for full document replacement?

    # TODO: Add endpoints for updating documents

    return router  # Return the configured router instance
