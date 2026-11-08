# Tooling

## Task runners

`Makefile`, `Taskfile.yml` and `justfile` expose the same targets (`help` lists them):

| Target | Runs |
|---|---|
| `tests` / `test-unit` | `mvn -q test` |
| `test-class TEST=Name` | `mvn test -Dtest=Name` |
| `coverage` | `mvn -DskipTests jacoco:report` |
| `perf`, `perf-fast` | `mvn -DskipTests verify -P perf[-fast]`; the `-Dbench.threads/wi/mi/...` flags these targets pass are read only by `JmhBenchmarkRunner`, not the profiles (use `-Dbench.args`) |
| `perf-runner` | JMH via `JmhBenchmarkRunner` (honors `-Dbench.*`) |
| `build`, `clean`, `install`, `format` | Maven equivalents |
| `ci-*` (`ci-all`, `ci-all-fast`) | Clean, build, tests, perf, coverage, package artifacts |

Maven is the source of truth; pick one runner, they are interchangeable.

## Maven profiles

| Profile | Effect |
|---|---|
| `coverage-strict` | JaCoCo check: 60% line, 50% branch |
| `with-integration` | Includes `@Tag("integration")` tests |
| `perf` / `perf-fast` | JMH benchmark runs |

Checkstyle (`config/checkstyle/google_checks.xml`, suppressions alongside) runs at `validate` on
main and test sources.

## Code generation

`scripts/generators/generate.sh`: see [Extending](extending.md). Templates in
`scripts/generators/templates/`; shared helpers in `scripts/common.sh`.

## Spec coverage reports

| Script | Output |
|---|---|
| `docs/kmip-spec/scrape_kmip_all_versions.py` | `docs/kmip-spec/kmip-all-versions-data.json`, `docs/kmip-pending-implementation.md` |
| `docs/kmip-spec/compare_kmip_enumerations.py` | `docs/kmip-spec/kmip-enumerations-comparison.csv` |
| `scripts/chunk_kmip_spec.py` | `docs/kmip-spec/chunks/` (small per-entity files; cheaper to read than the big JSON/MD) |
| `scripts/kmip-coverage-report.py` | `docs/kmip-coverage/v*.md` (model + codec presence per version) |
| `scripts/audit_supported_versions.py` | Drift report for enum `supportedVersions` (`--json`, `--fail-on-drift`) |
| `scripts/kmip-spec-scraper-v*.py`, `kmip-testcases-scraper-v3.0.py` | Raw spec/test-case scrapers |
| `scripts/comprehensive_enum_sync.py` | CSV to enum sync through the generator |
| `scripts/fix-codec-stubs.py`, `scripts/fix_deserializer_stubs.py` | One-off repair helpers for generated stubs |

Generated files in `docs/` are outputs; regenerate rather than edit. Run scripts from the repo
root.

## Claude Code agents and skills (`.claude/`)

Optional automation, described in [`.claude/README.md`](../../.claude/README.md): agents
(`kmip-spec-analyst`, `kmip-pm`, `kmip-architect`, `kmip-type-developer`, `kmip-test-engineer`,
`kmip-codec-registrar`) and skills (`kmip-add-enum`, `kmip-add-structure`, `kmip-add-operation`,
`kmip-scrape-spec`, `kmip-chunk-spec`, `kmip-implementation-status`, `kmip-version-audit`,
`kmip-fix-tc-failures`, `bmad-generate-kmip-code`). They wrap the scripts above; nothing
in the build depends on them.
