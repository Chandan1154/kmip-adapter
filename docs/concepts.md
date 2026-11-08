# Concepts

All types live under `org.purplebean.kmip`. The core contracts are in `api/`.

## `KmipDataType`

Root interface. Every KMIP element implements:

| Method | Meaning |
|---|---|
| `getKmipTag()` | The 3-byte KMIP tag (`KmipTag`) |
| `getEncodingType()` | TTLV item type (`EncodingType`: `STRUCTURE`, `INTEGER`, `ENUMERATION`, `DATE_TIME`, ...) |
| `getValue()` | Underlying Java value |
| `isSupported()` | Whether the type is valid under the **current** `KmipContext` spec |

`KmipDataType.TAG_REGISTRY` maps `(KmipSpec, tag, encodingType)` to the implementing class. Codecs
use it to decide which class to instantiate when reading.

## Kinds of types

| Kind | Interface | Package | Example |
|---|---|---|---|
| Primitive wrapper | `KmipDataType` | `model/<v>/type` | `ProtocolVersionMajor`, `ActivationDate` |
| Structure | `KmipStructure` | `model/<v>/structure` | `ProtocolVersion`, `Attribute` |
| Enumeration | `KmipEnumeration` | `model/<v>/enumeration` | `State`, `NameType` |
| Bit mask | `KmipMaskType` | `model/core/type` | `CryptographicUsageMask` |
| Attribute | `KmipAttribute` (also a data type or enumeration) | alongside the above | `ActivationDate`, `State` |
| Operation payload | `RequestPayloadStructure` / `ResponsePayloadStructure` | `model/<v>/structure/{request,response}/payload` | `CreateOpRequestPayload` |

`<v>` is one of `core`, `v1x2`, `v2x1`, `v3x0`; see [Versioning](versioning.md).

### Structures

`KmipStructure.getValue()` returns the ordered `KmipDataType[]` of children; order is the wire
order. Structures are immutable Lombok `@Data @Builder(toBuilder = true)` classes with `@NonNull`
required fields, a private validating constructor, and static `of(...)` factories.

```java
ProtocolVersion v = ProtocolVersion.of(1, 2);   // or builder()
v.getValue();                                   // [ProtocolVersionMajor(1), ProtocolVersionMinor(2)]
```

### Enumerations

Each enumeration is a class wrapping a `Value`. Spec values live in a nested `Standard` enum;
vendor values are created at runtime with `register` and live in `Extension`.

```java
State active = State.Standard.ACTIVE.inst();              // spec value
State custom = State.register(0x80000001, "Quarantined",
    Set.of(KmipSpec.V1_2)).inst();                        // vendor value
```

- Extension integers must be in `0x80000000`-`0xFFFFFFFF` (negative as a Java `int`), otherwise
  `IllegalArgumentException`.
- `register` is idempotent: an existing value or description is returned unchanged.
- `fromValue(int)` / `fromName(String)` only return values supported in the current spec.
- JSON and XML use the value's **description** (`"Active"`, `"UninterpretedTextString"`);
  TTLV uses the integer.

### Attributes

`KmipAttribute` adds capability flags from the spec (`isAlwaysPresent`, `isServerInitializable`,
`isClientInitializable`, `isServerModifiable(State)`, `isClientModifiable(State)`,
`isClientDeletable`, `isMultiInstanceAllowed`) and conversions to the generic KMIP 1.x
`Attribute` form: `getAttributeName()` (title-cased, `"Activation Date"`), `getAttributeValue()`,
`getCanonicalName()`.

`KmipAttribute.ATTRIBUTE_BUILDER_REGISTRY` rebuilds a typed attribute from a generic
`AttributeName` + `AttributeValue` pair, which is how a received `Attribute` structure becomes
an `ActivationDate` again:

```java
ActivationDate.of(attribute.getAttributeName(), attribute.getAttributeValue());
```

### Tags

`KmipTag.Standard` holds every spec tag. Vendor tags (`0x540000`-`0x54FFFF`) are added with
`KmipTag.register(int, String, Set<KmipSpec>)`.

## Registries and static initialization

Each concrete type registers itself in a `static {}` block (`KmipDataType.register`,
`KmipAttribute.register`, `KmipEnumeration.register`, ...) for every spec in its
`supportedVersions`, skipping `UnknownVersion`/`UnsupportedVersion`. Registration is triggered by
`KmipInitializer`, which loads each class named in the SPI file. Consequences:

- A type that is not in the SPI file is invisible to codecs.
- Initialization is global and one-shot, so it must happen under a spec in which every tag
  resolves; do it **before** `KmipContext.setSpec`.
