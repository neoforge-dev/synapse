"""Optimized Memgraph graph store implementation."""

import asyncio
import json
import logging
from datetime import date, datetime, timezone
from typing import Any

# Import specific exceptions if needed, or catch the base mgclient.Error
# from mgclient import OperationalError, DatabaseError # Example
import mgclient
import neo4j.time  # Import neo4j.time for type checking
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from graph_rag.config import Settings, get_settings
from graph_rag.core.graph_store import GraphStore
from graph_rag.core.interfaces import GraphRepository  # Import GraphRepository protocol
from graph_rag.domain.models import Chunk, Document, Entity, Node, Relationship

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define exceptions to retry on using available mgclient errors
_RETRY_EXCEPTIONS = (mgclient.Error, ConnectionRefusedError, ConnectionError)

# Define retry parameters using the loaded settings
# Add checks for attribute existence just in case
_MAX_RETRIES = getattr(settings, "memgraph_max_retries", 3)
_RETRY_DELAY = getattr(
    settings, "memgraph_retry_delay", 2
)  # Assuming memgraph_retry_delay is the correct name


def _convert_neo4j_temporal_types(data: dict[str, Any]) -> dict[str, Any]:
    """Converts Neo4j temporal types to standard Python types."""
    converted_data = {}
    for key, value in data.items():
        if isinstance(value, (neo4j.time.DateTime, neo4j.time.Date, neo4j.time.Time)):
            converted_data[key] = value.to_native()
        else:
            converted_data[key] = value
    return converted_data


class MemgraphConnectionConfig(BaseSettings):  # Inherit from BaseSettings
    """Configuration specific to Memgraph connection.
    Can be initialized from a global Settings object or load directly
    from environment variables with MEMGRAPH_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="MEMGRAPH_",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields if passed from a broader Settings object
    )

    host: str = Field(
        "127.0.0.1", description="Hostname or IP address of the Memgraph instance."
    )
    port: int = Field(7687, description="Port number for the Memgraph instance.")
    user: str | None = Field(
        None, description="Username for Memgraph connection (if required)."
    )
    password: SecretStr | None = Field(
        None, description="Password for Memgraph connection (if required)."
    )
    use_ssl: bool = Field(
        False, description="Whether to use SSL for Memgraph connection."
    )
    max_retries: int = Field(
        3, ge=0, description="Maximum connection/query retries for Memgraph."
    )
    retry_delay: int = Field(
        2, ge=1, description="Delay in seconds between Memgraph retries."
    )

    def __init__(self, settings_obj: Settings | None = None, **kwargs):
        """
        Initializes MemgraphConnectionConfig.
        Prioritizes values from settings_obj if provided, otherwise loads from env or defaults.
        kwargs are passed to BaseSettings for env/default loading.
        """
        if settings_obj:
            # If a Settings object is provided, use its values, overriding env/defaults
            super().__init__(
                host=settings_obj.memgraph_host,
                port=settings_obj.memgraph_port,
                user=settings_obj.memgraph_user,
                password=settings_obj.memgraph_password,  # Already a SecretStr or None
                use_ssl=settings_obj.memgraph_use_ssl,
                max_retries=settings_obj.memgraph_max_retries,
                retry_delay=settings_obj.memgraph_retry_delay,
                **kwargs,  # Pass through any other kwargs for BaseSettings
            )
        else:
            # No Settings object, load from environment variables (MEMGRAPH_ prefix) or defaults
            super().__init__(**kwargs)


class MemgraphGraphRepository(GraphStore, GraphRepository):
    """Optimized Memgraph implementation of both GraphStore and GraphRepository interfaces."""

    def __init__(self, settings_obj: Settings | None = None):
        """Initializes the repository, establishing connection parameters."""
        if settings_obj is None:
            # Ensure we get a Settings instance if None is passed
            settings_obj = get_settings()
        self.config = MemgraphConnectionConfig(settings_obj=settings_obj)
        self._connection: mgclient.Connection | None = (
            None  # Added connection attribute
        )
        # mgclient uses synchronous connect, connection pooling is handled internally or needs manual management
        # We don't store a persistent driver/connection object here in this sync implementation
        logger.info(
            f"MemgraphGraphRepository initialized for {self.config.host}:{self.config.port}"
        )

    async def connect(self):
        """Establishes and stores a connection for reuse."""
        # Assume connection is None or needs re-establishing if connect is called
        # Rely on mgclient to raise errors if operations are attempted on a closed connection
        if self._connection is None:
            loop = asyncio.get_running_loop()
            try:
                self._connection = await loop.run_in_executor(
                    None, self._get_connection
                )
                logger.info("Persistent connection established.")
            except Exception as e:
                logger.error(
                    f"Failed to establish persistent connection: {e}", exc_info=True
                )
                self._connection = None  # Ensure it's None on failure
                raise  # Re-raise the connection error

    async def close(self):
        """Closes the stored connection if it exists."""
        # Directly attempt to close if connection exists
        if self._connection:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, self._connection.close)
                logger.info("Persistent connection closed.")
            except Exception as e:
                logger.error(
                    f"Failed to close persistent connection: {e}", exc_info=True
                )
            finally:
                self._connection = None

    @retry(
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_fixed(_RETRY_DELAY),
        retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
        reraise=True,
    )
    def _get_connection(self) -> mgclient.Connection:
        """Establishes and returns a new synchronous connection to Memgraph."""
        try:
            logger.debug(
                f"Attempting to connect to Memgraph at {self.config.host}:{self.config.port}..."
            )
            # Ensure username and password are strings, even if empty, for positional args
            db_user = self.config.user if self.config.user is not None else ""
            # Extract raw string from SecretStr for mgclient
            db_password = (
                self.config.password.get_secret_value()
                if self.config.password is not None
                else ""
            )

            conn = mgclient.Connection(
                host=self.config.host,
                port=self.config.port,
                username=db_user,  # Use sanitized user
                password=db_password,  # Use sanitized password
                sslmode=mgclient.MG_SSLMODE_REQUIRE
                if self.config.use_ssl
                else mgclient.MG_SSLMODE_DISABLE,
            )
            logger.debug("Connection successful.")
            return conn
        except mgclient.Error as e:
            logger.error(f"Failed to connect to Memgraph: {e}", exc_info=True)
            raise  # Re-raise to allow tenacity to handle retries
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during connection: {e}", exc_info=True
            )
            raise

    async def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Executes a Cypher query and returns results.
        Uses the existing connection if available, otherwise creates a temporary one.
        """
        loop = asyncio.get_running_loop()
        conn_to_use: mgclient.Connection | None = None
        cursor: mgclient.Cursor | None = None
        is_temporary_connection = False

        try:
            # Use existing connection if available
            if self._connection:
                conn_to_use = self._connection
                logger.debug("Using existing persistent connection for query.")
            else:
                # Create a temporary connection for this query
                conn_to_use = await loop.run_in_executor(None, self._get_connection)
                is_temporary_connection = True
                logger.debug("Created temporary connection for query.")

            if not conn_to_use:  # Safety check
                raise ConnectionError("Failed to get a database connection.")

            cursor = conn_to_use.cursor()
            logger.debug(f"Executing query: {query} with params: {params}")
            await loop.run_in_executor(None, cursor.execute, query, params or {})

            column_names = (
                [desc.name for desc in cursor.description] if cursor.description else []
            )
            results_raw = await loop.run_in_executor(None, cursor.fetchall)
            logger.debug(
                f"Raw results type: {type(results_raw)}, Content: {results_raw}"
            )
            dict_results = []
            for row in results_raw:
                try:
                    logger.debug(f"Processing row type: {type(row)}, Content: {row}")
                    dict_results.append(dict(zip(column_names, row, strict=False)))
                except TypeError as te:
                    logger.error(
                        f"TypeError processing row: {row}. Error: {te}", exc_info=True
                    )
                    raise

            # Restore automatic commit
            await loop.run_in_executor(None, conn_to_use.commit)
            logger.debug(
                f"Query executed and committed successfully, {len(dict_results)} results fetched. Temp: {is_temporary_connection}"
            )

            return dict_results
        except (mgclient.Error, ConnectionError) as e:
            logger.error(
                f"Error executing query: {query} | Params: {params} | Error: {e}",
                exc_info=True,
            )
            # Only attempt rollback on the connection we actually used
            if conn_to_use:
                try:
                    await loop.run_in_executor(
                        None, conn_to_use.rollback
                    )  # Rollback on error
                except Exception as rb_exc:
                    logger.error(
                        f"Failed to rollback transaction: {rb_exc}", exc_info=True
                    )
            raise  # Re-raise the original error
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}", exc_info=True)
            # Check if conn_to_use is not None before attempting rollback
            if conn_to_use:
                try:
                    await loop.run_in_executor(None, conn_to_use.rollback)
                except Exception as rb_exc:
                    logger.error(
                        f"Failed to rollback transaction: {rb_exc}", exc_info=True
                    )
            raise
        finally:
            # Close cursor always
            if cursor:
                try:
                    await loop.run_in_executor(None, cursor.close)  # Close cursor
                except Exception as c_exc:
                    logger.error(f"Failed to close cursor: {c_exc}", exc_info=True)
            # Only close the connection if it was temporary
            if is_temporary_connection and conn_to_use:
                try:
                    await loop.run_in_executor(
                        None, conn_to_use.close
                    )  # Close temporary connection
                    logger.debug("Temporary connection closed.")
                except Exception as conn_exc:
                    logger.error(
                        f"Failed to close temporary connection: {conn_exc}",
                        exc_info=True,
                    )

    async def add_document(self, document: Document):
        """Adds a document node to the graph."""
        logger.debug(f"Adding document {document.id}")

        # Prepare parameters, ensuring timezone aware datetimes
        created_at_dt = document.created_at or datetime.now(timezone.utc)
        if created_at_dt.tzinfo is None:
            created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)

        updated_at_dt = datetime.now(timezone.utc)

        params = {
            "id": document.id,
            "content": document.content,
            "metadata": document.metadata
            if document.metadata
            else {},  # Pass metadata as a map parameter
            "created_at": created_at_dt,
            "updated_at": updated_at_dt,
        }

        # Use individual property assignments in SET clauses
        query = """
        MERGE (d:Document {id: $id})
        ON CREATE SET 
            d.content = $content, 
            d.metadata = $metadata, 
            d.created_at = $created_at, 
            d.updated_at = $updated_at
        ON MATCH SET 
            d.content = $content, 
            d.metadata = $metadata, 
            d.updated_at = $updated_at 
        """

        try:
            # Execute query assumes commit happens within or implicitly
            await self.execute_query(query, params)
            logger.info(f"Successfully added/updated document {document.id}")
        except Exception as e:
            logger.error(f"Failed to add document {document.id}: {e}", exc_info=True)
            raise

    async def get_document_by_id(self, document_id: str) -> Document | None:
        """Retrieves a document by its ID, returning a Document object or None."""
        logger.debug(f"Attempting to retrieve document with ID: {document_id}")
        query = """
            MATCH (doc:Document {id: $document_id})
            RETURN doc
        """
        result = await self.execute_query(query, {"document_id": document_id})

        if not result:
            logger.warning(f"Document with ID '{document_id}' not found.")
            return None

        record = result[0]
        doc_node = record.get("doc")
        if doc_node is None:
            logger.error(
                f"Query for document {document_id} returned a record but no 'doc' field: {record}"
            )
            return None

        # Process properties (assuming execute_query returns processed dicts)
        if hasattr(doc_node, "properties") and isinstance(doc_node.properties, dict):
            doc_properties = doc_node.properties
        elif isinstance(doc_node, dict):
            doc_properties = doc_node
        else:
            logger.error(
                f"Unexpected type for doc_node: {type(doc_node)} for document {document_id}"
            )
            return None

        # Directly use metadata if it's a dict, handle potential errors
        metadata = doc_properties.get("metadata")
        if not isinstance(metadata, dict):
            if metadata is not None:
                # If it's not a dict but not None, log a warning and default to empty dict
                # This handles cases where it might unexpectedly be a string or other type
                logging.warning(
                    f"Metadata for document {document_id} is not a dictionary (Type: {type(metadata)}). Attempting to parse if string, else defaulting to empty dict."
                )
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                        if not isinstance(metadata, dict):
                            logging.warning(
                                f"Parsed metadata string for {document_id} did not result in a dict. Defaulting to empty dict."
                            )
                            metadata = {}
                    except json.JSONDecodeError:
                        logging.error(
                            f"Failed to parse metadata string for {document_id}. Defaulting to empty dict."
                        )
                        metadata = {}
                    except Exception as e:
                        logging.error(
                            f"Unexpected error parsing metadata string for {document_id}: {e}"
                        )
                        metadata = {}
                else:
                    # If it's not a string (and not None, not a dict), default to empty dict
                    metadata = {}
            else:
                # If metadata is None, default to empty dict
                metadata = {}

        # Convert timestamps (handle potential string or datetime objects)
        created_at = self._parse_datetime(
            doc_properties.get("created_at"), document_id, "created_at"
        )
        updated_at = self._parse_datetime(
            doc_properties.get("updated_at"), document_id, "updated_at"
        )

        try:
            # Instantiate and return the Document object
            return Document(
                id=doc_properties.get("id"),
                content=doc_properties.get("content"),  # Ensure content is retrieved
                metadata=metadata,  # Use the processed metadata
                created_at=created_at,
                updated_at=updated_at,
            )
        except Exception as e:
            logger.error(
                f"Failed to instantiate Document object for ID {document_id}: {e}",
                exc_info=True,
            )
            return None

    # Helper method for robust datetime parsing
    def _parse_datetime(
        self, value: Any, obj_id: str, field_name: str
    ) -> datetime | None:
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Handle potential timezone 'Z' suffix
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(value, datetime):
                dt = value
            elif isinstance(value, date):
                # Convert date to datetime (midnight)
                dt = datetime.combine(value, datetime.min.time())
            else:
                logging.warning(
                    f"Unexpected type for {field_name} for object {obj_id}: {type(value)}. Returning None."
                )
                return None

            # Ensure timezone-aware (assume UTC if naive)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        except ValueError as e:
            logging.error(
                f"Error parsing {field_name} string for object {obj_id}: '{value}'. Error: {e}"
            )
            return None
        except Exception as e:
            logging.error(
                f"Unexpected error converting {field_name} for object {obj_id}: {e}"
            )
            return None

    async def add_chunk(self, chunk: Chunk) -> None:
        """Adds or updates a chunk node and connects it to its document."""
        logger.debug(
            f"Adding/updating chunk {chunk.id} for document {chunk.document_id}"
        )
        created_at_dt = chunk.created_at or datetime.now(timezone.utc)
        if isinstance(created_at_dt, datetime) and created_at_dt.tzinfo is None:
            created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
        updated_at_dt = datetime.now(timezone.utc)

        query = """
        MERGE (c:Chunk {id: $id})
        ON CREATE SET
            c.document_id = $document_id,
            c.text = $text,
            c.embedding = $embedding,
            c.metadata = $metadata,
            c.created_at = $created_at,
            c.updated_at = $updated_at
        ON MATCH SET
            c.text = $text,
            c.embedding = $embedding,
            c.metadata = $metadata,
            c.updated_at = $updated_at
        WITH c
        MATCH (d:Document {id: $document_id})
        WHERE d IS NOT NULL  // Ensure the document node exists
        MERGE (d)-[:CONTAINS]->(c)
        RETURN count(d) as doc_count // Return count to check if match succeeded
        """

        # Ensure metadata is handled correctly (empty dict if None or missing)
        metadata_param = getattr(chunk, "metadata", None)
        metadata_param = metadata_param if metadata_param is not None else {}

        # Construct params dictionary using primitive types or explicitly handled types
        params = {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "text": chunk.text,
            "embedding": chunk.embedding,  # Pass embedding list directly (or None)
            "metadata": metadata_param,  # Use the guaranteed dict
            "created_at": created_at_dt,
            "updated_at": updated_at_dt,
        }

        try:
            results = await self.execute_query(query, params)
            if results and results[0].get("doc_count", 0) == 1:
                logger.info(
                    f"Successfully added/updated chunk {chunk.id} for document {chunk.document_id}"
                )
            else:
                logger.error(
                    f"Failed to add chunk {chunk.id}: Document {chunk.document_id} not found."
                )
                raise ValueError(
                    f"Document with ID {chunk.document_id} not found."
                )  # Raise specific error
        except Exception as e:
            # Avoid catching the ValueError we just raised
            if not isinstance(e, ValueError) or "Document with ID" not in str(e):
                logger.error(
                    f"Failed to add chunk {chunk.id} or relationship: {e}",
                    exc_info=True,
                )
                raise  # Re-raise other exceptions
            else:
                raise  # Re-raise the ValueError

    async def add_node(self, node: Node):
        """Adds or updates a generic node to the graph using its type as the label."""

        node_type_for_query = node.type
        if not node_type_for_query:
            logger.warning(
                f"Node {node.id} has an empty type. Defaulting to 'UnknownNode' for Cypher query."
            )
            node_type_for_query = "UnknownNode"

        logger.debug(
            f"Adding/updating node {node.id} (Original Type: '{node.type}', Using Type: '{node_type_for_query}')"
        )

        # Prepare properties map
        props_to_set = node.model_dump(
            exclude={"id", "created_at", "updated_at", "properties"}, exclude_none=True
        )
        if node.properties:
            props_to_set.update(node.properties)

        # Timestamps
        created_at_dt = node.created_at or datetime.now(timezone.utc)
        if isinstance(created_at_dt, datetime) and created_at_dt.tzinfo is None:
            created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
        updated_at_dt = datetime.now(timezone.utc)
        props_to_set["updated_at"] = updated_at_dt  # Add/update timestamp in props

        # Use SET n = props, n.created_at = $created_at, n.id = $id
        query = f"""
        MERGE (n:{escape_cypher_string(node_type_for_query)} {{id: $id}})
        ON CREATE SET n = $props, n.created_at = $created_at, n.id = $id
        ON MATCH SET n += $props
        """
        params = {
            "id": node.id,
            "props": props_to_set,
            "created_at": created_at_dt,
        }

        try:
            await self.execute_query(query, params)
            logger.info(f"Successfully added/updated node {node.id} ({node.type})")
        except Exception as e:
            logger.error(f"Failed to add node {node.id}: {e}", exc_info=True)
            raise

    async def add_nodes(self, nodes: list[Node]):
        """Adds multiple nodes in a single transaction using UNWIND."""
        if not nodes:
            return

        logger.debug(f"Adding/updating {len(nodes)} nodes in bulk.")
        nodes_data = []
        for node in nodes:
            props_to_set = node.properties.copy() if node.properties else {}
            created_at = node.created_at
            if isinstance(created_at, datetime) and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            updated_at = datetime.now(timezone.utc)
            props_to_set["updated_at"] = updated_at

            nodes_data.append(
                {
                    "id": node.id,
                    "type": node.type,  # Need type for label
                    "props": props_to_set,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

        # Note: This Cypher query assumes all nodes have the same type/label.
        # If nodes can have different types, this needs a more complex approach
        # (e.g., grouping by type or using APOC).
        # For now, assume a common label or handle error if types differ.
        first_node_type = nodes[0].type
        if not all(n.type == first_node_type for n in nodes):
            logger.error(
                "Bulk add_nodes currently only supports nodes of the same type."
            )
            # Fallback to individual adds for mixed types
            for node in nodes:
                await self.add_node(node)
            return

        query = f"""
        UNWIND $nodes as node_data
        MERGE (n:{escape_cypher_string(first_node_type)} {{id: node_data.id}})
        ON CREATE SET n += node_data.props, n.created_at = node_data.created_at
        ON MATCH SET n += node_data.props, n.updated_at = node_data.updated_at
        """
        params = {"nodes": nodes_data}
        try:
            await self.execute_query(query, params)
            logger.info(
                f"Successfully added/updated {len(nodes)} nodes with type {first_node_type}."
            )
        except Exception as e:
            logger.error(f"Failed to bulk add nodes: {e}", exc_info=True)
            raise

    async def get_node_by_id(self, node_id: str) -> Node | None:
        """Retrieves a node by its ID, determining its type (Document, Chunk, or Entity)."""
        query = """
        MATCH (n {id: $node_id})
        RETURN n, labels(n) as labels
        """
        params = {"node_id": node_id}
        try:
            results = await self.execute_query(query, params)
            if not results:
                logger.debug(f"Node with ID {node_id} not found.")
                return None

            node_obj = results[0].get("n")
            labels = results[0].get("labels", [])

            if not node_obj:
                logger.error(
                    f"Node object 'n' not found in query result for ID {node_id}."
                )
                return None

            node_properties = (
                node_obj.properties.copy() if hasattr(node_obj, "properties") else {}
            )
            logger.debug(
                f"Node {node_id} found. Raw Props from DB: {node_properties}, Labels: {labels}"
            )

            # Keep a copy of all properties before popping standard fields
            all_properties = node_properties.copy()

            retrieved_id = node_properties.pop("id", node_id)
            created_at_str = node_properties.pop(
                "created_at", None
            )  # Pop before potential conversion
            updated_at_str = node_properties.pop(
                "updated_at", None
            )  # Pop before potential conversion

            # Apply type conversions (if needed, potentially using _convert_neo4j_temporal_types)
            # For now, just parse the date strings we popped
            created_at, updated_at = None, None
            try:
                created_at = (
                    datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if isinstance(created_at_str, str)
                    else created_at_str
                )  # Handle non-string cases
            except (ValueError, TypeError):
                logger.warning(f"Could not parse created_at: {created_at_str}")
                created_at = None  # Fallback
            try:
                updated_at = (
                    datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    if isinstance(updated_at_str, str)
                    else updated_at_str
                )  # Handle non-string cases
            except (ValueError, TypeError):
                logger.warning(f"Could not parse updated_at: {updated_at_str}")
                updated_at = None  # Fallback

            # Also remove popped standard fields from the all_properties dict that will be passed to the model constructor
            all_properties.pop("id", None)
            all_properties.pop("created_at", None)
            all_properties.pop("updated_at", None)

            # Determine type
            node_model_type = None
            specific_entity_type = None
            base_labels = {"Node", "Entity", "_Node", "_Entity"}
            if "Document" in labels:
                node_model_type = "Document"
            elif "Chunk" in labels:
                node_model_type = "Chunk"
            else:
                for label in labels:
                    if label not in base_labels:
                        specific_entity_type = label
                        node_model_type = "Entity"
                        break
                if node_model_type is None and labels:
                    node_model_type = "Node"

            # Pass the full 'all_properties' dict to the 'properties' argument
            if node_model_type == "Document":
                # Extract specific fields needed for constructor args from the original dict
                content = node_properties.get("content", None)  # Use get instead of pop
                metadata = node_properties.get("metadata", {})  # Use get instead of pop
                return Document(
                    id=retrieved_id,
                    content=content,
                    metadata=metadata,
                    created_at=created_at,
                    updated_at=updated_at,
                    properties=all_properties,
                )
            elif node_model_type == "Chunk":
                text = node_properties.get("text", None)  # Use get instead of pop
                doc_id = node_properties.get(
                    "document_id", None
                )  # Use get instead of pop
                embedding = node_properties.get(
                    "embedding", None
                )  # Use get instead of pop
                return Chunk(
                    id=retrieved_id,
                    text=text,
                    document_id=doc_id,
                    embedding=embedding,
                    created_at=created_at,
                    updated_at=updated_at,
                    properties=all_properties,
                )
            elif node_model_type == "Entity":
                entity_name = node_properties.get(
                    "name", None
                )  # Use get instead of pop
                entity_type = specific_entity_type or "UnknownEntity"
                return Entity(
                    id=retrieved_id,
                    name=entity_name,
                    type=entity_type,
                    properties=all_properties,
                    created_at=created_at,
                    updated_at=updated_at,
                )
            elif node_model_type == "Node":
                node_name = node_properties.get("name", None)  # Use get instead of pop
                node_type = (
                    specific_entity_type
                    or next((label for label in labels if label not in base_labels), None)
                    or (labels[0] if labels else "Node")
                )
                return Node(
                    id=retrieved_id,
                    name=node_name,
                    type=node_type,
                    properties=all_properties,
                    created_at=created_at,
                    updated_at=updated_at,
                )
            else:
                logger.warning(
                    f"Node {retrieved_id} has no determinable type. Returning generic Node."
                )
                # Pass the original properties even for unknown types
                return Node(
                    id=retrieved_id,
                    type="Node",
                    properties=all_properties,
                    created_at=created_at,
                    updated_at=updated_at,
                )

        except Exception as e:
            logger.error(f"Failed to retrieve node {node_id}: {e}", exc_info=True)
            return None

    async def search_nodes_by_properties(
        self,
        properties: dict[str, Any],
        node_type: str | None = None,
        limit: int = 10,
    ) -> list[Node]:
        """Searches for nodes matching given properties, optionally filtering by type."""
        logger.debug(
            f"Searching nodes by properties: {properties}, type: {node_type}, limit: {limit}"
        )

        label_filter = f":{escape_cypher_string(node_type)}" if node_type else ""
        where_clauses = []
        params = {}  # Start with empty params
        prop_index = 0
        for key, value in properties.items():
            # Use parameterized props for safety
            param_name = f"prop_{prop_index}"
            where_clauses.append(f"n.`{escape_cypher_string(key)}` = ${param_name}")
            params[param_name] = value
            prop_index += 1

        where_clause = " AND ".join(where_clauses) if where_clauses else ""
        if where_clause:
            where_clause = f"WHERE {where_clause}"

        # Query returns the node object directly
        query = f"""
        MATCH (n{label_filter}) {where_clause}
        RETURN n
        LIMIT toInteger($limit)
        """
        params["limit"] = limit

        nodes = []
        try:
            results = await self.execute_query(query, params)
            for record in results:
                # Extract node object from result dict
                node_obj = record.get("n")
                if not node_obj:
                    continue

                # Extract properties and labels from node object
                node_props = (
                    node_obj.properties if hasattr(node_obj, "properties") else {}
                )
                labels = node_obj.labels if hasattr(node_obj, "labels") else set()
                converted_props = _convert_neo4j_temporal_types(node_props)

                node_id_prop = converted_props.pop("id", None)
                if not node_id_prop:
                    continue  # Skip nodes without ID?

                # Determine type - Safely handle the set of labels
                # Option 1: Get the first label if it exists
                found_node_type = next(iter(labels), "Unknown") if labels else "Unknown"
                # Option 2: Join labels if multiple are possible (adjust Node model if needed)
                # found_node_type = ":".join(sorted(list(labels))) if labels else "Unknown"

                created_at = converted_props.pop("created_at", None)
                updated_at = converted_props.pop("updated_at", None)
                name_prop = converted_props.pop("name", None)
                if name_prop and "name" not in converted_props:
                    converted_props["name"] = name_prop

                nodes.append(
                    Node(
                        id=node_id_prop,
                        type=found_node_type,
                        properties=converted_props,
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )
            return nodes
        except Exception as e:
            logger.error(f"Failed to search nodes by properties: {e}", exc_info=True)
            raise

    async def add_relationship(self, relationship: Relationship):
        """Adds a relationship to the graph with specific error handling."""

        rel_type_for_query = relationship.type
        if not rel_type_for_query:
            logger.warning(
                f"Relationship between {relationship.source_id} and {relationship.target_id} has an empty type. Defaulting to 'UnknownRelationship' for Cypher query."
            )
            rel_type_for_query = "UnknownRelationship"

        logger.debug(
            f"Adding relationship {relationship.source_id} -> {rel_type_for_query} -> {relationship.target_id}"
        )

        # Use properties field from Edge model
        props = relationship.properties.copy() if relationship.properties else {}
        # Handle timestamps for the relationship itself
        created_at = relationship.created_at
        if isinstance(created_at, datetime) and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        updated_at = datetime.now(timezone.utc)
        props["updated_at"] = updated_at  # Set updated_at on match/create
        props["id"] = (
            relationship.id
        )  # Ensure the relationship's ID is included in the properties to be set

        query = f"""
        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
        MERGE (source)-[r:{escape_cypher_string(rel_type_for_query)}]->(target)
        ON CREATE SET r = $props, r.created_at = $created_at
        ON MATCH SET r += $props, r.updated_at = $updated_at
        """
        await self.execute_query(
            query,
            {
                "source_id": relationship.source_id,
                "target_id": relationship.target_id,
                "props": props,  # props now includes the 'id'
                "created_at": created_at,
                "updated_at": updated_at,  # Pass updated_at as separate parameter
            },
        )
        logger.debug(
            f"Added/Updated relationship: {relationship.source_id} -[{relationship.type}]-> {relationship.target_id}"
        )

    async def add_entities_and_relationships(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> None:
        """Adds multiple entities and relationships in a single transaction."""
        if not entities and not relationships:
            return

        # Use .model_dump() for Pydantic v2 entities
        entity_params = [
            {
                "id": e.id,
                "type": e.type,  # Pass type for label creation
                # Entity model doesn't have properties field directly, get from .model_dump() if needed
                "props": e.model_dump(
                    exclude={"id", "type", "created_at", "updated_at"},
                    exclude_none=True,
                ),
            }
            for e in entities
        ]

        query = f"""
        UNWIND $entities AS entity_data
        MERGE (n:{entities[0].type if entities else "Entity"} {{id: entity_data.id}})
        ON CREATE SET n = entity_data.props, n.created_at = timestamp()
        ON MATCH SET n = entity_data.props, n.updated_at = timestamp()
        """

        if relationships:
            query += """
            WITH n
            UNWIND $relationships AS rel_data
            MATCH (source {{id: rel_data.source_id}}), (target {{id: rel_data.target_id}})
            MERGE (source)-[r:{relationships[0].type}]->(target) # Assuming all rels same type
            ON CREATE SET r = rel_data.props, r.created_at = timestamp()
            ON MATCH SET r = rel_data.props, r.updated_at = timestamp()
            """
            # Use properties field from Edge model
            rel_params = [
                {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "type": r.type,  # Pass type for relationship creation
                    "props": r.properties.copy() if r.properties else {},
                }
                for r in relationships
            ]
        else:
            rel_params = []

        # Need to handle potentially different entity types in bulk merge/create
        # This requires a more complex query, potentially using APOC or multiple statements.
        # Simplified approach for now: assuming all entities have the same type or handling error/fallback.
        if entities:
            first_entity_type = entities[0].type
            if not all(e.type == first_entity_type for e in entities):
                logger.warning(
                    "Bulk add_entities_and_relationships processing mixed entity types individually."
                )
                # Fallback to individual adds
                for entity in entities:
                    await self.add_node(entity)  # Reuse add_node which handles types
                entity_query_part = ""  # Skip bulk entity query part
            else:
                entity_query_part = f"""
                UNWIND $entities AS entity_data
                MERGE (n:{escape_cypher_string(first_entity_type)} {{id: entity_data.id}})
                ON CREATE SET n = entity_data.props, n.created_at = timestamp()
                ON MATCH SET n += entity_data.props, n.updated_at = timestamp()
                WITH collect(n) as nodes_processed, $relationships as rels
                """  # Added WITH clause to pass relationships
        else:
            entity_query_part = "WITH $relationships as rels\n"  # Start with relationships if no entities

        if relationships:
            # Assuming all relationships have the same type for simplicity in MERGE
            first_rel_type = relationships[0].type
            if (
                not first_rel_type
            ):  # Check if the type of the first relationship is empty
                logger.warning(
                    "First relationship in batch has an empty type. Defaulting to 'UnknownRelationship' for Cypher query for this batch if all types are consistently empty or matching this first empty type."
                )
                first_rel_type_for_query = "UnknownRelationship"
            else:
                first_rel_type_for_query = first_rel_type

            if not all(
                r.type == first_rel_type for r in relationships
            ):  # Compares with original first_rel_type
                logger.warning(
                    "Bulk add_entities_and_relationships processing mixed relationship types individually."
                )
                # Fallback for relationships
                rel_query_part = ""  # Skip bulk rel part
                # Handle entities first if they exist
                if entity_query_part:
                    await self.execute_query(
                        entity_query_part.replace(
                            "WITH collect(n) as nodes_processed, $relationships as rels",
                            "",
                        ),
                        {"entities": entity_params},
                    )
                # Add relationships individually
                for rel in relationships:
                    await self.add_relationship(rel)
                # Set final query to empty if handled individually
                query = ""
            else:
                rel_query_part = f"""
                  UNWIND rels AS rel_data
                  MATCH (source {{id: rel_data.source_id}}), (target {{id: rel_data.target_id}})
                  MERGE (source)-[r:{escape_cypher_string(first_rel_type_for_query)}]->(target)
                  ON CREATE SET r = rel_data.props, r.created_at = timestamp()
                  ON MATCH SET r += rel_data.props, r.updated_at = timestamp()
                  """
            query = entity_query_part + rel_query_part
        else:
            query = entity_query_part.replace(
                ", $relationships as rels", ""
            )  # Remove rels if no relationships

        if query:  # Only execute if query is not empty (not handled individually)
            await self.execute_query(
                query, {"entities": entity_params, "relationships": rel_params}
            )
        logger.debug(
            f"Bulk processed {len(entities)} entities and {len(relationships)} relationships"
        )

    async def get_entity_by_id(self, entity_id: str) -> Entity | None:
        """Retrieves a single entity by its unique ID with error handling."""
        try:
            node = await self.get_node_by_id(entity_id)
            if node:
                # Attempt to convert the retrieved Node to an Entity
                try:
                    # Ensure properties is a dict even if None initially
                    node_properties = node.properties if node.properties else {}
                    # Extract name using get, default to id. DO NOT pop from original dict.
                    name = node_properties.get("name", node.id)
                    # Remaining items in node_properties are the additional properties
                    # We should pass the full properties dict (which still includes name if present)
                    # to the properties argument inherited from Node.
                    entity = Entity(
                        id=node.id,
                        name=name,  # Set the direct name attribute
                        type=node.type,  # Use the actual type retrieved from the node
                        properties=node_properties,  # Pass the full properties dict here
                        created_at=node.created_at,
                        updated_at=node.updated_at,
                    )
                    # Optional: Log successful conversion for clarity
                    # logger.debug(f"Successfully converted Node {entity_id} to Entity.")
                    return entity
                except Exception as conversion_error:
                    logger.error(
                        f"Failed to convert retrieved Node {entity_id} to Entity: {conversion_error}",
                        exc_info=True,
                    )
                    return None  # Return None if conversion fails
            # If node is None initially
            return None
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}", exc_info=True)
            raise

    async def get_neighbors(
        self,
        entity_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "both",
    ) -> tuple[list[Entity], list[Relationship]]:
        """Retrieves neighbors and relationships for a given entity ID."""
        logger.debug(
            f"Getting neighbors for entity {entity_id}, direction: {direction}, types: {relationship_types}"
        )

        # Build relationship type filter string
        rel_type_filter = ""
        if relationship_types:
            # Escape and format types for the query
            formatted_types = [f":`{t}`" for t in relationship_types]
            rel_type_filter = "|".join(formatted_types)

        # Build match clause based on direction
        if direction == "outgoing":
            match_clause = f"-[r{rel_type_filter}]->(neighbor)"
        elif direction == "incoming":
            match_clause = f"<-[r{rel_type_filter}]-(neighbor)"
        else:  # both
            match_clause = f"-[r{rel_type_filter}]-(neighbor)"

        # Query to get neighbor nodes, relationships, and necessary details
        # Ensure we get elementId for relationships if needed for unique ID
        query = f"""
        MATCH (start_node {{id: $entity_id}}){match_clause}
        WHERE start_node <> neighbor  // Avoid self-loops unless specifically desired
        RETURN \
            neighbor, \
            labels(neighbor) as neighbor_labels, \
            r as relationship, \
            type(r) as relationship_type, \
            id(r) as relationship_internal_id, // Use id(r) for internal ID
            startNode(r).id as source_node_id, // Explicitly get source ID
            endNode(r).id as target_node_id    // Explicitly get target ID
        """
        params = {"entity_id": entity_id}

        try:
            results = await self.execute_query(query, params)
            logger.debug(
                f"Neighbor query for {entity_id} returned {len(results)} results."
            )

            neighbors = []
            relationships = []
            processed_neighbor_ids = set()
            processed_rel_ids = set()

            for record in results:
                # Extract raw mgclient objects
                neighbor_node_obj = record.get("neighbor")
                neighbor_labels = record.get("neighbor_labels", [])
                rel_obj = record.get("relationship")
                rel_type = record.get("relationship_type")
                rel_internal_id = record.get("relationship_internal_id")
                source_id = record.get("source_node_id")
                target_id = record.get("target_node_id")

                if not neighbor_node_obj:
                    logger.warning(f"Neighbor node object missing in record: {record}")
                    continue

                # Get properties from the neighbor node object
                neighbor_props = (
                    neighbor_node_obj.properties.copy()
                    if hasattr(neighbor_node_obj, "properties")
                    else {}
                )
                neighbor_id = neighbor_props.get("id")
                if not neighbor_id:
                    logger.warning(
                        f"Neighbor node data missing 'id' property: {neighbor_props}"
                    )
                    continue

                if neighbor_id not in processed_neighbor_ids:
                    # Pop known fields, pass rest to properties
                    created_at_n = neighbor_props.pop("created_at", None)
                    updated_at_n = neighbor_props.pop("updated_at", None)
                    # Parse dates if necessary (add parsing logic here if needed)

                    # Determine neighbor type robustly
                    neighbor_node_model_type = "Node"
                    neighbor_entity_type = None
                    base_labels = {"Node", "Entity", "_Node", "_Entity"}
                    if "Document" in neighbor_labels:
                        neighbor_node_model_type = "Document"
                    elif "Chunk" in neighbor_labels:
                        neighbor_node_model_type = "Chunk"
                    else:
                        specific_labels = [
                            label for label in neighbor_labels if label not in base_labels
                        ]
                        if specific_labels:
                            neighbor_entity_type = specific_labels[0]
                            neighbor_node_model_type = "Entity"
                        elif neighbor_labels:
                            neighbor_entity_type = neighbor_labels[0]  # Fallback
                            neighbor_node_model_type = "Entity"

                    # Create the appropriate model instance
                    neighbor_node = None
                    if neighbor_node_model_type == "Document":
                        content = neighbor_props.pop("content", None)
                        metadata = neighbor_props.pop("metadata", {})
                        neighbor_node = Document(
                            id=neighbor_id,
                            content=content,
                            metadata=metadata,
                            properties=neighbor_props,
                            created_at=created_at_n,
                            updated_at=updated_at_n,
                        )
                    elif neighbor_node_model_type == "Chunk":
                        text = neighbor_props.pop("text", None)
                        doc_id = neighbor_props.pop("document_id", None)
                        embedding = neighbor_props.pop("embedding", None)
                        neighbor_node = Chunk(
                            id=neighbor_id,
                            text=text,
                            document_id=doc_id,
                            embedding=embedding,
                            properties=neighbor_props,
                            created_at=created_at_n,
                            updated_at=updated_at_n,
                        )
                    elif neighbor_node_model_type == "Entity":
                        name = neighbor_props.pop("name", None)
                        neighbor_node = Entity(
                            id=neighbor_id,
                            name=name,
                            type=neighbor_entity_type or "UnknownEntity",
                            properties=neighbor_props,
                            created_at=created_at_n,
                            updated_at=updated_at_n,
                        )
                    else:  # Generic Node
                        name = neighbor_props.pop("name", None)
                        node_type = (
                            neighbor_entity_type
                            or next(
                                (label for label in neighbor_labels if label not in base_labels),
                                None,
                            )
                            or (neighbor_labels[0] if neighbor_labels else "Node")
                        )
                        neighbor_node = Node(
                            id=neighbor_id,
                            name=name,
                            type=node_type,
                            properties=neighbor_props,
                            created_at=created_at_n,
                            updated_at=updated_at_n,
                        )

                    if neighbor_node:
                        neighbors.append(neighbor_node)
                        processed_neighbor_ids.add(neighbor_id)

                # Reconstruct Relationship (if not already processed)
                if rel_internal_id and rel_internal_id not in processed_rel_ids:
                    if not rel_obj:
                        logger.warning(
                            f"Relationship object missing in record for internal id {rel_internal_id}"
                        )
                        continue

                    # Get properties from the relationship object
                    rel_props = (
                        rel_obj.properties.copy()
                        if hasattr(rel_obj, "properties")
                        else {}
                    )
                    # Retrieve the user_id property we stored
                    relationship_user_id = rel_props.pop("user_id", None)
                    created_at_r = rel_props.pop("created_at", None)
                    updated_at_r = rel_props.pop("updated_at", None)
                    # Parse dates if necessary

                    relationship = Relationship(
                        # Use the user_id stored as a property, fallback to internal id
                        id=str(relationship_user_id)
                        if relationship_user_id
                        else str(rel_internal_id),
                        source_id=source_id,
                        target_id=target_id,
                        type=rel_type,
                        properties=rel_props,  # Remaining properties
                        created_at=created_at_r,
                        updated_at=updated_at_r,
                    )
                    relationships.append(relationship)
                    processed_rel_ids.add(rel_internal_id)

            logger.debug(
                f"Found {len(neighbors)} unique neighbors and {len(relationships)} unique relationships for {entity_id}."
            )
            return neighbors, relationships

        except Exception as e:
            logger.error(
                f"Failed to get neighbors for entity {entity_id}: {e}", exc_info=True
            )
            return [], []  # Return empty lists on error

    async def search_entities_by_properties(
        self, properties: dict[str, Any], limit: int | None = None
    ) -> list[Entity]:
        """Searches for entities matching specific properties."""
        # Check if 'type' is specified to use as a label constraint
        node_type = None
        if "type" in properties:
            node_type = properties.pop(
                "type"
            )  # Remove 'type' from properties to avoid using it as a property filter

        # Build the label filter
        label_filter = f":`{node_type}`" if node_type else ""

        # Build property filters
        where_clauses = []
        params = {}
        for i, (key, value) in enumerate(properties.items()):
            param_name = f"prop_val_{i}"
            # Escape key if needed
            safe_key = key
            where_clauses.append(f"e.`{safe_key}` = ${param_name}")
            params[param_name] = value

        # Build the WHERE clause
        where_clause = " AND ".join(where_clauses)
        where_part = f"WHERE {where_clause}" if where_clauses else ""

        # Build the LIMIT clause
        limit_clause = f"LIMIT {int(limit)}" if limit is not None and limit > 0 else ""

        # Query to use the label filter
        query = f"""
        MATCH (e{label_filter})
        {where_part}
        RETURN e
        {limit_clause}
        """

        results = await self.execute_query(query, params)
        entities = []

        for result in results:
            if "e" in result:
                node_data: mgclient.Node = result[
                    "e"
                ]  # Assuming result['e'] is mgclient.Node

                # Access properties correctly from mgclient.Node
                node_properties = (
                    node_data.properties if hasattr(node_data, "properties") else {}
                )
                node_id = str(
                    node_properties.get("id", "")
                )  # Get ID from properties dict
                # Determine type: Use explicit type from properties if stored, else label, else fallback
                node_actual_type = node_properties.get("type", node_type or "Unknown")

                # Reconstruct Entity
                entity = Entity(
                    id=node_id,
                    type=node_actual_type,
                    # Pass all properties excluding id/type if they are already handled
                    properties={
                        k: v
                        for k, v in node_properties.items()
                        if k not in ["id", "type"]
                    },
                    # Alternatively, pass the full properties dict if Entity model handles it:
                    # properties=node_properties
                )
                # Manually set name if it's a special field
                if "name" in node_properties:
                    entity.name = node_properties["name"]

                entities.append(entity)

        return entities

    async def add_entity(self, entity: Entity):
        """Adds or updates an Entity node to the graph."""
        # Reuse the add_node logic, ensuring the type is correctly handled
        # The Entity model already sets type='Entity'
        await self.add_node(entity)

    async def delete_document(self, document_id: str) -> bool:
        """Deletes a document and its associated chunks and relationships."""
        # Query: Match the document by ID
        # Optional Match: Match chunks by their document_id property
        # Detach and delete both matched document and chunks
        query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (c:Chunk {document_id: $doc_id}) // Match chunks by property
        DETACH DELETE d, c // Delete document and associated chunks
        RETURN count(d) as deleted_doc_count
        """
        params = {"doc_id": document_id}

        try:
            delete_results = await self.execute_query(query, params)
            # Check if the document itself was deleted (count(d) > 0)
            if delete_results and delete_results[0].get("deleted_doc_count", 0) > 0:
                logger.info(
                    f"Successfully deleted document {document_id} and associated chunks."
                )
                return True
            else:
                logger.warning(f"Document {document_id} not found or already deleted.")
                return False

        except Exception as e:
            logger.error(
                f"Error during deletion process for document {document_id}: {e}",
                exc_info=True,
            )
            return False

    async def __aenter__(self):
        """Context manager entry."""
        await self.execute_query("RETURN 1")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    async def get_chunks_by_document_id(self, document_id: str) -> list[Chunk]:
        """Get all chunks associated with a document."""
        query = """
        MATCH (d:Document {id: $document_id})-[:CONTAINS]->(c:Chunk)
        RETURN c
        """
        params = {"document_id": document_id}

        chunks = []
        try:
            results = await self.execute_query(query, params)
            for record in results:
                chunk_node = record.get("c")  # Get the mgclient.Node object
                if chunk_node and hasattr(chunk_node, "properties"):
                    chunk_properties = (
                        chunk_node.properties
                    )  # Access the properties dictionary
                    chunk = Chunk(
                        id=chunk_properties.get("id", ""),
                        text=chunk_properties.get("text", ""),
                        document_id=document_id,  # Already have this from the query/param
                        embedding=chunk_properties.get(
                            "embedding"
                        ),  # Assuming embedding is stored
                        metadata=chunk_properties.get(
                            "metadata", {}
                        ),  # Assuming metadata is stored
                        created_at=chunk_properties.get(
                            "created_at"
                        ),  # Assuming created_at is stored
                        updated_at=chunk_properties.get(
                            "updated_at"
                        ),  # Assuming updated_at is stored
                        properties=chunk_properties,  # Store the properties dict
                    )
                    chunks.append(chunk)
            return chunks
        except Exception as e:
            logger.error(
                f"Error retrieving chunks for document {document_id}: {e}",
                exc_info=True,
            )
            return []

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        """Adds multiple chunk nodes."""
        for chunk in chunks:
            await self.add_chunk(chunk)
        logger.info(f"Added {len(chunks)} chunks to graph store")

    async def get_chunk_by_id(self, chunk_id: str) -> Chunk | None:
        """Retrieves a chunk by its ID."""
        query = """
        MATCH (c:Chunk {id: $id})
        RETURN c
        """
        params = {"id": chunk_id}
        results = await self.execute_query(query, params)
        if results and len(results) > 0:
            chunk_node = results[0].get("c")  # Get the mgclient.Node object
            if chunk_node and hasattr(chunk_node, "properties"):
                chunk_properties = (
                    chunk_node.properties
                )  # Access the properties dictionary
                return Chunk(
                    id=chunk_properties.get("id", ""),
                    text=chunk_properties.get("text", ""),
                    document_id=chunk_properties.get(
                        "document_id", ""
                    ),  # Get from properties
                    embedding=chunk_properties.get(
                        "embedding"
                    ),  # Assuming embedding is stored
                    metadata=chunk_properties.get(
                        "metadata", {}
                    ),  # Assuming metadata is stored
                    created_at=chunk_properties.get(
                        "created_at"
                    ),  # Assuming created_at is stored
                    updated_at=chunk_properties.get(
                        "updated_at"
                    ),  # Assuming updated_at is stored
                    properties=chunk_properties,  # Store the properties dict
                )
        return None

    async def update_node_properties(
        self, node_id: str, properties: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Updates properties of an existing node."""
        query = """
        MATCH (n {id: $id})
        SET n += $properties
        RETURN n
        """
        params = {"id": node_id, "properties": properties}
        results = await self.execute_query(query, params)
        if results and len(results) > 0:
            return results[0].get("n", {})
        return None

    async def apply_schema_constraints(self) -> None:
        """Applies predefined schema constraints (e.g., uniqueness)."""
        # Define constraints for key entity types
        constraints = [
            "CREATE CONSTRAINT ON (d:Document) ASSERT d.id IS UNIQUE",
            "CREATE CONSTRAINT ON (c:Chunk) ASSERT c.id IS UNIQUE",
            "CREATE CONSTRAINT ON (e:Entity) ASSERT e.id IS UNIQUE",
            "CREATE CONSTRAINT ON (r:Relationship) ASSERT r.id IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                await self.execute_query(constraint)
                logger.info(f"Applied schema constraint: {constraint}")
            except Exception as e:
                # Skip if constraint already exists or other issues
                logger.warning(f"Failed to apply constraint '{constraint}': {e}")
                continue

    async def detect_communities(
        self, algorithm: str = "louvain", write_property: str | None = None
    ) -> list[dict[str, Any]]:
        """Runs a community detection algorithm (requires MAGE).
        Returns list of nodes with their community IDs.
        Optionally writes community ID back to nodes.
        """
        # Check if MAGE algorithms are available
        check_query = "CALL mg.procedures() YIELD name WHERE name CONTAINS 'community' RETURN count(*) as count"
        try:
            result = await self.execute_query(check_query)
            if not result or result[0].get("count", 0) == 0:
                logger.warning(
                    "MAGE community detection algorithms not available. Install MAGE for this feature."
                )
                return []
        except Exception as e:
            logger.error(f"Error checking for MAGE algorithms: {e}")
            return []

        # Select appropriate algorithm query
        if algorithm.lower() == "louvain":
            algo_query = """
            CALL community.louvain() 
            YIELD node, community
            """
        elif algorithm.lower() == "label_propagation":
            algo_query = """
            CALL community.label_propagation() 
            YIELD node, community
            """
        else:
            logger.error(f"Unsupported community detection algorithm: {algorithm}")
            return []

        # Add write clause if requested
        if write_property:
            algo_query += f"\nSET node.{write_property} = community"

        algo_query += "\nRETURN node.id as id, labels(node) as labels, community"

        try:
            results = await self.execute_query(algo_query)
            community_data = []

            for record in results:
                community_data.append(
                    {
                        "id": record.get("id"),
                        "labels": record.get("labels", []),
                        "community": record.get("community"),
                    }
                )

            logger.info(
                f"Detected {len(set(r.get('community') for r in community_data))} communities across {len(community_data)} nodes"
            )
            return community_data

        except Exception as e:
            logger.error(f"Failed to detect communities using {algorithm}: {e}")
            return []

    async def query_subgraph(
        self,
        start_node_id: str,
        max_depth: int = 1,
        relationship_types: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Queries a subgraph starting from a node."""
        # Build relationship type filter if specified
        rel_filter = ""
        if relationship_types and len(relationship_types) > 0:
            safe_types = [escape_cypher_string(rt) for rt in relationship_types]
            rel_types = "|".join([f"`{t}`" for t in safe_types])
            rel_filter = f":{rel_types}"

        # Query to extract the subgraph
        query = f"""
        MATCH path = (start {{id: $start_id}})-[{rel_filter}*1..{max_depth}]-(n)
        WITH COLLECT(DISTINCT start) + COLLECT(DISTINCT n) AS nodes,
             COLLECT(DISTINCT relationships(path)) AS path_rels
        UNWIND nodes AS node
        WITH COLLECT(DISTINCT {{
            id: node.id,
            labels: labels(node),
            properties: properties(node)
        }}) AS unique_nodes, path_rels
        UNWIND path_rels AS rels
        UNWIND rels AS rel
        WITH unique_nodes, COLLECT(DISTINCT {{
            id: id(rel),
            source: startNode(rel).id,
            target: endNode(rel).id,
            type: type(rel),
            properties: properties(rel)
        }}) AS unique_rels
        RETURN unique_nodes AS nodes, unique_rels AS relationships
        """

        params = {"start_id": start_node_id}

        try:
            results = await self.execute_query(query, params)
            if not results or len(results) == 0:
                return [], []

            nodes = results[0].get("nodes", [])
            relationships = results[0].get("relationships", [])

            logger.info(
                f"Query subgraph starting from {start_node_id} (depth={max_depth}): {len(nodes)} nodes, {len(relationships)} relationships"
            )
            return nodes, relationships

        except Exception as e:
            logger.error(f"Failed to query subgraph for node {start_node_id}: {e}")
            return [], []

    async def execute_read(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[Any]:
        """Executes a read-only Cypher query."""
        # For this implementation, we use the same execute_query method
        return await self.execute_query(query, parameters)

    async def execute_write(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> Any:
        """Executes a write query. Wraps execute_query for semantic clarity."""
        return await self.execute_query(query, parameters)

    async def get_relationship_by_id(
        self, relationship_id: str
    ) -> Relationship | None:
        """Retrieves a relationship by its assigned ID property."""
        logger.debug(f"Getting relationship by ID: {relationship_id}")
        query = """
        MATCH (source)-[r]->(target)
        WHERE r.id = $rel_id
        RETURN
            r.id AS id, 
            source.id AS source_id, 
            target.id AS target_id, 
            type(r) AS type,
            properties(r) AS properties
        LIMIT 1
        """
        params = {"rel_id": relationship_id}

        try:
            results = await self.execute_query(query, params)
            if not results:
                logger.warning(f"Relationship with ID {relationship_id} not found.")
                return None

            rel_data = results[0]

            # Process properties, converting datetime strings if necessary
            properties = rel_data.get("properties", {})
            # Assuming properties stored might include datetime strings like in add_relationship
            parsed_properties = {}
            for key, value in properties.items():
                # Attempt to parse if string, handle potential errors
                if isinstance(value, str):
                    try:
                        # Use fromisoformat for ISO format datetime strings
                        parsed_properties[key] = datetime.fromisoformat(
                            value.replace("Z", "+00:00")
                        )
                    except ValueError:
                        # Keep original string if not a valid ISO datetime
                        parsed_properties[key] = value
                else:
                    parsed_properties[key] = value

            # Remove the 'id' property from the properties dict as it's part of the main object
            parsed_properties.pop("id", None)

            return Relationship(
                id=rel_data["id"],
                source_id=rel_data["source_id"],
                target_id=rel_data["target_id"],
                type=rel_data["type"],
                properties=parsed_properties,
            )

        except Exception as e:
            logger.error(
                f"Error getting relationship {relationship_id}: {e}", exc_info=True
            )
            return None

    async def link_chunk_to_entities(
        self, chunk_id: str, entity_ids: list[str]
    ) -> None:
        """Creates CONTAINS relationships from a chunk node to multiple entity nodes."""
        if not entity_ids:
            logger.debug(
                f"No entity IDs provided to link to chunk {chunk_id}. Skipping."
            )
            return

        # Use UNWIND for batch creation of relationships
        # Match chunk by its ID, Match entities by their IDs
        # Create MENTIONS relationship if it doesn't already exist (MERGE)
        query = """
        MATCH (c:Chunk {id: $chunk_id})
        UNWIND $entity_ids as entityId
        MATCH (e {id: entityId}) // Match entity nodes by ID regardless of label
        MERGE (c)-[r:MENTIONS]->(e)
        RETURN count(r) as created_count
        """
        params = {"chunk_id": chunk_id, "entity_ids": entity_ids}

        try:
            results = await self.execute_query(query, params)
            created_count = results[0]["created_count"] if results else 0
            logger.info(
                f"Created/merged {created_count} MENTIONS relationships for chunk {chunk_id}."
            )
        except Exception as e:
            logger.error(
                f"Failed to link chunk {chunk_id} to entities {entity_ids}: {e}",
                exc_info=True,
            )
            # Consider how to handle partial failures if needed
            raise


def escape_cypher_string(value: str) -> str:
    """Escapes characters in a string for safe use in Cypher labels/types."""
    if not value:
        raise ValueError("Cypher label/type cannot be empty.")
    # Basic escaping, might need refinement based on Memgraph label rules
    return value.replace("`", "``").replace('"', '\\"').replace("'", "\\'")
