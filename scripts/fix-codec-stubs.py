#!/usr/bin/env python3
"""
Fixes stub codec deserializers by replacing TODO blocks with correct dispatch logic.

Two fix categories:
  1. New structures (ObjectDefaults, DefaultsInformation, Constraints, Constraint,
     Attributes, CommonAttributes, PrivateKeyAttributes, PublicKeyAttributes)
  2. Genuinely-empty operation payloads (no fields per KMIP spec)
"""

import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEC_DIR = os.path.join(PROJECT_ROOT, "src", "main", "java", "org", "purplebean", "kmip", "codec")

# The TODO block that the generator emits
TODO_PATTERN = re.compile(
    r'(\s+// TODO: Implement setting values.*?// \s*\}\s*\n)',
    re.DOTALL
)

# ---------------------------------------------------------------------------
# Fix definitions
# ---------------------------------------------------------------------------

# JSON and XML share the same dispatch skeleton (Jackson JsonParser + ctxt.readValue)
# TTLV uses byte[] tag + mapper.readValue

def json_dispatch(cases: list[tuple[str, str, str]]) -> str:
    """cases: list of (KmipTag constant, field builder method, type class name)"""
    if not cases:
        return "        // No fields per KMIP spec"
    lines = ["        KmipTag.Value nodeTag = KmipTag.fromName(tag);",
             "        switch (nodeTag) {"]
    for tag_const, builder_method, type_class in cases:
        lines.append(f"            case KmipTag.Standard.{tag_const} -> {builder_method}(ctxt.readValue(p, {type_class}.class));")
    lines.append('            default -> throw new IllegalArgumentException("Unsupported tag: " + nodeTag);')
    lines.append("        }")
    return "\n".join(lines)


def xml_dispatch(cases: list[tuple[str, str, str]]) -> str:
    return json_dispatch(cases)  # XML uses same Jackson API as JSON


def ttlv_dispatch(cases: list[tuple[str, str, str]]) -> str:
    if not cases:
        return "        // No fields per KMIP spec"
    lines = ["        KmipTag.Value nodeTag = KmipTag.fromBytes(tag);",
             "        switch (nodeTag) {"]
    for tag_const, builder_method, type_class in cases:
        lines.append(f"            case KmipTag.Standard.{tag_const} -> {builder_method}(mapper.readValue(p, {type_class}.class));")
    lines.append('            default -> throw new IllegalArgumentException("Unsupported tag: " + nodeTag);')
    lines.append("        }")
    return "\n".join(lines)


def catchall_json(builder_method: str, type_class: str) -> str:
    """For heterogeneous lists — no tag switch, just read as type."""
    return f"        {builder_method}(ctxt.readValue(p, {type_class}.class));"


def catchall_ttlv(builder_method: str, type_class: str) -> str:
    return f"        {builder_method}(mapper.readValue(p, {type_class}.class));"


# class_name -> {format: replacement_body}
STRUCTURE_FIXES = {
    "ObjectDefaults": {
        "json": json_dispatch([
            ("OBJECT_TYPE", "builder.objectType", "ObjectType"),
            ("ATTRIBUTES",  "builder.attributes",  "Attributes"),
        ]),
        "xml": xml_dispatch([
            ("OBJECT_TYPE", "builder.objectType", "ObjectType"),
            ("ATTRIBUTES",  "builder.attributes",  "Attributes"),
        ]),
        "ttlv": ttlv_dispatch([
            ("OBJECT_TYPE", "builder.objectType", "ObjectType"),
            ("ATTRIBUTES",  "builder.attributes",  "Attributes"),
        ]),
    },
    "DefaultsInformation": {
        "json": json_dispatch([("OBJECT_DEFAULTS", "builder.objectDefault", "ObjectDefaults")]),
        "xml":  xml_dispatch([("OBJECT_DEFAULTS",  "builder.objectDefault", "ObjectDefaults")]),
        "ttlv": ttlv_dispatch([("OBJECT_DEFAULTS", "builder.objectDefault", "ObjectDefaults")]),
    },
    "Constraints": {
        "json": json_dispatch([("CONSTRAINT", "builder.constraint", "Constraint")]),
        "xml":  xml_dispatch([("CONSTRAINT",  "builder.constraint", "Constraint")]),
        "ttlv": ttlv_dispatch([("CONSTRAINT", "builder.constraint", "Constraint")]),
    },
    # Constraint holds an open-typed List<KmipDataType> — no tag dispatch needed
    "Constraint": {
        "json": catchall_json("builder.value", "KmipDataType"),
        "xml":  catchall_json("builder.value", "KmipDataType"),
        "ttlv": catchall_ttlv("builder.value", "KmipDataType"),
    },
    # Attributes family: heterogeneous List<KmipAttribute> — delegate to KmipAttribute registry
    "Attributes": {
        "json": catchall_json("builder.attribute", "KmipAttribute"),
        "xml":  catchall_json("builder.attribute", "KmipAttribute"),
        "ttlv": catchall_ttlv("builder.attribute", "KmipAttribute"),
    },
    "CommonAttributes": {
        "json": catchall_json("builder.attribute", "KmipAttribute"),
        "xml":  catchall_json("builder.attribute", "KmipAttribute"),
        "ttlv": catchall_ttlv("builder.attribute", "KmipAttribute"),
    },
    "PrivateKeyAttributes": {
        "json": catchall_json("builder.attribute", "KmipAttribute"),
        "xml":  catchall_json("builder.attribute", "KmipAttribute"),
        "ttlv": catchall_ttlv("builder.attribute", "KmipAttribute"),
    },
    "PublicKeyAttributes": {
        "json": catchall_json("builder.attribute", "KmipAttribute"),
        "xml":  catchall_json("builder.attribute", "KmipAttribute"),
        "ttlv": catchall_ttlv("builder.attribute", "KmipAttribute"),
    },
}

# Genuinely empty payloads — setValue body becomes a no-op comment
EMPTY_PAYLOADS = [
    "InteropOpResponsePayload",
    "LogOpResponsePayload",
    "LogoutOpResponsePayload",
    "ObliterateOpResponsePayload",
    "PingOpRequestPayload",
    "PingOpResponsePayload",
    "SetConstraintsOpResponsePayload",
    "SetDefaultsOpResponsePayload",
]

# ---------------------------------------------------------------------------
# File patching
# ---------------------------------------------------------------------------

def find_deserializer(class_name: str, fmt: str) -> str:
    cap = fmt.capitalize()
    filename = f"{class_name}{cap}Deserializer.java"
    for root, _dirs, files in os.walk(CODEC_DIR):
        if filename in files:
            return os.path.join(root, filename)
    return None


def patch_file(path: str, new_body: str) -> bool:
    with open(path, encoding="utf-8") as f:
        src = f.read()

    if "// TODO" not in src:
        return False  # Already fixed

    # Locate setValue method and replace its body
    # Strategy: find the TODO block and replace it with new_body
    # The TODO block spans from "// TODO: Implement..." to the closing comment block
    old_block = re.search(
        r'(\s*// TODO: Implement setting values on the builder based on the tag\n'
        r'(?:\s*//[^\n]*\n)*)',
        src
    )
    if not old_block:
        print(f"  WARNING: Could not find TODO block in {path}")
        return False

    old_str = old_block.group(0)
    new_str = "\n" + new_body + "\n"
    new_src = src.replace(old_str, new_str, 1)

    if new_src == src:
        print(f"  WARNING: Replacement had no effect in {path}")
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    fixed = 0
    skipped = 0

    print("=== Fixing structure deserializers ===")
    for class_name, fmt_map in STRUCTURE_FIXES.items():
        for fmt, new_body in fmt_map.items():
            path = find_deserializer(class_name, fmt)
            if not path:
                print(f"  MISSING: {class_name} {fmt} deserializer not found")
                skipped += 1
                continue
            if patch_file(path, new_body):
                print(f"  FIXED:   {os.path.basename(path)}")
                fixed += 1
            else:
                print(f"  SKIP:    {os.path.basename(path)} (already done or no match)")
                skipped += 1

    print("\n=== Fixing empty payload deserializers ===")
    for class_name in EMPTY_PAYLOADS:
        for fmt in ["json", "xml", "ttlv"]:
            path = find_deserializer(class_name, fmt)
            if not path:
                print(f"  MISSING: {class_name} {fmt} deserializer not found")
                skipped += 1
                continue
            if patch_file(path, "        // No fields per KMIP spec"):
                print(f"  FIXED:   {os.path.basename(path)}")
                fixed += 1
            else:
                print(f"  SKIP:    {os.path.basename(path)} (already done or no match)")
                skipped += 1

    print(f"\nDone: {fixed} fixed, {skipped} skipped.")


if __name__ == "__main__":
    main()
