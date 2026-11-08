---
name: kmip-add-structure
description: Add a missing KMIP structure end-to-end — design fields from the spec, generate boilerplate via scripts/generators/generate.sh structure, fill in field types and getValues(), register SPI entries, and run tests. Trigger when the user says "add KMIP structure X", "implement OtpCredential / PasswordCredential / DeactivationReason", or picks a structure from kmip-pending-implementation.md §7.1.
---

# Add a missing KMIP structure

End-to-end workflow for implementing one of the missing structures listed in `docs/kmip-pending-implementation.md` §7.1 — most are v3.0 additions (typed Link replacements, credential variants, deactivation, etc.).

## Inputs needed from user
- **Structure name** (PascalCase)
- (Optional) `--module` if version-scoped (e.g., `v3x0`)
- (Optional) `-s <sub-package>` for nested categorization (e.g., `link` for the typed-link family)
- (Optional) `--attr` if the structure also implements `KmipAttribute`

## Steps

### 1. Pull spec entry
**Prefer chunks** to save tokens:
- `docs/kmip-spec/chunks/pending/07-missing-and-changed-structures.md` for the §7.1 row + §7.2 breaking-change notes (a few KB vs 140 KB).
- `docs/kmip-spec/chunks/tags/<tag-slug>.json` for tag coverage and reserved-in-version flags.

If chunks are missing, run the `kmip-chunk-spec` skill first. Extract:
- Tag (hex, e.g., `0x4201A1`)
- Field list in spec order, each with: name, type (KMIP child type or primitive), optionality, repeatability
- The KMIP version(s) this structure is valid in

### 2. Read a peer structure
Identify a structurally similar existing class:
- For credential-family: `Credential.java` and its existing variants
- For typed-link family: any existing link class (or `Link.java` if still present pre-deprecation)
- For generic structures: `Certificate.java` or `KeyWrappingData.java`

Note the conventions:
- `@Data @Builder(toBuilder = true)` on the class
- `private static final KmipTag kmipTag = KmipTag.Standard.<NAME>.inst();`
- `private static final Set<KmipSpec> supportedVersions = Set.of(...);`
- Static block calling `KmipDataType.register(spec, tag, encodingType, Class.class)`
- `@NonNull` on required fields, plain on optional
- `getValues()` returning the child `KmipDataType` list in spec order (drives serialization)
- `validate()` enforcing cross-field invariants

### 3. Dry-run the generator
```bash
cd "$(git rev-parse --show-toplevel)"
./scripts/generators/generate.sh structure <Name>          # default module=core
./scripts/generators/generate.sh structure -m v3x0 <Name>  # version-scoped
./scripts/generators/generate.sh structure -s link <Name>  # nested sub-package
```

### 4. Real generation
Add `--all` (or specific flags) and re-run:
```bash
./scripts/generators/generate.sh structure --module <m> [-s <subpkg>] [--attr] --all <Name>
```
Creates:
- Model class at `src/main/java/.../model/<m>/structure[/subpkg]/<Name>.java`
- Domain test
- 3× serializer + 3× deserializer (the deserializers use structure-specific templates `Structure{Ttlv,Json,Xml}Deserializer.java.template` that scaffold a `setValue(field, ...)` switch)
- 3× codec test
- 1× benchmark subject
- SPI entries

### 5. Fill in the field list
Open the generated `<Name>.java`. Add each field as:
```java
@NonNull          // omit for optional fields
private final FieldType fieldName;
```
For repeatable fields, use `List<FieldType>` (with Lombok `@Singular` on the `@Builder` to get convenient builder methods).

### 6. Implement `getValues()`
Return the list of child `KmipDataType` instances in spec order. Skip null optional fields. This list drives all three codecs.

### 7. Fill the deserializer builder
Each of the three generated `<Name>{Ttlv,Json,Xml}Deserializer.java` has a `setValue(builder, kmipTag, value)` switch — add a case for each field tag, deserialize to the field's type, and call `builder.<fieldName>(value)`.

### 8. Verify SPI + build + tests
```bash
grep -nH "<Name>" src/main/resources/META-INF/services/* src/test/resources/META-INF/services/*
mvn -q compile test-compile
mvn -q test -Dtest=<Name>Test,<Name>TtlvTest,<Name>JsonTest,<Name>XmlTest
```

### 9. Cross-version handling
If the structure replaces a deprecated tag (per §7.2 of the pending doc — e.g., the v3.0 typed-link family replaces generic `Link`), also:
- Confirm the deprecated class either restricts its `supportedVersions` to exclude the new version, OR throws from `validate()` when invoked under the new version's context.
- Add a regression test that asserts the new structure throws under a version where it is not yet defined.

### 10. Report
Files created, test results, breaking-change notes the architect should follow up on.

## Hard rules

- **Always confirm the structure's KMIP tag from `kmip-all-versions-data.json`** before editing — the project's `KmipTag.Standard.<NAME>` enum entry must exist. If it doesn't, that's a missing-tag bug; surface it before implementing the structure.
- **Always implement `getValues()` in spec order** — the order is part of the wire contract for TTLV.
- **For typed-link family structures**, prefer a shared sub-package (`-s link`) — the architect should have made this call; if not, ask.
- **Never inline a child structure's field list** — child types must be their own classes (composition over inlining), even if it means creating a small companion class first.
- **Always run targeted `mvn -Dtest=...`** before declaring done.
