# Architecture

## Package layout

`src/main/java/org/purplebean/kmip/`

| Package | Contents |
|---|---|
| `api/` | Contracts and registries: `KmipDataType`, `KmipStructure`, `KmipEnumeration`, `KmipAttribute`, `KmipMaskType`, `KmipTag`, `EncodingType`, `KmipSpec`, `KmipContext`, `KmipInitializer`, `ManagedObject`, key/credential value interfaces |
| `api/request`, `api/response` | Message-level interfaces: `Request/ResponseMessageStructure`, `...HeaderStructure`, `...BatchItemStructure`, `...PayloadStructure`, each with per-spec registries |
| `model/core` | Shared types: `enumeration/`, `type/`, `structure/` (incl. `request/`, `response/` generic message classes) |
| `model/v1x2`, `model/v2x1`, `model/v3x0` | Types and operation payloads introduced in that version; payloads sit in `structure/{request,response}/payload/` named `<Operation>Op{Request,Response}Payload` |
| `codec/` | `KmipCodecManager` plus `ttlv/`, `json/`, `xml/` (each with `serializer/`, `deserializer/` and a `Kmip<Format>Module`) |
| `util/` | `StringUtils` (PascalCase to Title Case for attribute names) |
| `Main` | Demo entry point |

Tests mirror this under `src/test/java` (see [Testing](testing.md)).

## Design rules

- **Interface-driven.** Codecs only know `KmipDataType` and its sub-interfaces plus the registries.
- **Immutable value objects.** Lombok `@Data @Builder(toBuilder = true)`, final `@NonNull` fields,
  validation in a private constructor.
- **Self-registering types.** Each class registers itself in a `static {}` block per supported
  spec. There is no central switch statement to edit.
- **Spec is ambient state.** `KmipContext` (thread-local) is consulted by constructors, registries
  and codecs rather than passed as a parameter.
- **Spec names are preserved.** Class and field names transcribe the OASIS names, including
  abbreviations; `config/checkstyle/checkstyle-suppressions.xml` documents the exceptions.

## Wiring: how a type becomes known

1. The class has a `kmipTag`, `encodingType`, `supportedVersions` and a `static {}` registration.
2. Its fully-qualified name is a line in
   `src/main/resources/META-INF/services/org.purplebean.kmip.api.KmipDataType`.
   `KmipInitializer` reads that file and `Class.forName`s each line (it is not a `ServiceLoader`
   call, despite the SPI file layout).
3. For each format, a serializer and a deserializer class exist and are listed in the format's
   SPI files (`...KmipDataType{Json,Xml,Ttlv}{Serializer,Deserializer}`), which the
   `Kmip<Format>Module` loads.
4. For tests, a benchmark subject is listed in
   `src/test/resources/META-INF/services/org.purplebean.kmip.benchmark.api.KmipBenchmarkSubject`.

A fully wired type therefore appears in 7 main SPI files (data type + 6 codec classes) and 1 test
SPI file. `scripts/generators/generate.sh` writes all of them; a type missing from the first file
is silently ignored by readers.

## Read path

```
bytes/text --> Kmip<Format>Module --> tag + type
           --> KmipDataType.getClassFromRegistry(tag, type)   // uses KmipContext spec
           --> <Type><Format>Deserializer --> builder --> validated instance
```

Structures are read by iterating child nodes and dispatching on child tag in `setValue`.
Attributes are rebuilt through `KmipAttribute.ATTRIBUTE_BUILDER_REGISTRY`; enumerations through
`KmipEnumeration.FROM_VALUE_REGISTRY` / `FROM_NAME_REGISTRY`.

## Write path

```
instance --> <Type><Format>Serializer --> tag, type name, value (children via getValue())
```

## Request/response layer

`RequestMessageStructure`, `RequestHeaderStructure`, `RequestBatchItemStructure` and
`RequestPayloadStructure` (and the `Response` mirror) are interfaces. Payload implementations
register against `(spec, Operation)`. Generic `Simple*` implementations exist for
`UnknownVersion`. Operation payloads exist for the KMIP 1.2, 2.1 and 3.0 operations. Known gap: the Query response
does not yet carry the capability/profile/validation structures. Open work is tracked in
`_bmad-output/planning-artifacts/epics.md`; the generated
[pending-implementation report](kmip-pending-implementation.md) can lag behind, so regenerate it
before trusting it.
