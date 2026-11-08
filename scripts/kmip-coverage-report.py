#!/usr/bin/env python3
"""
Generates KMIP model coverage reports, one Markdown file per KMIP version.

Output: docs/kmip-coverage/v{version}.md

Each file has tables per category:
  - Enumerations
  - Data Types
  - Structures
  - Operation Payloads

Codec status (JSON / XML / TTLV) is derived from the presence and content of
codec source files under src/main/java/.../codec/.
"""

import os
import re
import sys
from collections import defaultdict
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, "src", "main", "java", "org", "purplebean", "kmip", "model")
CODEC_DIR = os.path.join(PROJECT_ROOT, "src", "main", "java", "org", "purplebean", "kmip", "codec")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "kmip-coverage")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSIONS_ORDER = ["V1_1", "V1_2", "V2_0", "V2_1", "V3_0"]
VERSION_LABEL = {
    "V1_1": "v1.1",
    "V1_2": "v1.2",
    "V2_0": "v2.0",
    "V2_1": "v2.1",
    "V3_0": "v3.0",
}
CATEGORIES = ["Enumeration", "Data Type", "Structure", "Operation Payload"]
FORMATS = ["json", "xml", "ttlv"]


# ---------------------------------------------------------------------------
# Java source parsing helpers
# ---------------------------------------------------------------------------

def _extract_class_name(content: str) -> Optional[str]:
    m = re.search(r'public(?:\s+\w+)*\s+class\s+(\w+)', content)
    return m.group(1) if m else None


def _extract_tag(content: str) -> Optional[str]:
    # public static final KmipTag kmipTag = KmipTag.Standard.FOO_BAR.inst();
    m = re.search(r'KmipTag\s+kmipTag\s*=\s*KmipTag\.Standard\.(\w+)\.inst\(\)', content)
    if m:
        return m.group(1)
    # operation payloads inherit kmipTag from interface — mark as inherited
    if "RequestPayloadStructure" in content or "ResponsePayloadStructure" in content:
        return "(inherited)"
    return None


def _extract_supported_versions(content: str) -> list:
    m = re.search(r'supportedVersions\s*=\s*Set\.of\(([^)]+)\)', content)
    if not m:
        return []
    raw = m.group(1)
    versions = re.findall(r'KmipSpec\.(\w+)', raw)
    return [v for v in versions if v not in ("UnknownVersion", "UnsupportedVersion")]


def _extract_encoding_type(content: str) -> Optional[str]:
    # public static final EncodingType encodingType = EncodingType.TEXT_STRING;
    m = re.search(r'EncodingType\s+encodingType\s*=\s*EncodingType\.(\w+)', content)
    return m.group(1) if m else None


def _extract_fields(content: str) -> list:
    """
    Extract non-static private final fields with their type and nullability.
    Returns list of {"type": str, "name": str, "required": bool, "list": bool}.
    """
    fields = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        # Skip static fields
        if re.search(r'\bstatic\b', line):
            continue
        m = re.search(r'\bprivate\s+final\s+([\w<>, ]+?)\s+(\w+)\s*;', line)
        if not m:
            continue
        raw_type = m.group(1).strip()
        name = m.group(2).strip()

        # Check annotations on up to 4 preceding lines
        preceding = "\n".join(lines[max(0, i - 4):i])
        required = "@NonNull" in preceding
        is_list = "List<" in raw_type

        # Clean up generic type for display, e.g. List<SomeType> -> List<SomeType>
        fields.append({"type": raw_type, "name": name, "required": required, "list": is_list})
    return fields


def _categorize(filepath: str, content: str) -> str:
    rel = filepath.replace(MODEL_DIR, "")
    if "/enumeration/" in rel:
        return "Enumeration"
    if "/type/" in rel:
        return "Data Type"
    # Payload: in a payload sub-package OR implements Request/ResponsePayload
    if "/payload/" in rel \
            or "RequestPayloadStructure" in content \
            or "ResponsePayloadStructure" in content:
        return "Operation Payload"
    return "Structure"


def _operation_name(filepath: str) -> Optional[str]:
    """Extract the operation verb from a payload file path, e.g. 'Create'."""
    m = re.search(r'/payload/(\w+OpRequest|\w+OpResponse)', filepath)
    if m:
        name = m.group(1).replace("OpRequestPayload", "").replace("OpResponsePayload", "")
        return name
    return None


# ---------------------------------------------------------------------------
# Codec status helpers
# ---------------------------------------------------------------------------

# Pre-index codec files once for fast lookup
_codec_index: dict[str, dict[str, dict[str, str]]] = {}  # class_name -> format -> {ser, des}


def _build_codec_index():
    for root, _dirs, files in os.walk(CODEC_DIR):
        for fname in files:
            if not fname.endswith(".java"):
                continue
            path = os.path.join(root, fname)
            for fmt in FORMATS:
                cap = fmt.capitalize()
                ser_sfx = f"{cap}Serializer.java"
                des_sfx = f"{cap}Deserializer.java"
                if fname.endswith(ser_sfx):
                    cls = fname[: -len(ser_sfx)]
                    _codec_index.setdefault(cls, {}).setdefault(fmt, {})["ser"] = path
                elif fname.endswith(des_sfx):
                    cls = fname[: -len(des_sfx)]
                    _codec_index.setdefault(cls, {}).setdefault(fmt, {})["des"] = path


def _is_stub_deserializer(path: str) -> bool:
    """
    True when the deserializer is a stub.
    Enumerations use a direct builder.value() call — no switch needed.
    Structures are stubs when their setValue() has a TODO comment.
    """
    with open(path, encoding="utf-8") as f:
        src = f.read()
    return "// TODO" in src


def _codec_status(class_name: str) -> dict:
    """
    Returns {"json": status, "xml": status, "ttlv": status}
    status is one of: "complete", "stub", "missing"
    """
    result = {}
    fmt_map = _codec_index.get(class_name, {})
    for fmt in FORMATS:
        entry = fmt_map.get(fmt, {})
        if not entry:
            result[fmt] = "missing"
            continue
        # Serializer presence is sufficient (delegates to abstract base)
        # Deserializer determines stub status
        des_path = entry.get("des")
        if des_path and _is_stub_deserializer(des_path):
            result[fmt] = "stub"
        elif des_path:
            result[fmt] = "complete"
        else:
            result[fmt] = "missing"
    return result


# ---------------------------------------------------------------------------
# Status emoji helpers
# ---------------------------------------------------------------------------

def _codec_emoji(status: str) -> str:
    return {"complete": "✅", "stub": "⚠️", "missing": "❌"}.get(status, "?")


def _field_str(fields: list) -> str:
    if not fields:
        return "—"
    parts = []
    for f in fields:
        req = "" if f["required"] else "?"
        parts.append(f"`{f['name']}{req}: {f['type']}`")
    return "<br>".join(parts)


# ---------------------------------------------------------------------------
# Model scanning
# ---------------------------------------------------------------------------

def scan_models() -> list:
    """Walk MODEL_DIR and return a list of model info dicts."""
    models = []
    for root, _dirs, files in os.walk(MODEL_DIR):
        for fname in files:
            if not fname.endswith(".java"):
                continue
            path = os.path.join(root, fname)
            with open(path, encoding="utf-8") as f:
                content = f.read()

            class_name = _extract_class_name(content)
            if not class_name:
                continue

            # Skip interfaces and abstract classes
            if re.search(r'\b(interface|abstract)\s+class\b', content):
                continue
            # Skip enum declarations (they contain 'enum' keyword as type)
            if re.search(r'^public\s+enum\b', content, re.MULTILINE):
                continue

            tag = _extract_tag(content)
            versions = _extract_supported_versions(content)
            encoding = _extract_encoding_type(content)
            category = _categorize(path, content)
            fields = [] if category == "Enumeration" else _extract_fields(content)
            codec = _codec_status(class_name)

            # Derive a short package label relative to model root
            rel_pkg = os.path.relpath(root, MODEL_DIR).replace(os.sep, ".")

            models.append({
                "class": class_name,
                "package": rel_pkg,
                "tag": tag or "—",
                "versions": versions,
                "encoding": encoding or "STRUCTURE",
                "category": category,
                "fields": fields,
                "codec": codec,
                "path": path,
            })

    return models


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

LEGEND = """
> **Codec legend:** ✅ complete &nbsp; ⚠️ stub (deserializer has TODO) &nbsp; ❌ missing
>
> **Field legend:** `fieldName: Type` — required, `fieldName?: Type` — nullable/optional
"""


def _enum_table(models: list[dict]) -> str:
    rows = [
        "| Class | Package | Tag | All Supported Versions | JSON | XML | TTLV |",
        "|-------|---------|-----|------------------------|------|-----|------|",
    ]
    for m in sorted(models, key=lambda x: x["class"]):
        vs = ", ".join(VERSION_LABEL.get(v, v) for v in VERSIONS_ORDER if v in m["versions"]) or "—"
        c = m["codec"]
        rows.append(
            f"| `{m['class']}` | `{m['package']}` | `{m['tag']}` | {vs} "
            f"| {_codec_emoji(c['json'])} | {_codec_emoji(c['xml'])} | {_codec_emoji(c['ttlv'])} |"
        )
    return "\n".join(rows)


def _type_table(models: list[dict]) -> str:
    rows = [
        "| Class | Package | Tag | Encoding | All Supported Versions | JSON | XML | TTLV |",
        "|-------|---------|-----|----------|------------------------|------|-----|------|",
    ]
    for m in sorted(models, key=lambda x: x["class"]):
        vs = ", ".join(VERSION_LABEL.get(v, v) for v in VERSIONS_ORDER if v in m["versions"]) or "—"
        c = m["codec"]
        rows.append(
            f"| `{m['class']}` | `{m['package']}` | `{m['tag']}` | `{m['encoding']}` | {vs} "
            f"| {_codec_emoji(c['json'])} | {_codec_emoji(c['xml'])} | {_codec_emoji(c['ttlv'])} |"
        )
    return "\n".join(rows)


def _structure_table(models: list[dict]) -> str:
    rows = [
        "| Class | Package | Tag | All Supported Versions | Fields | JSON | XML | TTLV |",
        "|-------|---------|-----|------------------------|--------|------|-----|------|",
    ]
    for m in sorted(models, key=lambda x: x["class"]):
        vs = ", ".join(VERSION_LABEL.get(v, v) for v in VERSIONS_ORDER if v in m["versions"]) or "—"
        c = m["codec"]
        fields = _field_str(m["fields"])
        rows.append(
            f"| `{m['class']}` | `{m['package']}` | `{m['tag']}` | {vs} | {fields} "
            f"| {_codec_emoji(c['json'])} | {_codec_emoji(c['xml'])} | {_codec_emoji(c['ttlv'])} |"
        )
    return "\n".join(rows)


def _payload_table(models: list[dict]) -> str:
    rows = [
        "| Class | Package | Tag | All Supported Versions | Fields | JSON | XML | TTLV |",
        "|-------|---------|-----|------------------------|--------|------|-----|------|",
    ]
    for m in sorted(models, key=lambda x: x["class"]):
        vs = ", ".join(VERSION_LABEL.get(v, v) for v in VERSIONS_ORDER if v in m["versions"]) or "—"
        c = m["codec"]
        fields = _field_str(m["fields"])
        rows.append(
            f"| `{m['class']}` | `{m['package']}` | `{m['tag']}` | {vs} | {fields} "
            f"| {_codec_emoji(c['json'])} | {_codec_emoji(c['xml'])} | {_codec_emoji(c['ttlv'])} |"
        )
    return "\n".join(rows)


def _summary_table(version: str, by_category: dict[str, list]) -> str:
    rows = [
        "| Category | Total | JSON ✅ | JSON ⚠️ | JSON ❌ | XML ✅ | XML ⚠️ | XML ❌ | TTLV ✅ | TTLV ⚠️ | TTLV ❌ |",
        "|----------|-------|---------|---------|--------|--------|--------|-------|---------|---------|--------|",
    ]
    for cat in CATEGORIES:
        ms = by_category.get(cat, [])
        if not ms:
            continue
        total = len(ms)
        row = f"| {cat} | {total}"
        for fmt in FORMATS:
            counts = {"complete": 0, "stub": 0, "missing": 0}
            for m in ms:
                counts[m["codec"].get(fmt, "missing")] += 1
            row += f" | {counts['complete']} | {counts['stub']} | {counts['missing']}"
        row += " |"
        rows.append(row)
    return "\n".join(rows)


def generate_version_doc(version: str, models: list[dict]) -> str:
    label = VERSION_LABEL[version]
    by_cat: dict[str, list] = defaultdict(list)
    for m in models:
        by_cat[m["category"]].append(m)

    lines = [
        f"# KMIP {label} — Model Coverage Report",
        "",
        f"Models that declare `KmipSpec.{version}` in their `supportedVersions`.",
        "",
        "## Summary",
        "",
        _summary_table(version, by_cat),
        "",
        LEGEND,
    ]

    for cat in CATEGORIES:
        ms = by_cat.get(cat, [])
        if not ms:
            continue
        lines += [f"---", "", f"## {cat}s ({len(ms)})", ""]
        if cat == "Enumeration":
            lines.append(_enum_table(ms))
        elif cat == "Data Type":
            lines.append(_type_table(ms))
        elif cat == "Structure":
            lines.append(_structure_table(ms))
        elif cat == "Operation Payload":
            lines.append(_payload_table(ms))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Building codec index...")
    _build_codec_index()

    print("Scanning model sources...")
    all_models = scan_models()
    print(f"  Found {len(all_models)} model classes")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Group by version
    version_models: dict[str, list] = defaultdict(list)
    for m in all_models:
        for v in m["versions"]:
            if v in VERSIONS_ORDER:
                version_models[v].append(m)

    # Write one file per version
    for version in VERSIONS_ORDER:
        ms = version_models.get(version, [])
        if not ms:
            continue
        label = VERSION_LABEL[version]
        out_path = os.path.join(OUTPUT_DIR, f"{label}.md")
        content = generate_version_doc(version, ms)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Written {out_path}  ({len(ms)} models)")

    # Also write an "all versions" index
    _write_index(all_models, version_models)
    print(f"  Written {os.path.join(OUTPUT_DIR, 'README.md')}")


def _write_index(all_models: list[dict], version_models: dict[str, list]):
    lines = [
        "# KMIP Model Coverage — Index",
        "",
        "Generated by `scripts/kmip-coverage-report.py`.",
        "",
        "## Files",
        "",
    ]
    for v in VERSIONS_ORDER:
        label = VERSION_LABEL[v]
        count = len(version_models.get(v, []))
        if count:
            lines.append(f"- [{label}.md]({label}.md) — {count} models")
    lines += [
        "",
        "## Overall Counts",
        "",
        f"Total distinct model classes scanned: **{len(all_models)}**",
        "",
        "| Version | Models |",
        "|---------|--------|",
    ]
    for v in VERSIONS_ORDER:
        label = VERSION_LABEL[v]
        count = len(version_models.get(v, []))
        if count:
            lines.append(f"| {label} | {count} |")
    lines.append("")
    with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
