#!/usr/bin/env python3
"""Replace TODO stubs in generated structure deserializers with proper setValue implementations."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# For each structure: list of (KmipTag.Standard.CONST, builderMethod, TypeClass)
# For list-append entries (Singular), set append=True
STRUCTURES = {
    "AsynchronousCorrelationValues": {
        "extra_imports": [],
        "fields": [
            ("ASYNCHRONOUS_CORRELATION_VALUE", "asynchronousCorrelationValue", "AsynchronousCorrelationValue"),
        ],
    },
    "AsynchronousRequest": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.type.SubmissionDate",
        ],
        "fields": [
            ("ASYNCHRONOUS_CORRELATION_VALUE", "asynchronousCorrelationValue", "AsynchronousCorrelationValue"),
            ("OPERATION", "operation", "Operation"),
            ("SUBMISSION_DATE", "submissionDate", "SubmissionDate"),
            ("PROCESSING_STAGE", "processingStage", "ProcessingStage"),
        ],
    },
    "AttributeReference": {
        "extra_imports": [],
        "fields": [
            ("VENDOR_IDENTIFICATION", "vendorIdentification", "VendorIdentification"),
            ("ATTRIBUTE_NAME", "attributeName", "AttributeName"),
        ],
    },
    "CapabilityInformation": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.type.*",
        ],
        "fields": [
            ("STREAMING_CAPABILITY", "streamingCapability", "StreamingCapability"),
            ("ASYNCHRONOUS_CAPABILITY", "asynchronousCapability", "AsynchronousCapability"),
            ("ATTESTATION_CAPABILITY", "attestationCapability", "AttestationCapability"),
            ("BATCH_UNDO_CAPABILITY", "batchUndoCapability", "BatchUndoCapability"),
            ("BATCH_CONTINUE_CAPABILITY", "batchContinueCapability", "BatchContinueCapability"),
            ("UNWRAP_MODE", "unwrapMode", "UnwrapMode"),
            ("DESTROY_ACTION", "destroyAction", "DestroyAction"),
            ("SHREDDING_ALGORITHM", "shreddingAlgorithm", "ShreddingAlgorithm"),
            ("RNG_MODE", "rngMode", "RngMode"),
            ("QUANTUM_SAFE_CAPABILITY", "quantumSafeCapability", "QuantumSafeCapability"),
        ],
    },
    "ObjectGroups": {
        "extra_imports": [],
        "fields": [
            ("OBJECT_GROUP", "objectGroup", "ObjectGroup"),
        ],
    },
    "Objects": {
        "extra_imports": [],
        "fields": [
            ("UNIQUE_IDENTIFIER", "uniqueIdentifier", "UniqueIdentifier"),
        ],
    },
    "Operations": {
        "extra_imports": [],
        "fields": [
            ("OPERATION", "operation", "Operation"),
        ],
    },
    "ProfileInformation": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.structure.ProfileVersion",
            "org.purplebean.kmip.model.v2_1.type.ServerUri",
            "org.purplebean.kmip.model.v2_1.type.ServerPort",
        ],
        "fields": [
            ("PROFILE_NAME", "profileName", "ProfileName"),
            ("PROFILE_VERSION", "profileVersion", "ProfileVersion"),
            ("SERVER_URI", "serverUri", "ServerUri"),
            ("SERVER_PORT", "serverPort", "ServerPort"),
        ],
    },
    "ProfileVersion": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.type.ProfileVersionMajor",
            "org.purplebean.kmip.model.v2_1.type.ProfileVersionMinor",
        ],
        "fields": [
            ("PROFILE_VERSION_MAJOR", "profileVersionMajor", "ProfileVersionMajor"),
            ("PROFILE_VERSION_MINOR", "profileVersionMinor", "ProfileVersionMinor"),
        ],
    },
    "ProtectionStorageMasks": {
        "extra_imports": [],
        "fields": [
            ("PROTECTION_STORAGE_MASK", "protectionStorageMask", "ProtectionStorageMask"),
        ],
    },
    "Right": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.structure.Operations",
            "org.purplebean.kmip.model.v2_1.structure.ObjectGroups",
        ],
        "fields": [
            ("USAGE_LIMITS", "usageLimits", "UsageLimits"),
            ("OPERATIONS", "operations", "Operations"),
            # managedObjects field uses FQN to avoid java.util.Objects conflict
            ("OBJECTS", "managedObjects", "org.purplebean.kmip.model.v2_1.structure.Objects"),
            ("OBJECT_GROUPS", "objectGroups", "ObjectGroups"),
        ],
    },
    "Rights": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.structure.Right",
        ],
        "fields": [
            ("RIGHT", "right", "Right"),
        ],
    },
    "RngParameters": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.type.PredictionResistance",
        ],
        "fields": [
            ("RNG_ALGORITHM", "rngAlgorithm", "RngAlgorithm"),
            ("CRYPTOGRAPHIC_ALGORITHM", "cryptographicAlgorithm", "CryptographicAlgorithm"),
            ("CRYPTOGRAPHIC_LENGTH", "cryptographicLength", "CryptographicLength"),
            ("HASHING_ALGORITHM", "hashingAlgorithm", "HashingAlgorithm"),
            ("DRBG_ALGORITHM", "drbgAlgorithm", "DrbgAlgorithm"),
            ("RECOMMENDED_CURVE", "recommendedCurve", "RecommendedCurve"),
            ("FIPS186_VARIATION", "fips186Variation", "Fips186Variation"),
            ("PREDICTION_RESISTANCE", "predictionResistance", "PredictionResistance"),
        ],
    },
    "ValidationInformation": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.type.*",
        ],
        "fields": [
            ("VALIDATION_AUTHORITY_TYPE", "validationAuthorityType", "ValidationAuthorityType"),
            ("VALIDATION_AUTHORITY_COUNTRY", "validationAuthorityCountry", "ValidationAuthorityCountry"),
            ("VALIDATION_AUTHORITY_URI", "validationAuthorityUri", "ValidationAuthorityUri"),
            ("VALIDATION_VERSION_MAJOR", "validationVersionMajor", "ValidationVersionMajor"),
            ("VALIDATION_VERSION_MINOR", "validationVersionMinor", "ValidationVersionMinor"),
            ("VALIDATION_TYPE", "validationType", "ValidationType"),
            ("VALIDATION_LEVEL", "validationLevel", "ValidationLevel"),
            ("VALIDATION_CERTIFICATE_IDENTIFIER", "validationCertificateIdentifier", "ValidationCertificateIdentifier"),
            ("VALIDATION_CERTIFICATE_URI", "validationCertificateUri", "ValidationCertificateUri"),
            ("VALIDATION_VENDOR_URI", "validationVendorUri", "ValidationVendorUri"),
            ("VALIDATION_PROFILE", "validationProfile", "ValidationProfile"),
        ],
    },
    # core structure
    "RandomNumberGenerator": {
        "extra_imports": [
            "org.purplebean.kmip.model.v2_1.structure.RngParameters",
        ],
        "fields": [
            ("RNG_PARAMETERS", "rngParameters", "RngParameters"),
        ],
    },
}

TODO_PATTERN = re.compile(
    r'(\s*)// TODO: Implement setting values on the builder based on the tag\n'
    r'.*?// \}',
    re.DOTALL
)


def build_json_xml_switch(fields: list, indent: str = "        ") -> str:
    lines = [f"{indent}KmipTag.Value nodeTag = KmipTag.fromName(tag);"]
    lines.append(f"{indent}switch (nodeTag) {{")
    for tag_const, builder_method, type_class in fields:
        # Use FQN inline if type_class contains dots (to avoid import conflicts)
        lines.append(
            f"{indent}    case KmipTag.Standard.{tag_const} -> "
            f"builder.{builder_method}(ctxt.readValue(p, {type_class}.class));"
        )
    lines.append(f"{indent}    default -> throw new IllegalArgumentException(\"Unsupported tag: \" + nodeTag);")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def build_ttlv_switch(fields: list, indent: str = "        ") -> str:
    lines = [f"{indent}KmipTag.Value nodeTag = KmipTag.fromBytes(tag);"]
    lines.append(f"{indent}switch (nodeTag) {{")
    for tag_const, builder_method, type_class in fields:
        lines.append(
            f"{indent}    case KmipTag.Standard.{tag_const} -> "
            f"builder.{builder_method}(mapper.readValue(p, {type_class}.class));"
        )
    lines.append(f"{indent}    default -> throw new IllegalArgumentException(\"Unsupported tag: \" + nodeTag);")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def add_imports(content: str, extra_imports: list) -> str:
    if not extra_imports:
        return content
    # Find position after existing imports (last import statement)
    last_import_match = None
    for m in re.finditer(r'^import .*;$', content, re.MULTILINE):
        last_import_match = m
    if not last_import_match:
        return content
    pos = last_import_match.end()
    # Build import block for imports not already present
    new_imports = []
    for imp in extra_imports:
        imp_stmt = f"import {imp};"
        if imp_stmt not in content:
            new_imports.append(imp_stmt)
    if not new_imports:
        return content
    insert = "\n" + "\n".join(new_imports)
    return content[:pos] + insert + content[pos:]


def fix_file(path: Path, struct_name: str, is_ttlv: bool) -> bool:
    content = path.read_text()
    if "// TODO: Implement" not in content:
        return False  # already fixed or not a stub

    info = STRUCTURES[struct_name]
    fields = info["fields"]
    extra_imports = info["extra_imports"]

    if is_ttlv:
        switch_body = build_ttlv_switch(fields)
    else:
        switch_body = build_json_xml_switch(fields)

    new_content = TODO_PATTERN.sub(
        lambda m: m.group(1) + switch_body,
        content,
        count=1
    )

    if new_content == content:
        print(f"  WARNING: Pattern not matched in {path}", file=sys.stderr)
        return False

    new_content = add_imports(new_content, extra_imports)
    path.write_text(new_content)
    return True


def main():
    codec_dirs = {
        "json": ROOT / "src/main/java/org/purplebean/kmip/codec/json/deserializer/model",
        "xml":  ROOT / "src/main/java/org/purplebean/kmip/codec/xml/deserializer/model",
        "ttlv": ROOT / "src/main/java/org/purplebean/kmip/codec/ttlv/deserializer/model",
    }

    fixed = 0
    for struct_name, info in STRUCTURES.items():
        for codec, base_dir in codec_dirs.items():
            is_ttlv = (codec == "ttlv")
            # Search recursively under base_dir for the file
            pattern = f"**/{struct_name}{codec.upper() if codec != 'ttlv' else 'Ttlv'}Deserializer.java"
            # Use more flexible glob
            candidates = list(base_dir.rglob(f"{struct_name}*Deserializer.java"))
            candidates = [c for c in candidates if codec.capitalize() in c.name or (codec == 'ttlv' and 'Ttlv' in c.name)]
            if not candidates:
                print(f"  NOT FOUND: {struct_name} / {codec}")
                continue
            for path in candidates:
                if fix_file(path, struct_name, is_ttlv):
                    print(f"  FIXED: {path.relative_to(ROOT)}")
                    fixed += 1
                else:
                    print(f"  SKIPPED: {path.relative_to(ROOT)}")

    print(f"\nTotal fixed: {fixed}")


if __name__ == "__main__":
    main()
