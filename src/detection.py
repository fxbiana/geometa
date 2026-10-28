"""Detector façade stubs.

Visual detectors live under ``src/features/``.  This module re-exports the
object detector entry point and keeps legacy stub names for older callers.
Place inference is not performed here.
"""

from typing import Any, Optional


def detect_architecture():
    return []


def detect_signage():
    return []


def detect_vehicle():
    return []


def detect_terrain():
    return []


def detect_language():
    return []


def detect_coverage():
    return []


def detect_objects(image=None, **kwargs: Any):
    """Run YOLO-World street-furniture detection; return ``ObjectAnalysis``.

    When ``image`` is omitted, returns an empty ``ObjectAnalysis`` so callers
    and the API never crash on a missing frame.
    """
    from .features.objects import ObjectAnalysis, detect_objects as _detect_objects

    if image is None:
        return ObjectAnalysis(measurements=(), observations=())
    return _detect_objects(image, **kwargs)


def meta_detection(_image: Optional[Any] = None):
    # No detector is implemented behind this legacy boundary yet.  Returning
    # an empty result is safer than manufacturing unsupported evidence.
    del _image
    return []
