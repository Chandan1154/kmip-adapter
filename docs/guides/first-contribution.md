# Your first contribution: adding an enumeration

A worked example using a throwaway enum, `TutorialColor`. Every command below was run against this
repository (the example itself was discarded afterwards). For a real type, take the tag, values and
versions from the OASIS spec.

## 0. Check it is actually missing

```bash
grep -n "Tutorial" src/main/java/org/purplebean/kmip/api/KmipTag.java   # no output
python3 docs/kmip-spec/scrape_kmip_all_versions.py                      # refresh the gap report
```

Open `docs/kmip-pending-implementation.md` (or the entity's file under
`docs/kmip-spec/chunks/enumerations/`) and note the tag value, the enum values, and the spec
versions.

## 1. Add the tag

Generated code references `KmipTag.Standard.<UPPER_SNAKE_NAME>`. Add it to
`src/main/java/org/purplebean/kmip/api/KmipTag.java` in tag-value order, with the versions it exists
in:

```java
TUTORIAL_COLOR(0x42FF01, "TutorialColor", KmipSpec.UnknownVersion, KmipSpec.V2_1),
```

(Most standard tags already exist; this step is only needed for new tags.)

## 2. Generate

```bash
scripts/generators/generate.sh enum --all -m v2x1 TutorialColor
```

Creates 12 files (model, 6 codec classes, 4 tests, benchmark subject) and appends to 8 SPI files:
`git status` shows them.

## 3. Fill in the values

In `model/v2x1/enumeration/TutorialColor.java`, replace the TODO in `Standard`:

```java
RED(0x00000001, "Red", KmipSpec.UnknownVersion, KmipSpec.V2_1),
GREEN(0x00000002, "Green", KmipSpec.UnknownVersion, KmipSpec.V2_1);
```

Use the spec's integer values and exact display names (these are the JSON/XML strings). Per-value
version sets matter: a value removed in 3.0 must not list `V3_0`. The generated codec tests use
`Standard.values()[0]` and `[1]`, so an enum needs at least two values for the tests to run.

## 4. Test

```bash
mvn test -Dcheckstyle.skip -Dtest='TutorialColor*'
# Tests run: 16, Failures: 0, Errors: 0
```

## 5. Make it pass checkstyle

Generated sources use 4-space indentation and long lines, so the real build (`mvn test`, checkstyle
at `validate`, severity `error`) rejects them: a fresh generated enum produced 419 violations.
Reformat to Google style (IntelliJ: import the Google Java style scheme and reformat the new files;
look at `State.java` or `ProtocolVersion.java` for the target shape), add Javadoc, then:

```bash
mvn test            # full build including checkstyle
python3 scripts/audit_supported_versions.py     # supportedVersions vs the spec
```

## 6. Finish

- Regenerate reports if the type counts changed (`python3 scripts/kmip-coverage-report.py`).
- Commit with a conventional message, e.g. `feat(model): add TutorialColor enumeration`.
- Open a PR against `develop` and state any AI assistance.

Structures and data types follow the same steps; see [Extending](extending.md) for their extra
edits (fields, `getValue()` order, deserializer `setValue`).
