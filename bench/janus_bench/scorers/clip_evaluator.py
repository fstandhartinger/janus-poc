"""CLIP evaluator for image-text similarity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

torch: Any
PILImageModule: Any
CLIPModel: Any
CLIPProcessor: Any

try:
    import torch as torch_module
    from PIL import Image as PILImageModule
    from transformers import CLIPModel as CLIPModelType, CLIPProcessor as CLIPProcessorType

    torch = torch_module
    CLIPModel = CLIPModelType
    CLIPProcessor = CLIPProcessorType
except Exception:  # pragma: no cover - optional dependency
    torch = None
    PILImageModule = None
    CLIPModel = None
    CLIPProcessor = None

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL.Image import Image as PilImage


class CLIPEvaluator:
    """Evaluate image-text similarity using CLIP."""

    def __init__(self) -> None:
        if (
            torch is None
            or PILImageModule is None
            or CLIPModel is None
            or CLIPProcessor is None
        ):
            raise ImportError("CLIP dependencies not available")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    def evaluate(self, image: "PilImage", text: str) -> float:
        inputs = self.processor(
            text=[text],
            images=image,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            similarity = logits_per_image.softmax(dim=1)[0][0].item()
        return float(similarity)
