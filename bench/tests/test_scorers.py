"""Tests for scoring functions."""

import pytest

from janus_bench.models import StreamingMetrics, TaskResult, TaskType
from janus_bench.scorers import (
    score_quality,
    score_speed,
    score_cost,
    score_streaming,
    score_multimodal,
    compute_composite_score,
)


class TestQualityScorer:
    """Tests for quality scoring."""

    def test_exact_answer_match(self):
        """Test scoring with exact answer match."""
        score = score_quality("The capital of France is Paris.", "Paris")
        assert score == 1.0

    def test_exact_answer_no_match(self):
        """Test scoring with exact answer no match."""
        score = score_quality("The capital of France is London.", "Paris")
        assert score == 0.0

    def test_keyword_all_match(self):
        """Test scoring with all keywords present."""
        score = score_quality(
            "Photosynthesis uses sunlight and carbon dioxide to produce oxygen.",
            expected_keywords=["sunlight", "carbon dioxide", "oxygen"],
        )
        assert score == 1.0

    def test_keyword_partial_match(self):
        """Test scoring with partial keyword match."""
        score = score_quality(
            "Photosynthesis uses sunlight.",
            expected_keywords=["sunlight", "carbon dioxide", "oxygen"],
        )
        assert score == pytest.approx(1 / 3, rel=0.01)

    def test_empty_response(self):
        """Test scoring empty response."""
        assert score_quality("") == 0.0
        assert score_quality(None) == 0.0

    def test_no_expectations(self):
        """Test scoring with no expected answer or keywords."""
        score = score_quality("This is a reasonable response to the question.")
        assert score == 0.7  # Default score for decent length response


class TestSpeedScorer:
    """Tests for speed scoring."""

    def test_fast_response(self):
        """Test scoring for fast response."""
        score = score_speed(latency_seconds=2.0, ttft_seconds=0.5)
        assert score == 1.0

    def test_target_response(self):
        """Test scoring at target latency."""
        score = score_speed(latency_seconds=8.0, ttft_seconds=2.0)
        assert score == 1.0

    def test_slow_response(self):
        """Test scoring for slow response."""
        score = score_speed(latency_seconds=16.0, ttft_seconds=4.0)
        assert 0.4 < score < 0.6  # Half score range

    def test_no_ttft(self):
        """Test scoring without TTFT data."""
        score = score_speed(latency_seconds=4.0)
        assert score == 1.0  # Uses latency only

    def test_tps_influences_score(self):
        """Test TPS contributes to speed score."""
        slow_tps = score_speed(latency_seconds=8.0, ttft_seconds=2.0, tps=5.0)
        fast_tps = score_speed(latency_seconds=8.0, ttft_seconds=2.0, tps=15.0)

        assert fast_tps > slow_tps


class TestCostScorer:
    """Tests for cost scoring."""

    def test_low_cost(self):
        """Test scoring for low cost."""
        score = score_cost(total_tokens=500, cost_usd=0.005)
        assert score >= 0.9

    def test_high_cost(self):
        """Test scoring for high cost."""
        score = score_cost(total_tokens=5000, cost_usd=0.05)
        assert 0.1 < score < 0.5  # Score is lower for high cost

    def test_no_cost_data(self):
        """Test scoring with no cost data."""
        score = score_cost()
        assert score == 0.5  # Neutral default


class TestStreamingScorer:
    """Tests for streaming scoring."""

    def test_good_streaming(self):
        """Test scoring for good streaming behavior."""
        metrics = StreamingMetrics(
            ttft_seconds=0.5,
            max_gap_seconds=0.5,
            total_chunks=20,
            keep_alive_count=2,
            total_duration_seconds=5.0,
        )
        score = score_streaming(metrics)
        assert score >= 0.9

    def test_slow_ttft(self):
        """Test scoring for slow TTFT."""
        metrics = StreamingMetrics(
            ttft_seconds=4.0,
            max_gap_seconds=0.5,
            total_chunks=20,
            keep_alive_count=2,
            total_duration_seconds=10.0,
        )
        score = score_streaming(metrics)
        assert 0.4 < score < 0.8

    def test_large_gaps(self):
        """Test scoring for large gaps."""
        metrics = StreamingMetrics(
            ttft_seconds=0.5,
            max_gap_seconds=5.0,
            total_chunks=10,
            keep_alive_count=0,
            total_duration_seconds=10.0,
        )
        score = score_streaming(metrics)
        assert score < 0.85  # Score penalized for large gaps but good TTFT helps

    def test_no_metrics(self):
        """Test scoring with no metrics."""
        score = score_streaming(None)
        assert score == 0.0


class TestMultimodalScorer:
    """Tests for multimodal scoring."""

    def test_image_acknowledged(self):
        """Test scoring when image is acknowledged."""
        score = score_multimodal(
            "I can see a red image in this picture.",
            has_image_input=True,
        )
        assert score >= 0.7

    def test_image_not_acknowledged(self):
        """Test scoring when image is not acknowledged."""
        score = score_multimodal(
            "Hello, how can I help you today?",
            has_image_input=True,
        )
        assert score == 0.2

    def test_no_image_input(self):
        """Test scoring for non-multimodal task."""
        score = score_multimodal(
            "Any response here.",
            has_image_input=False,
        )
        assert score == 1.0  # N/A

    def test_image_generation_fallback_without_clip(self, monkeypatch):
        """Test image generation scoring without CLIP evaluator."""
        monkeypatch.setattr(
            "janus_bench.scorers.multimodal._get_clip_evaluator",
            lambda: None,
        )
        score = score_multimodal(
            "Here is the image: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
            has_image_input=False,
            metadata={
                "multimodal_task_type": "image_generation",
                "evaluation": {
                    "reference_prompt": "red apple on white background",
                    "min_score": 0.25,
                },
            },
        )
        assert score == 0.8

    def test_image_understanding_key_facts(self):
        """Test image understanding scoring with expected elements."""
        score = score_multimodal(
            "The chart shows an upward increase over time.",
            has_image_input=True,
            metadata={
                "multimodal_task_type": "image_understanding",
                "evaluation": {
                    "expected_elements": ["upward", "growth", "increase"],
                    "min_matches": 1,
                },
            },
        )
        assert score == 1.0

    def test_mixed_media_contains_any(self):
        """Test mixed media scoring with contains_any evaluation."""
        score = score_multimodal(
            "That looks like a golden retriever.",
            has_image_input=True,
            metadata={
                "multimodal_task_type": "mixed_media",
                "evaluation": {"type": "contains_any", "expected": ["retriever", "labrador"]},
            },
        )
        assert score == 1.0

    def test_modality_routing_behavior(self):
        """Test modality routing scoring for expected behavior."""
        score = score_multimodal(
            "Here is the image: data:image/png;base64,AAA",
            has_image_input=False,
            metadata={
                "multimodal_task_type": "modality_routing",
                "expected_behavior": "generate_image",
                "evaluation": {
                    "indicators": {
                        "generate_image": ["data:image", "generated"],
                        "refuse": ["cannot", "unable"],
                    }
                },
            },
        )
        assert score == 1.0


class TestCompositeScorer:
    """Tests for composite score calculation."""

    def test_perfect_scores(self):
        """Test composite calculation with perfect scores."""
        results = [
            TaskResult(
                task_id="test_001",
                benchmark="janus_research",
                task_type=TaskType.RESEARCH,
                success=True,
                response_text="Test response",
                latency_seconds=2.0,
                quality_score=1.0,
                speed_score=1.0,
                cost_score=1.0,
                streaming_score=1.0,
                multimodal_score=1.0,
            ),
            TaskResult(
                task_id="test_002",
                benchmark="janus_tool_use",
                task_type=TaskType.TOOL_USE,
                success=True,
                response_text="Test response",
                latency_seconds=2.0,
                quality_score=1.0,
                speed_score=1.0,
                cost_score=1.0,
                streaming_score=1.0,
                multimodal_score=1.0,
            ),
            TaskResult(
                task_id="test_003",
                benchmark="janus_streaming",
                task_type=TaskType.STREAMING,
                success=True,
                response_text="Test response",
                latency_seconds=2.0,
                streaming_metrics=StreamingMetrics(
                    ttft_seconds=0.2,
                    max_gap_seconds=0.1,
                    total_chunks=10,
                    keep_alive_count=0,
                    total_duration_seconds=2.0,
                ),
                tokens_per_second=20.0,
                quality_score=1.0,
                speed_score=1.0,
                cost_score=1.0,
                streaming_score=1.0,
                multimodal_score=1.0,
            ),
            TaskResult(
                task_id="test_004",
                benchmark="janus_cost",
                task_type=TaskType.COST,
                success=True,
                response_text="Test response",
                latency_seconds=2.0,
                quality_score=1.0,
                speed_score=1.0,
                cost_score=1.0,
                streaming_score=1.0,
                multimodal_score=1.0,
            ),
            TaskResult(
                task_id="test_005",
                benchmark="janus_multimodal",
                task_type=TaskType.MULTIMODAL,
                success=True,
                response_text="Test response",
                latency_seconds=2.0,
                quality_score=1.0,
                speed_score=1.0,
                cost_score=1.0,
                streaming_score=1.0,
                multimodal_score=1.0,
            ),
        ]
        scores = compute_composite_score(results)
        assert scores["composite_score"] == pytest.approx(100.0, rel=1e-6)

    def test_research_metrics_in_results(self):
        """Ensure research metrics are aggregated in benchmark metrics."""
        results = [
            TaskResult(
                task_id="research_001",
                benchmark="janus_research",
                task_type=TaskType.RESEARCH,
                success=True,
                response_text="According to source: https://example.com, ...",
                latency_seconds=1.0,
                quality_score=0.8,
                metadata={
                    "research_task_type": "fact_verification",
                    "search_used": True,
                    "citation_used": True,
                },
            ),
            TaskResult(
                task_id="research_002",
                benchmark="janus_research",
                task_type=TaskType.RESEARCH,
                success=True,
                response_text="Summary without explicit citation.",
                latency_seconds=2.0,
                quality_score=0.6,
                metadata={
                    "research_task_type": "current_events",
                    "search_used": False,
                    "citation_used": False,
                },
            ),
        ]

        scores = compute_composite_score(results)
        metrics = scores["benchmark_metrics"]["janus_research"]

        assert metrics["search_usage_rate"] == 0.5
        assert metrics["citation_rate"] == 0.5
        assert metrics["by_task_type"]["fact_verification"]["count"] == 1
        assert metrics["by_task_type"]["current_events"]["count"] == 1

    def test_zero_scores(self):
        """Test composite calculation with zero scores."""
        results = [
            TaskResult(
                task_id="test_001",
                benchmark="janus_research",
                task_type=TaskType.RESEARCH,
                success=False,
                latency_seconds=60.0,
                quality_score=0.0,
                speed_score=0.0,
                cost_score=0.0,
                streaming_score=0.0,
                multimodal_score=0.0,
            ),
        ]
        scores = compute_composite_score(results)
        assert scores["composite_score"] == 0.0

    def test_empty_results(self):
        """Test composite calculation with no results."""
        scores = compute_composite_score([])
        assert scores["composite_score"] == 0.0

    def test_custom_weights(self):
        """Test composite calculation with custom weights."""
        results = [
            TaskResult(
                task_id="test_001",
                benchmark="core",
                task_type=TaskType.RESEARCH,
                success=True,
                latency_seconds=2.0,
                quality_score=1.0,
                speed_score=0.5,
                cost_score=0.5,
                streaming_score=0.5,
                multimodal_score=1.0,
            ),
        ]
        scores = compute_composite_score(
            results,
            weight_quality=80,
            weight_speed=5,
            weight_cost=5,
            weight_streaming=5,
            weight_multimodal=5,
        )
        # Quality dominates with 80% weight
        assert scores["composite_score"] >= 80.0

    def test_janus_composite_scoring(self):
        """Test Janus composite scoring across benchmark groups."""
        results = [
            TaskResult(
                task_id="research_001",
                benchmark="janus_research",
                task_type=TaskType.RESEARCH,
                success=True,
                latency_seconds=1.0,
                quality_score=0.8,
                speed_score=0.0,
                cost_score=0.0,
                streaming_score=0.0,
                multimodal_score=0.0,
            ),
            TaskResult(
                task_id="tool_001",
                benchmark="janus_tool_use",
                task_type=TaskType.TOOL_USE,
                success=True,
                latency_seconds=1.0,
                quality_score=0.6,
                speed_score=0.0,
                cost_score=0.0,
                streaming_score=0.0,
                multimodal_score=0.0,
            ),
            TaskResult(
                task_id="multimodal_001",
                benchmark="janus_multimodal",
                task_type=TaskType.MULTIMODAL,
                success=True,
                latency_seconds=1.0,
                quality_score=0.0,
                speed_score=0.0,
                cost_score=0.0,
                streaming_score=0.0,
                multimodal_score=0.8,
            ),
            TaskResult(
                task_id="streaming_001",
                benchmark="janus_streaming",
                task_type=TaskType.STREAMING,
                success=True,
                latency_seconds=1.0,
                streaming_metrics=StreamingMetrics(
                    ttft_seconds=0.5,
                    max_gap_seconds=0.2,
                    total_chunks=10,
                    keep_alive_count=0,
                    total_duration_seconds=1.0,
                ),
                tokens_per_second=20.0,
                quality_score=0.0,
                speed_score=0.0,
                cost_score=0.0,
                streaming_score=0.9,
                multimodal_score=0.0,
            ),
            TaskResult(
                task_id="cost_001",
                benchmark="janus_cost",
                task_type=TaskType.COST,
                success=True,
                latency_seconds=1.0,
                total_tokens=500,
                cost_usd=0.01,
                quality_score=0.0,
                speed_score=0.0,
                cost_score=0.5,
                streaming_score=0.0,
                multimodal_score=0.0,
            ),
        ]

        scores = compute_composite_score(results)
        assert scores["composite_score"] == pytest.approx(77.0, rel=0.01)
