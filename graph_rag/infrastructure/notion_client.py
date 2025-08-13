import logging
from typing import Any, AsyncGenerator, Optional

import httpx

from graph_rag.config import Settings

logger = logging.getLogger(__name__)


class NotionClient:
    """Minimal Notion API client for incremental sync.

    Uses search and database query endpoints to list pages and fetch content.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        api_key = self.settings.notion_api_key.get_secret_value() if self.settings.notion_api_key else None
        if not api_key:
            raise RuntimeError("Notion API key not configured")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": self.settings.notion_version,
            "Content-Type": "application/json",
        }
        self._base = self.settings.notion_base_url.rstrip("/")

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self._base, headers=self._headers, timeout=30.0)

    def _request(self, method: str, url: str, *, json: dict | None = None) -> dict[str, Any]:
        retries = int(getattr(self.settings, "notion_max_retries", 5) or 5)
        backoff = 0.5
        for attempt in range(retries):
            with self._client() as client:
                try:
                    resp = client.request(method, url, json=json)
                    if resp.status_code == 429:
                        raise httpx.HTTPStatusError("rate limited", request=resp.request, response=resp)
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as e:
                    if e.response is not None and e.response.status_code == 429 and attempt < retries - 1:
                        import time as _time, random as _rand
                        # Respect client-side QPS and server backoff header if present
                        retry_after = e.response.headers.get("Retry-After") if e.response is not None else None
                        try:
                            delay_hdr = float(retry_after) if retry_after else None
                        except Exception:
                            delay_hdr = None
                        base = delay_hdr or min(backoff, float(self.settings.notion_backoff_ceiling))
                        # Add jitter (±20%) to prevent thundering herd
                        jitter = base * (_rand.uniform(0.8, 1.2))
                        delay = min(jitter, float(self.settings.notion_backoff_ceiling))
                        _time.sleep(delay)
                        # Exponential backoff with ceiling
                        backoff = min(backoff * 2.0, float(self.settings.notion_backoff_ceiling))
                        continue
                    raise
                finally:
                    # Simple client-side throttle based on max QPS
                    try:
                        import time as _time

                        _time.sleep(max(0.0, 1.0 / float(self.settings.notion_max_qps)))
                    except Exception:
                        pass

    def list_pages(self, query: Optional[str] = None, start_cursor: Optional[str] = None, page_size: int = 50) -> dict[str, Any]:
        payload: dict[str, Any] = {"page_size": page_size}
        if query:
            payload["query"] = query
        if start_cursor:
            payload["start_cursor"] = start_cursor
        return self._request("POST", "/search", json=payload)

    def query_database(
        self, database_id: str, start_cursor: Optional[str] = None, page_size: int = 50
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"page_size": page_size}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        return self._request("POST", f"/databases/{database_id}/query", json=payload)

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self._request("GET", f"/pages/{page_id}")

    def get_blocks(self, block_id: str) -> dict[str, Any]:
        return self._request("GET", f"/blocks/{block_id}/children?page_size=100")
