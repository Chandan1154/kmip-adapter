---
stepsCompleted: [step-01, step-02, step-03, step-04]
inputDocuments:
  - docs/kmip-pending-implementation.md
  - docs/kmip-implementation-inventory.json
  - docs/kmip-coverage/
---

# kmip-adapter - Remaining Work (re-baselined 2026-11-08)

All original Epics 1-4 (28 stories: Ticket, Constraints, Defaults, Pkcs11, Login/Logout, Import/Export, Process,
Poll, QueryAsyncRequests, ObjectGroups, CredentialValue, Capability sub-structures, ItemType, test suites, etc.)
were verified against `src/main` and are IMPLEMENTED (models, payloads, TTLV/JSON/XML codecs, tests;
all enumerations present; V12/V21/V30 verification tests pass). Their story files were removed.
This file lists only what is still open, grouped by KMIP version. Epic numbering restarts at 10.

Verified gaps (evidence):
- `QueryOpResponsePayload` (v2x1, shared by 3.0) has no fields for CapabilityInformation, ProfileInformation,
  ValidationInformation, RngParameters, ProtectionStorageMasks, ClientRegistrationMethod; these structures exist but are unwired.
- Tag `CLUSTER_INFO` (0x420134) exists in `KmipTag` but no `ClusterInfo` type class exists.
- ~149 `// TODO: Adjust supported versions` markers in `model/v2x1/type/*` (supportedVersions not audited against spec).
- `CryptographicAlgorithm.java` has `// TODO: fix all enum descriptions`.
- `docs/kmip-pending-implementation.md` section 6.3 ("stub payloads") and `docs/kmip-coverage` warning flags are stale (all payloads are implemented).

## Epic 10: KMIP 1.2 - Maintenance only

No functional gaps found (V12 verification passes; 1.2 coverage 100% complete).

### Story 10.1: Keep 1.2 round-trip regression green while editing shared types
Acceptance: `KmipV12VerificationTest` stays green after Epics 20/21 changes (shared enums/types touched by the audits).

## Epic 20: KMIP 2.1 - Completion

### Story 20.1: Wire capability structures into Query response (was 3.7)
Add CapabilityInformation, ProfileInformation (repeating), ValidationInformation (repeating), RngParameters (repeating),
ProtectionStorageMasks, ClientRegistrationMethod (repeating) to `QueryOpResponsePayload` (builder, `of`, `getValues`, validate), per KMIP 2.1 Query response table.
Acceptance: TTLV/JSON/XML round-trip tests with all fields; spec test-case XML containing Query responses passes in `KmipV21VerificationTest`.

### Story 20.2: Decide and implement ClusterInfo
Check KMIP 2.1 spec (Server Information / Query) for ClusterInfo usage and encoding; add type (kmip-add-structure/-enum skill) or document why tag-only.

### Story 20.3: Audit supportedVersions on v2x1 types (was 4.3)
Resolve all `TODO: Adjust supported versions` in `model/v2x1/type/*` (e.g. AsynchronousCapability, StreamingCapability, CertificateSubject*/Issuer*, Validation*); run `kmip-version-audit` skill.
Acceptance: no TODO markers; no over/under-tagged types vs spec.

### Story 20.4: Fix enumeration description strings (was 4.2)
Resolve `CryptographicAlgorithm` TODO and audit other enums so XML/JSON names match spec text exactly.
Acceptance: round-trip tests pass using spec-sample names for each enum.

### Story 20.5: SPI registration audit (was 4.5)
Verify every KmipDataType and its TTLV/JSON/XML serializer/deserializer is registered in `META-INF/services/*` (currently modified/uncommitted in working tree); add an automated test that fails on unregistered types.

### Story 20.6: Regenerate coverage artifacts
Run `kmip-scrape-spec` and `scripts/kmip-coverage-report.py`; stale stub flags removed. (Coordinate with docs owner.)

## Epic 30: KMIP 3.0 - Completion

Prerequisite: Epic 20 (3.0 shares v2x1 types, QueryOpResponsePayload and enums).

### Story 30.1: Verify 3.0 reserved/removed tags and breaking changes
Confirm (test) that Link/Name sub-tags, Batch Count, Batch Order Option, Unique Batch Item ID, Object Group, Template ObjectType are not emitted/accepted under V3_0 (KmipTag already excludes V3_0 for these).
Acceptance: negative tests per item.

### Story 30.2: 3.0 Query response and operation coverage
After 20.1, confirm 3.0 Query response (incl. new 3.0 fields, if any) and Create User/Group/Credential, Deactivate, Obliterate payloads match the 3.0 spec field-by-field; add spec test-case verification (`KmipV30VerificationTest`) for all 3.0 operation samples.

### Story 30.3: supportedVersions audit of v3x0 types and enums
Run `kmip-version-audit` for 3.0-only enums (Deactivation Reason Code, OTP Algorithm, Object Class, Ephemeral, Split Key Polynomial) and v3x0 structures.

## Cross-cutting cleanup (any version)
- Remove `ZzDocProbe` enum from `src/main` (probe/scratch class) if unused.
- Re-enable or delete the 3 `@Disabled` debug tests in `KmipV21VerificationTest`.
