#!/usr/bin/env python3
"""
Comprehensive script to update KMIP enum files with proper version management, sorting, and missing enum handling.

python3 scripts/comprehensive_enum_sync.py  \
    --csv docs/kmip-spec/v3.x/sections/kmip-spec-enumerations-v3.0-os_enumerations.csv \
    --enum-dir src/main/java/org/purplebean/kmip/common/enumeration \
    --write
"""

import sys
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# Mapping from CSV enumeration_category to Java enum filename stem
SPECIAL_CATEGORY_TO_FILE = {
    "DRBG Algorithm": "DrbgAlgorithm",
    "FIPS186 Variation": "Fips186Variation",
    "NIST Key Type": "NistKeyType",
    "Key Wrap Type": "KeyWrapType",
    "Adjustment Type": "AdjustmentType",
    "Batch Error Continuation Option": "BatchErrorContinuationOption",
    "Digital Signature Algorithm": "DigitalSignatureAlgorithm",
    "Data": "DataEnumeration",
}

# Categories in CSV that are not represented as enums or should be ignored here
IGNORE_CATEGORIES = {
    "Opaque Data Type",  # appears to only have extensions in CSV
    "Item Type",  # TTLV data types, not business domain enums
}

# Special file mappings for non-enum files with their full paths
SPECIAL_FILE_PATHS = {
    "Tag": "src/main/java/org/purplebean/kmip/KmipTag.java"
}

# Special file mappings for non-enum files (for backward compatibility)
SPECIAL_FILE_MAPPINGS = {
    "Tag": "KmipTag"  # Maps category to Java filename without extension
}

CONST_LINE_RE = re.compile(r"^\s*([A-Z0-9_]+)\s*\(\s*0x([0-9A-Fa-f]{6,8})\s*,\s*\"([^\"]*)\"\s*,\s*(.*?)\)\s*[,;]?\s*$")
ENUM_HEADER_RE = re.compile(r"\benum\s+Standard\s+implements?\s+Value|\benum\s+Standard\s+\w*\s*implements?\s*Value?")


def generate_enum_file(file_stem: str, root_dir: Path) -> bool:
    """
    Generate a new Java enum file using generate_enum.sh script.
    
    Args:
        file_stem: The name of the enum file to generate (without .java extension)
        root_dir: The root directory of the project
        
    Returns:
        True if generation was successful, False otherwise
    """
    generate_script = root_dir / "generate_enum.sh"
    
    if not generate_script.exists():
        print(f"Error: generate_enum.sh script not found at {generate_script}")
        return False
    
    try:
        print(f"Generating missing enum file: {file_stem}")
        result = subprocess.run(
            ["sh", str(generate_script), file_stem],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"Successfully generated {file_stem}.java")
            return True
        else:
            print(f"Error generating {file_stem}.java:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"Timeout generating {file_stem}.java")
        return False
    except Exception as e:
        print(f"Exception generating {file_stem}.java: {e}")
        return False


def convert_version_to_constant(version: str) -> str:
    """Convert version string to Java constant format."""
    if not version:
        raise ValueError("Version cannot be empty")

    # Replace dots with underscores and ensure uppercase
    version = version.replace('.', '_').upper()

    # Special case for unknown version
    if version == "UNKNOWN":
        return "KmipSpec.UnknownVersion"

    return f"KmipSpec.V{version}"


def category_to_file(category: str) -> Optional[str]:
    """Convert CSV category to Java enum filename."""
    if category in IGNORE_CATEGORIES:
        return None
    if category in SPECIAL_CATEGORY_TO_FILE:
        return SPECIAL_CATEGORY_TO_FILE[category]
    if category in SPECIAL_FILE_MAPPINGS:
        return SPECIAL_FILE_MAPPINGS[category]

    # General conversion: title case words, remove spaces and punctuation
    parts = re.split(r"[^A-Za-z0-9]+", category.strip())
    parts = [p for p in parts if p]
    if not parts:
        return None

    # Fix common acronyms casing used in codebase
    fixed = []
    for p in parts:
        if p.lower() in {"uri", "rsa", "dsa", "dh", "ec", "ecdsa", "ecmqv", "pgp", "x509"}:
            fixed.append(p.upper() if p.lower() != "x509" else "X509")
        else:
            fixed.append(p.capitalize())
    return "".join(fixed)


def get_java_file_path(file_stem: str, root: Path, enum_dir: Path) -> Optional[Path]:
    """Get the full path to a Java file, checking special locations."""
    # First check if this is a special file with a known path
    for category, rel_path in SPECIAL_FILE_PATHS.items():
        if file_stem == category_to_file(category):
            full_path = root / rel_path
            if full_path.exists():
                return full_path

    # Then check the standard enum directory
    java_file = enum_dir / f"{file_stem}.java"
    if java_file.exists():
        return java_file

    # Finally check the kmip directory
    kmip_dir = root / "src/main/java/org/purplebean/kmip"
    java_file = kmip_dir / f"{file_stem}.java"
    return java_file if java_file.exists() else None


def parse_csv(csv_path: Path) -> Dict[str, Dict[int, str]]:
    """Parse the KMIP specification CSV file into a dictionary of enums."""
    categories: Dict[str, Dict[int, str]] = {}
    try:
        with csv_path.open(newline="", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not all(field in reader.fieldnames for field in ["enumeration_category", "enumeration_name", "value"]):
                raise ValueError("CSV file is missing required columns. Expected: enumeration_category, enumeration_name, value")

            for row in reader:
                cat = row["enumeration_category"].strip()
                name = row["enumeration_name"].strip()
                val_hex = row["value"].strip()
                v1_2 = row.get("v1_2", "").strip()
                v2_1 = row.get("v2_1", "").strip()
                v3_0 = row.get("v3_0", "").strip()

                # Skip empty values or extension ranges
                if not val_hex or 'XXXXXXX' in val_hex or ('X' in val_hex and val_hex.count('X') > 1):
                    continue

                # Add 0x prefix if missing
                if not val_hex.startswith('0x'):
                    val_hex = f'0x{val_hex}'

                try:
                    val = int(val_hex, 16)
                except ValueError as e:
                    print(f"Warning: Invalid hex value '{val_hex}' in {csv_path.name}: {e}", file=sys.stderr)
                    continue

                file_stem = category_to_file(cat)
                if not file_stem:
                    continue

                categories.setdefault(file_stem, {})[val] = name

    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing CSV file {csv_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not categories:
        print(f"Warning: No valid enum data found in {csv_path}", file=sys.stderr)

    return categories


def convert_to_upper_snake_case(name: str) -> str:
    """Convert name to UPPER_SNAKE_CASE"""
    # Try to form a reasonable constant name; ensure uniqueness
    base = re.sub(r"[^A-Za-z0-9]+", "_", name).upper()
    base = re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = "VAL"
    name = base
    i = 2
    while name in {"VAL"}:
        name = f"{base}_{i}"
        i += 1
    return name
    # Handle camelCase and PascalCase
    name = re.sub(r'([a-z])([A-Z])', r'\1_\2', name)
    name = re.sub(r'([A-Z])([A-Z][a-z])', r'\1_\2', name)
    # Replace non-alphanumeric with underscore
    name = re.sub(r'[^A-Za-z0-9]+', '_', name)
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores and convert to uppercase
    return name.strip('_').upper()


def read_java_enum_structure(java_path: Path) -> Tuple[List[Tuple[str, int, str, str]], str]:
    """Read the complete Standard enum structure including constants, fields, constructor, and methods."""
    if not java_path.exists():
        return [], ""

    constants = []
    enum_structure_lines = []
    in_standard_enum = False
    brace_count = 0

    with open(java_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Special handling for KmipTag.Standard enum
    is_kmip_tag = 'KmipTag.java' in str(java_path)

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Look for the start of the Standard enum
        if not in_standard_enum:
            if 'enum Standard implements Value' in line:
                in_standard_enum = True
                brace_count = 1  # Count the opening brace
                enum_structure_lines.append(line.rstrip())
                continue

        if in_standard_enum:
            enum_structure_lines.append(line.rstrip())

            # Count braces to find the matching closing brace
            brace_count += line.count('{')
            brace_count -= line.count('}')

            if brace_count == 0:
                break  # Found the end of the enum

    # Extract constants from the enum structure
    for line in enum_structure_lines:
        m = CONST_LINE_RE.match(line.strip())
        if m:
            const_name = m.group(1)
            value = int(m.group(2), 16)
            description = m.group(3)
            versions = m.group(4).strip()
            constants.append((const_name, value, description, versions))

    return constants, '\n'.join(enum_structure_lines)


def compute_changes(
    file_stem: str,
    java_path: Path,
    spec_vals: Dict[int, str],
    target_version: str,
    unknown_version: str = "KmipSpec.UnknownVersion"
) -> Optional[Dict]:
    """Compute changes needed to synchronize an enum with the specification."""
    consts, enum_structure = read_java_enum_structure(java_path)
    if not consts:
        return None

    existing_vals = {v for _, v, _, _ in consts}
    expected_vals = set(spec_vals.keys())

    missing = sorted(expected_vals - existing_vals)
    extra = sorted(existing_vals - expected_vals)

    to_edit = {}
    for name, val, desc, vers in consts:
        print(f"DEBUG compute_changes: {name} (value=0x{val:08X}), expected_vals has {val}: {val in expected_vals}")

        # Check if this is a placeholder constant that should be replaced
        is_placeholder = ('reserve' in name.lower() or 'placeholder' in name.lower())
        correct_spec_name = spec_vals.get(val, "")

        if is_placeholder and correct_spec_name and 'reserved' not in correct_spec_name.lower():
            # This is a placeholder that should be replaced with correct name/description
            to_edit[name] = (val, desc, vers, True)  # True -> replace with correct name/description
            print(f"  -> Added to to_edit (placeholder replacement needed)")
        elif val in expected_vals:
            # Must support Unknown + target version
            if (unknown_version not in vers or
                target_version not in vers):
                # Find the original index in the structure
                to_edit[name] = (val, desc, vers, True)  # True -> set to Unknown + target_version
                print(f"  -> Added to to_edit (needs version update)")
        else:
            # Remove target_version if present
            if target_version in vers:
                to_edit[name] = (val, desc, vers, False)  # False -> remove target_version only
                print(f"  -> Added to to_edit (remove target version)")

    return {
        "missing": missing,
        "extra": extra,
        "to_edit": to_edit,
        "consts": consts,
        "enum_structure": enum_structure
    }


def update_versions_arg(vers: str, set_only_target: bool, target_version: str, unknown_version: str = "KmipSpec.UnknownVersion") -> str:
    """Update version arguments to include or exclude target version."""
    # Normalize and de-duplicate tokens while preserving order
    raw_tokens = [t.strip() for t in vers.split(',') if t.strip()]
    seen = set()
    tokens = []
    for t in raw_tokens:
        if t not in seen:
            seen.add(t)
            tokens.append(t)

    # Helper to identify version tokens and sort them
    version_re = re.compile(r"^KmipSpec\.V(\d+)_(\d+)$")

    def is_version(tok: str) -> bool:
        return bool(version_re.match(tok))

    def version_key(tok: str):
        m = version_re.match(tok)
        if not m:
            return (9999, 9999)
        return (int(m.group(1)), int(m.group(2)))

    # Ensure Unknown is present for all constants
    if unknown_version not in tokens:
        tokens.insert(0, unknown_version)

    if set_only_target:
        # ADD the target version if missing, but do not drop any other versions
        if target_version not in tokens:
            tokens.append(target_version)
    else:
        # REMOVE the target version if present, but keep others intact
        tokens = [t for t in tokens if t != target_version]

    # Reorder: Unknown first, then versions in ascending order, then any other tokens (if any)
    unknown_list = [t for t in tokens if t == unknown_version]
    version_list = [t for t in tokens if t != unknown_version and is_version(t)]
    other_list = [t for t in tokens if t != unknown_version and not is_version(t)]

    version_list_sorted = sorted(version_list, key=version_key)

    ordered = []
    if unknown_list:
        ordered.append(unknown_version)
    ordered.extend(version_list_sorted)
    ordered.extend(other_list)

    # Final de-duplication in case of any accidental duplicates
    final_seen = set()
    final_tokens = []
    for t in ordered:
        if t not in final_seen:
            final_seen.add(t)
            final_tokens.append(t)

    return ", ".join(final_tokens)


def convert_to_pascal_case(name: str) -> str:
    """Convert UPPER_SNAKE_CASE name to PascalCase"""
    # Split by underscores and capitalize each part
    parts = name.split('_')
    # Capitalize first letter of each part and join
    return ''.join(word.capitalize() for word in parts if word)


def convert_to_upper_snake_case(name: str) -> str:
    """Convert name to UPPER_SNAKE_CASE"""
    # Handle camelCase and PascalCase
    name = re.sub(r'([a-z])([A-Z])', r'\1_\2', name)
    name = re.sub(r'([A-Z])([A-Z][a-z])', r'\1_\2', name)
    # Replace non-alphanumeric with underscore
    name = re.sub(r'[^A-Za-z0-9]+', '_', name)
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores and convert to uppercase
    return name.strip('_').upper()


def generate_sorted_enum_constants(
    existing_constants: List[Tuple[str, int, str, str]],
    spec_vals: Dict[int, str],
    missing_spec: Dict[int, str],
    extra_vals: Set[int],
    to_edit: Dict[str, Tuple[int, str, str, bool]],
    is_tag: bool,
    target_version: str,
    unknown_version: str = "KmipSpec.UnknownVersion",
    expected_vals: Set[int] = None
) -> List[str]:
    """Generate all enum constants sorted by hex value."""

    # Collect all constants (existing + new)
    all_constants = []
    existing_values = set()
    existing_names = set()

    # Add existing constants, updating their version info if needed
    for name, value, description, versions in existing_constants:
        # Skip reserved enums - don't modify their versions
        if 'reserved' in name.lower() or 'reserved' in description.lower():
            # Keep them as-is without version modifications
            all_constants.append((name, value, description, versions))
            existing_values.add(value)
            existing_names.add(name)
            continue

        # Initialize variables
        const_name = name
        description = description  # Use the original description from tuple unpacking

        # Check if this constant needs updates
        if name in to_edit:
            val, desc, vers, should_replace = to_edit[name]
            if should_replace:
                # This is a placeholder that should be replaced with correct name/description
                correct_spec_name = spec_vals.get(value, "")
                if correct_spec_name and 'reserved' not in correct_spec_name.lower():
                    const_name = convert_to_upper_snake_case(correct_spec_name)
                    description = convert_to_pascal_case(const_name)
                    # Add target version support
                    updated_versions = update_versions_arg(vers, True, target_version, unknown_version)
                else:
                    # Fallback to original name/description
                    const_name = name
                    description = desc
                    updated_versions = vers
            else:
                # Normal version update
                if (unknown_version not in vers or
                    target_version not in vers):
                    # Add target version (for constants in CSV)
                    updated_versions = update_versions_arg(vers, True, target_version, unknown_version)
                else:
                    # Remove target version (for constants not in CSV)
                    updated_versions = update_versions_arg(vers, False, target_version, unknown_version)
                const_name = name
                description = desc
        else:
            # Only ensure target version support for constants that are in the CSV
            if expected_vals is None or value in expected_vals:
                # For constants in CSV that don't need changes, ensure they have proper version support
                updated_versions = update_versions_arg(versions, True, target_version, unknown_version)
            else:
                # For constants not in CSV, keep their existing versions unchanged
                updated_versions = versions
            const_name = name
            # description is already available from the tuple unpacking

        print(f"DEBUG: Processing {name} (value=0x{value:08X}), is_placeholder={should_replace if name in to_edit else 'N/A'}, correct_spec_name='{spec_vals.get(value, '')}', new_name='{const_name}', new_desc='{description}'")

        # For existing constants, use the description (either original or corrected)
        all_constants.append((const_name, value, description, updated_versions))

    # Add missing constants (only those not already existing by value)
    for value, spec_name in missing_spec.items():
        # Skip reserved enums - don't add them even if they're in CSV
        if 'reserved' in spec_name.lower():
            continue

        if value not in existing_values:  # Only add if truly new
            # Convert to UPPER_SNAKE_CASE for enum name
            const_name = convert_to_upper_snake_case(spec_name)

            # Convert to PascalCase for description
            description = convert_to_pascal_case(const_name)

            # Ensure uniqueness
            original_name = const_name
            counter = 2
            while const_name in existing_names:
                const_name = f"{original_name}_{counter}"
                counter += 1
            existing_names.add(const_name)

            # Add new constant with target version
            new_versions = f"{unknown_version}, {target_version}"
            all_constants.append((const_name, value, description, new_versions))

    # Sort by hex value (integer representation)
    all_constants.sort(key=lambda x: x[1])

    # Generate formatted lines
    lines = []
    for i, (name, value, description, versions) in enumerate(all_constants):
        # Format hex value
        if is_tag:
            hex_val = f"0x{value:06X}"  # 6 chars for Tag
        else:
            hex_val = f"0x{value:08X}"  # 8 chars for others

        # Determine delimiter (comma for all except last, semicolon for last)
        delimiter = ";" if i == len(all_constants) - 1 else ","

        # Create constant line - use varargs format to match existing files
        line = f"        {name}({hex_val}, \"{description}\", {versions}){delimiter}\n"
        lines.append(line)

    return lines

def generate_complete_enum_structure(sorted_constants_lines: List[str], original_enum_structure: str) -> List[str]:
    """Generate the complete Standard enum structure with updated constants."""

    # Split the original enum structure into lines
    original_lines = original_enum_structure.split('\n')

    # Find where the constants section starts and ends in the original
    constants_start_idx = -1
    constants_end_idx = -1

    for i, line in enumerate(original_lines):
        if 'enum Standard implements Value' in line:
            constants_start_idx = i + 1  # Start after the enum declaration
        elif line.strip().endswith(';') and constants_start_idx != -1 and constants_end_idx == -1:
            # Look for the line that ends with semicolon (last constant line)
            # But make sure it's not the enum closing brace
            if '}' not in line and not line.strip().startswith('//'):
                constants_end_idx = i
                break

    if constants_start_idx == -1 or constants_end_idx == -1:
        # If we can't find the boundaries, return the sorted constants only
        return sorted_constants_lines

    # Extract the non-constants parts (fields, constructor, methods)
    before_constants = original_lines[:constants_start_idx]
    after_constants = original_lines[constants_end_idx + 1:]

    # Combine everything
    result_lines = []
    result_lines.extend(before_constants)
    result_lines.extend([line for line in sorted_constants_lines])
    result_lines.extend(after_constants)

    return result_lines


def apply_changes(
    java_path: Path,
    changes: Dict,
    spec_vals: Dict[int, str],
    write: bool,
    target_version: str,
    unknown_version: str = "KmipSpec.UnknownVersion"
) -> Dict[str, int]:
    """Apply changes to the Java enum file using sorted constants approach."""

    if not write:
        # Return what would be changed
        result = {
            "missing_values": [f"0x{v:08X}" for v in changes["missing"]],
            "extra_values": [f"0x{v:08X}" for v in changes["extra"]],
            "needs_version_fixes": len(changes["to_edit"]),
            "would_add_constants": len(changes["missing"])
        }
        return result

    # Use the sorting approach to completely regenerate the enum constants
    is_tag = 'KmipTag.java' in str(java_path)

    # Generate sorted constants
    existing_constants = changes["consts"]
    sorted_lines = generate_sorted_enum_constants(
        existing_constants,
        spec_vals,  # spec_vals as second parameter
        dict(zip(changes["missing"], [spec_vals.get(v, "") for v in changes["missing"]])),  # missing_spec as dict
        set(changes["extra"]),  # Convert extra values to set
        changes["to_edit"],
        is_tag,
        target_version,
        unknown_version,
        set(spec_vals.keys())  # Pass expected values from CSV
    )

    # Generate the complete updated enum structure
    updated_enum_lines = generate_complete_enum_structure(sorted_lines, changes["enum_structure"])

    # Update the Java file
    with open(java_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the start and end of the Standard enum
    enum_start_idx = -1
    enum_end_idx = -1
    brace_count = 0
    in_enum = False

    for i, line in enumerate(lines):
        if 'enum Standard implements Value' in line:
            enum_start_idx = i
            in_enum = True
            brace_count = 1  # Count the opening brace
            break

    if not in_enum:
        print(f"Could not find Standard enum in {java_path}")
        return {"error": "Could not find enum"}

    # Find the end of the enum
    for i in range(enum_start_idx + 1, len(lines)):
        line = lines[i]
        brace_count += line.count('{')
        brace_count -= line.count('}')

        if brace_count == 0:
            enum_end_idx = i
            break

    if enum_end_idx == -1:
        print(f"Could not find Standard enum boundaries in {java_path}")
        return {"error": "Could not find enum boundaries"}

    # Replace the entire Standard enum section
    new_lines = (
        lines[:enum_start_idx] +  # Everything up to enum declaration
        updated_enum_lines +  # Updated enum structure
        lines[enum_end_idx + 1:]  # Everything after the enum
    )

    # Write back to file with proper newlines
    with open(java_path, 'w', encoding='utf-8') as f:
        for i, line in enumerate(new_lines):
            # Ensure each line ends with a newline
            if not line.endswith('\n'):
                line = line + '\n'
            f.write(line)


    print(f"Updated {java_path} with {len(sorted_lines)} sorted constants")

    return {
        "missing_values": [f"0x{v:08X}" for v in changes["missing"]],
        "extra_values": [f"0x{v:08X}" for v in changes["extra"]],
        "needs_version_fixes": len(changes["to_edit"]),
        "added_constants": len(changes["missing"])
    }


def process_file(
    file_stem: str,
    java_path: Path,
    spec_vals: Dict[int, str],
    write: bool,
    target_version: str,
    unknown_version: str = "KmipSpec.UnknownVersion"
) -> Dict:
    """Process a single Java enum file."""
    changes = compute_changes(file_stem, java_path, spec_vals, target_version, unknown_version)
    if changes is None:
        print(f"Skipping {file_stem}: Could not parse enum constants")
        return {}

    if not changes["missing"] and not changes["to_edit"] and not changes["extra"]:
        print(f"{file_stem}: No changes needed")
        return {}

    if write:
        result = apply_changes(java_path, changes, spec_vals, write, target_version, unknown_version)
        if "error" in result:
            print(f"Error updating {file_stem}: {result['error']}", file=sys.stderr)
            return {}
        print(f"Updated {file_stem}: {result}")
        return result
    else:
        result = {
            "missing_values": [f"0x{v:08X}" for v in changes["missing"]],
            "extra_values": [f"0x{v:08X}" for v in changes["extra"]],
            "needs_version_fixes": len(changes["to_edit"]),
            "would_add_constants": len(changes["missing"])
        }
        print(json.dumps({file_stem: result}, indent=4))
        return result


def extract_version_from_filename(csv_path: Path) -> str:
    """Extract KMIP version from CSV filename."""
    filename = csv_path.name
    # Pattern: kmip-spec-enumerations-v{version}-os_enumerations.csv
    import re
    match = re.search(r'v(\d+\.\d+)', filename)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract version from filename: {filename}")


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Comprehensive script to update KMIP enum files with proper version management, sorting, and missing enum handling."
    )
    parser.add_argument(
        "--csv",
        type=str,
        required=True,
        help="Path to KMIP specification CSV file"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply changes to files (default: dry run)"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Process only this specific enum file (relative to enum dir)"
    )
    parser.add_argument(
        "--enum-dir",
        type=str,
        help="Directory containing enum Java files (default: src/main/java/org/purplebean/kmip/common/enumeration)"
    )

    args = parser.parse_args()

    # Extract version from CSV filename
    root = Path(__file__).resolve().parents[1]
    csv_path = Path(args.csv) if Path(args.csv).is_absolute() else root / args.csv

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    try:
        version = extract_version_from_filename(csv_path)
        target_version = convert_version_to_constant(version)
        unknown_version = "KmipSpec.UnknownVersion"
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Set up paths
    enum_dir = Path(args.enum_dir) if args.enum_dir else root / "src/main/java/org/purplebean/kmip/common/enumeration"

    if not enum_dir.exists() or not any(enum_dir.iterdir()):
        print(f"Error: Enum directory not found or empty: {enum_dir}", file=sys.stderr)
        return 1

    print(f"Using KMIP version: {target_version}")
    print(f"Using specification: {csv_path}")
    print(f"Using enum directory: {enum_dir}")
    print(f"Mode: {'WRITE' if args.write else 'DRY RUN'}")

    # Parse CSV and process files
    csv_vals = parse_csv(csv_path)
    if not csv_vals:
        print("No valid enum data found in CSV, nothing to do.")
        return 0

    summary = {}

    # Process enum files
    if args.file:
        # Process single file
        file_path = get_java_file_path(Path(args.file).stem, root, enum_dir)
        if not file_path or not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 1

        file_stem = file_path.stem
        if file_stem not in csv_vals:
            print(f"Warning: No CSV entry found for {file_stem}", file=sys.stderr)
            return 1

        result = process_file(
            file_stem=file_stem,
            java_path=file_path,
            spec_vals=csv_vals[file_stem],
            write=args.write,
            target_version=target_version,
            unknown_version=unknown_version
        )
        if result:
            summary[file_stem] = result
    else:
        # Process all files
        for file_stem, spec_vals in csv_vals.items():
            java_file = get_java_file_path(file_stem, root, enum_dir)
            if not java_file or not java_file.exists():
                print(f"Java file not found for {file_stem}, attempting to generate...")
                if not generate_enum_file(file_stem, root):
                    print(f"Warning: Could not generate file for {file_stem}, skipping", file=sys.stderr)
                    continue
                # Try to get the file path again after generation
                java_file = get_java_file_path(file_stem, root, enum_dir)
                if not java_file or not java_file.exists():
                    print(f"Warning: File still not found after generation for {file_stem}, skipping", file=sys.stderr)
                    continue

            result = process_file(
                file_stem=file_stem,
                java_path=java_file,
                spec_vals=spec_vals,
                write=args.write,
                target_version=target_version,
                unknown_version=unknown_version
            )

            if result:  # Only add to summary if there are changes
                summary[file_stem] = {
                    "missing_values": result.get("missing_values", []),
                    "extra_values": result.get("extra_values", []),
                    "needs_version_fixes": result.get("needs_version_fixes", 0),
                    "added_constants": result.get("added_constants", 0),
                    "would_add_constants": result.get("would_add_constants", 0)
                }

    # Print summary if processing all files
    if not args.file and summary:
        print("\nSummary of changes:" if args.write else "\nSummary of changes needed:")
        print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
