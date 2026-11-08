# Contributing

## Ground rules

- If you use AI, say so in the PR and discussions.
- Understand the project goals first; blindly generated PRs are rejected.
- Docs are reviewed for brevity. Say it once, link instead of repeating.
- Open PRs against `develop` (or a feature branch), never directly to a release branch.

## Workflow

```bash
git clone https://github.com/purplebean/kmip-adapter.git
cd kmip-adapter
git checkout -b feature/<short-name> develop
mvn test                       # must pass, checkstyle included
```

1. Add or change code. New KMIP types: use the generator ([Extending](extending.md)).
2. Add or update tests with real values ([Testing](testing.md)).
3. Update docs if behavior or an example changed, including
   `documentation/DocumentationExamplesTest` when a doc sample changes.
4. Regenerate reports if you added or removed model classes
   (`python3 docs/kmip-spec/scrape_kmip_all_versions.py`, `python3 scripts/kmip-coverage-report.py`).
5. Push and open a PR.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <summary>`;
types `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`. Examples in the
history: `test(checkstyle): fix import ordering across test sources`,
`feat(model): implement ItemType enumeration with full codec and test coverage`.

## Code style

- Google Java Style via Checkstyle (severity `error`, applies to tests); 2-space indent, 100
  columns, Javadoc on public classes and methods.
- Keep OASIS names verbatim; if that trips a naming check, extend the suppression file with a
  comment rather than renaming.
- Never widen a type's `supportedVersions` without checking the spec.

## Issues

Bug reports: library version, KMIP spec version, minimal code, expected vs actual. Feature
requests: the spec section the change implements.

Participation is governed by the [Code of Conduct](../CODE_OF_CONDUCT.md).
