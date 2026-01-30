"""Unit tests for observability context module."""

import asyncio
import time

import pytest

from cast_highlight_mcp.observability.context import (
    RequestContext,
    get_current_context,
    get_request_id,
    request_context,
)


class TestRequestContext:
    """Tests for RequestContext dataclass."""

    def test_request_context_creates_with_required_fields(self):
        """RequestContext should store request_id and tool_name."""
        ctx = RequestContext(
            request_id="test-123",
            tool_name="highlight_get_company",
            start_time=time.perf_counter(),
        )
        assert ctx.request_id == "test-123"
        assert ctx.tool_name == "highlight_get_company"
        assert ctx.start_time > 0

    def test_request_context_elapsed_ms_returns_positive_duration(self):
        """elapsed_ms should return time since start in milliseconds."""
        ctx = RequestContext(
            request_id="test-123",
            tool_name="test_tool",
            start_time=time.perf_counter(),
        )
        # Sleep briefly to ensure measurable elapsed time
        time.sleep(0.01)  # 10ms
        elapsed = ctx.elapsed_ms()
        assert elapsed >= 10.0  # At least 10ms
        assert elapsed < 1000.0  # Less than 1 second

    def test_request_context_elapsed_ms_increases_over_time(self):
        """elapsed_ms should increase with subsequent calls."""
        ctx = RequestContext(
            request_id="test-123",
            tool_name="test_tool",
            start_time=time.perf_counter(),
        )
        elapsed1 = ctx.elapsed_ms()
        time.sleep(0.005)  # 5ms
        elapsed2 = ctx.elapsed_ms()
        assert elapsed2 > elapsed1


class TestRequestContextManager:
    """Tests for request_context context manager."""

    def test_request_context_generates_unique_id(self):
        """Each context should have a unique request_id."""
        ids = []
        for _ in range(10):
            with request_context(tool_name="test_tool") as ctx:
                ids.append(ctx.request_id)
        # All IDs should be unique
        assert len(ids) == len(set(ids))

    def test_request_context_stores_tool_name(self):
        """Context should store the tool_name correctly."""
        with request_context(tool_name="highlight_get_application") as ctx:
            assert ctx.tool_name == "highlight_get_application"

    def test_request_context_accepts_custom_request_id(self):
        """Context should accept a custom request_id."""
        with request_context(tool_name="test_tool", request_id="custom-id-123") as ctx:
            assert ctx.request_id == "custom-id-123"

    def test_request_context_sets_start_time(self):
        """Context should set start_time on entry."""
        before = time.perf_counter()
        with request_context(tool_name="test_tool") as ctx:
            after = time.perf_counter()
            assert before <= ctx.start_time <= after

    def test_request_context_cleanup_on_exit(self):
        """Context should be cleared after context manager exits."""
        with request_context(tool_name="test_tool"):
            assert get_current_context() is not None
        # After exit, context should be None
        assert get_current_context() is None


class TestGetCurrentContext:
    """Tests for get_current_context function."""

    def test_get_current_context_returns_none_without_context(self):
        """Should return None when no context is set."""
        # Ensure no context is set
        assert get_current_context() is None

    def test_get_current_context_returns_context_inside_manager(self):
        """Should return the RequestContext inside context manager."""
        with request_context(tool_name="test_tool") as ctx:
            current = get_current_context()
            assert current is not None
            assert current.request_id == ctx.request_id
            assert current.tool_name == ctx.tool_name


class TestGetRequestId:
    """Tests for get_request_id function."""

    def test_get_request_id_returns_id_inside_context(self):
        """Should return request_id when inside context."""
        with request_context(tool_name="test_tool") as ctx:
            assert get_request_id() == ctx.request_id

    def test_get_request_id_returns_ephemeral_outside_context(self):
        """Should return an ephemeral ID when no context is set."""
        # Ensure we're outside any context
        assert get_current_context() is None
        request_id = get_request_id()
        # Should be a string starting with "ephemeral-"
        assert request_id.startswith("ephemeral-")
        # Should have some random component
        assert len(request_id) > len("ephemeral-")

    def test_get_request_id_ephemeral_ids_are_unique(self):
        """Ephemeral IDs should be unique across calls."""
        ids = [get_request_id() for _ in range(10)]
        assert len(ids) == len(set(ids))


class TestNestedContexts:
    """Tests for nested context behavior."""

    def test_nested_contexts_inner_overrides_outer(self):
        """Inner context should override outer context."""
        with request_context(tool_name="outer_tool") as outer:
            assert get_current_context().tool_name == "outer_tool"
            with request_context(tool_name="inner_tool") as inner:
                assert get_current_context().tool_name == "inner_tool"
                assert get_current_context().request_id == inner.request_id
            # After inner exits, should return to outer
            assert get_current_context().tool_name == "outer_tool"
            assert get_current_context().request_id == outer.request_id

    def test_nested_contexts_restore_correctly(self):
        """Exiting nested context should restore previous context."""
        with request_context(tool_name="level1", request_id="id-1"):
            assert get_request_id() == "id-1"
            with request_context(tool_name="level2", request_id="id-2"):
                assert get_request_id() == "id-2"
                with request_context(tool_name="level3", request_id="id-3"):
                    assert get_request_id() == "id-3"
                assert get_request_id() == "id-2"
            assert get_request_id() == "id-1"
        assert get_current_context() is None


class TestConcurrentContexts:
    """Tests for async concurrent context isolation."""

    @pytest.mark.asyncio
    async def test_concurrent_contexts_are_isolated(self):
        """Each async task should have isolated context."""
        results = {}

        async def worker(worker_id: str):
            with request_context(tool_name=f"tool_{worker_id}") as ctx:
                # Store our context info
                results[worker_id] = {
                    "request_id": ctx.request_id,
                    "tool_name": ctx.tool_name,
                }
                # Yield control to other tasks
                await asyncio.sleep(0.01)
                # Verify our context is still correct
                current = get_current_context()
                assert current.request_id == ctx.request_id
                assert current.tool_name == f"tool_{worker_id}"

        # Run multiple workers concurrently
        await asyncio.gather(
            worker("A"),
            worker("B"),
            worker("C"),
        )

        # Verify each worker had unique request_id
        request_ids = [r["request_id"] for r in results.values()]
        assert len(request_ids) == len(set(request_ids))

    @pytest.mark.asyncio
    async def test_context_does_not_leak_between_tasks(self):
        """Context from one task should not affect another."""
        task_a_saw_b = False
        task_b_saw_a = False

        async def task_a():
            nonlocal task_a_saw_b
            with request_context(tool_name="task_a", request_id="id-a"):
                await asyncio.sleep(0.02)
                ctx = get_current_context()
                if ctx and ctx.request_id == "id-b":
                    task_a_saw_b = True

        async def task_b():
            nonlocal task_b_saw_a
            await asyncio.sleep(0.01)  # Start slightly after task_a
            with request_context(tool_name="task_b", request_id="id-b"):
                await asyncio.sleep(0.01)
                ctx = get_current_context()
                if ctx and ctx.request_id == "id-a":
                    task_b_saw_a = True

        await asyncio.gather(task_a(), task_b())

        # Neither task should see the other's context
        assert not task_a_saw_b
        assert not task_b_saw_a


class TestRequestIdFormat:
    """Tests for request ID format."""

    def test_auto_generated_request_id_is_valid_format(self):
        """Auto-generated request IDs should be short UUIDs."""
        with request_context(tool_name="test_tool") as ctx:
            # Should be alphanumeric
            assert ctx.request_id.replace("-", "").isalnum()
            # Should be reasonably short (8 chars from UUID4)
            # or full UUID if we decide to use that
            assert len(ctx.request_id) >= 8
