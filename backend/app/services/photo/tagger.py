"""
CV Structure Auto-Tagger — MobileNetV3 / ONNX inference.

Structure classes (10):
  check_dam, farm_pond, contour_trench, gully_plug, percolation_tank,
  plantation, afforestation, livelihood_structure, water_body,
  agriculture_field, degraded_barren_land

Condition classes (5):
  functional, damaged, silted, under_construction, unknown

Model: MobileNetV3-Small, quantized to INT8 ONNX for offline rural use.
Fallback: rule-based heuristics using simple image statistics if model is unavailable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# Class labels
STRUCTURE_LABELS = [
    "check_dam", "farm_pond", "contour_trench", "gully_plug",
    "percolation_tank", "plantation", "afforestation", "livelihood_structure",
    "water_body", "agriculture_field", "degraded_barren_land",
]

CONDITION_LABELS = [
    "functional", "damaged", "silted", "under_construction", "unknown",
]

MODEL_VERSION = "mobilenetv3-small-int8-v1.0"
INPUT_SIZE = (224, 224)


@dataclass
class TaggingResult:
    """CV auto-tagger output."""
    structure_type: str
    condition: str
    confidence: float
    caption: str
    model_version: str
    raw_predictions: dict


def _load_onnx_model():
    """Load the ONNX model. Returns None if not available."""
    try:
        import onnxruntime as ort
        import pathlib

        model_path = pathlib.Path(__file__).parent.parent.parent.parent / "ml" / "models" / "structure_classifier.onnx"
        if not model_path.exists():
            return None

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        return ort.InferenceSession(str(model_path), sess_options)
    except Exception as e:
        log.warning(f"ONNX model not available: {e}")
        return None


# Global model instance (loaded once per worker process)
_SESSION = None


def _get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = _load_onnx_model()
    return _SESSION


def _preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Preprocess image bytes to model input tensor."""
    try:
        from PIL import Image

        img = Image.open(__import__("io").BytesIO(image_bytes)).convert("RGB")
        img = img.resize(INPUT_SIZE, Image.BILINEAR)
        arr = np.array(img, dtype=np.float32)
        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr / 255.0 - mean) / std
        return arr.transpose(2, 0, 1)[np.newaxis, :]  # NCHW
    except Exception as e:
        log.warning(f"Image preprocessing failed: {e}")
        return np.zeros((1, 3, 224, 224), dtype=np.float32)


def _softmax(logits: np.ndarray) -> np.ndarray:
    e = np.exp(logits - logits.max())
    return e / e.sum()


def _onnx_inference(image_bytes: bytes) -> Optional[tuple[np.ndarray, np.ndarray]]:
    """Run ONNX inference. Returns (structure_probs, condition_probs) or None."""
    sess = _get_session()
    if sess is None:
        return None

    try:
        inp = _preprocess_image(image_bytes)
        outputs = sess.run(None, {"input": inp})
        structure_probs = _softmax(outputs[0][0])
        condition_probs = _softmax(outputs[1][0]) if len(outputs) > 1 else None
        return structure_probs, condition_probs
    except Exception as e:
        log.warning(f"ONNX inference failed: {e}")
        return None


def _heuristic_tag(image_bytes: bytes) -> tuple[str, str, float]:
    """
    Rule-based fallback tagger using color/texture statistics.
    Used when the ONNX model is unavailable (e.g., first-run without model file).
    Returns (structure_type, condition, confidence).
    """
    try:
        from PIL import Image

        img = Image.open(__import__("io").BytesIO(image_bytes)).convert("RGB")
        img_resized = img.resize((64, 64))
        arr = np.array(img_resized, dtype=np.float32)

        # Simple color-based heuristics
        r_mean, g_mean, b_mean = arr[:, :, 0].mean(), arr[:, :, 1].mean(), arr[:, :, 2].mean()
        blue_dominance = b_mean / (r_mean + g_mean + b_mean + 1e-6)
        green_dominance = g_mean / (r_mean + g_mean + b_mean + 1e-6)

        if blue_dominance > 0.38:
            return "water_body", "functional", 0.55
        elif green_dominance > 0.38:
            return "plantation", "functional", 0.50
        else:
            return "check_dam", "unknown", 0.40
    except Exception:
        return "degraded_barren_land", "unknown", 0.30


def _build_caption(structure: str, condition: str, confidence: float) -> str:
    """Auto-generate a descriptive caption for the photo."""
    cond_phrases = {
        "functional": "in functional condition",
        "damaged": "showing signs of damage",
        "silted": "heavily silted — reduced capacity",
        "under_construction": "under construction",
        "unknown": "condition undetermined",
    }
    structure_display = structure.replace("_", " ").title()
    cond_display = cond_phrases.get(condition, condition)
    return (
        f"Auto-tagged: {structure_display} — {cond_display}. "
        f"Classifier confidence: {confidence:.0%}. "
        f"Requires officer review."
    )


def tag_structure(image_bytes: bytes) -> TaggingResult:
    """
    Run CV auto-tagger on a DRISHTI photo.
    Returns a TaggingResult with structure type, condition, confidence, and caption.
    """
    result = _onnx_inference(image_bytes)

    if result is not None:
        structure_probs, condition_probs = result
        struct_idx = int(np.argmax(structure_probs))
        structure_type = STRUCTURE_LABELS[struct_idx]
        confidence = float(structure_probs[struct_idx])

        if condition_probs is not None:
            cond_idx = int(np.argmax(condition_probs))
            condition = CONDITION_LABELS[cond_idx]
        else:
            condition = "unknown"

        raw_preds = {
            "structure": {STRUCTURE_LABELS[i]: float(structure_probs[i]) for i in range(len(STRUCTURE_LABELS))},
        }
        if condition_probs is not None:
            raw_preds["condition"] = {CONDITION_LABELS[i]: float(condition_probs[i]) for i in range(len(CONDITION_LABELS))}
    else:
        # Fallback
        structure_type, condition, confidence = _heuristic_tag(image_bytes)
        raw_preds = {"structure": {structure_type: confidence}, "fallback": True}

    return TaggingResult(
        structure_type=structure_type,
        condition=condition,
        confidence=confidence,
        caption=_build_caption(structure_type, condition, confidence),
        model_version=MODEL_VERSION if _get_session() else "heuristic-v1.0",
        raw_predictions=raw_preds,
    )
