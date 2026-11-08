---
name: kmip-chunk-spec
description: Re-run the spec chunker to split the 575 KB kmip-all-versions-data.json and 140 KB kmip-pending-implementation.md into ~500 small per-entity files under docs/kmip-spec/chunks/, so future agent/skill reads consume far fewer tokens. Trigger after `kmip-scrape-spec`, when pending implementation doc is regenerated, or when the chunks/ index is missing/stale.
---

# Re-chunk KMIP spec sources for token-efficient agent reads

The chunker (`scripts/chunk_kmip_spec.py`) splits two large source files into per-entity slices that agents/skills should prefer over the source.

## What gets chunked

| Source | Size | Chunked into |
|---|---|---|
| `docs/kmip-spec/kmip-all-versions-data.json` | ~575 KB | `chunks/enumerations/<slug>.{json,md}` (~65 enums × 1–11 KB) + `chunks/tags/<slug>.json` (~200 tags × ~1 KB) |
| `docs/kmip-pending-implementation.md` | ~140 KB | `chunks/pending/NN-<section>.md` (one file per `## N.` section) + `chunks/operations/<op>.md` (one file per operation in §6) |

## When to use

- **After `kmip-scrape-spec`** — the new scraped JSON must be re-chunked or the chunks fall out of sync.
- **After `docs/kmip-pending-implementation.md` is regenerated** by the scraper.
- **At session start, if `docs/kmip-spec/chunks/index.md` is older than the source files**:
  ```bash
  stat -f %m docs/kmip-spec/chunks/index.md docs/kmip-spec/kmip-all-versions-data.json
  ```
  If the chunks index timestamp is older → rechunk.

## When NOT to use

- Without a corresponding scrape — if the source JSON didn't change, re-chunking is pointless work.
- Inside another skill's main flow when the chunks index already looks fresh.

## Steps

1. **Check the source timestamps** vs `chunks/index.md`. Skip if chunks are newer.
2. **Run the chunker**:
   ```bash
   cd "$(git rev-parse --show-toplevel)"
   python3 scripts/chunk_kmip_spec.py
   ```
   Add `--clean` to wipe `chunks/` first (use when the spec scrape removed entities — otherwise stale chunks linger).
3. **Verify counts** — typical output: ~500 files across `enumerations/`, `tags/`, `pending/`, `operations/`. Sanity-check that `chunks/enumerations/` has at least as many files as the spec has enums.
4. **Update any committed `chunks/` directory** in your branch — the chunker is deterministic but its output is large; commit chunks separately from feature changes for clean diffs.

## Hard rules

- **Never edit chunk files by hand.** They're rebuilt every chunker run. Edit the source (`kmip-all-versions-data.json` is also generated — edit the scraper or its HTML inputs instead).
- **Don't commit chunks/ during routine feature work** unless the source actually changed. Otherwise every PR shows hundreds of file changes.
- **If the chunker errors**, suspect a malformed scraper output — the JSON file is the authority; if its shape changed, the chunker needs updating.

## Token math (why this skill exists)

| Read pattern | Tokens (approx) |
|---|---|
| Load whole `kmip-all-versions-data.json` to look up one enum | ~140k |
| Load `chunks/enumerations/data.json` for the same lookup | ~300 |
| Load whole `kmip-pending-implementation.md` | ~35k |
| Load one section, e.g. `chunks/pending/06-missing-operations.md` | ~1–2k |

A typical "implement enum X" workflow that previously cost ~175k tokens just to research the spec now costs ~2k.
