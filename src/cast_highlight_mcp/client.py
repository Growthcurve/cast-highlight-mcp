"""CAST Highlight API client."""

from typing import Any

import httpx

from .config import Config


class HighlightClient:
    """Client for CAST Highlight REST API."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers=self.headers,
            )
        return self._client

    async def close(self):
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
    async def list_domains(self, company_id: int | None = None) -> list[dict]:
        """List all domains for a company by scanning accessible domain IDs."""
        cid = company_id or self.config.company_id
        # Get company info to know domain count
        company = await self.get(f"/companies/{cid}")
        domain_count = company.get("domains", 0)

        # Scan for domains near company ID (API doesn't have list endpoint)
        found_domains = []
        client = await self._get_client()

        # Scan range around company ID
        for offset in range(-10, 50):
            if len(found_domains) >= domain_count:
                break
            domain_id = cid + offset
            try:
                url = f"{self.base_url}/domains/{domain_id}"
                response = await client.get(url)
                if response.status_code == 200:
                    found_domains.append(response.json())
            except Exception:
                pass

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
