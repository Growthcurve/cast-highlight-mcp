"""Request context management using contextvars for async-safe correlation.

This module provides:
- RequestContext dataclass for storing per-request information
- request_context() context manager for setting/clearing context
- get_request_id() for safe request ID retrieval with fallback
- get_current_context() for accessing the full context

The implementation uses Python's contextvars module which is designed for
asyncio and provides automatic isolation between concurrent coroutines.
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Generator


@dataclass
class RequestContext:
    """Holds structured context for correlated log entries and metrics.

    Attributes:
        request_id: Unique identifier for request correlation
        tool_name: Name of the MCP tool being invoked
        start_time: High-resolution timestamp from time.perf_counter()
    """

    request_id: str
    tool_name: str
    start_time: float

    def elapsed_ms(self) -> float:
        """Calculate elapsed time since context creation in milliseconds.

        Returns:
            Elapsed time in milliseconds with sub-millisecond precision.
        """
        return (time.perf_counter() - self.start_time) * 1000


# Module-level context variable for thread/async-safe context storage
_context_var: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


@contextmanager
def request_context(
    tool_name: str,
    request_id: str | None = None,
) -> Generator[RequestContext, None, None]:
    """Context manager for correlated logging within a request.

    Creates a RequestContext and sets it in the context variable. The context
    is automatically cleared when the context manager exits, restoring any
    previous context that was set.

    Args:
        tool_name: Name of the MCP tool being invoked
        request_id: Optional custom request ID. If None, generates a short UUID.

    Yields:
        RequestContext instance for the duration of the context.

    Example:
        with request_context(tool_name="highlight_get_company") as ctx:
            logger.info("Tool call started", extra={"context": {"request_id": ctx.request_id}})
            # ... do work ...
            duration = ctx.elapsed_ms()
    """
    # Generate request ID if not provided (8-char short UUID for readability)
    if request_id is None:
        request_id = uuid.uuid4().hex[:8]

    # Create context object
    ctx = RequestContext(
        request_id=request_id,
        tool_name=tool_name,
        start_time=time.perf_counter(),
    )

    # Store in context variable, saving token for restoration
    token = _context_var.set(ctx)

    try:
        yield ctx
    finally:
        # Restore previous context (or None)
        _context_var.reset(token)


def get_current_context() -> RequestContext | None:
    """Get the current request context from any code location.

    Returns:
        Current RequestContext if inside a request_context(), None otherwise.
    """
    return _context_var.get()


def get_request_id() -> str:
    """Get the current request ID, with fallback for when no context is set.

    This function is safe to call from any code location. If called outside
    of a request_context(), it returns an ephemeral ID that can still be
    used for logging.

    Returns:
        The current request ID if inside a context, or an ephemeral ID
        prefixed with "ephemeral-" if no context is set.
    """
    ctx = _context_var.get()
    if ctx is not None:
        return ctx.request_id
    # Generate ephemeral ID for logging outside of request context
    return f"ephemeral-{uuid.uuid4().hex[:8]}"
