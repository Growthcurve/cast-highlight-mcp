"""CAST Highlight API client."""

import asyncio
import logging
import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .config import Config
from .observability import get_current_context, get_logger, get_metrics_collector

logger = get_logger(__name__)


def _is_retryable_exception(exc: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Retryable conditions:
    - Connection errors (network issues)
    - Timeout errors
    - 5xx server errors (except 501 Not Implemented)
    - 429 Too Many Requests (rate limiting)

    Non-retryable conditions:
    - 4xx client errors (except 429)
    - 501 Not Implemented (server doesn't support the request)
    """
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status_code: int = exc.response.status_code
        # Retry on 429 (rate limit) and 5xx (except 501)
        if status_code == 429:
            return True
        if 500 <= status_code < 600 and status_code != 501:
            return True

    return False


class HighlightClient:
    """Client for CAST Highlight REST API."""

    def __init__(self, config: Config):
        # Validate retry configuration to ensure sane values
        if config.retry_attempts < 1:
            raise ValueError("retry_attempts must be at least 1")
        if config.retry_min_wait < 0:
            raise ValueError("retry_min_wait must be non-negative")
        if config.retry_max_wait < config.retry_min_wait:
            raise ValueError("retry_max_wait must be >= retry_min_wait")
        if config.retry_multiplier <= 0:
            raise ValueError("retry_multiplier must be positive")

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
                    verify=True,  # Explicitly require TLS certificate verification
                )
            return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        async with self._lock:
            if self._client:
                await self._client.aclose()
                self._client = None

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make an HTTP request to the CAST Highlight API with retry logic.

        Includes structured logging, metrics collection, and automatic retries
        with exponential backoff for transient failures.

        Retry behavior:
        - Retries on: connection errors, timeouts, 429 (rate limit), 5xx errors
        - Does NOT retry on: 4xx client errors (except 429), 501 Not Implemented
        - Uses exponential backoff between retries

        Observability operations use graceful degradation - they will not cause
        request failures if they encounter errors.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/companies/123")
            **kwargs: Additional arguments passed to httpx.request

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: For non-retryable 4xx/5xx responses or after
                all retries exhausted
            httpx.RequestError: For connection/timeout errors after all retries
                exhausted
        """
        # Get current context for request correlation (with graceful degradation)
        try:
            ctx = get_current_context()
            request_id = ctx.request_id if ctx else "no-context"
        except Exception:
            request_id = "no-context"

        # Log request start (DEBUG level) - graceful degradation
        try:
            logger.debug(
                "HTTP request started",
                extra={
                    "context": {
                        "method": method,
                        "path": path,
                        "request_id": request_id,
                    }
                },
            )
        except Exception:
            pass  # Logging should never break the request

        overall_start_time = time.perf_counter()
        attempt_number = 0

        async def _make_request() -> Any:
            """Inner function that makes the actual request."""
            nonlocal attempt_number
            attempt_number += 1
            attempt_start_time = time.perf_counter()

            client = await self._get_client()
            url = f"{self.base_url}{path}"
            response = await client.request(method, url, **kwargs)

            # Calculate per-attempt duration (not cumulative across retries)
            duration_ms = (time.perf_counter() - attempt_start_time) * 1000
            status_code = response.status_code

            # Determine log level based on status code
            if 200 <= status_code < 300:
                log_level = logging.DEBUG
            elif 400 <= status_code < 500:
                log_level = logging.WARNING
            else:  # 5xx
                log_level = logging.ERROR

            # Log completion - graceful degradation
            try:
                extra_context: dict[str, Any] = {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "request_id": request_id,
                }
                if attempt_number > 1:
                    extra_context["attempt"] = attempt_number
                logger.log(
                    log_level,
                    "HTTP request completed",
                    extra={"context": extra_context},
                )
            except Exception:
                pass

            # Record HTTP metrics - graceful degradation
            try:
                metrics = get_metrics_collector()
                metrics.record_http_request(method, status_code, duration_ms)
            except Exception:
                pass

            response.raise_for_status()
            return response.json()

        # Configure retry behavior
        retry_config = AsyncRetrying(
            stop=stop_after_attempt(self.config.retry_attempts),
            wait=wait_exponential(
                multiplier=self.config.retry_multiplier,
                min=self.config.retry_min_wait,
                max=self.config.retry_max_wait,
            ),
            retry=retry_if_exception(_is_retryable_exception),
            reraise=True,
        )

        try:
            async for attempt in retry_config:
                with attempt:
                    return await _make_request()
        except httpx.TimeoutException:
            total_duration_ms = (time.perf_counter() - overall_start_time) * 1000
            try:
                # Use accurate message based on whether retries occurred
                msg = (
                    "HTTP request timeout after retries"
                    if attempt_number > 1
                    else "HTTP request timeout"
                )
                logger.warning(
                    msg,
                    extra={
                        "context": {
                            "method": method,
                            "path": path,
                            "total_duration_ms": round(total_duration_ms, 2),
                            "error_type": "timeout",
                            "request_id": request_id,
                            "attempts": attempt_number,
                        }
                    },
                )
            except Exception:
                pass
            raise

        except httpx.HTTPStatusError as e:
            total_duration_ms = (time.perf_counter() - overall_start_time) * 1000
            # Log if this was a retryable error that exhausted retries
            if _is_retryable_exception(e) and attempt_number > 1:
                try:
                    logger.error(
                        "HTTP request failed after retries",
                        extra={
                            "context": {
                                "method": method,
                                "path": path,
                                "status_code": e.response.status_code,
                                "total_duration_ms": round(total_duration_ms, 2),
                                "request_id": request_id,
                                "attempts": attempt_number,
                            }
                        },
                    )
                except Exception:
                    pass
            raise

        except httpx.RequestError as e:
            total_duration_ms = (time.perf_counter() - overall_start_time) * 1000
            try:
                # Use accurate message based on whether retries occurred
                msg = (
                    "HTTP request failed after retries"
                    if attempt_number > 1
                    else "HTTP request failed"
                )
                logger.error(
                    msg,
                    extra={
                        "context": {
                            "method": method,
                            "path": path,
                            "total_duration_ms": round(total_duration_ms, 2),
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "request_id": request_id,
                            "attempts": attempt_number,
                        }
                    },
                )
            except Exception:
                pass
            raise

        # This should not be reachable, but satisfies type checker
        raise RuntimeError("Unexpected retry loop exit")

    async def get(self, path: str, **kwargs) -> Any:
        return await self._request("GET", path, **kwargs)

    # Company endpoints
    async def get_company(self, company_id: int | None = None) -> dict:
        """Get company details."""
        cid = company_id or self.config.company_id
        return await self.get(f"/companies/{cid}")

    # Domain endpoints
    async def list_domains(
        self,
        company_id: int | None = None,
        delay: float = 0,
        max_consecutive_misses: int = 5,
        max_iterations: int | None = None,
    ) -> list[dict]:
        """List all domains for a company by scanning accessible domain IDs.

        Args:
            company_id: Optional company ID (uses config default if not provided)
            delay: Delay in seconds between requests for rate limiting (default: 0).
                   Must be non-negative.
            max_consecutive_misses: Stop scanning after this many consecutive
                   non-200 responses (default: 5). Helps avoid unnecessary requests
                   when domain IDs are not contiguous.
            max_iterations: Maximum number of domain IDs to scan (default: None,
                   which uses max(domain_count * 3, 20) as a safety limit).

        Returns:
            List of domain dictionaries found during scanning. May be fewer than
            the expected domain count if authentication or network errors occur.

        Raises:
            ValueError: If delay is negative, max_consecutive_misses < 1, or
                max_iterations < 1 (when provided).

        Note:
            This method scans domain IDs starting from the company ID since
            the API does not provide a direct list endpoint. Domain IDs are
            typically assigned sequentially starting at the company ID.
            All scanning errors (auth, network) are logged at debug level.
        """
        if delay < 0:
            raise ValueError("delay must be non-negative")
        if max_consecutive_misses < 1:
            raise ValueError("max_consecutive_misses must be at least 1")
        if max_iterations is not None and max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        cid = company_id or self.config.company_id
        # Get company info to know domain count
        company = await self.get(f"/companies/{cid}")
        # Handle None from API (e.g., "domains": null) by coercing to 0
        domain_count = company.get("domains") or 0

        # Calculate iteration limit to prevent unbounded scanning
        iteration_limit = (
            max_iterations if max_iterations is not None else max(domain_count * 3, 20)
        )

        # Scan for domains starting at company ID (API doesn't have list endpoint)
        # Domain IDs are typically sequential starting from company ID
        found_domains: list[dict] = []
        client = await self._get_client()

        # Get request context once for correlation (doesn't change during scan)
        ctx = get_current_context()
        request_id = ctx.request_id if ctx else "no-context"

        # Scan forward from company ID
        is_first_request = True
        consecutive_misses = 0
        offset = 0
        while (
            len(found_domains) < domain_count
            and consecutive_misses < max_consecutive_misses
            and offset < iteration_limit
        ):
            # Rate limiting between requests (not before first request)
            if delay > 0 and not is_first_request:
                await asyncio.sleep(delay)
            is_first_request = False

            domain_id = cid + offset
            offset += 1

            try:
                url = f"{self.base_url}/domains/{domain_id}"
                response = await client.get(url)
                if response.status_code == 200:
                    found_domains.append(response.json())
                    consecutive_misses = 0  # Reset on success
                elif response.status_code in (401, 403):
                    consecutive_misses += 1
                    logger.debug(
                        "Authentication error scanning domain",
                        extra={
                            "context": {
                                "domain_id": domain_id,
                                "status_code": response.status_code,
                                "request_id": request_id,
                            }
                        },
                    )
                else:
                    # 404 or other status - count as miss
                    consecutive_misses += 1
            except httpx.TimeoutException as e:
                consecutive_misses += 1
                logger.debug(
                    "Timeout scanning domain",
                    extra={
                        "context": {
                            "domain_id": domain_id,
                            "error_type": "timeout",
                            "error_message": str(e),
                            "request_id": request_id,
                        }
                    },
                )
            except httpx.ConnectError as e:
                consecutive_misses += 1
                logger.debug(
                    "Connection error scanning domain",
                    extra={
                        "context": {
                            "domain_id": domain_id,
                            "error_type": "ConnectError",
                            "error_message": str(e),
                            "request_id": request_id,
                        }
                    },
                )
            except httpx.RequestError as e:
                consecutive_misses += 1
                logger.debug(
                    "Request error scanning domain",
                    extra={
                        "context": {
                            "domain_id": domain_id,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "request_id": request_id,
                        }
                    },
                )
            except Exception as e:
                consecutive_misses += 1
                logger.debug(
                    "Unexpected error scanning domain",
                    extra={
                        "context": {
                            "domain_id": domain_id,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "request_id": request_id,
                        }
                    },
                )

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
