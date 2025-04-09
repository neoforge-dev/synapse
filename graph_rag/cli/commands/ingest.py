import typer
import logging
import json
import sys # Import sys for stderr
from pathlib import Path
from typing import Optional, Dict, Any

import httpx # For making requests to the FastAPI backend

# Import settings
from graph_rag.config import settings

# --- Configuration --- 
# Construct default API URL from settings
DEFAULT_API_BASE_URL = f"http://{settings.api_host}:{settings.api_port}/api/v1"
DEFAULT_INGEST_URL = f"{DEFAULT_API_BASE_URL}/ingestion/documents"

# Configure logging for CLI
# You might want a more sophisticated setup using a config file or library
logging.basicConfig(level=settings.api_log_level.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Typer App --- 
app = typer.Typer(help="Commands for interacting with the GraphRAG API.")

# --- Helper Function for API Requests --- 
def make_api_request(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Makes a POST request to the specified API endpoint and handles common errors."""
    logger.info(f"Sending request to {url}...")
    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload, timeout=30.0) # Adjust timeout as needed
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            
            response_data = response.json()
            logger.info(f"API Response ({response.status_code}): {response_data}")
            return response_data
            
    except httpx.RequestError as exc:
        error_msg = f"Error: Failed to connect to the API at {url}. Is it running? Details: {exc}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)
    except httpx.HTTPStatusError as exc:
        error_msg = f"Error: API returned status {exc.response.status_code}. Response: {exc.response.text}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)
    except json.JSONDecodeError as e:
        error_msg = f"Error: Could not decode JSON response from API. Details: {e}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e:
        error_msg = f"An unexpected error occurred during API request: {e}"
        logger.error(error_msg, exc_info=True)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)

# --- Ingestion Command --- 
@app.command("ingest")
def ingest_document(
    ctx: typer.Context,
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Direct text content to ingest."),
    file_path: Optional[Path] = typer.Option(
        None, 
        "--file", "-f", 
        help="Path to a text file to ingest.", 
        exists=True, 
        file_okay=True, 
        dir_okay=False, 
        readable=True,
        resolve_path=True # Ensure path is absolute if needed
    ),
    metadata_json: str = typer.Option(
        '{"source": "cli"}', 
        "--metadata", "-m", 
        help="Metadata as a JSON string (e.g., '{"key": "value"}')."
    ),
    document_id: Optional[str] = typer.Option(
        None, 
        "--doc-id", 
        help="Optional specific ID for the document."
    ),
    # Use the URL derived from settings as the default
    api_url: str = typer.Option(
        DEFAULT_INGEST_URL, 
        "--url", 
        help="URL of the ingestion API endpoint."
    )
):
    """Ingest a single document by sending it to the GraphRAG API."""
    
    # --- Input Validation --- 
    if not content and not file_path:
        logger.error("Error: Must provide either --content/-c or --file/-f")
        print("Error: Must provide either --content/-c or --file/-f", file=sys.stderr)
        raise typer.Exit(code=1)
    if content and file_path:
        logger.error("Error: Cannot provide both --content/-c and --file/-f")
        print("Error: Cannot provide both --content/-c and --file/-f", file=sys.stderr)
        raise typer.Exit(code=1)

    # --- Get Content --- 
    doc_content: str = ""
    input_source = "direct content"
    if file_path:
        input_source = f"file: {file_path}"
        try:
            doc_content = file_path.read_text(encoding='utf-8') # Specify encoding
            logger.info(f"Read content from file: {file_path}")
        except Exception as e:
            error_msg = f"Error reading file {file_path}: {e}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            raise typer.Exit(code=1)
    elif content:
        doc_content = content

    if not doc_content.strip():
        logger.error("Error: Document content is empty or whitespace only.")
        print(f"Error: Document content from {input_source} is empty.", file=sys.stderr)
        raise typer.Exit(code=1)
        
    # --- Parse Metadata --- 
    metadata: Dict[str, Any] = {}
    try:
        metadata = json.loads(metadata_json)
        if not isinstance(metadata, dict):
             raise ValueError("Metadata must be a JSON object (dict).")
        logger.info(f"Using metadata: {metadata}")
    except json.JSONDecodeError as e:
        error_msg = f"Error: Invalid JSON provided for metadata: {e}. Input was: {metadata_json}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)
    except ValueError as e:
        error_msg = f"Error: Invalid metadata format: {e}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        raise typer.Exit(code=1)
        
    # --- Prepare API Payload --- 
    payload = {
        "content": doc_content,
        "metadata": metadata,
        "document_id": document_id # Will be None if not provided
    }
    # Remove null values if the API expects them to be absent
    payload = {k: v for k, v in payload.items() if v is not None}
    
    # --- Call API --- 
    response_data = make_api_request(api_url, payload)
    
    # --- Output Result --- 
    print(f"Ingestion request accepted by API.")
    print(f"Document ID: {response_data.get('document_id', 'N/A')}")
    if response_data.get('task_id'):
        print(f"Task ID: {response_data['task_id']}")
    # Pretty print the full response if needed
    # print(json.dumps(response_data, indent=2))

# Add other commands (e.g., query, status) later
# query_app = typer.Typer(help="Commands for querying the GraphRAG system.")
# app.add_typer(query_app, name="query")

# @query_app.command("ask")
# def ask_query(...):
#    pass

if __name__ == "__main__":
    app() 