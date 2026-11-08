---
name: kmip-add-enum
description: Add a missing KMIP enumeration end-to-end — design, generate boilerplate via scripts/generators/generate.sh enum, fill in Standard values, register SPI entries, and run tests. Trigger when the user says "add KMIP enum X", "implement the Data enumeration", "fill in the missing enum Y", or picks an enum item from kmip-pending-implementation.md §2.
---

# Add a missing KMIP enumeration

End-to-end workflow for implementing one of the missing enumerations listed in `docs/kmip-pending-implementation.md` §2 (currently: `Data`, `Item Type`, `Unique Identifier`).

## Inputs needed from user
- **Enum name** (PascalCase or spec title-case — both accepted)
- (Optional) `--module` if the enum is version-scoped instead of `core`
- (Optional) `--attr` if the enum also implements `KmipAttribute` (true when the type appears in the spec's Attribute table)

If any of these are ambiguous, derive defaults from `docs/kmip-pending-implementation.md` and `docs/kmip-spec/kmip-all-versions-data.json`, then confirm with the user once before proceeding.

## Pre-flight: tag-collision check (always run)

KMIP overloads several tags across encoding types — the SAME KMIP tag can carry a Boolean in v1.x and an Enumeration in v2.x+, or a ByteString payload and an Enumeration discriminator in different operations. The project supports this via the `(spec, tag, encodingType)` discriminator on `KmipDataType.register(...)`.

**Before generating, check**:
```bash
NAME=YourEnum   # e.g., Data, UniqueIdentifier, ItemType
# 1. Does the KMIP tag already exist in KmipTag.Standard?
grep -nE "\b${NAME^^/ /_}\b|${NAME^^}\b" src/main/java/org/purplebean/kmip/api/KmipTag.java
# 2. Does any existing Java class already register that tag?
TAG_CONST=$(grep -E "^\s+[A-Z_]+\(0x[0-9A-Fa-f]+, \"${NAME}\"" src/main/java/org/purplebean/kmip/api/KmipTag.java | sed -E 's/^\s+([A-Z_]+).*/\1/')
grep -rn "KmipTag\.Standard\.${TAG_CONST}\.inst()" src/main/java/org/purplebean/kmip/model/
```

**Three outcomes**:

1. **No existing class** — proceed normally. Class lands in `model/core/enumeration/<Name>.java` with a unique class name.

2. **Existing class in a DIFFERENT package + DIFFERENT `encodingType`** — this is the supported dual-encoding pattern. **Reference precedent**: `AsynchronousIndicator`:
   - `model/core/type/AsynchronousIndicator.java` → `EncodingType.BOOLEAN`, supports `V1_2` (legacy form, pre-v2.0 spec)
   - `model/core/enumeration/AsynchronousIndicator.java` → `EncodingType.ENUMERATION`, supports `V2_1, V3_0` (post-v2.0 spec)
   - Same Java class name in both packages; consumers disambiguate by import.
   
   **For the new enum**: place it in `model/core/enumeration/`, give it the same simple class name as the existing peer (e.g., `UniqueIdentifier`), and ensure the `supportedVersions` set has **no overlap** with the existing peer's `supportedVersions` so the runtime registry has a single owner per `(spec, tag, encodingType)` tuple.

3. **Existing class in the SAME package or with conflicting `(spec, encodingType)`** — STOP. Hand back to the architect: the spec is ambiguous or the existing class needs renaming first.

### Naming exception: Java keyword/library collisions

If the spec's bare name collides with a common Java import (e.g., `Data` collides with `lombok.Data` annotation, which every project class uses), use a suffix:
- `Data` → `DataEnumeration` (matches the existing `DataByteString` naming for the same tag, encoding=BYTE_STRING)
- Document the deviation at the top of the new class's Javadoc.

**Currently known collisions** (per audit on 2026-06-21):

| Missing enum | Tag | Existing peer | Suggested new class name |
|---|---|---|---|
| Data | `0x4200C2` | `model/core/type/DataByteString.java` (BYTE_STRING) | `DataEnumeration` (avoids `lombok.Data` collision) |
| Unique Identifier | `0x420094` | `model/core/type/UniqueIdentifier.java` (TEXT_STRING) | `UniqueIdentifier` in `enumeration/` package (matches `AsynchronousIndicator` pattern) |
| Item Type | not yet in `KmipTag.Standard` | none | `ItemType` (add tag first) |

### supportedVersions discipline

The audit on 2026-06-21 found 16 enums had drift between their `supportedVersions` Set and the spec. To avoid re-introducing drift:

- **Always start from the spec** (`kmip-all-versions-data.json` — `data['versions'][i]['enumerations']` lists which enums exist at version `i`), then map to project's Java constants per §8 of `kmip-pending-implementation.md`:
  - Spec v1.2 / v1.3 / v1.4 → `KmipSpec.V1_2`
  - Spec v2.0 / v2.1 → `KmipSpec.V2_1`
  - Spec v3.0 → `KmipSpec.V3_0`
- **Always include `KmipSpec.UnknownVersion`** in the class-level `supportedVersions` (matches every other class in the project).
- **Never copy supportedVersions verbatim** from a sibling enum without re-deriving from the spec — sibling drift propagates.
- **After editing**, run the `kmip-version-audit` skill to confirm the new enum lands at OK status.

## Steps

### 1. Pull the spec entry
**Prefer the chunked file** to save tokens — read `docs/kmip-spec/chunks/enumerations/<slug>.json` (where `<slug>` is the enum name lowercased with non-alphanumerics → `-`). Fall back to the 575 KB `docs/kmip-spec/kmip-all-versions-data.json` only if the chunk file is missing (then run the `kmip-chunk-spec` skill).

Extract from the chunk:
- Tag (hex)
- Full list of `(value, name, description, versions)` tuples
- Supported KMIP versions

If the entry is missing or malformed, stop — recommend running the `kmip-scrape-spec` skill first.

### 2. Read a peer class
For shape conventions, read one of:
- `src/main/java/org/purplebean/kmip/model/core/enumeration/State.java` — full reference, also implements `KmipAttribute`
- `src/main/java/org/purplebean/kmip/model/core/enumeration/ObjectClass.java` — v3.0-only example

Note the static-block registration pattern: `KmipDataType.register`, `KmipAttribute.register` (if applicable), `KmipEnumeration.register`.

### 3. Dry-run the generator
```bash
cd "$(git rev-parse --show-toplevel)"
./scripts/generators/generate.sh enum <Name>
```
(No flags → dry-run.) Confirm the proposed file list looks right.

### 4. Real generation
```bash
./scripts/generators/generate.sh enum --module core [--attr] --all <Name>
```
This creates:
- `src/main/java/.../model/core/enumeration/<Name>.java`
- `src/test/java/.../model/core/enumeration/<Name>Test.java`
- `src/main/java/.../codec/{ttlv,json,xml}/{serializer,deserializer}/model/core/enumeration/<Name>{Ttlv,Json,Xml}{Serializer,Deserializer}.java`
- `src/test/java/.../codec/{ttlv,json,xml}/model/core/enumeration/<Name>{Ttlv,Json,Xml}Test.java`
- `src/test/java/.../benchmark/subjects/model/core/enumeration/<Name>BenchmarkSubject.java`
- SPI entries appended to 7 service files (auto-sorted by `add_service_entry` in `scripts/common.sh`).

### 5. Fill in the `Standard` enum constants
Open the generated `<Name>.java`. Replace the template's placeholder `Standard` values with the real ones from step 1. For each value, supply `(intValue, "Title Case Description", Set.of(KmipSpec.V*, ...))`.

Example shape (mirror `State.java:34-77`):
```java
public enum Standard implements Value {
    DECRYPT(0x00000001, "Decrypt", Set.of(KmipSpec.V2_0, KmipSpec.V2_1, KmipSpec.V3_0)),
    // ...
    ;
    private final int value;
    private final String description;
    private final Set<KmipSpec> supportedVersions;
    // constructor + Value interface methods
}
```

### 6. Update class-level `supportedVersions`
Set the class-level `Set<KmipSpec> supportedVersions` to the union of versions across all `Standard` values, plus `KmipSpec.UnknownVersion`.

### 7. Verify SPI registrations
```bash
grep -nH "<Name>" src/main/resources/META-INF/services/* src/test/resources/META-INF/services/*
```
Expect ≥7 hits (1 master + 3 ser + 3 des, plus 1 benchmark). If any missing, hand off to the `kmip-codec-registrar` agent.

### 8. Compile + run tests
```bash
mvn -q compile test-compile
mvn -q test -Dtest=<Name>Test,<Name>TtlvTest,<Name>JsonTest,<Name>XmlTest
```

### 9. Report
- Files created (count and one sample path per kind)
- Test results
- Whether `docs/kmip-pending-implementation.md` will need a re-scrape (yes — recommend running `kmip-scrape-spec` after `git commit`)

## Hard rules

- **Always read the peer class before editing the generated stub.** The generator's stub is intentionally incomplete; the conventions live in existing classes.
- **Never invent KMIP integer values.** Always source from `kmip-all-versions-data.json`. If a value is ambiguous, stop and surface the ambiguity.
- **`--attr` is non-reversible**: the generator picks a different template. If you guessed wrong, the only fix is to delete the generated files and re-run.
- **Run the targeted `mvn -Dtest=...` subset** before declaring done — full `mvn test` is too slow for a tight inner loop, but a typo in the generated test will fail compile of the whole `test-compile` phase.
