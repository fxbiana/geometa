"""Wave 2 evaluation harness (eval-only; no detector logic).

Reports:
  * object-observation precision (predicted types vs expected)
  * top-country accuracy (when countries are predicted)
  * failing-closed ``country without claim`` checks

Unit tests inject observation lists and a claim catalog for purity.
Integration against live detectors / ``POST /v1/analyses`` is optional and
skipable when ``src.features.objects`` / ``src.features.script`` are absent.

This module must not import or modify production detector implementations, and
it must not hard-code geography into detectors — country justification always
flows through ``claims_for_observation`` / an injected claim lookup.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

# Object-family observation types used for the Wave 2 precision metric.
# Road / script types may appear in the same pack but are excluded from
# ``object_precision`` unless listed here.
OBJECT_OBSERVATION_TYPES = frozenset(
    {
        "bollard_present",
        "utility_pole_present",
        "guardrail_present",
        "traffic_cone_present",
        "street_furniture_present",
    }
)

ClaimLookup = Callable[[str], Sequence[Any]]


@dataclass(frozen=True)
class Wave2Example:
    example_id: str
    image_path: Path
    family: str
    expected_observations: Tuple[str, ...]
    expected_countries: Tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class Wave2CaseResult:
    example_id: str
    predicted_observations: Tuple[str, ...]
    expected_observations: Tuple[str, ...]
    predicted_countries: Tuple[str, ...]
    expected_countries: Tuple[str, ...]
    top_country: Optional[str]
    top_country_hit: Optional[bool]
    unjustified_countries: Tuple[str, ...]
    object_true_positives: int
    object_false_positives: int
    object_false_negatives: int


@dataclass(frozen=True)
class Wave2Report:
    pack_version: str
    cases: Tuple[Wave2CaseResult, ...]
    object_precision: Optional[float]
    object_recall: Optional[float]
    top_country_accuracy: Optional[float]
    country_without_claim_violations: Tuple[str, ...]
    printed_summary: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack_version": self.pack_version,
            "object_precision": self.object_precision,
            "object_recall": self.object_recall,
            "top_country_accuracy": self.top_country_accuracy,
            "country_without_claim_violations": list(self.country_without_claim_violations),
            "cases": [
                {
                    "example_id": case.example_id,
                    "predicted_observations": list(case.predicted_observations),
                    "expected_observations": list(case.expected_observations),
                    "predicted_countries": list(case.predicted_countries),
                    "expected_countries": list(case.expected_countries),
                    "top_country": case.top_country,
                    "top_country_hit": case.top_country_hit,
                    "unjustified_countries": list(case.unjustified_countries),
                    "object_true_positives": case.object_true_positives,
                    "object_false_positives": case.object_false_positives,
                    "object_false_negatives": case.object_false_negatives,
                }
                for case in self.cases
            ],
            "summary": self.printed_summary,
        }


def default_fixture_pack() -> Path:
    return Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "wave2"


def load_wave2_pack(pack_dir: str | Path | None = None) -> Tuple[str, Tuple[Wave2Example, ...]]:
    """Load a Wave 2 fixture pack (manifest + stills + expected country/obs sets)."""
    root = Path(pack_dir) if pack_dir is not None else default_fixture_pack()
    manifest_path = root / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    pack_version = str(payload.get("pack_version", "unknown"))
    examples: list[Wave2Example] = []
    for row in payload.get("examples", []):
        example_id = str(row["id"])
        image_path = (root / row["image"]).resolve()
        expected_path = root / "expected" / f"{example_id}.json"
        expected = json.loads(expected_path.read_text(encoding="utf-8")) if expected_path.is_file() else row
        observations = tuple(expected.get("expected_observations", row.get("expected_observations", [])))
        countries = tuple(expected.get("expected_countries", row.get("expected_countries", [])))
        examples.append(
            Wave2Example(
                example_id=example_id,
                image_path=image_path,
                family=str(row.get("family", "unknown")),
                expected_observations=observations,
                expected_countries=countries,
                notes=str(row.get("notes", "")),
            )
        )
    if not examples:
        raise ValueError("wave2 fixture pack contains no examples")
    return pack_version, tuple(examples)


def objects_detector_available() -> bool:
    """True when the Wave 2 objects feature module is importable."""
    return importlib.util.find_spec("src.features.objects") is not None


def script_detector_available() -> bool:
    """True when the Wave 2 script feature module is importable."""
    return importlib.util.find_spec("src.features.script") is not None


def wave2_detectors_available() -> bool:
    return objects_detector_available() and script_detector_available()


def _observation_types(observations: Sequence[Any]) -> Tuple[str, ...]:
    types: list[str] = []
    for item in observations:
        if isinstance(item, str):
            types.append(item)
        else:
            types.append(str(getattr(item, "observation_type")))
    return tuple(types)


def _approved_claim_countries(claim: Any) -> Tuple[str, ...]:
    production_ready = bool(getattr(claim, "production_ready", False))
    review_status = str(getattr(claim, "review_status", ""))
    if not production_ready or review_status != "approved":
        return ()
    supports = tuple(getattr(claim, "supports", ()) or ())
    weakens = tuple(getattr(claim, "weakens", ()) or ())
    return supports + weakens


def countries_justified_by_claims(
    observations: Sequence[Any],
    claim_lookup: ClaimLookup,
) -> frozenset[str]:
    """Return countries backed by an approved claim matching an observation."""
    justified: set[str] = set()
    for observation_type in _observation_types(observations):
        for claim in claim_lookup(observation_type):
            justified.update(_approved_claim_countries(claim))
    return frozenset(justified)


def unjustified_countries(
    predicted_countries: Sequence[str],
    observations: Sequence[Any],
    claim_lookup: ClaimLookup,
) -> Tuple[str, ...]:
    justified = countries_justified_by_claims(observations, claim_lookup)
    return tuple(sorted(set(predicted_countries) - justified))


def assert_countries_have_claims(
    predicted_countries: Sequence[str],
    observations: Sequence[Any],
    claim_lookup: ClaimLookup,
) -> None:
    """Fail closed: every predicted country must be justified by an approved claim."""
    bad = unjustified_countries(predicted_countries, observations, claim_lookup)
    if bad:
        raise AssertionError(
            "country without claim: "
            + ", ".join(bad)
            + " (every country must match an approved claim for an observation)"
        )


def object_precision_counts(
    predicted: Sequence[str],
    expected: Sequence[str],
    *,
    object_types: frozenset[str] = OBJECT_OBSERVATION_TYPES,
) -> Tuple[int, int, int]:
    """Return (true_positives, false_positives, false_negatives) for object types."""
    predicted_objects = {item for item in predicted if item in object_types}
    expected_objects = {item for item in expected if item in object_types}
    tp = len(predicted_objects & expected_objects)
    fp = len(predicted_objects - expected_objects)
    fn = len(expected_objects - predicted_objects)
    return tp, fp, fn


def precision_from_counts(tp: int, fp: int) -> Optional[float]:
    denom = tp + fp
    if denom == 0:
        return None
    return tp / denom


def recall_from_counts(tp: int, fn: int) -> Optional[float]:
    denom = tp + fn
    if denom == 0:
        return None
    return tp / denom


def default_claim_lookup(observation_type: str) -> Sequence[Any]:
    """Load approved claims from the production catalog (read-only)."""
    from .claims import claims_for_observation

    return claims_for_observation(observation_type)


def evaluate_case(
    example: Wave2Example,
    *,
    predicted_observations: Sequence[Any],
    predicted_countries: Sequence[str],
    claim_lookup: ClaimLookup | None = None,
) -> Wave2CaseResult:
    """Score one fixture case from injected (or live) predictions."""
    lookup = claim_lookup or default_claim_lookup
    predicted_types = _observation_types(predicted_observations)
    countries = tuple(predicted_countries)
    bad = unjustified_countries(countries, predicted_types, lookup)
    top = countries[0] if countries else None
    if top is None:
        hit: Optional[bool] = None if example.expected_countries else True
    else:
        hit = top in example.expected_countries
    tp, fp, fn = object_precision_counts(predicted_types, example.expected_observations)
    return Wave2CaseResult(
        example_id=example.example_id,
        predicted_observations=predicted_types,
        expected_observations=example.expected_observations,
        predicted_countries=countries,
        expected_countries=example.expected_countries,
        top_country=top,
        top_country_hit=hit,
        unjustified_countries=bad,
        object_true_positives=tp,
        object_false_positives=fp,
        object_false_negatives=fn,
    )


def aggregate_report(
    pack_version: str,
    cases: Sequence[Wave2CaseResult],
) -> Wave2Report:
    tp = sum(case.object_true_positives for case in cases)
    fp = sum(case.object_false_positives for case in cases)
    fn = sum(case.object_false_negatives for case in cases)
    object_precision = precision_from_counts(tp, fp)
    object_recall = recall_from_counts(tp, fn)

    ranked = [case for case in cases if case.top_country_hit is not None]
    if ranked:
        top_country_accuracy = sum(1 for case in ranked if case.top_country_hit) / len(ranked)
    else:
        top_country_accuracy = None

    violations = tuple(
        f"{case.example_id}:{country}"
        for case in cases
        for country in case.unjustified_countries
    )
    summary = format_report_summary(
        object_precision=object_precision,
        object_recall=object_recall,
        top_country_accuracy=top_country_accuracy,
        violations=violations,
        case_count=len(cases),
    )
    return Wave2Report(
        pack_version=pack_version,
        cases=tuple(cases),
        object_precision=object_precision,
        object_recall=object_recall,
        top_country_accuracy=top_country_accuracy,
        country_without_claim_violations=violations,
        printed_summary=summary,
    )


def format_report_summary(
    *,
    object_precision: Optional[float],
    object_recall: Optional[float],
    top_country_accuracy: Optional[float],
    violations: Sequence[str],
    case_count: int,
) -> str:
    def pct(value: Optional[float]) -> str:
        return "n/a" if value is None else f"{value:.3f}"

    lines = [
        f"wave2_eval cases={case_count}",
        f"precision for objects: {pct(object_precision)}",
        f"object recall: {pct(object_recall)}",
        f"top-country accuracy: {pct(top_country_accuracy)}",
        (
            "country without claim: none"
            if not violations
            else "country without claim: " + ", ".join(violations)
        ),
    ]
    return "\n".join(lines)


def evaluate_injected(
    pack_version: str,
    examples: Sequence[Wave2Example],
    predictions: Mapping[str, Mapping[str, Any]],
    *,
    claim_lookup: ClaimLookup | None = None,
) -> Wave2Report:
    """Evaluate a pack using injected observation lists and country predictions.

    ``predictions[example_id]`` may contain:
      * ``observations``: sequence of observation type strings or Observation
      * ``countries``: ordered country codes (rank order; index 0 is top)
    """
    cases = []
    for example in examples:
        payload = predictions.get(example.example_id, {})
        cases.append(
            evaluate_case(
                example,
                predicted_observations=payload.get("observations", ()),
                predicted_countries=payload.get("countries", ()),
                claim_lookup=claim_lookup,
            )
        )
    return aggregate_report(pack_version, cases)


def countries_from_analysis_result(result: Any) -> Tuple[str, ...]:
    """Extract ranked country candidates from an AnalysisResult-like object."""
    candidates = getattr(result, "candidates", ()) or ()
    ordered = sorted(
        (c for c in candidates if getattr(c, "eligible", True)),
        key=lambda c: getattr(c, "rank", 10**9),
    )
    return tuple(str(c.candidate_id) for c in ordered)


def evaluate_via_pipeline(
    examples: Sequence[Wave2Example],
    *,
    pack_version: str,
    claim_lookup: ClaimLookup | None = None,
    claim_version: str | None = None,
) -> Wave2Report:
    """Run ``analyze_source`` on each still and join labels only for metrics."""
    from .claims import CLAIM_CATALOG_VERSION
    from .pipeline import run_analysis

    version = claim_version or CLAIM_CATALOG_VERSION
    cases = []
    for example in examples:
        result = run_analysis(example.image_path, claim_version=version)
        cases.append(
            evaluate_case(
                example,
                predicted_observations=result.observations,
                predicted_countries=countries_from_analysis_result(result),
                claim_lookup=claim_lookup,
            )
        )
    return aggregate_report(pack_version, cases)


def print_report(report: Wave2Report) -> None:
    print(report.printed_summary)


def examples_for_pipeline(examples: Sequence[Wave2Example]) -> Tuple[Wave2Example, ...]:
    """Select stills the current pipeline can score without Wave 2 detectors.

    Object/script families require ``src.features.objects`` / ``script``; until
    those land, pipeline mode keeps road fixtures only so object FN noise does
    not dominate the printed precision/recall lines.
    """
    if wave2_detectors_available():
        return tuple(examples)
    return tuple(example for example in examples if example.family == "road")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pack",
        type=Path,
        default=None,
        help="Path to tests/fixtures/wave2 (default: repo fixture pack)",
    )
    parser.add_argument(
        "--mode",
        choices=("pipeline",),
        default="pipeline",
        help="Live evaluation mode (injected mode is test-only)",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pack_version, examples = load_wave2_pack(args.pack)
    if args.mode == "pipeline":
        selected = examples_for_pipeline(examples)
        if len(selected) < len(examples):
            skipped = len(examples) - len(selected)
            print(
                f"wave2_eval: skipping {skipped} object/script stills "
                "(detectors unavailable; use injected pytest path)"
            )
        report = evaluate_via_pipeline(selected, pack_version=pack_version)
    else:  # pragma: no cover
        raise SystemExit(f"unsupported mode: {args.mode}")
    print_report(report)
    rendered = json.dumps(report.as_dict(), indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
