"""Generate the deterministic 100-image M1-FE2 pilot manifest.

The input is the approved external subset manifest.  Only metadata is written;
the external image files are never copied or changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List


def _validated_entries(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    root = Path(str(payload["dataset"]["local_root"])).resolve()
    paths = set()
    hashes = set()
    ids = set()
    for entry in payload["entries"]:
        relative = Path(str(entry["relative_path"]))
        if relative.is_absolute():
            raise ValueError("approved relative_path must not be absolute")
        resolved = (root / relative).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("approved path escapes dataset.local_root") from exc
        path_key = str(resolved).casefold()
        if path_key in paths:
            raise ValueError("approved image paths must be unique")
        paths.add(path_key)
        entry_id = entry.get("id", entry.get("example_id"))
        if entry_id is not None:
            if str(entry_id) in ids:
                raise ValueError("approved entry IDs must be unique")
            ids.add(str(entry_id))
        declared = str(entry.get("content_hash", entry.get("sha256", "")))
        if not declared or len(declared) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in declared
        ):
            raise ValueError("approved entries require a SHA-256 content hash")
        if declared.casefold() in hashes:
            raise ValueError("approved content hashes must be unique")
        hashes.add(declared.casefold())
        if not resolved.is_file():
            raise ValueError("approved image does not exist: {0}".format(resolved))
        actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if actual.casefold() != declared.casefold():
            raise ValueError("approved content hash mismatch: {0}".format(resolved))
    return payload["entries"]


def select_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_label: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        by_label.setdefault(str(entry["label"]), []).append(entry)
    selected: List[Dict[str, Any]] = []
    for label in sorted(by_label):
        selected.extend(sorted(by_label[label], key=lambda item: item["selection_key"])[:3])
    selected_ids = {item["relative_path"] for item in selected}
    remainder = [item for item in entries if item["relative_path"] not in selected_ids]
    selected.extend(sorted(remainder, key=lambda item: item["selection_key"])[: 100 - len(selected)])
    return sorted(selected, key=lambda item: (str(item["label"]), item["selection_key"]))


def generate(source: Path, output: Path, dataset_root: str = "images/compressed_dataset") -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    entries = select_entries(_validated_entries(payload))
    if len(entries) != 100:
        raise ValueError("approved subset did not provide 100 unique pilot entries")
    result = {
        "manifest_schema_version": "m1-fe2-pilot-1",
        "dataset": {
            "name": payload["dataset"]["name"],
            "local_root": os.path.relpath(
                Path(dataset_root).resolve(), output.parent.resolve()
            ),
            "role": "external exploratory corpus; not official benchmark",
        },
        "selection_policy": {
            "size": 100,
            "per_label_floor": 3,
            "ordering": "label ascending, then approved selection_key ascending",
            "source_manifest": str(source),
            "images_copied": False,
        },
        "entries": [
            {
                "id": "pilot-{0:03d}".format(index),
                "relative_path": item["relative_path"],
                "country": item["label"],
                "content_hash": item["content_hash"],
                "width": item["width"],
                "height": item["height"],
                "format": item["format"],
            }
            for index, item in enumerate(entries, 1)
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("approved_manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dataset-root", default="images/compressed_dataset")
    args = parser.parse_args()
    generate(args.approved_manifest, args.output, args.dataset_root)


if __name__ == "__main__":
    main()
