"""Tests for multimodal scoring helpers."""

from janus_bench.scorers.multimodal import score_multimodal


def test_image_generation_requires_image():
    metadata = {
        "multimodal_task_type": "image_generation",
        "evaluation": {"type": "clip_similarity"},
    }
    score = score_multimodal(
        "No image content provided.",
        has_image_input=False,
        metadata=metadata,
        prompt="Generate an image of a red apple.",
    )
    assert score == 0.0


def test_image_understanding_key_facts():
    metadata = {
        "multimodal_task_type": "image_understanding",
        "evaluation": {"expected_elements": ["increase", "growth"], "min_matches": 1},
    }
    score = score_multimodal(
        "The chart shows clear growth over time.",
        has_image_input=True,
        metadata=metadata,
    )
    assert score == 1.0


def test_mixed_media_contains_any():
    metadata = {
        "multimodal_task_type": "mixed_media",
        "evaluation": {"type": "contains_any", "expected": ["cat", "kitten"]},
    }
    score = score_multimodal(
        "This is a cat sitting on the table.",
        has_image_input=True,
        metadata=metadata,
    )
    assert score == 1.0


def test_modality_routing_text_response():
    metadata = {
        "multimodal_task_type": "modality_routing",
        "expected_behavior": "text_response",
        "evaluation": {
            "indicators": {
                "text_response": ["paris", "capital"],
                "generate_image": ["data:image", "!["],
            }
        },
    }
    score = score_multimodal(
        "Paris is the capital of France.",
        has_image_input=False,
        metadata=metadata,
    )
    assert score == 1.0
