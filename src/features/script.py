"""Sign-crop writing-system observations (no country codes).

Reads text from a caller-provided sign crop via PaddleOCR when available,
then classifies the writing system with a deterministic Unicode-range
heuristic.  OCR is pluggable so CI can run without GPU, network, or models.
"""

from __future__ import annotations

from collections import Counter
from typing import Callable, Optional, Protocol, Tuple, Union

from PIL import Image

try:  # Support both ``python -m src.main`` and package imports.
    from ..contracts import (
        ImageRegion,
        Observation,
        ObservationState,
        RegionType,
    )
except ImportError:  # pragma: no cover - compatibility for old scripts
    from contracts import ImageRegion, Observation, ObservationState, RegionType


SCRIPT_OBSERVATION_TYPE = "script_writing_system"
SCRIPT_DETECTOR_VERSION = "script-1"
KNOWN_WRITING_SYSTEMS = frozenset({"hangul", "thai", "cyrillic", "kana", "latin"})
_DOMINANCE_THRESHOLD = 0.70


class OcrBackend(Protocol):
    """Thin OCR surface: image in, plain text out."""

    def extract_text(self, image: Image.Image) -> str: ...


OcrBackendFn = Callable[[Image.Image], str]


def classify_writing_system(text: str) -> Tuple[str, ObservationState, float]:
    """Map OCR text to one writing system using Unicode ranges.

    Returns ``(value, state, confidence)``.  Value is one of the known
    systems, or ``\"unknown\"`` when empty / mixed / unrecognized.  Never
    emits a country code.
    """
    counts: Counter[str] = Counter()
    for char in text:
        label = _script_for_char(char)
        if label is not None:
            counts[label] += 1

    total = sum(counts.values())
    if total == 0:
        return "unknown", ObservationState.AMBIGUOUS, 0.0

    if len(counts) == 1:
        system, n = next(iter(counts.items()))
        confidence = min(0.99, 0.55 + 0.05 * min(n, 8))
        return system, ObservationState.POSITIVE, confidence

    dominant, dominant_n = counts.most_common(1)[0]
    share = dominant_n / total
    if share >= _DOMINANCE_THRESHOLD:
        return dominant, ObservationState.POSITIVE, round(0.5 + 0.4 * share, 3)

    # Mixed scripts without a clear majority.
    return "unknown", ObservationState.AMBIGUOUS, round(0.35 * share, 3)


def analyze_script(
    image_or_crop: Image.Image,
    *,
    source_id: str,
    analysis_id: str,
    ocr_backend: Optional[Union[OcrBackend, OcrBackendFn]] = None,
    ocr_text: Optional[str] = None,
    detector_version: str = SCRIPT_DETECTOR_VERSION,
    region_type: RegionType = RegionType.FULL_IMAGE,
) -> Observation:
    """Classify writing system on a sign crop and emit one Observation.

    Assumes the caller already cropped a sign; does not run object detection.
    When ``ocr_text`` is set it is used directly (tests / injected OCR).
    Otherwise ``ocr_backend`` runs, defaulting to PaddleOCR with a safe
    empty-text fallback when the package or models are unavailable.
    """
    if image_or_crop.size[0] <= 0 or image_or_crop.size[1] <= 0:
        raise ValueError("image must have positive dimensions")

    if ocr_text is None:
        backend = ocr_backend if ocr_backend is not None else default_ocr_backend()
        text = _run_backend(backend, image_or_crop)
    else:
        text = ocr_text

    value, state, confidence = classify_writing_system(text)
    width, height = image_or_crop.size
    coordinates = (0, 0, width, height) if region_type is RegionType.BOUNDING_BOX else None
    region = ImageRegion(source_id, region_type, coordinates)

    return Observation(
        id=f"{analysis_id}:observation:{SCRIPT_OBSERVATION_TYPE}",
        analysis_id=analysis_id,
        source_id=source_id,
        region=region,
        observation_type=SCRIPT_OBSERVATION_TYPE,
        value=value,
        confidence=confidence,
        state=state,
        supporting_measurement_ids=(),
        detector_version=detector_version,
    )


def default_ocr_backend() -> OcrBackend:
    """Prefer PaddleOCR; fall back to a no-op backend for offline CI."""
    paddle = PaddleOcrBackend.try_create()
    if paddle is not None:
        return paddle
    return NullOcrBackend()


class NullOcrBackend:
    """Deterministic stand-in when OCR models cannot be loaded."""

    def extract_text(self, image: Image.Image) -> str:
        return ""


class PaddleOcrBackend:
    """Thin wrapper around PaddleOCR. Construction fails soft via try_create."""

    def __init__(self, engine: object) -> None:
        self._engine = engine

    @classmethod
    def try_create(cls) -> Optional["PaddleOcrBackend"]:
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except Exception:
            return None
        try:
            # CPU-friendly defaults; lang choice does not affect Unicode
            # classification of whatever characters are returned.
            engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        except Exception:
            return None
        return cls(engine)

    def extract_text(self, image: Image.Image) -> str:
        import numpy as np

        rgb = image.convert("RGB")
        array = np.asarray(rgb)
        try:
            result = self._engine.ocr(array, cls=True)
        except TypeError:
            result = self._engine.ocr(array)
        except Exception:
            return ""
        return _flatten_paddle_result(result)


def _run_backend(backend: Union[OcrBackend, OcrBackendFn], image: Image.Image) -> str:
    extract = getattr(backend, "extract_text", None)
    if extract is not None and callable(extract):
        return str(extract(image) or "")
    if callable(backend):
        return str(backend(image) or "")
    raise TypeError("ocr_backend must be callable or expose extract_text()")


def _flatten_paddle_result(result: object) -> str:
    """Normalize PaddleOCR result structures into a single text string."""
    if not result:
        return ""
    pieces: list[str] = []
    # Typical shape: list per image → list of [box, (text, conf)]
    for block in result:
        if not block:
            continue
        if isinstance(block, dict):
            # Newer dict-style outputs
            texts = block.get("rec_texts") or block.get("text")
            if isinstance(texts, (list, tuple)):
                pieces.extend(str(t) for t in texts if t)
            elif texts:
                pieces.append(str(texts))
            continue
        for line in block:
            if not line:
                continue
            if isinstance(line, (list, tuple)) and len(line) >= 2:
                payload = line[1]
                if isinstance(payload, (list, tuple)) and payload:
                    pieces.append(str(payload[0]))
                elif isinstance(payload, str):
                    pieces.append(payload)
            elif isinstance(line, str):
                pieces.append(line)
    return " ".join(pieces).strip()


def _script_for_char(char: str) -> Optional[str]:
    if not char or char.isspace() or not char.isalpha():
        return None
    code = ord(char)

    # Hangul jamo + compatibility jamo + syllables
    if (
        0x1100 <= code <= 0x11FF
        or 0x3130 <= code <= 0x318F
        or 0xA960 <= code <= 0xA97F
        or 0xAC00 <= code <= 0xD7A3
        or 0xD7B0 <= code <= 0xD7FF
    ):
        return "hangul"

    # Thai
    if 0x0E00 <= code <= 0x0E7F:
        return "thai"

    # Cyrillic (+ supplements commonly seen on signs)
    if 0x0400 <= code <= 0x04FF or 0x0500 <= code <= 0x052F:
        return "cyrillic"

    # Hiragana + Katakana (+ phonetic extensions)
    if (
        0x3040 <= code <= 0x309F
        or 0x30A0 <= code <= 0x30FF
        or 0x31F0 <= code <= 0x31FF
        or 0xFF66 <= code <= 0xFF9D
    ):
        return "kana"

    # Basic Latin letters + Latin-1 / Extended-A/B
    if (
        0x0041 <= code <= 0x005A
        or 0x0061 <= code <= 0x007A
        or 0x00C0 <= code <= 0x024F
        or 0x1E00 <= code <= 0x1EFF
    ):
        return "latin"

    return None
