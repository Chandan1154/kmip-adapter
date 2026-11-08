#!/usr/bin/env python3
"""
Audit `supportedVersions` Set in every KmipEnumeration class against the scraped
KMIP spec coverage in `docs/kmip-spec/kmip-all-versions-data.json`.

Convention (per `docs/kmip-pending-implementation.md` §8): the project folds spec
versions 1.3/1.4 into V1_2 and 2.0/2.1 into V2_1. UnknownVersion is always present.

Usage:
    python3 scripts/audit_supported_versions.py              # text report
    python3 scripts/audit_supported_versions.py --json       # machine-readable
    python3 scripts/audit_supported_versions.py --fail-on-drift   # exit 1 if any drift
"""

from __future__ import annotations
import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
JSON_PATH = REPO / "docs/kmip-spec/kmip-all-versions-data.json"
ENUM_DIRS = [
    REPO / "src/main/java/org/purplebean/kmip/model/core/enumeration",
    REPO / "src/main/java/org/purplebean/kmip/model/v1_2/enumeration",
    REPO / "src/main/java/org/purplebean/kmip/model/v2_1/enumeration",
    REPO / "src/main/java/org/purplebean/kmip/model/v3_0/enumeration",
]

SPEC_TO_JAVA = {
    "1.2": "V1_2",
    "1.3": "V1_2",   # folded
    "1.4": "V1_2",   # folded
    "2.0": "V2_1",   # folded
    "2.1": "V2_1",
    "3.0": "V3_0",
}

SV_RE = re.compile(
    r"private\s+static\s+final\s+Set<KmipSpec>\s+supportedVersions\s*=\s*Set\.of\(([^)]+)\)"
)
KMIPSPEC_RE = re.compile(r"KmipSpec\.(\w+)")


def load_enum_spec_versions() -> dict[str, set[str]]:
    """Map spec enum name -> set of versions it appears in."""
    data = json.loads(JSON_PATH.read_text())
    out: dict[str, set[str]] = {}
    for vd in data["versions"]:
        v = vd["version"]
        for name in vd.get("enumerations", {}).keys():
            out.setdefault(name, set()).add(v)
    return out


def expected_java_versions(spec_versions: set[str]) -> set[str]:
    return {SPEC_TO_JAVA[v] for v in spec_versions if v in SPEC_TO_JAVA} | {"UnknownVersion"}


def class_to_spec_norm(cls: str) -> str:
    """Normalised key for case-insensitive matching: 'NistKeyType' -> 'nistkeytype'."""
    return re.sub(r"[\s\-_/.#]", "", cls).lower()


def audit() -> list[dict]:
    enum_to_specvers = load_enum_spec_versions()
    spec_norm_lookup = {class_to_spec_norm(k): k for k in enum_to_specvers}

    results = []
    for d in ENUM_DIRS:
        if not d.is_dir():
            continue
        for jf in sorted(d.glob("*.java")):
            cls = jf.stem
            text = jf.read_text()
            m = SV_RE.search(text)
            if not m:
                continue
            actual = set(KMIPSPEC_RE.findall(m.group(1)))
            spec_name = spec_norm_lookup.get(class_to_spec_norm(cls))
            spec_v = enum_to_specvers.get(spec_name, set()) if spec_name else set()
            expected = expected_java_versions(spec_v)
            if not spec_name:
                status = "UNMATCHED"
            elif actual == expected:
                status = "OK"
            else:
                status = "DRIFT"
            results.append({
                "class": cls,
                "file": str(jf.relative_to(REPO)),
                "spec_name": spec_name,
                "spec_versions": sorted(spec_v),
                "actual": sorted(actual),
                "expected": sorted(expected),
                "missing": sorted(expected - actual),
                "extra": sorted(actual - expected),
                "status": status,
            })
    return results


def render_text(results: list[dict]) -> str:
    ok = [r for r in results if r["status"] == "OK"]
    drift = [r for r in results if r["status"] == "DRIFT"]
    unm = [r for r in results if r["status"] == "UNMATCHED"]
    lines = []
    lines.append(f"=== supportedVersions audit ({len(results)} enum classes) ===")
    lines.append(f"  OK: {len(ok)}    DRIFT: {len(drift)}    UNMATCHED: {len(unm)}\n")
    if drift:
        lines.append("--- DRIFT ---")
        for r in drift:
            lines.append(f"\n  {r['class']}  (spec='{r['spec_name']}')")
            lines.append(f"    spec versions:      {r['spec_versions']}")
            lines.append(f"    actual:             {r['actual']}")
            lines.append(f"    expected:           {r['expected']}")
            if r["missing"]:
                lines.append(f"    MISSING in actual:  {r['missing']}")
            if r["extra"]:
                lines.append(f"    EXTRA in actual:    {r['extra']}")
    if unm:
        lines.append("\n--- UNMATCHED (no spec enum matches the class name) ---")
        for r in unm:
            lines.append(f"  {r['class']}   actual={r['actual']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument("--fail-on-drift", action="store_true",
                    help="exit 1 if any DRIFT (UNMATCHED ignored)")
    args = ap.parse_args()

    results = audit()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(render_text(results))
    if args.fail_on_drift and any(r["status"] == "DRIFT" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
