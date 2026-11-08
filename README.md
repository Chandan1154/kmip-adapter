# KMIP Adapter

[![Java 21](https://img.shields.io/badge/Java-21-orange.svg)](https://openjdk.org/projects/jdk/21/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](LICENSE)

A Java 21 library of typed [KMIP](https://docs.oasis-open.org/kmip/spec/) data types (enumerations,
attributes, structures, operation payloads) with TTLV, JSON and XML codecs. Covers KMIP 1.2 through
3.0; the active version is selected per thread.

> Status: `1.0-SNAPSHOT`, not published to Maven Central. Enumerations, structures and operation
> payloads for KMIP 1.2, 2.1 and 3.0 are implemented; the message layer is generic
> (`Simple*`) and the Query response lacks capability structures. Open work:
> `_bmad-output/planning-artifacts/epics.md`; regenerate coverage via
> [Tooling](docs/guides/tooling.md#spec-coverage-reports).

## Install

Build and install locally, then depend on it:

```bash
mvn install -DskipTests
```

```xml
<dependency>
  <groupId>org.purplebean</groupId>
  <artifactId>kmip-adapter</artifactId>
  <version>1.0-SNAPSHOT</version>
</dependency>
```

Lombok is `provided`; consumers do not need it.

## Quick start

```java
KmipInitializer.initialize();            // 1. register all types BEFORE setting a spec
KmipContext.setSpec(KmipSpec.V1_2);      // 2. pick the KMIP version for this thread
try {
  var mapper = KmipCodecManager.createJsonMapper();
  ProtocolVersion version = ProtocolVersion.of(1, 2);

  String json = mapper.writeValueAsString(version);
  ProtocolVersion back = mapper.readValue(json, ProtocolVersion.class);
} finally {
  KmipContext.clear();                   // 3. reset the thread
}
```

```json
{"tag":"ProtocolVersion","type":"Structure","value":[
  {"tag":"ProtocolVersionMajor","type":"Integer","value":1},
  {"tag":"ProtocolVersionMinor","type":"Integer","value":2}]}
```

Step 1 matters: types register themselves in static initializers using the *current* spec, so a
spec set too early makes class loading fail. See [Versioning](docs/guides/versioning.md).

More samples (XML, TTLV, enums, attributes): [examples](docs/guides/examples.md). Every sample is
executed by `DocumentationExamplesTest`.

## Documentation

| Doc | Read it for |
|---|---|
| [Getting started](docs/guides/getting-started.md) | Requirements, build, first round trip |
| [Concepts](docs/guides/concepts.md) | `KmipDataType`, structures, enumerations, attributes, registries |
| [Versioning](docs/guides/versioning.md) | `KmipSpec`, `KmipContext`, `supportedVersions`, init order |
| [Serialization](docs/guides/serialization.md) | JSON / XML / TTLV shapes and mappers |
| [Examples](docs/guides/examples.md) | Verified, copy-pasteable samples |
| [Messages](docs/guides/messages.md) | Build a Create request, read it back, known quirks |
| [Troubleshooting](docs/guides/troubleshooting.md) · [Glossary](docs/guides/glossary.md) | Common errors; KMIP terms |
| [First contribution](docs/guides/first-contribution.md) | Worked tutorial: add an enum |
| [Roadmap](docs/roadmap.md) | Open work per KMIP version |
| [Architecture](docs/guides/architecture.md) | Package layout, SPI wiring, request/response API |
| [Extending](docs/guides/extending.md) | Adding enums, data types, structures with the generator |
| [Testing](docs/guides/testing.md) | Test suites, coverage, benchmarks |
| [Tooling](docs/guides/tooling.md) | Make/Task/just, scripts, spec scrapers, Claude agents |
| [Contributing](docs/guides/contributing.md) | Rules, branches, commits, checks |

## Build and test

```bash
mvn test                       # unit tests (checkstyle runs in validate)
mvn test -Dtest=ProtocolVersionTest
mvn -Pcoverage-strict verify   # JaCoCo gate: 60% line, 50% branch
mvn -Pperf verify              # JMH benchmarks
```

`make`, `task` and `just` wrap the same commands; see [Tooling](docs/guides/tooling.md).

## License

LGPL v3, see [LICENSE](LICENSE). Contribution rules: [contributing guide](docs/guides/contributing.md).
