# Documentation

Start with the [root README](../README.md), then:

**Using the library**
1. [Getting started](getting-started.md)
2. [Concepts](concepts.md)
3. [Versioning](versioning.md) (read before writing any code that sets a spec)
4. [Serialization](serialization.md)
5. [Examples](examples.md)

**Working on the library**
- [Architecture](architecture.md)
- [Extending](extending.md): add enums, data types, structures
- [Testing](testing.md)
- [Tooling](tooling.md)
- [Contributing](contributing.md)

**Generated reference (do not edit by hand)**
- [`kmip-pending-implementation.md`](kmip-pending-implementation.md): spec-vs-code gap report
- [`kmip-coverage/`](kmip-coverage/README.md): per-version list of implemented model classes
- `kmip-spec/`: scraped OASIS spec data, per-entity `chunks/`, test-case HTML
- `kmip-implementation-inventory.json`: machine-readable inventory

Code samples in these docs are executed by
`src/test/java/org/purplebean/kmip/documentation/DocumentationExamplesTest.java`. If you change
an example, change the test in the same commit.
