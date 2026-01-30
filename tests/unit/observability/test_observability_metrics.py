"""Unit tests for the metrics collection module."""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor


class TestToolMetricsDataclass:
    """Tests for the ToolMetrics dataclass."""

    def test_tool_metrics_initialization(self):
        """Verify ToolMetrics initializes with correct defaults."""
        from cast_highlight_mcp.observability.metrics import ToolMetrics

        metrics = ToolMetrics(tool_name="highlight_get_company")

        assert metrics.tool_name == "highlight_get_company"
        assert metrics.calls_total == 0
        assert metrics.calls_success == 0
        assert metrics.calls_error == 0
        assert metrics.latency_sum_ms == 0.0
        assert isinstance(metrics.latency_buckets, dict)
        assert isinstance(metrics.latency_values, list)
        assert len(metrics.latency_values) == 0
        assert isinstance(metrics.errors_by_type, dict)
        assert metrics.last_call_timestamp is None

    def test_tool_metrics_histogram_buckets_initialized(self):
        """Verify histogram buckets are initialized with expected boundaries."""
        from cast_highlight_mcp.observability.metrics import (
            LATENCY_BUCKETS_MS,
            ToolMetrics,
        )

        metrics = ToolMetrics(tool_name="test_tool")

        # Check all expected buckets exist and are initialized to 0
        for bucket in LATENCY_BUCKETS_MS:
            assert bucket in metrics.latency_buckets
            assert metrics.latency_buckets[bucket] == 0

        # Check +inf bucket
        assert float("inf") in metrics.latency_buckets
        assert metrics.latency_buckets[float("inf")] == 0


class TestHttpMetricsDataclass:
    """Tests for the HttpMetrics dataclass."""

    def test_http_metrics_initialization(self):
        """Verify HttpMetrics initializes with correct defaults."""
        from cast_highlight_mcp.observability.metrics import HttpMetrics

        metrics = HttpMetrics()

        assert metrics.requests_total == 0
        assert isinstance(metrics.requests_by_status, dict)
        assert isinstance(metrics.requests_by_method, dict)
        assert metrics.latency_sum_ms == 0.0
        assert isinstance(metrics.latency_buckets, dict)
        assert isinstance(metrics.latency_values, list)
        assert metrics.errors_total == 0


class TestObservabilityStateDataclass:
    """Tests for the ObservabilityState dataclass."""

    def test_observability_state_initialization(self):
        """Verify ObservabilityState initializes correctly."""
        from cast_highlight_mcp.observability.metrics import ObservabilityState

        state = ObservabilityState()

        assert state.start_time > 0
        assert isinstance(state.tools, dict)
        assert len(state.tools) == 0
        assert state.http is not None
        assert state.reset_count == 0
        assert state.last_reset_time is None


class TestMetricsCollectorRecordToolCall:
    """Tests for MetricsCollector.record_tool_call() method."""

    def test_record_tool_call_increments_total_counter(self):
        """Verify calls_total increments on each call."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_tool_call("test_tool", duration_ms=150.0, success=True)
        collector.record_tool_call("test_tool", duration_ms=200.0, success=False)

        state = collector.get_metrics()
        assert state.tools["test_tool"].calls_total == 3

    def test_record_tool_call_success_increments_success_counter(self):
        """Verify calls_success increments when success=True."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_tool_call("test_tool", duration_ms=150.0, success=True)

        state = collector.get_metrics()
        assert state.tools["test_tool"].calls_success == 2
        assert state.tools["test_tool"].calls_error == 0

    def test_record_tool_call_error_increments_error_counter(self):
        """Verify calls_error increments when success=False."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_tool_call("test_tool", duration_ms=100.0, success=False)
        collector.record_tool_call(
            "test_tool", duration_ms=150.0, success=False, error_type="http_404"
        )

        state = collector.get_metrics()
        assert state.tools["test_tool"].calls_error == 2
        assert state.tools["test_tool"].calls_success == 0

    def test_record_tool_call_records_error_type(self):
        """Verify error_type is recorded correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_tool_call(
            "test_tool", duration_ms=100.0, success=False, error_type="http_404"
        )
        collector.record_tool_call(
            "test_tool", duration_ms=150.0, success=False, error_type="http_404"
        )
        collector.record_tool_call(
            "test_tool", duration_ms=200.0, success=False, error_type="timeout"
        )

        state = collector.get_metrics()
        assert state.tools["test_tool"].errors_by_type["http_404"] == 2
        assert state.tools["test_tool"].errors_by_type["timeout"] == 1

    def test_record_tool_call_accumulates_latency_sum(self):
        """Verify latency_sum_ms accumulates correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_tool_call("test_tool", duration_ms=150.5, success=True)
        collector.record_tool_call("test_tool", duration_ms=200.5, success=True)

        state = collector.get_metrics()
        assert abs(state.tools["test_tool"].latency_sum_ms - 451.0) < 0.001

    def test_record_tool_call_stores_latency_values(self):
        """Verify latency values are stored for percentile calculation."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_tool_call("test_tool", duration_ms=200.0, success=True)
        collector.record_tool_call("test_tool", duration_ms=300.0, success=True)

        state = collector.get_metrics()
        assert len(state.tools["test_tool"].latency_values) == 3
        assert 100.0 in state.tools["test_tool"].latency_values
        assert 200.0 in state.tools["test_tool"].latency_values
        assert 300.0 in state.tools["test_tool"].latency_values

    def test_record_tool_call_updates_histogram_buckets(self):
        """Verify histogram buckets are updated correctly (cumulative)."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        # 75ms should increment buckets 100, 250, 500, 1000, 2500, 5000, 10000, +inf
        collector.record_tool_call("test_tool", duration_ms=75.0, success=True)

        state = collector.get_metrics()
        buckets = state.tools["test_tool"].latency_buckets

        # Buckets below 75ms should be 0
        assert buckets[10] == 0
        assert buckets[25] == 0
        assert buckets[50] == 0

        # Buckets >= 75ms should be 1
        assert buckets[100] == 1
        assert buckets[250] == 1
        assert buckets[500] == 1
        assert buckets[1000] == 1
        assert buckets[2500] == 1
        assert buckets[5000] == 1
        assert buckets[10000] == 1
        assert buckets[float("inf")] == 1

    def test_record_tool_call_updates_last_call_timestamp(self):
        """Verify last_call_timestamp is updated."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        before = time.time()
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        after = time.time()

        state = collector.get_metrics()
        assert state.tools["test_tool"].last_call_timestamp is not None
        assert before <= state.tools["test_tool"].last_call_timestamp <= after

    def test_record_tool_call_creates_new_tool_metrics(self):
        """Verify new tool metrics are created for unknown tools."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_tool_call("tool_a", duration_ms=100.0, success=True)
        collector.record_tool_call("tool_b", duration_ms=200.0, success=False)

        state = collector.get_metrics()
        assert "tool_a" in state.tools
        assert "tool_b" in state.tools
        assert state.tools["tool_a"].calls_total == 1
        assert state.tools["tool_b"].calls_total == 1

    def test_record_tool_call_disabled_collector(self):
        """Verify no metrics recorded when collector is disabled."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector(enabled=False)

        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)

        state = collector.get_metrics()
        assert len(state.tools) == 0


class TestMetricsCollectorRecordHttpRequest:
    """Tests for MetricsCollector.record_http_request() method."""

    def test_record_http_request_increments_total(self):
        """Verify requests_total increments on each call."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_http_request("GET", 200, duration_ms=100.0)
        collector.record_http_request("GET", 200, duration_ms=150.0)
        collector.record_http_request("POST", 201, duration_ms=200.0)

        state = collector.get_metrics()
        assert state.http.requests_total == 3

    def test_record_http_request_tracks_status_codes(self):
        """Verify requests_by_status is populated correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_http_request("GET", 200, duration_ms=100.0)
        collector.record_http_request("GET", 200, duration_ms=150.0)
        collector.record_http_request("GET", 404, duration_ms=50.0)
        collector.record_http_request("GET", 500, duration_ms=200.0)

        state = collector.get_metrics()
        assert state.http.requests_by_status[200] == 2
        assert state.http.requests_by_status[404] == 1
        assert state.http.requests_by_status[500] == 1

    def test_record_http_request_tracks_methods(self):
        """Verify requests_by_method is populated correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_http_request("GET", 200, duration_ms=100.0)
        collector.record_http_request("GET", 200, duration_ms=150.0)
        collector.record_http_request("POST", 201, duration_ms=200.0)

        state = collector.get_metrics()
        assert state.http.requests_by_method["GET"] == 2
        assert state.http.requests_by_method["POST"] == 1

    def test_record_http_request_tracks_errors(self):
        """Verify errors_total increments for 4xx and 5xx responses."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_http_request("GET", 200, duration_ms=100.0)
        collector.record_http_request("GET", 400, duration_ms=50.0)
        collector.record_http_request("GET", 404, duration_ms=50.0)
        collector.record_http_request("GET", 500, duration_ms=200.0)

        state = collector.get_metrics()
        assert state.http.errors_total == 3  # 400, 404, 500

    def test_record_http_request_accumulates_latency(self):
        """Verify latency_sum_ms accumulates correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_http_request("GET", 200, duration_ms=100.0)
        collector.record_http_request("GET", 200, duration_ms=150.5)
        collector.record_http_request("GET", 200, duration_ms=200.5)

        state = collector.get_metrics()
        assert abs(state.http.latency_sum_ms - 451.0) < 0.001

    def test_record_http_request_updates_histogram(self):
        """Verify histogram buckets are updated correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_http_request("GET", 200, duration_ms=75.0)

        state = collector.get_metrics()
        buckets = state.http.latency_buckets

        assert buckets[50] == 0
        assert buckets[100] == 1
        assert buckets[float("inf")] == 1


class TestMetricsCollectorGetMetrics:
    """Tests for MetricsCollector.get_metrics() method."""

    def test_get_metrics_returns_observability_state(self):
        """Verify get_metrics returns an ObservabilityState."""
        from cast_highlight_mcp.observability.metrics import (
            MetricsCollector,
            ObservabilityState,
        )

        collector = MetricsCollector()
        state = collector.get_metrics()

        assert isinstance(state, ObservabilityState)

    def test_get_metrics_returns_copy(self):
        """Verify get_metrics returns a copy (not the internal state)."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)

        state1 = collector.get_metrics()
        state1.tools["test_tool"].calls_total = 999

        state2 = collector.get_metrics()
        assert state2.tools["test_tool"].calls_total == 1


class TestMetricsCollectorExportJson:
    """Tests for MetricsCollector.export_json() method."""

    def test_export_json_returns_valid_json(self):
        """Verify export_json returns valid JSON string."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)

        result = collector.export_json()

        # Should not raise
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_export_json_includes_timestamp(self):
        """Verify JSON export includes timestamp."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        result = json.loads(collector.export_json())

        assert "timestamp" in result
        assert result["timestamp"].endswith("Z")

    def test_export_json_includes_uptime(self):
        """Verify JSON export includes uptime_seconds."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        time.sleep(0.01)  # Small delay
        result = json.loads(collector.export_json())

        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0.01

    def test_export_json_includes_tool_metrics(self):
        """Verify JSON export includes tool metrics."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_tool_call(
            "test_tool", duration_ms=200.0, success=False, error_type="http_404"
        )

        result = json.loads(collector.export_json())

        assert "tools" in result
        assert "test_tool" in result["tools"]

        tool = result["tools"]["test_tool"]
        assert tool["calls_total"] == 2
        assert tool["calls_success"] == 1
        assert tool["calls_error"] == 1
        assert "latency_avg_ms" in tool
        assert "latency_p50_ms" in tool
        assert "latency_p90_ms" in tool
        assert "latency_p95_ms" in tool
        assert "latency_p99_ms" in tool
        assert "errors_by_type" in tool
        assert tool["errors_by_type"]["http_404"] == 1

    def test_export_json_includes_http_metrics(self):
        """Verify JSON export includes HTTP metrics."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_http_request("GET", 200, duration_ms=100.0)
        collector.record_http_request("GET", 404, duration_ms=50.0)

        result = json.loads(collector.export_json())

        assert "http" in result

        http = result["http"]
        assert http["requests_total"] == 2
        assert http["requests_by_status"]["200"] == 1
        assert http["requests_by_status"]["404"] == 1
        assert http["errors_total"] == 1
        assert "latency_avg_ms" in http
        assert "latency_p50_ms" in http

    def test_export_json_calculates_percentiles_correctly(self):
        """Verify percentiles are calculated correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        # Add 10 samples: 10, 20, 30, ..., 100
        for i in range(1, 11):
            collector.record_tool_call("test_tool", duration_ms=float(i * 10), success=True)

        result = json.loads(collector.export_json())
        tool = result["tools"]["test_tool"]

        # p50 should be around 55 (median between 50 and 60)
        assert 50 <= tool["latency_p50_ms"] <= 60

        # p90 should be around 91
        assert 85 <= tool["latency_p90_ms"] <= 95


class TestMetricsCollectorExportPrometheus:
    """Tests for MetricsCollector.export_prometheus() method."""

    def test_export_prometheus_returns_string(self):
        """Verify export_prometheus returns a string."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        result = collector.export_prometheus()

        assert isinstance(result, str)

    def test_export_prometheus_includes_tool_calls_total(self):
        """Verify Prometheus export includes tool_calls_total counter."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector(prefix="highlight")
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_tool_call(
            "test_tool", duration_ms=200.0, success=False, error_type="http_404"
        )

        result = collector.export_prometheus()

        assert "# HELP highlight_tool_calls_total" in result
        assert "# TYPE highlight_tool_calls_total counter" in result
        assert 'highlight_tool_calls_total{tool_name="test_tool",status="success"} 1' in result
        assert 'highlight_tool_calls_total{tool_name="test_tool",status="error"} 1' in result

    def test_export_prometheus_includes_tool_duration_histogram(self):
        """Verify Prometheus export includes tool duration histogram."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector(prefix="highlight")
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)

        result = collector.export_prometheus()

        assert "# HELP highlight_tool_duration_seconds" in result
        assert "# TYPE highlight_tool_duration_seconds histogram" in result
        assert 'highlight_tool_duration_seconds_bucket{tool_name="test_tool"' in result
        assert 'highlight_tool_duration_seconds_sum{tool_name="test_tool"}' in result
        assert 'highlight_tool_duration_seconds_count{tool_name="test_tool"}' in result

    def test_export_prometheus_includes_http_requests_total(self):
        """Verify Prometheus export includes HTTP requests counter."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector(prefix="highlight")
        collector.record_http_request("GET", 200, duration_ms=100.0)

        result = collector.export_prometheus()

        assert "# HELP highlight_http_requests_total" in result
        assert "# TYPE highlight_http_requests_total counter" in result
        assert 'highlight_http_requests_total{method="GET",status_code="200"}' in result

    def test_export_prometheus_includes_uptime(self):
        """Verify Prometheus export includes uptime gauge."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector(prefix="highlight")
        result = collector.export_prometheus()

        assert "# HELP highlight_uptime_seconds" in result
        assert "# TYPE highlight_uptime_seconds gauge" in result
        assert "highlight_uptime_seconds" in result

    def test_export_prometheus_uses_custom_prefix(self):
        """Verify custom prefix is used in metric names."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector(prefix="custom")
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)

        result = collector.export_prometheus()

        assert "custom_tool_calls_total" in result
        assert "highlight_tool_calls_total" not in result


class TestMetricsCollectorReset:
    """Tests for MetricsCollector.reset() method."""

    def test_reset_clears_all_metrics(self):
        """Verify reset() clears all tool and HTTP metrics."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_http_request("GET", 200, duration_ms=100.0)

        collector.reset()

        state = collector.get_metrics()
        assert len(state.tools) == 0
        assert state.http.requests_total == 0

    def test_reset_increments_reset_count(self):
        """Verify reset() increments reset_count."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.reset()
        state1 = collector.get_metrics()
        assert state1.reset_count == 1

        collector.reset()
        state2 = collector.get_metrics()
        assert state2.reset_count == 2

    def test_reset_updates_last_reset_time(self):
        """Verify reset() updates last_reset_time."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        before = time.time()
        collector.reset()
        after = time.time()

        state = collector.get_metrics()
        assert state.last_reset_time is not None
        assert before <= state.last_reset_time <= after

    def test_reset_single_tool(self):
        """Verify reset(tool_name) only resets specific tool."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_tool_call("tool_a", duration_ms=100.0, success=True)
        collector.record_tool_call("tool_b", duration_ms=200.0, success=True)
        collector.record_http_request("GET", 200, duration_ms=100.0)

        collector.reset(tool_name="tool_a")

        state = collector.get_metrics()
        assert state.tools["tool_a"].calls_total == 0
        assert state.tools["tool_b"].calls_total == 1
        assert state.http.requests_total == 1  # HTTP not reset

    def test_reset_nonexistent_tool(self):
        """Verify reset(tool_name) does not raise for unknown tool."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        # Should not raise
        collector.reset(tool_name="nonexistent")


class TestMetricsCollectorThreadSafety:
    """Tests for thread safety of MetricsCollector."""

    def test_concurrent_tool_call_recording(self):
        """Verify concurrent tool call recording is thread-safe."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        num_threads = 10
        calls_per_thread = 100

        def record_calls():
            for _ in range(calls_per_thread):
                collector.record_tool_call("test_tool", duration_ms=100.0, success=True)

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=record_calls)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        state = collector.get_metrics()
        expected_total = num_threads * calls_per_thread
        assert state.tools["test_tool"].calls_total == expected_total

    def test_concurrent_http_request_recording(self):
        """Verify concurrent HTTP request recording is thread-safe."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        num_threads = 10
        requests_per_thread = 100

        def record_requests():
            for _ in range(requests_per_thread):
                collector.record_http_request("GET", 200, duration_ms=100.0)

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=record_requests)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        state = collector.get_metrics()
        expected_total = num_threads * requests_per_thread
        assert state.http.requests_total == expected_total

    def test_concurrent_mixed_operations(self):
        """Verify concurrent mixed operations (record, export, reset) are thread-safe."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        errors = []

        def record_operations():
            try:
                for i in range(50):
                    collector.record_tool_call("tool", duration_ms=float(i), success=True)
                    collector.record_http_request("GET", 200, duration_ms=float(i))
            except Exception as e:
                errors.append(e)

        def export_operations():
            try:
                for _ in range(20):
                    collector.export_json()
                    collector.export_prometheus()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            futures.append(executor.submit(record_operations))
            futures.append(executor.submit(record_operations))
            futures.append(executor.submit(export_operations))

            for f in futures:
                f.result()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestMetricsCollectorGracefulDegradation:
    """Tests for graceful degradation of MetricsCollector."""

    def test_disabled_collector_no_effect(self):
        """Verify disabled collector has no effect on calls."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector(enabled=False)

        # These should not raise and should not store anything
        collector.record_tool_call("test_tool", duration_ms=100.0, success=True)
        collector.record_http_request("GET", 200, duration_ms=100.0)

        state = collector.get_metrics()
        assert len(state.tools) == 0
        assert state.http.requests_total == 0


class TestGetMetricsCollectorSingleton:
    """Tests for get_metrics_collector() singleton function."""

    def test_get_metrics_collector_returns_collector(self):
        """Verify get_metrics_collector returns a MetricsCollector."""
        from cast_highlight_mcp.observability.metrics import (
            MetricsCollector,
            get_metrics_collector,
        )

        collector = get_metrics_collector()
        assert isinstance(collector, MetricsCollector)

    def test_get_metrics_collector_returns_same_instance(self):
        """Verify get_metrics_collector returns the same instance."""
        from cast_highlight_mcp.observability.metrics import get_metrics_collector

        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        assert collector1 is collector2


class TestPercentileCalculation:
    """Tests for percentile calculation."""

    def test_percentile_empty_list(self):
        """Verify percentile calculation with empty list returns 0."""
        from cast_highlight_mcp.observability.metrics import calculate_percentile

        assert calculate_percentile([], 50) == 0.0
        assert calculate_percentile([], 99) == 0.0

    def test_percentile_single_element(self):
        """Verify percentile calculation with single element returns that element."""
        from cast_highlight_mcp.observability.metrics import calculate_percentile

        assert calculate_percentile([100.0], 50) == 100.0
        assert calculate_percentile([100.0], 99) == 100.0

    def test_percentile_known_values(self):
        """Verify percentile calculation with known data."""
        from cast_highlight_mcp.observability.metrics import calculate_percentile

        samples = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

        # p50 (median) should be interpolated between 50 and 60
        p50 = calculate_percentile(samples, 50)
        assert 50 <= p50 <= 60

        # p0 should be minimum
        p0 = calculate_percentile(samples, 0)
        assert p0 == 10.0

        # p100 should be maximum
        p100 = calculate_percentile(samples, 100)
        assert p100 == 100.0

    def test_percentile_p95_p99(self):
        """Verify p95 and p99 percentile calculations."""
        from cast_highlight_mcp.observability.metrics import calculate_percentile

        # Create 100 samples: 1, 2, ..., 100
        samples = [float(i) for i in range(1, 101)]

        p95 = calculate_percentile(samples, 95)
        assert 94 <= p95 <= 96

        p99 = calculate_percentile(samples, 99)
        assert 98 <= p99 <= 100


class TestHistogramBuckets:
    """Tests for histogram bucket behavior."""

    def test_histogram_buckets_are_cumulative(self):
        """Verify histogram buckets are cumulative (Prometheus convention)."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        # Add a 5ms sample - should be in 10, 25, 50, 100, ... +inf buckets
        collector.record_tool_call("test_tool", duration_ms=5.0, success=True)

        state = collector.get_metrics()
        buckets = state.tools["test_tool"].latency_buckets

        assert buckets[10] == 1
        assert buckets[25] == 1
        assert buckets[50] == 1
        assert buckets[100] == 1
        assert buckets[float("inf")] == 1

    def test_histogram_boundary_values(self):
        """Verify histogram handles boundary values correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        # Exactly on boundary (10ms)
        collector.record_tool_call("test_tool", duration_ms=10.0, success=True)

        state = collector.get_metrics()
        buckets = state.tools["test_tool"].latency_buckets

        # 10ms should be <= 10ms bucket
        assert buckets[10] == 1

    def test_histogram_very_large_values(self):
        """Verify histogram handles values larger than all buckets."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        # 100 seconds - larger than all buckets except +inf
        collector.record_tool_call("test_tool", duration_ms=100000.0, success=True)

        state = collector.get_metrics()
        buckets = state.tools["test_tool"].latency_buckets

        # All buckets should be 0 except +inf
        assert buckets[10] == 0
        assert buckets[10000] == 0
        assert buckets[float("inf")] == 1


class TestLatencySampleBounding:
    """Tests for latency sample bounding (sliding window)."""

    def test_latency_samples_bounded(self):
        """Verify latency samples are bounded to prevent memory growth."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector._max_latency_samples = 100  # Set lower limit for test

        # Add more samples than the limit
        for i in range(150):
            collector.record_tool_call("test_tool", duration_ms=float(i), success=True)

        state = collector.get_metrics()
        assert len(state.tools["test_tool"].latency_values) <= 100


class TestEdgeCaseLatencyValues:
    """Tests for edge case latency values."""

    def test_histogram_with_zero_latency(self):
        """Verify zero latency is handled correctly."""
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_tool_call("test", 0.0, True)
        state = collector.get_metrics()

        # Zero latency should go in the first bucket (10ms) since 0.0 <= 10
        assert state.tools["test"].latency_buckets[10] == 1
        assert state.tools["test"].latency_sum_ms == 0.0
        assert state.tools["test"].calls_total == 1

    def test_histogram_with_negative_latency(self):
        """Verify negative latency doesn't break metrics.

        While negative latency is logically impossible, the collector
        should handle it gracefully without raising exceptions.
        """
        from cast_highlight_mcp.observability.metrics import MetricsCollector

        collector = MetricsCollector()

        # Should not raise
        collector.record_tool_call("test", -5.0, True)

        state = collector.get_metrics()
        # Metrics should still be recorded
        assert state.tools["test"].calls_total == 1
        assert state.tools["test"].latency_sum_ms == -5.0
        # Negative values satisfy all bucket conditions (value <= boundary)
        # so all buckets including the first should be incremented
        assert state.tools["test"].latency_buckets[10] == 1
        assert state.tools["test"].latency_buckets[float("inf")] == 1


class TestConcurrentSingletonCreation:
    """Tests for singleton pattern under concurrent access."""

    def test_concurrent_get_metrics_collector_returns_same_instance(self):
        """Verify singleton pattern under concurrent access."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        from cast_highlight_mcp.observability.metrics import (
            get_metrics_collector,
            reset_metrics_collector,
        )

        # Reset to clear any existing singleton
        reset_metrics_collector()

        instances = []
        lock = threading.Lock()

        def get_instance():
            collector = get_metrics_collector()
            with lock:
                instances.append(collector)

        # Create many threads attempting to get the collector simultaneously
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(get_instance) for _ in range(50)]
            for f in futures:
                f.result()

        # All instances should be the same object
        assert len(instances) == 50
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance, (
                "Singleton returned different instances under concurrent access"
            )
