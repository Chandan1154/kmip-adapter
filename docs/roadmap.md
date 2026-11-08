# Roadmap

Open work, summarized from `_bmad-output/planning-artifacts/epics.md` (re-baselined 2026-11-08;
that file has acceptance criteria and `_bmad-output/implementation-artifacts/sprint-status.yaml`
tracks status). Verify against the code before starting; this page can lag.

## KMIP 1.2
No functional gaps. Keep `KmipV12VerificationTest` green while shared types change.

## KMIP 2.1
1. Add capability, profile, validation, RNG and protection-storage-mask information and client
   registration methods to `QueryOpResponsePayload` (the only functional gap).
2. Decide on `ClusterInfo` (tag exists, no class).
3. Audit `supportedVersions` on `model/v2x1/type/*` (about 149 `TODO: Adjust supported versions`).
4. Fix enum description strings (`CryptographicAlgorithm` first).
5. Audit SPI registrations and add a test that fails on unregistered types.
6. Regenerate the gap and coverage reports.

## KMIP 3.0 (after the 2.1 work, which it shares types with)
1. Negative tests that reserved/removed tags are rejected under `V3_0`.
2. Field-by-field check of the 3.0 Query response and the new payloads
   (Create User/Group/Credential, Deactivate, Obliterate).
3. `supportedVersions` audit of 3.0-only enums and structures.

## Cross-cutting
- Re-enable or delete the `@Disabled` debug tests in `KmipV21VerificationTest`.
- Generated code still needs its wildcard imports replaced before it passes checkstyle (kept on
  purpose so devs can reach any model class while filling stubs).
- Fix TTLV reading through message interfaces ([Messages](guides/messages.md#quirks-to-know)).

Want to help? Start with [Your first contribution](guides/first-contribution.md).
