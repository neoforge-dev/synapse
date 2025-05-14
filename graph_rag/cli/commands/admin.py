import json
import logging
import sys

import httpx
import typer

# TODO: Make API base URL configurable
API_BASE_URL = "http://localhost:8000"
HEALTH_URL = f"{API_BASE_URL}/health"

logger = logging.getLogger(__name__)


def check_health(
    api_url: str = typer.Option(
        HEALTH_URL, help="URL of the health check API endpoint."
    ),
):
    """Check the health status of the Synapse API."""
    logger.info(f"Checking API health at {api_url}...")

    try:
        with httpx.Client() as client:
            response = client.get(api_url, timeout=10.0)
            response.raise_for_status()  # Raises for 4xx/5xx

            response_data = response.json()
            logger.info(
                f"API Health Response ({response.status_code}): {response_data}"
            )
            status = response_data.get("status", "unknown")
            print(f"API Status: {status.upper()}")
            if response.status_code != 200 or status != "healthy":
                print("Warning: API reported an unhealthy status.", file=sys.stderr)
                raise SystemExit(1)
            print("API appears healthy.")

    except httpx.RequestError as exc:
        logger.error(
            f"API request failed: {exc.request.method} {exc.request.url} - {exc}"
        )
        print(
            f"Error: Failed to connect to the API at {api_url}. Is it running?",
            file=sys.stderr,
        )
        raise SystemExit(1)
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"API returned an error: {exc.response.status_code} - {exc.response.text}"
        )
        detail = exc.response.text
        try:
            detail_json = exc.response.json()
            detail = detail_json.get("detail", detail)
        except json.JSONDecodeError:
            pass
        print(
            f"Error: API health check failed with status {exc.response.status_code}. Detail: {detail}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during health check: {e}", exc_info=True
        )
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        raise SystemExit(1)


# Add other admin commands later (e.g., config show, db status)
