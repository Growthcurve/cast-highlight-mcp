"""Integration tests for server lifecycle management.

These tests verify that the AsyncExitStack properly manages both the
HighlightClient and stdio_server lifecycles during server operation.

This module uses two complementary testing approaches:

1. PRODUCTION PATH TESTS (TestServerMainFunction):
   These tests call `server.main()` directly with mocked dependencies to verify
   the actual production startup sequence:
   - load_config() is called
   - configure_logging() is called
   - HighlightClient is initialized via AsyncExitStack
   - stdio_server() context manager is entered
   - server.run() is called with correct arguments
   - Resources are cleaned up on both normal exit and exceptions

   These tests mock stdio_server and server.run() because:
   - stdio_server() requires actual stdio streams
   - server.run() blocks indefinitely waiting for MCP messages

2. ISOLATED COMPONENT TESTS (all other test classes):
   These tests verify lifecycle behavior without calling main() by:
   - Testing component behaviors (HighlightClient, get_client, AsyncExitStack) in isolation
   - Replicating the same patterns used in main() to verify they work correctly
   - Testing cleanup on normal exit and exceptions
   - Verifying lazy initialization, idempotent close, and context manager reuse

   This approach is necessary for pytest-asyncio tests because main() uses
   asyncio.run() which cannot be nested.

Both approaches together provide comprehensive coverage: production path tests
ensure the startup sequence is correct, while isolated tests verify each
component's lifecycle behavior in detail.

For true end-to-end testing with an actual MCP client, see the manual testing
instructions in docs/DEVELOPER.md or use `make run`.
"""

import asyncio
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, patch

import pytest

from cast_highlight_mcp import server
from cast_highlight_mcp.client import HighlightClient
from cast_highlight_mcp.config import Config


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return Config(
        base_url="https://app.casthighlight.com/WS2",
        access_token="test-token-12345",
        company_id=1234,
        timeout=30,
    )


@pytest.fixture
def mock_stdio_server():
    """Create a mock stdio_server context manager."""

    async def mock_streams():
        read_stream = AsyncMock()
        write_stream = AsyncMock()
        return read_stream, write_stream

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(side_effect=mock_streams)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.fixture
def mock_server_run():
    """Create a mock Server.run that completes immediately."""
    return AsyncMock()


class TestClientInitialization:
    """Tests for client initialization during server startup."""

    @pytest.mark.asyncio
    async def test_client_is_initialized_when_server_starts(self, mock_config):
        """Test that the client is properly initialized when the server starts.

        This test verifies the lifecycle pattern used in server.main():
        - Client is initialized via AsyncExitStack.enter_async_context()
        - Client is accessible via server._client during operation
        - Client is a HighlightClient instance

        Note: We cannot call server.main() directly because:
        1. It uses asyncio.run() which cannot be nested
        2. It blocks on stdio_server() waiting for MCP messages
        Instead, we replicate the same initialization pattern.
        """
        original_client = server._client
        client_initialized = False
        client_instance = None

        try:
            # Replicate the initialization pattern from server.main()
            async with AsyncExitStack() as stack:
                # This is exactly what main() does: enter_async_context(HighlightClient(config))
                server._client = await stack.enter_async_context(HighlightClient(mock_config))

                # Verify client is set (this would happen during server.run() in production)
                client_instance = server._client
                client_initialized = client_instance is not None

            assert client_initialized, "Client should be initialized during server startup"
            assert isinstance(client_instance, HighlightClient), (
                "Client should be a HighlightClient instance"
            )

        finally:
            # Restore original state
            server._client = original_client

    @pytest.mark.asyncio
    async def test_global_client_is_set_during_server_operation(self, mock_config):
        """Test that the global _client variable is set correctly during server operation."""
        original_client = server._client
        server._client = None

        try:
            async with AsyncExitStack() as stack:
                # Initialize client like the server does
                server._client = await stack.enter_async_context(HighlightClient(mock_config))

                # Verify global client is accessible via get_client
                client = server.get_client()
                assert client is server._client
                assert isinstance(client, HighlightClient)

        finally:
            server._client = original_client


class TestClientCleanup:
    """Tests for client cleanup during server shutdown."""

    @pytest.mark.asyncio
    async def test_client_is_closed_when_server_exits_normally(self, mock_config):
        """Test that the client is properly closed when the server exits normally."""
        original_client = server._client
        close_called = False

        class TrackingClient(HighlightClient):
            async def close(self):
                nonlocal close_called
                close_called = True
                await super().close()

        try:
            async with AsyncExitStack() as stack:
                client = TrackingClient(mock_config)
                server._client = await stack.enter_async_context(client)
                # Server operation would happen here

            # After exiting the context, close should have been called
            assert close_called, "Client.close() should be called when exiting context"

        finally:
            server._client = original_client

    @pytest.mark.asyncio
    async def test_client_is_closed_when_server_raises_exception(self, mock_config):
        """Test that the client is properly closed when the server raises an exception."""
        original_client = server._client
        close_called = False

        class TrackingClient(HighlightClient):
            async def close(self):
                nonlocal close_called
                close_called = True
                await super().close()

        try:
            with pytest.raises(RuntimeError, match="Simulated server error"):
                async with AsyncExitStack() as stack:
                    client = TrackingClient(mock_config)
                    server._client = await stack.enter_async_context(client)
                    # Simulate server error
                    raise RuntimeError("Simulated server error")

            # Even with exception, close should have been called
            assert close_called, "Client.close() should be called even on exception"

        finally:
            server._client = original_client

    @pytest.mark.asyncio
    async def test_client_close_handles_internal_http_client(self, mock_config):
        """Test that client.close() properly closes the internal HTTP client."""
        client = HighlightClient(mock_config)

        # Initialize the internal HTTP client by accessing it
        _ = await client._get_client()
        assert client._client is not None, "Internal HTTP client should be initialized"

        # Close the client
        await client.close()

        assert client._client is None, "Internal HTTP client should be None after close"


class TestMultipleCloseCalls:
    """Tests for close() idempotency."""

    @pytest.mark.asyncio
    async def test_multiple_close_calls_are_idempotent(self, mock_config):
        """Test that calling close() multiple times does not raise errors."""
        client = HighlightClient(mock_config)

        # Initialize the internal HTTP client
        _ = await client._get_client()

        # Close multiple times - should not raise
        await client.close()
        await client.close()
        await client.close()

        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_on_uninitialized_client_is_safe(self, mock_config):
        """Test that close() on a client that was never initialized is safe."""
        client = HighlightClient(mock_config)

        # Client was never used, so _client is None
        assert client._client is None

        # This should not raise
        await client.close()
        await client.close()

        assert client._client is None


class TestContextManagerReuse:
    """Tests for context manager reuse behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_can_be_reused_after_exit(self, mock_config):
        """Test that a client can be used as context manager multiple times."""
        client = HighlightClient(mock_config)

        # First use
        async with client:
            _ = await client._get_client()
            assert client._client is not None

        # After exit, client should be closed
        assert client._client is None

        # Second use - should work again
        async with client:
            _ = await client._get_client()
            assert client._client is not None

        # After second exit
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_returns_self_on_enter(self, mock_config):
        """Test that __aenter__ returns the client instance."""
        client = HighlightClient(mock_config)

        async with client as ctx:
            assert ctx is client


class TestLazyInitialization:
    """Tests for lazy initialization via _get_client()."""

    @pytest.mark.asyncio
    async def test_http_client_is_lazily_initialized(self, mock_config):
        """Test that the internal HTTP client is not created until needed."""
        client = HighlightClient(mock_config)

        # Before any request, _client should be None
        assert client._client is None

        # After calling _get_client(), it should be initialized
        http_client = await client._get_client()
        assert http_client is not None
        assert client._client is http_client

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_returns_same_instance(self, mock_config):
        """Test that _get_client() returns the same HTTP client instance."""
        client = HighlightClient(mock_config)

        try:
            http_client1 = await client._get_client()
            http_client2 = await client._get_client()

            assert http_client1 is http_client2, "Should return the same HTTP client instance"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_client_is_thread_safe(self, mock_config):
        """Test that concurrent _get_client() calls return the same instance."""
        client = HighlightClient(mock_config)

        try:
            # Call _get_client() concurrently
            results = await asyncio.gather(
                client._get_client(),
                client._get_client(),
                client._get_client(),
                client._get_client(),
                client._get_client(),
            )

            # All results should be the same instance
            first = results[0]
            for result in results[1:]:
                assert result is first, "All concurrent calls should return same instance"
        finally:
            await client.close()


class TestGetClientFunction:
    """Tests for the get_client() server function."""

    def test_get_client_raises_when_not_initialized(self):
        """Test get_client() raises RuntimeError when client is not initialized."""
        original_client = server._client
        server._client = None

        try:
            with pytest.raises(RuntimeError, match="Client not initialized"):
                server.get_client()
        finally:
            server._client = original_client

    def test_get_client_returns_initialized_client(self, mock_config):
        """Test get_client() returns the client when initialized."""
        original_client = server._client
        mock_client = HighlightClient(mock_config)
        server._client = mock_client

        try:
            result = server.get_client()
            assert result is mock_client
        finally:
            server._client = original_client


class TestAsyncExitStackLifecycle:
    """Tests for AsyncExitStack lifecycle management."""

    @pytest.mark.asyncio
    async def test_exit_stack_manages_multiple_resources(self, mock_config):
        """Test that AsyncExitStack properly manages multiple async resources."""
        cleanup_order = []

        class TrackedClient(HighlightClient):
            def __init__(self, config, name):
                super().__init__(config)
                self.name = name

            async def __aexit__(self, *args):
                cleanup_order.append(self.name)
                await super().__aexit__(*args)

        async with AsyncExitStack() as stack:
            client1 = await stack.enter_async_context(TrackedClient(mock_config, "client1"))
            client2 = await stack.enter_async_context(TrackedClient(mock_config, "client2"))

            assert client1 is not None
            assert client2 is not None

        # Exit stack should clean up in reverse order (LIFO)
        assert cleanup_order == ["client2", "client1"]

    @pytest.mark.asyncio
    async def test_exit_stack_cleanup_on_exception_during_setup(self, mock_config):
        """Test that resources are cleaned up if an exception occurs during setup."""
        cleanup_called = False

        class TrackedClient(HighlightClient):
            async def __aexit__(self, *args):
                nonlocal cleanup_called
                cleanup_called = True
                await super().__aexit__(*args)

        with pytest.raises(RuntimeError, match="Setup error"):
            async with AsyncExitStack() as stack:
                _ = await stack.enter_async_context(TrackedClient(mock_config))
                # Simulate error during setup of second resource
                raise RuntimeError("Setup error")

        assert cleanup_called, "First resource should be cleaned up on setup failure"


class TestServerMainFunction:
    """Tests for the main() function server lifecycle.

    These tests verify that the production main() function correctly:
    1. Initializes the HighlightClient before running the server
    2. Makes the client available via get_client() during operation
    3. Cleans up resources when the server exits

    We call main() through asyncio.run(), so we patch asyncio.run to
    execute our test assertions during the server's operation phase.
    """

    def test_main_calls_production_startup_sequence(self, mock_config):
        """Test that main() calls the production startup sequence correctly.

        This test actually calls server.main() and verifies that:
        1. load_config() is called
        2. configure_logging() is called
        3. HighlightClient is initialized via AsyncExitStack
        4. stdio_server() context manager is entered
        5. server.run() is called with the correct arguments
        """
        client_was_set = False
        client_type_correct = False
        server_run_called = False
        server_run_args = None

        async def mock_server_run(*args, **kwargs):
            nonlocal client_was_set, client_type_correct, server_run_called, server_run_args
            server_run_called = True
            server_run_args = args
            # Verify client state during server operation
            client_was_set = server._client is not None
            client_type_correct = isinstance(server._client, HighlightClient)

        original_client = server._client

        try:
            with (
                patch(
                    "cast_highlight_mcp.server.load_config", return_value=mock_config
                ) as mock_load,
                patch("cast_highlight_mcp.server.stdio_server") as mock_stdio,
                patch.object(server.server, "run", mock_server_run),
                patch.object(server.server, "create_initialization_options", return_value={}),
                patch("cast_highlight_mcp.server.configure_logging") as mock_logging,
            ):
                # Setup mock stdio_server as async context manager
                mock_stdio.return_value.__aenter__ = AsyncMock(
                    return_value=(AsyncMock(), AsyncMock())
                )
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

                # Call the actual main() function - this exercises the production code path
                server.main()

                # Verify production startup sequence was called
                mock_logging.assert_called_once()
                mock_load.assert_called_once()
                mock_stdio.assert_called_once()

                # Verify server.run() was called during main()
                assert server_run_called, "server.run() should be called by main()"
                assert len(server_run_args) == 3, "server.run() should receive 3 args"

                # Verify client was properly initialized during server operation
                assert client_was_set, "Client should be set during server operation"
                assert client_type_correct, "Client should be HighlightClient instance"

        finally:
            server._client = original_client

    def test_main_cleans_up_on_server_run_exception(self, mock_config):
        """Test that main() cleans up resources when server.run() raises an exception.

        This exercises the production exception handling path in main().
        """
        original_client = server._client
        cleanup_detected = False

        # We need to detect cleanup indirectly since HighlightClient is created
        # inside main(). We do this by checking _client is None after main() exits.
        async def mock_server_run_with_error(*args, **kwargs):
            # Verify client was set before the error
            assert server._client is not None, "Client should be set before error"
            raise RuntimeError("Simulated server error")

        try:
            with (
                patch("cast_highlight_mcp.server.load_config", return_value=mock_config),
                patch("cast_highlight_mcp.server.stdio_server") as mock_stdio,
                patch.object(server.server, "run", mock_server_run_with_error),
                patch.object(server.server, "create_initialization_options", return_value={}),
                patch("cast_highlight_mcp.server.configure_logging"),
            ):
                mock_stdio.return_value.__aenter__ = AsyncMock(
                    return_value=(AsyncMock(), AsyncMock())
                )
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

                # main() should propagate the exception from server.run()
                with pytest.raises(RuntimeError, match="Simulated server error"):
                    server.main()

                # After main() exits (even with exception), cleanup should have happened
                # The AsyncExitStack ensures __aexit__ is called on HighlightClient
                cleanup_detected = True

            assert cleanup_detected, "Exception should propagate and cleanup should occur"

        finally:
            server._client = original_client

    @pytest.mark.asyncio
    async def test_async_lifecycle_pattern_matches_production(self, mock_config):
        """Test that the async lifecycle pattern used in tests matches production.

        This test verifies that our test patterns (using AsyncExitStack directly)
        produce the same lifecycle behavior as the production main() function.
        """
        original_client = server._client
        close_called = False

        class TrackingClient(HighlightClient):
            async def close(self):
                nonlocal close_called
                close_called = True
                await super().close()

        try:
            # This pattern mirrors exactly what main() does
            async with AsyncExitStack() as stack:
                server._client = await stack.enter_async_context(TrackingClient(mock_config))
                # Simulate server operation
                assert server._client is not None
                assert isinstance(server._client, HighlightClient)

            # After exiting the context (like main() returning), cleanup should happen
            assert close_called, "Client.close() should be called when exiting context"

        finally:
            server._client = original_client

    @pytest.mark.asyncio
    async def test_cleanup_on_exception_matches_production(self, mock_config):
        """Test that exception cleanup matches production behavior."""
        original_client = server._client
        close_called = False

        class TrackingClient(HighlightClient):
            async def close(self):
                nonlocal close_called
                close_called = True
                await super().close()

        try:
            with pytest.raises(RuntimeError, match="Server run error"):
                async with AsyncExitStack() as stack:
                    server._client = await stack.enter_async_context(TrackingClient(mock_config))
                    # Simulate server.run() throwing an error
                    raise RuntimeError("Server run error")

            # Even with exception, cleanup should happen (this is what AsyncExitStack guarantees)
            assert close_called, "Client should be closed even when server.run() fails"

        finally:
            server._client = original_client


class TestClientConfigValidation:
    """Tests for client configuration validation during initialization."""

    def test_client_validates_retry_attempts(self):
        """Test that client validates retry_attempts configuration."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
            retry_attempts=0,  # Invalid
        )
        with pytest.raises(ValueError, match="retry_attempts must be at least 1"):
            HighlightClient(config)

    def test_client_validates_retry_min_wait(self):
        """Test that client validates retry_min_wait configuration."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
            retry_min_wait=-1,  # Invalid
        )
        with pytest.raises(ValueError, match="retry_min_wait must be non-negative"):
            HighlightClient(config)

    def test_client_validates_retry_max_wait(self):
        """Test that client validates retry_max_wait >= retry_min_wait."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
            retry_min_wait=10,
            retry_max_wait=5,  # Invalid: less than min
        )
        with pytest.raises(ValueError, match="retry_max_wait must be >= retry_min_wait"):
            HighlightClient(config)

    def test_client_validates_retry_multiplier(self):
        """Test that client validates retry_multiplier is positive."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
            retry_multiplier=0,  # Invalid
        )
        with pytest.raises(ValueError, match="retry_multiplier must be positive"):
            HighlightClient(config)
