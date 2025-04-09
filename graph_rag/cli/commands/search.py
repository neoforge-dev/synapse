import typer
import logging
import json
import sys
from typing import Optional

import httpx

# TODO: Make API base URL configurable
API_BASE_URL = "http://localhost:8000/api/v1"
SEARCH_URL = f"{API_BASE_URL}/search/query"

logger = logging.getLogger(__name__)

app = typer.Typer(help="Commands for searching the graph.")

@app.command("query")
def search_query(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="The search query string."),
    search_type: str = typer.Option("vector", "--type", "-t", help="Search type ('vector' or 'keyword')."),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of results to return."),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream results as JSON Lines."),
    api_url: str = typer.Option(SEARCH_URL, help="URL of the search API endpoint.")
):
    """Query the GraphRAG system for relevant context chunks."""
    
    if search_type not in ["vector", "keyword"]:
        logger.error(f"Invalid search type: {search_type}. Must be 'vector' or 'keyword'.")
        raise typer.Exit(code=1)
        
    logger.info(f"Executing search: query='{query}', type='{search_type}', limit={limit}, stream={stream}")
    
    # Prepare request payload
    payload = {
        "query": query,
        "search_type": search_type,
        "limit": limit
    }
    
    # Construct URL with stream parameter
    request_url = f"{api_url}?stream={'true' if stream else 'false'}"
    
    try:
        if stream:
            # Handle streaming response
            logger.info(f"Requesting streaming search from {request_url}...")
            with httpx.stream("POST", request_url, json=payload, timeout=None) as response: # No timeout for stream
                response.raise_for_status()
                if response.headers.get("content-type") != "application/x-ndjson":
                    logger.warning(f"Expected ndjson stream, but got content type: {response.headers.get('content-type')}")
                
                print("--- Streaming Results (JSON Lines) ---", file=sys.stderr)
                for line in response.iter_lines():
                    print(line) # Print each JSON line as it arrives
                print("--- End of Stream ---", file=sys.stderr)

        else:
            # Handle batch response
            logger.info(f"Requesting batch search from {request_url}...")
            with httpx.Client() as client:
                response = client.post(request_url, json=payload, timeout=60.0) # Longer timeout for potentially large batch
                response.raise_for_status()
                response_data = response.json()
                
                logger.info(f"API Response ({response.status_code}) - {len(response_data.get('results', []))} results.")
                # Pretty print the JSON response
                print(json.dumps(response_data, indent=2))

    except httpx.RequestError as exc:
        logger.error(f"API request failed: {exc.request.method} {exc.request.url} - {exc}")
        print(f"Error: Failed to connect to the API at {api_url}. Is it running?", file=sys.stderr)
        raise typer.Exit(code=1)
    except httpx.HTTPStatusError as exc:
        logger.error(f"API returned an error: {exc.response.status_code} - {exc.response.text}")
        # Try to parse JSON error detail if possible
        detail = exc.response.text
        try: 
            detail_json = exc.response.json()
            detail = detail_json.get("detail", detail)
        except json.JSONDecodeError:
            pass # Keep original text if not JSON
        print(f"Error: API returned status {exc.response.status_code}. Detail: {detail}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

# Add other search commands later if needed 