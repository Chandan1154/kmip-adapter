# Versioning

## `KmipSpec`

`UnknownVersion`, `UnsupportedVersion`, `V1_0`, `V1_1`, `V1_2`, `V1_3`, `V1_4`, `V2_0`, `V2_1`,
`V3_0`. `KmipSpec.fromValue(ProtocolVersion)` maps a wire version to a spec and throws
`NoSuchElementException` for unknown pairs. `toString()` is `V1.2`.

## `KmipContext`

A `ThreadLocal<KmipSpec>`, default `UnknownVersion`.

```java
KmipContext.setSpec(KmipSpec.V2_1);                 // null clears
KmipContext.getSpec();
KmipContext.clear();
KmipContext.withSpec(KmipSpec.V3_0, () -> /* ... */); // restores the previous spec afterwards
```

`withSpec` takes a `Supplier`, not a `Runnable`, so it returns a value and cannot throw checked
exceptions; wrap `IOException` yourself or use `setSpec` / `finally { clear(); }`.

The context is per thread. Executors, `CompletableFuture`s and virtual threads do **not** inherit
it; set it inside the task.

## What the spec affects

- **Construction:** most types call `isSupported()` in their constructor and throw
  `IllegalArgumentException("Unsupported object type for V1.0: ...")` when the current spec is not
  in the type's `supportedVersions`.
- **Lookup:** all registries are keyed by spec, so a tag read under V1.2 resolves to a different
  class (or none) than under V2.1.
- **Enumeration values:** `fromValue`/`fromName` reject values not supported in the current spec.

## `supportedVersions`

Every type declares `private static final Set<KmipSpec> supportedVersions`. `UnknownVersion` is
included for types usable without a spec; it is never registered in the registries. Tag and
enumeration-value version sets are checked against the OASIS specs by
`scripts/audit_supported_versions.py` (see [Tooling](tooling.md)).

## Initialization order (important)

Registration runs in static initializers and evaluates tags under whatever spec the **current
thread** has at class-load time. If the spec is set first, loading can fail, for example:

```
IllegalArgumentException: Value 'ClientRegistrationMethod' for KmipTag is not supported
for KMIP spec V1.2
```

So:

```java
KmipInitializer.initialize();        // while the context is still UnknownVersion
KmipContext.setSpec(KmipSpec.V1_2);
```

Touching `KmipCodecManager` first has the same effect. Threads other than the one that triggered
initialization are fine, since registries are global.

## Source layout by version

| Package | Contents |
|---|---|
| `model/core` | Types shared by many versions (the 1.2 base set; the generator defaults to this module) |
| `model/v1x2` | 1.2-only structures and operation payloads |
| `model/v2x1` | Types introduced in 2.0/2.1 (also valid in 3.0 where tagged) |
| `model/v3x0` | Types introduced in 3.0 |

The package says where a type was introduced; `supportedVersions` is the source of truth for
where it is valid (for example `ActivationDate` is tagged 1.2, 1.3, 1.4, 2.0, 2.1 and 3.0).

## Message-level types

`RequestMessageStructure` / `ResponseMessageStructure` (and header, batch item, payload) are
interfaces with per-spec registries. The bundled `SimpleRequestMessage`/`SimpleResponseMessage`
families are generic implementations registered for `UnknownVersion` only; `SimpleRequestHeader`
rejects other specs. Treat them as scaffolding, not a finished protocol layer.
