---
name: kmip-version-audit
description: Audit `supportedVersions` Set across every KMIP enumeration class against the OASIS spec and report drift (over-tagged classes that emit wire-invalid KMIP, or under-tagged classes that reject valid spec versions). Trigger when the user says "audit supportedVersions", "check KMIP version drift", "find over-tagged enums", "are the enums spec-correct", or after adding/editing enum classes.
---

# Audit `supportedVersions` against KMIP spec

Detects two failure modes:

- **Over-tagged** (🔴 spec-correctness bug): a class's `supportedVersions` set includes a `KmipSpec` value where the spec marks the tag/enum as reserved or undefined → serializer emits wire-invalid KMIP for that version.
- **Under-tagged** (🟡 acceptance gap): a class is missing a `KmipSpec` value the spec supports → valid KMIP messages get rejected.

The audit runs `scripts/audit_supported_versions.py` which:

1. Reads `docs/kmip-spec/kmip-all-versions-data.json` and builds `enum name → {spec versions it exists in}`.
2. Walks every `.java` under `src/main/java/.../model/*/enumeration/`, extracts `private static final Set<KmipSpec> supportedVersions = Set.of(...)`.
3. Maps spec versions to project's `KmipSpec` constants (per pending doc §8: 1.3/1.4 → V1_2; 2.0/2.1 → V2_1; 3.0 → V3_0; always add UnknownVersion).
4. Diffs actual vs expected; reports DRIFT / OK / UNMATCHED.

## When to use
- After running `kmip-add-enum` skill — confirm the new enum is OK.
- After editing any enum's `supportedVersions` — confirm no regression.
- As a pre-commit/CI gate.
- When investigating a serialization bug that smells version-related ("works on v2.1, fails on v3.0").

## When NOT to use
- For non-enum types — this audit only covers `KmipEnumeration` subclasses.
- For per-value (`Standard.X.supportedVersions`) drift — only checks class-level. (Per-value audit is a future skill.)

## Steps

### 1. Refresh spec data (if stale)
```bash
cd "$(git rev-parse --show-toplevel)"
# Check if regeneration needed
git log -1 --format='%ai' docs/kmip-spec/kmip-all-versions-data.json
git log -1 --format='%ai' src/main/java/org/purplebean/kmip/model/
```
If the model is newer, invoke the `kmip-scrape-spec` skill first.

### 2. Run the audit
```bash
python3 scripts/audit_supported_versions.py
```
Output: a per-class report grouped into OK / DRIFT / UNMATCHED.

For CI / automated checks:
```bash
python3 scripts/audit_supported_versions.py --fail-on-drift
echo "exit=$?"   # 0 = clean, 1 = drift detected
```

For machine-readable output (e.g., feeding into another tool):
```bash
python3 scripts/audit_supported_versions.py --json > /tmp/audit.json
jq '.[] | select(.status=="DRIFT") | {class, missing, extra}' /tmp/audit.json
```

### 3. Triage each DRIFT entry
For each drifting class:
- **`MISSING in actual`** (under-tagged): add the listed `KmipSpec.*` constants to the Set. Low-risk; verifies more KMIP versions are accepted.
- **`EXTRA in actual`** (over-tagged): remove the listed `KmipSpec.*` constants. Cross-reference §7.2 of `kmip-pending-implementation.md` to flag whether this is a *reserved-tag* breaking change vs. a forward-compat over-promise.

### 4. Fix and re-audit
For bulk edits, use a Python script (see `scripts/audit_supported_versions.py` for the regex on `supportedVersions = Set.of(...)`). After edits, re-run the audit:
```bash
python3 scripts/audit_supported_versions.py --fail-on-drift && echo "clean"
```
Then run targeted tests:
```bash
mvn -q test -Dtest='<EditedClass1>Test,<EditedClass2>Test,...'
```

### 5. Report
Summary to user:
- `N` classes audited
- Before: `X` DRIFT
- After: `Y` DRIFT (ideally 0)
- Per-version-change consequences (which existing tests would now fail if the project ever relied on the over-tagged behavior)
- Followups: per-value `Standard.X.supportedVersions` audit; non-enum classes (structures/attributes) audit.

## Hard rules

- **Never change `supportedVersions` to make a failing test pass.** If a test fails because the class no longer accepts a version, the test was exercising spec-incorrect behavior — fix the test, not the class.
- **Always trust the spec over project history.** If a class has historically included `V1_2` for a v2.0+ enum, that's drift to fix, not "established convention".
- **Per-value `supportedVersions` matter too.** When tightening class-level versions, also tighten any `Standard.X(value, "Name", KmipSpec.<dropped>)` entries that referenced the dropped version. The audit doesn't catch this yet — manually grep:
  ```bash
  grep -nE 'KmipSpec\.<DROPPED>' src/main/java/org/purplebean/kmip/model/core/enumeration/<ClassName>.java
  ```
- **UNMATCHED entries are not always wrong** — `OpaqueDataType` exists in the project but the spec defines no Standard values for it (vendor-extensions only). Investigate before concluding the audit is wrong.
