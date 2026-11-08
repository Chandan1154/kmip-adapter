# Getting started

## Requirements

- JDK 21
- Maven 3.6+ (Maven wrapper is not used)
- Lombok is needed only to build the library (`provided` scope)

Runtime dependencies: Jackson (`databind`, `annotations`, `core`, `dataformat-xml`,
`datatype-jsr310`) and Apache `commons-text`. Spring is test-only.

## Build

```bash
git clone https://github.com/purplebean/kmip-adapter.git
cd kmip-adapter
mvn install -DskipTests     # compile + checkstyle, install to ~/.m2
mvn test                    # run the unit tests
```

Checkstyle (Google style, severity `error`) runs during `validate` and covers test sources, so a
style violation fails the build before compilation.

## First round trip

```java
import org.purplebean.kmip.api.KmipContext;
import org.purplebean.kmip.api.KmipInitializer;
import org.purplebean.kmip.api.KmipSpec;
import org.purplebean.kmip.codec.KmipCodecManager;
import org.purplebean.kmip.model.core.structure.ProtocolVersion;

KmipInitializer.initialize();
KmipContext.setSpec(KmipSpec.V1_2);
try {
  var json = KmipCodecManager.createJsonMapper();
  ProtocolVersion version = ProtocolVersion.of(1, 2);
  String text = json.writeValueAsString(version);
  ProtocolVersion back = json.readValue(text, ProtocolVersion.class);
  assert back.equals(version);
} finally {
  KmipContext.clear();
}
```

Rules to remember:

1. **Initialize before choosing a spec.** `KmipInitializer.initialize()` (or the first use of
   `KmipCodecManager`, which calls it) loads every type listed in
   `META-INF/services/org.purplebean.kmip.api.KmipDataType`. See [Versioning](versioning.md).
2. **Set a spec per thread and clear it.** With no spec, the context is `UnknownVersion`.
3. **Build mappers once.** `KmipCodecManager.createJsonMapper()/createXmlMapper()/
   createTtlvMapper()` return new, fully configured mappers; reuse them.

## Running the demo

`org.purplebean.kmip.Main` serializes a handful of types to JSON, XML and TTLV and prints the
round trips. Run it from your IDE after `mvn compile`.

## Next

[Concepts](concepts.md) · [Serialization](serialization.md) · [Examples](examples.md)
