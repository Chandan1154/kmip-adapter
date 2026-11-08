# Extending the library

Add new spec types with the generator, then fill in what it cannot know. Do not hand-write the
boilerplate: a type touches 12 files (model, 6 codec classes, 4 tests, benchmark subject) and 8 SPI lines.

## 1. Find out what is missing

```bash
python3 docs/kmip-spec/scrape_kmip_all_versions.py   # refresh docs/kmip-pending-implementation.md
```

Read the entity in `docs/kmip-pending-implementation.md` (or its small per-entity file under
`docs/kmip-spec/chunks/`) for tag, fields, and which spec versions include it. The OASIS spec is
the source of truth.

## 2. Generate

```bash
scripts/generators/generate.sh <enum|datatype|structure> [options] <Name>
```

| Option | Meaning |
|---|---|
| `-m, --module <m>` | `core` (default), `v1x2`, `v1x3`, `v1x4`, `v2x0`, `v2x1`, `v3x0`. Sets the package and the initial `supportedVersions` |
| `-s, --sub-package <p>` | Nested sub-package |
| `--attr` | Generate as a `KmipAttribute` |
| `--type <JavaType>` | `datatype` only; wrapped Java type (default `ByteBuffer`) |
| `--all` | Everything below (what you normally want) |
| `--class`, `--json-ser`, `--json-des`, `--xml-ser`, `--xml-des`, `--ttlv-ser`, `--ttlv-des` | Individual main files |
| `--domain-test`, `--json-test`, `--xml-test`, `--ttlv-test`, `--benchmark` | Individual test files |

```bash
scripts/generators/generate.sh enum      --all -m v3x0 DeactivationReasonCode
scripts/generators/generate.sh datatype  --all -m v3x0 --type Integer --attr SomeNewAttribute
scripts/generators/generate.sh structure --all -m v2x1 Constraints
```

Run it from the repository root. `DRY_RUN=true` prints what would be written. The generator creates
the model class, six codec classes, four test classes, a benchmark subject, and appends to every
SPI file.

## 3. Fill in the stub

The generator needs a tag to exist. If `KmipTag.Standard.<NAME>` is missing, add it (tag value and
version set from the spec) before the class compiles.

| Kind | You must edit |
|---|---|
| Enumeration | `Standard` constants with spec integer values and descriptions; `supportedVersions` per value |
| Data type | Validation in `validate()`; attribute capability flags if `--attr` |
| Structure | Fields (`@NonNull` for required), `getValue()` order, the deserializer's `setValue` switch |
| Any | `supportedVersions` set; remove placeholder TODOs |

Structure model sketch (real code: `ProtocolVersion`, `KeyWrappingData`):

```java
@Data
@Builder(toBuilder = true)
public class Example implements KmipStructure {
  public static final KmipTag kmipTag = KmipTag.Standard.EXAMPLE.inst();
  public static final EncodingType encodingType = EncodingType.STRUCTURE;
  private static final Set<KmipSpec> supportedVersions =
      Set.of(KmipSpec.UnknownVersion, KmipSpec.V2_1, KmipSpec.V3_0);

  static {
    for (KmipSpec spec : supportedVersions) {
      if (spec == KmipSpec.UnknownVersion || spec == KmipSpec.UnsupportedVersion) {
        continue;
      }
      KmipDataType.register(spec, kmipTag.getValue(), encodingType, Example.class);
    }
  }

  @NonNull private final UniqueIdentifier uniqueIdentifier;

  @Builder
  private Example(@NonNull UniqueIdentifier uniqueIdentifier) {
    this.uniqueIdentifier = uniqueIdentifier;
    validate();
  }

  @Override
  public KmipDataType[] getValue() {
    return Stream.of(uniqueIdentifier).filter(Objects::nonNull)
        .toArray(KmipDataType[]::new);
  }
  // getKmipTag(), getEncodingType(), isSupported() as in ProtocolVersion
}
```

Rules that bite:

- `supportedVersions` must match the spec; a wrongly widened set emits invalid KMIP for other
  versions. Check with `python3 scripts/audit_supported_versions.py`.
- Field order in `getValue()` is wire order.
- Attributes need `getAttributeName()` (title-cased tag description) and the `of(AttributeName,
  AttributeValue)` factory, registered with `KmipAttribute.register(...)`.
- Fill the generated tests with real values. An empty `builder().build()` on a `@NonNull` model
  throws in `createDefault()`.

## 4. Verify

```bash
mvn test -Dtest='Example*'          # domain + JSON/XML/TTLV round trips
python3 scripts/audit_supported_versions.py
python3 scripts/kmip-coverage-report.py
```

Then run `mvn test` (checkstyle failures abort the build) and refresh the gap report
([Tooling](tooling.md)).

## Vendor extensions at runtime (no code generation)

```java
State.register(0x80000001, "Quarantined", Set.of(KmipSpec.V1_2));   // enumeration value
KmipTag.register(0x540001, "MyVendorTag", Set.of(KmipSpec.V1_2));   // tag, 0x540000-0x54FFFF
```

Both throw `IllegalArgumentException` for out-of-range values or empty descriptions.
