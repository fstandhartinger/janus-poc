# Spec 33: Janus Multimodal Benchmark

## Status: DRAFT

## Context / Why

Janus intelligence implementations can leverage multimodal capabilities through the Chutes API, including:
- **Image generation** - FLUX, SDXL, Stable Diffusion
- **Vision** - Understanding images in prompts
- **Audio** - Text-to-speech (Kokoro), speech-to-text
- **Documents** - PDF parsing, document analysis

The Janus Multimodal Benchmark evaluates an implementation's ability to:
1. **Generate images** - Produce images from text descriptions
2. **Understand images** - Analyze and describe visual content
3. **Handle mixed media** - Process requests with text and images together
4. **Route appropriately** - Choose multimodal vs text-only paths

This benchmark contributes to the "Modality" scoring category (10% of composite score).

## Goals

- Measure image generation quality and relevance
- Evaluate vision/understanding capabilities
- Test multimodal request handling
- Assess appropriate routing decisions
- Provide automated scoring where possible

## Non-Goals

- Audio generation/understanding (limited tooling for automated eval)
- Video generation (future capability)
- Real-time streaming of images
- Subjective artistic quality evaluation

## Functional Requirements

### FR-1: Task Types

The benchmark includes four task types:

#### 1. Image Generation (20 items)

Test image generation from text prompts:

```json
{
  "id": "gen_001",
  "task_type": "image_generation",
  "prompt": "Generate an image of a red apple on a white background",
  "evaluation": {
    "type": "clip_similarity",
    "reference_prompt": "red apple on white background",
    "min_score": 0.25,
    "check_format": "png|jpg|webp"
  }
}
```

#### 2. Image Understanding (20 items)

Test vision/analysis capabilities:

```json
{
  "id": "vision_001",
  "task_type": "image_understanding",
  "image_url": "https://bench-data.janus.rodeo/multimodal/chart_001.png",
  "query": "What is the trend shown in this chart?",
  "evaluation": {
    "type": "key_facts",
    "expected_elements": ["upward", "growth", "increase"],
    "min_matches": 1
  }
}
```

#### 3. Mixed Media (10 items)

Test handling requests with both text and images:

```json
{
  "id": "mixed_001",
  "task_type": "mixed_media",
  "messages": [
    {"role": "user", "content": [
      {"type": "text", "text": "What breed of dog is this?"},
      {"type": "image_url", "image_url": {"url": "https://bench-data.janus.rodeo/multimodal/dog_001.jpg"}}
    ]}
  ],
  "evaluation": {
    "type": "contains_any",
    "expected": ["golden retriever", "labrador", "retriever"]
  }
}
```

#### 4. Modality Routing (10 items)

Test whether implementation correctly routes multimodal requests:

```json
{
  "id": "route_001",
  "task_type": "modality_routing",
  "prompt": "Create a logo for a coffee shop called 'Bean Dream'",
  "expected_behavior": "generate_image",
  "evaluation": {
    "type": "action_check",
    "indicators": {
      "generate_image": ["data:image", "![", "generated", "here is"],
      "refuse": ["cannot generate", "unable to create", "text-only"]
    }
  }
}
```

### FR-2: Image Generation Evaluation

Use CLIP similarity for automated image evaluation:

```python
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

class CLIPEvaluator:
    """Evaluate image-text similarity using CLIP."""

    def __init__(self):
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    def evaluate(self, image: Image.Image, text: str) -> float:
        """
        Calculate CLIP similarity between image and text.

        Returns:
            Similarity score 0.0-1.0
        """
        inputs = self.processor(
            text=[text],
            images=image,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            similarity = logits_per_image.softmax(dim=1)[0][0].item()

        return similarity
```

### FR-3: Vision Evaluation

Evaluate image understanding with key fact matching:

```python
def evaluate_vision_response(
    response: str,
    expected_elements: list[str],
    min_matches: int = 1
) -> tuple[float, str]:
    """
    Evaluate vision/understanding response.

    Returns:
        (score, reasoning)
    """
    response_lower = response.lower()
    matches = []

    for element in expected_elements:
        if element.lower() in response_lower:
            matches.append(element)

    if len(matches) >= min_matches:
        return 1.0, f"Found {len(matches)} expected elements: {matches}"

    if matches:
        score = len(matches) / min_matches
        return score, f"Partial match: found {len(matches)}/{min_matches} elements"

    return 0.0, "No expected elements found"
```

### FR-4: Adapter Implementation

```python
# backend/app/benchmarks/adapters/janus_multimodal.py

import base64
import io
import json
import re
import time
from typing import AsyncIterator
from pathlib import Path
from PIL import Image

from app.benchmarks.base import BenchmarkAdapter, ItemResult
from app.benchmarks.registry import register_adapter


@register_adapter("janus_multimodal")
class JanusMultimodalAdapter(BenchmarkAdapter):
    """Benchmark for multimodal capabilities."""

    def __init__(self, client, model_slug, judge_client=None):
        super().__init__(client, model_slug, judge_client)
        self._items: list[dict] = []
        self._clip_evaluator = None

    def get_name(self) -> str:
        return "janus_multimodal"

    def get_display_name(self) -> str:
        return "Janus Multimodal"

    def get_category(self) -> str:
        return "Janus Intelligence"

    async def get_total_items(self) -> int:
        if not self._items:
            await self.preload()
        return len(self._items)

    async def preload(self) -> None:
        data_path = Path(__file__).parent.parent / "data" / "janus" / "multimodal_items.json"
        if data_path.exists():
            with open(data_path) as f:
                data = json.load(f)
                self._items = data.get("items", [])

        # Lazy load CLIP evaluator
        try:
            from app.benchmarks.utils import CLIPEvaluator
            self._clip_evaluator = CLIPEvaluator()
        except ImportError:
            self._clip_evaluator = None

    async def enumerate_items(self) -> AsyncIterator[str]:
        if not self._items:
            await self.preload()
        for item in self._items:
            yield item["id"]

    async def evaluate_item(self, item_id: str) -> ItemResult:
        """Evaluate a single multimodal task."""
        item = next((i for i in self._items if i["id"] == item_id), None)
        if not item:
            return ItemResult(item_id=item_id, error=f"Item {item_id} not found")

        task_type = item.get("task_type")

        try:
            start_time = time.time()

            # Build messages based on task type
            if task_type == "mixed_media":
                messages = item.get("messages", [])
            elif task_type == "image_understanding":
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": item["image_url"]}},
                            {"type": "text", "text": item["query"]}
                        ]
                    }
                ]
            else:
                messages = [{"role": "user", "content": item.get("prompt", "")}]

            response = await self.client.chat_completion(
                model=self.model_slug,
                messages=messages,
                temperature=0.0,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            response_text = response.choices[0].message.content or ""

        except Exception as e:
            return ItemResult(
                item_id=item_id,
                prompt=str(item.get("prompt") or item.get("query", "")),
                error=str(e)
            )

        # Evaluate based on task type
        if task_type == "image_generation":
            score, reasoning, metadata = await self._evaluate_image_generation(item, response_text)
        elif task_type == "image_understanding":
            score, reasoning, metadata = self._evaluate_image_understanding(item, response_text)
        elif task_type == "mixed_media":
            score, reasoning, metadata = self._evaluate_mixed_media(item, response_text)
        elif task_type == "modality_routing":
            score, reasoning, metadata = self._evaluate_routing(item, response_text)
        else:
            score, reasoning, metadata = 0.0, f"Unknown task type: {task_type}", {}

        return ItemResult(
            item_id=item_id,
            item_hash=self.compute_item_hash(item),
            prompt=str(item.get("prompt") or item.get("query", "")),
            response=response_text[:1000],  # Truncate for storage
            is_correct=score >= 0.7,
            score=score,
            judge_output={"reasoning": reasoning, **metadata},
            latency_ms=latency_ms,
            input_tokens=response.usage.prompt_tokens if response.usage else None,
            output_tokens=response.usage.completion_tokens if response.usage else None,
        )

    async def _evaluate_image_generation(
        self,
        item: dict,
        response: str
    ) -> tuple[float, str, dict]:
        """Evaluate image generation response."""
        evaluation = item.get("evaluation", {})

        # Check if response contains an image
        image_patterns = [
            r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)',
            r'!\[.*?\]\((https?://[^\)]+)\)',
            r'https?://[^\s]+\.(png|jpg|jpeg|webp|gif)',
        ]

        image_found = False
        image_data = None

        for pattern in image_patterns:
            match = re.search(pattern, response)
            if match:
                image_found = True
                if 'base64' in pattern:
                    image_data = match.group(1)
                break

        if not image_found:
            return 0.0, "No image found in response", {"image_found": False}

        # If we have CLIP evaluator and base64 image, evaluate quality
        if self._clip_evaluator and image_data:
            try:
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                reference_prompt = evaluation.get("reference_prompt", item.get("prompt", ""))
                clip_score = self._clip_evaluator.evaluate(image, reference_prompt)

                min_score = evaluation.get("min_score", 0.2)
                if clip_score >= min_score:
                    return 1.0, f"CLIP score {clip_score:.3f} >= {min_score}", {
                        "image_found": True,
                        "clip_score": clip_score
                    }
                else:
                    return 0.5, f"CLIP score {clip_score:.3f} < {min_score}", {
                        "image_found": True,
                        "clip_score": clip_score
                    }
            except Exception as e:
                return 0.7, f"Image found but CLIP eval failed: {e}", {"image_found": True}

        # Image found but no CLIP evaluation available
        return 0.8, "Image generated (no quality eval)", {"image_found": True}

    def _evaluate_image_understanding(
        self,
        item: dict,
        response: str
    ) -> tuple[float, str, dict]:
        """Evaluate image understanding response."""
        evaluation = item.get("evaluation", {})
        expected = evaluation.get("expected_elements", [])
        min_matches = evaluation.get("min_matches", 1)

        score, reasoning = evaluate_vision_response(response, expected, min_matches)
        return score, reasoning, {"expected_elements": expected}

    def _evaluate_mixed_media(
        self,
        item: dict,
        response: str
    ) -> tuple[float, str, dict]:
        """Evaluate mixed media response."""
        evaluation = item.get("evaluation", {})
        eval_type = evaluation.get("type", "contains_any")

        if eval_type == "contains_any":
            expected = evaluation.get("expected", [])
            response_lower = response.lower()
            for exp in expected:
                if exp.lower() in response_lower:
                    return 1.0, f"Found expected: {exp}", {"matched": exp}
            return 0.0, f"None of expected found: {expected}", {}

        return 0.5, "Unknown evaluation type", {}

    def _evaluate_routing(
        self,
        item: dict,
        response: str
    ) -> tuple[float, str, dict]:
        """Evaluate modality routing decision."""
        expected = item.get("expected_behavior", "")
        evaluation = item.get("evaluation", {})
        indicators = evaluation.get("indicators", {})

        response_lower = response.lower()

        # Check expected behavior indicators
        if expected in indicators:
            for indicator in indicators[expected]:
                if indicator.lower() in response_lower:
                    return 1.0, f"Correct behavior: {expected}", {"behavior": expected}

        # Check if wrong behavior
        for behavior, behavior_indicators in indicators.items():
            if behavior != expected:
                for indicator in behavior_indicators:
                    if indicator.lower() in response_lower:
                        return 0.0, f"Wrong behavior: {behavior} instead of {expected}", {
                            "behavior": behavior,
                            "expected": expected
                        }

        return 0.5, "Behavior unclear", {}

    def supports_parallel_items(self) -> bool:
        return True

    def get_item_concurrency(self) -> int:
        return 3  # Image generation can be slow

    def get_item_timeout_seconds(self) -> int:
        return 180  # 3 minutes for image generation
```

### FR-5: Test Data Examples

```json
{
  "metadata": {
    "version": "1.0.0",
    "total_items": 60,
    "categories": {
      "image_generation": 20,
      "image_understanding": 20,
      "mixed_media": 10,
      "modality_routing": 10
    }
  },
  "items": [
    {
      "id": "gen_001",
      "task_type": "image_generation",
      "prompt": "Generate an image of a sunset over the ocean with orange and purple colors",
      "evaluation": {
        "type": "clip_similarity",
        "reference_prompt": "sunset ocean orange purple",
        "min_score": 0.22
      }
    },
    {
      "id": "gen_002",
      "task_type": "image_generation",
      "prompt": "Create a simple icon of a house in a minimalist style",
      "evaluation": {
        "type": "clip_similarity",
        "reference_prompt": "minimalist house icon",
        "min_score": 0.20
      }
    },
    {
      "id": "vision_001",
      "task_type": "image_understanding",
      "image_url": "https://bench-data.janus.rodeo/multimodal/chart_sales.png",
      "query": "Describe the trend shown in this sales chart",
      "evaluation": {
        "type": "key_facts",
        "expected_elements": ["increase", "growth", "rise", "upward"],
        "min_matches": 1
      }
    },
    {
      "id": "vision_002",
      "task_type": "image_understanding",
      "image_url": "https://bench-data.janus.rodeo/multimodal/code_screenshot.png",
      "query": "What programming language is shown in this code screenshot?",
      "evaluation": {
        "type": "key_facts",
        "expected_elements": ["python"],
        "min_matches": 1
      }
    },
    {
      "id": "mixed_001",
      "task_type": "mixed_media",
      "messages": [
        {
          "role": "user",
          "content": [
            {"type": "text", "text": "What animal is in this image?"},
            {"type": "image_url", "image_url": {"url": "https://bench-data.janus.rodeo/multimodal/cat_001.jpg"}}
          ]
        }
      ],
      "evaluation": {
        "type": "contains_any",
        "expected": ["cat", "feline", "kitten"]
      }
    },
    {
      "id": "route_001",
      "task_type": "modality_routing",
      "prompt": "Draw me a picture of a mountain landscape",
      "expected_behavior": "generate_image",
      "evaluation": {
        "type": "action_check",
        "indicators": {
          "generate_image": ["![", "data:image", "here is the image", "generated"],
          "refuse": ["cannot", "unable", "text-based", "don't have"]
        }
      }
    },
    {
      "id": "route_002",
      "task_type": "modality_routing",
      "prompt": "What is the capital of France?",
      "expected_behavior": "text_response",
      "evaluation": {
        "type": "action_check",
        "indicators": {
          "text_response": ["paris", "capital"],
          "generate_image": ["![", "data:image"]
        }
      }
    }
  ]
}
```

## Non-Functional Requirements

### NFR-1: Image Hosting

- Test images hosted at `bench-data.janus.rodeo`
- Images are public and accessible without auth
- Images are small (<1MB) for fast evaluation

### NFR-2: Evaluation Consistency

- CLIP scores are deterministic
- Key fact matching is case-insensitive
- Image detection patterns are comprehensive

### NFR-3: Graceful Degradation

- If CLIP evaluator unavailable, use detection-only scoring
- If image hosting down, skip image understanding items
- Clear error messages for failures

## Acceptance Criteria

- [ ] 60 multimodal items created
- [ ] Image generation evaluation with CLIP working
- [ ] Image understanding evaluation working
- [ ] Mixed media handling tested
- [ ] Modality routing detection working
- [ ] Test images hosted and accessible
- [ ] CLIP evaluator integration
- [ ] Fallback scoring when CLIP unavailable

## Open Questions / Risks

1. **Image quality subjectivity**: CLIP scores may not align with human perception
2. **Test image copyright**: Need to use or create images with proper licensing
3. **Model compatibility**: Not all models support vision inputs
4. **Generation latency**: Image generation can be slow, affecting benchmark time

## Related Specs

- `specs/30_janus_benchmark_integration.md` - Overview (10% modality weight)
- `specs/24_multimodal_routing.md` - Routing for multimodal requests
- `specs/competition/02_description_and_scoring.md` - Modality scoring category

## Files to Create

```
chutes-bench-runner/backend/app/benchmarks/
├── adapters/
│   └── janus_multimodal.py        # Adapter implementation
├── data/
│   └── janus/
│       └── multimodal_items.json  # Test data (60 items)
└── utils/
    └── clip_evaluator.py          # CLIP evaluation helper
```
