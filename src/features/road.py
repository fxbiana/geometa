"""Deterministic road-region measurements and visual observations."""

from dataclasses import dataclass
from typing import List, Tuple

from PIL import Image

try:  # Support both ``python -m src.main`` and legacy direct imports.
    from ..contracts import (
        ImageRegion,
        Measurement,
        Observation,
        ObservationState,
        RegionType,
    )
except ImportError:  # pragma: no cover - compatibility for old scripts
    from contracts import ImageRegion, Measurement, Observation, ObservationState, RegionType


@dataclass(frozen=True)
class RoadAnalysis:
    measurements: Tuple[Measurement, ...]
    observations: Tuple[Observation, ...]

    def as_dict(self) -> dict:
        """Compatibility representation for the prototype CLI."""
        return {
            "features": {item.feature: item.value for item in self.measurements},
            "observations": [item.observation_type for item in self.observations],
            "clues": [item.observation_type for item in self.observations if item.state == ObservationState.POSITIVE],
        }


def analyze_road(
    image: Image.Image,
    *,
    source_id: str = "source",
    analysis_id: str = "analysis",
    detector_version: str = "prototype-1",
) -> RoadAnalysis:
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("image must have positive dimensions")
    region_box = (0, 2 * height // 3, width, height)
    road_region = image.crop(region_box)
    pixels = list(road_region.convert("RGB").getdata())
    total_pixels = len(pixels)
    if not total_pixels:
        raise ValueError("road region must contain pixels")

    counts = {
        "gray_percentage": 0,
        "dark_percentage": 0,
        "bright_percentage": 0,
        "white_percentage": 0,
        "yellow_percentage": 0,
    }
    total_brightness = 0.0
    for r, g, b in pixels:
        brightness = (r + g + b) / 3
        total_brightness += brightness
        if max(r, g, b) - min(r, g, b) < 20:
            counts["gray_percentage"] += 1
        if brightness < 70:
            counts["dark_percentage"] += 1
        if brightness > 180:
            counts["bright_percentage"] += 1
        if r > 180 and g > 180 and b > 180:
            counts["white_percentage"] += 1
        if r > 150 and g > 120 and b < 100:
            counts["yellow_percentage"] += 1

    region = ImageRegion(source_id, RegionType.BOTTOM_THIRD, region_box)
    measurements = [
        Measurement(
            id=f"{analysis_id}:measurement:average_brightness",
            analysis_id=analysis_id,
            source_id=source_id,
            region=region,
            feature="average_brightness",
            value=total_brightness / total_pixels,
            unit="pixel_intensity_0_255",
            detector_version=detector_version,
        )
    ]
    for feature, count in counts.items():
        measurements.append(
            Measurement(
                id=f"{analysis_id}:measurement:{feature}",
                analysis_id=analysis_id,
                source_id=source_id,
                region=region,
                feature=feature,
                value=count / total_pixels,
                unit="ratio_0_1",
                detector_version=detector_version,
            )
        )
    by_feature = {item.feature: item for item in measurements}
    observations: List[Observation] = []

    def add(feature: str, observation_type: str, state: ObservationState = ObservationState.POSITIVE) -> None:
        observations.append(
            Observation(
                id=f"{analysis_id}:observation:{observation_type}",
                analysis_id=analysis_id,
                source_id=source_id,
                region=region,
                observation_type=observation_type,
                value=True,
                confidence=0.8,
                state=state,
                supporting_measurement_ids=(by_feature[feature].id,),
                detector_version=detector_version,
            )
        )

    if by_feature["gray_percentage"].value > 0.60:
        add("gray_percentage", "road_region_predominantly_gray")
    if by_feature["yellow_percentage"].value > 0.03:
        add("yellow_percentage", "possible_yellow_marking", ObservationState.AMBIGUOUS)
    if by_feature["dark_percentage"].value > 0.20:
        add("dark_percentage", "high_dark_pixel_ratio")
    if by_feature["white_percentage"].value > 0.20:
        add("white_percentage", "large_white_pixel_ratio")
    if not observations:
        add("average_brightness", "no_strong_road_color_characteristics", ObservationState.ABSENT)
    return RoadAnalysis(tuple(measurements), tuple(observations))
