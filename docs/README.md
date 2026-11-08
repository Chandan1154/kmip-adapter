# Documentation

Start with the [root README](../README.md).

## Guides (`guides/`, hand-written)

**Using the library**
1. [Getting started](guides/getting-started.md)
2. [Concepts](guides/concepts.md)
3. [Versioning](guides/versioning.md): read before writing code that sets a spec
4. [Serialization](guides/serialization.md)
5. [Examples](guides/examples.md)
6. [Building request and response messages](guides/messages.md)
7. [Troubleshooting](guides/troubleshooting.md) and [Glossary](guides/glossary.md)

**Contributing**
1. [Contributing](guides/contributing.md): rules, workflow, commits
2. [Your first contribution](guides/first-contribution.md): worked tutorial
3. [Architecture](guides/architecture.md)
4. [Extending](guides/extending.md): enums, data types, structures
5. [Testing](guides/testing.md) and [Tooling](guides/tooling.md)
6. [Roadmap](roadmap.md): what is still open

## Generated reference (regenerate, do not hand-edit)

| Path | Produced by |
|---|---|
| `kmip-pending-implementation.md` | `kmip-spec/scrape_kmip_all_versions.py` |
| `kmip-implementation-inventory.json` | inventory tooling |
| `kmip-coverage/` | `scripts/kmip-coverage-report.py` |
| `kmip-spec/` | scraped OASIS spec data, `chunks/`, test-case HTML (scrapers live here and are referenced by scripts and skills, so they are not moved) |

Code samples in the guides are executed by
`src/test/java/org/purplebean/kmip/documentation/DocumentationExamplesTest.java`. Change an example
and its test in the same commit.
