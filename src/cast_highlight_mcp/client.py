"""CAST Highlight API client."""

import asyncio
import logging
from typing import Any

import httpx

from .config import Config

logger = logging.getLogger(__name__)


class HighlightClient:
    """Client for CAST Highlight REST API."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "HighlightClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        """Exit async context manager, ensuring client is closed."""
        await self.close()

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=self.config.timeout,
                    headers=self.headers,
                )
            return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        async with self._lock:
            if self._client:
                await self._client.aclose()
                self._client = None

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    async def get(self, path: str, **kwargs) -> Any:
        return await self._request("GET", path, **kwargs)

    # Company endpoints
    async def get_company(self, company_id: int | None = None) -> dict:
        """Get company details."""
        cid = company_id or self.config.company_id
        return await self.get(f"/companies/{cid}")

    # Domain endpoints
    async def list_domains(
        self, company_id: int | None = None, delay: float = 0
    ) -> list[dict]:
        """List all domains for a company by scanning accessible domain IDs.

        Args:
            company_id: Optional company ID (uses config default if not provided)
            delay: Delay in seconds between requests for rate limiting (default: 0).
                   Must be non-negative.

        Returns:
            List of domain dictionaries found during scanning. May be fewer than
            the expected domain count if authentication or network errors occur.

        Raises:
            ValueError: If delay is negative.

        Note:
            This method scans a range of domain IDs around the company ID since
            the API does not provide a direct list endpoint. Authentication errors
            (401/403) are logged as warnings; network errors are logged at debug level.
        """
        if delay < 0:
            raise ValueError("delay must be non-negative")

        cid = company_id or self.config.company_id
        # Get company info to know domain count
        company = await self.get(f"/companies/{cid}")
        domain_count = company.get("domains", 0)

        # Scan for domains near company ID (API doesn't have list endpoint)
        found_domains: list[dict] = []
        client = await self._get_client()

        # Scan range around company ID
        is_first_request = True
        for offset in range(-10, 50):
            if len(found_domains) >= domain_count:
                break

            # Rate limiting between requests (not before first request)
            if delay > 0 and not is_first_request:
                await asyncio.sleep(delay)
            is_first_request = False

            domain_id = cid + offset
            try:
                url = f"{self.base_url}/domains/{domain_id}"
                response = await client.get(url)
                if response.status_code == 200:
                    found_domains.append(response.json())
                elif response.status_code in (401, 403):
                    logger.warning(
                        "Authentication error scanning domain %d: %d",
                        domain_id,
                        response.status_code,
                    )
                # 404 is expected during scanning, don't log
            except httpx.TimeoutException as e:
                logger.debug("Timeout scanning domain %d: %s", domain_id, e)
            except httpx.ConnectError as e:
                logger.debug("Connection error scanning domain %d: %s", domain_id, e)
            except httpx.RequestError as e:
                logger.debug("Request error scanning domain %d: %s", domain_id, e)
            except Exception as e:
                logger.debug("Unexpected error scanning domain %d: %s", domain_id, e)

        return found_domains

    async def get_domain(self, domain_id: int) -> dict:
        """Get domain details."""
        return await self.get(f"/domains/{domain_id}")

    async def get_domain_applications(self, domain_id: int) -> list[dict]:
        """Get all applications in a domain."""
        return await self.get(f"/domains/{domain_id}/applications")

    # Application endpoints
    async def get_application(self, app_id: int) -> dict:
        """Get application details."""
        return await self.get(f"/applications/{app_id}")

    async def get_application_metrics(self, app_id: int) -> dict:
        """Get application health metrics."""
        return await self.get(f"/applications/{app_id}/metrics")

    async def get_application_technologies(self, app_id: int) -> list[dict]:
        """Get application technology breakdown."""
        return await self.get(f"/applications/{app_id}/technologies")

    async def get_application_cloud_readiness(self, app_id: int) -> dict:
        """Get application cloud readiness assessment."""
        return await self.get(f"/applications/{app_id}/cloudReady")

    async def get_application_green_impact(self, app_id: int) -> dict:
        """Get application green/environmental impact."""
        return await self.get(f"/applications/{app_id}/green")

    async def get_application_cves(self, app_id: int) -> list[dict]:
        """Get CVEs affecting the application."""
        return await self.get(f"/applications/{app_id}/cve")

    async def get_application_third_parties(self, app_id: int) -> list[dict]:
        """Get third-party components used by the application."""
        return await self.get(f"/applications/{app_id}/thirdParties")

    # Benchmark endpoints
    async def get_benchmark(self) -> dict:
        """Get benchmark statistics across all Highlight applications."""
        return await self.get("/benchmark")
