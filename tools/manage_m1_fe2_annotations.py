"""Generate, validate, or (after human review) freeze M1-FE2 annotations.

This tool handles annotation records only. It never extracts detector outputs,
joins country labels, or evaluates prediction accuracy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

# Allow direct execution from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.annotations import (
    AnnotationRecord,
    AnnotationValidationError,
    ImageQuality,
    InterfaceContamination,
    freeze_annotations,
    load_annotations,
    write_annotations,
)


def generate_template(manifest: Path, output: Path) -> None:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    records: List[AnnotationRecord] = []
    for entry in payload["entries"]:
        records.append(
            AnnotationRecord(
                annotation_id="annotation-{0}".format(entry["id"]),
                image_id=entry["id"],
                image_path=entry["relative_path"],
                content_hash=entry["content_hash"],
                annotator=None,
                image_quality=ImageQuality.UNKNOWN,
                interface_contamination=InterfaceContamination.UNKNOWN,
                review_status="needs_review",
                schema_version="m1-fe2-3",
            )
        )
    if len(records) != 100:
        raise ValueError("M1-FE2 template must contain exactly 100 records")
    write_annotations(str(output), tuple(records))


def validate(path: Path) -> Tuple[AnnotationRecord, ...]:
    records = load_annotations(str(path))
    if len(records) != 100:
        raise AnnotationValidationError("M1-FE2 annotations must contain 100 records")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("manifest", type=Path)
    generate.add_argument("output", type=Path)
    check = subparsers.add_parser("validate")
    check.add_argument("annotations", type=Path)
    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("annotations", type=Path)
    freeze.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        generate_template(args.manifest, args.output)
    elif args.command == "validate":
        records = validate(args.annotations)
        print("valid annotation records: {0}".format(len(records)))
    else:
        records = validate(args.annotations)
        write_annotations(str(args.output), freeze_annotations(records))


if __name__ == "__main__":
    main()
