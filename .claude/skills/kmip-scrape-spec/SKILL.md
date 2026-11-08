---
name: kmip-scrape-spec
description: Re-run the OASIS KMIP spec scraper and refresh docs/kmip-pending-implementation.md so the implementation-gap report reflects the current source tree and the latest spec HTML. Trigger when the user says "refresh KMIP spec coverage", "regenerate pending implementation doc", "what's the latest implementation gap", "scrape KMIP spec", or after adding/removing model classes that would change the ✅/❌ tallies.
---

# Re-scrape KMIP specs and regenerate the pending-implementation report

## When to use
- User asks "what's missing in KMIP" and the timestamp on `docs/kmip-pending-implementation.md` is older than the most recent commit touching `src/main/java/.../model/`.
- User added a new HTML spec file under `docs/kmip-spec/v*/`.
- User just implemented one or more new types and wants the report to mark them ✅.

## When NOT to use
- The user only wants to *read* the existing report — just `Read` the markdown file.
- The user wants enum diffs across versions — that's a different script (`compare_kmip_enumerations.py`).

## Steps

1. **Check the spec HTML files are present.**
   ```bash
   cd "$(git rev-parse --show-toplevel)"
   ls docs/kmip-spec/v1.x/*.html docs/kmip-spec/v2.x/*.html docs/kmip-spec/v3.x/*.html
   ```
   If any expected version is missing, stop and tell the user — the scraper needs all six (`v1.2`, `v1.3`, `v1.4`, `v2.0`, `v2.1`, `v3.0`).

2. **Confirm Python deps.** The scraper uses BeautifulSoup4. If `python3 -c "import bs4"` fails, tell the user to `pip install beautifulsoup4 lxml` rather than installing yourself.

3. **Run the scraper.**
   ```bash
   python3 docs/kmip-spec/scrape_kmip_all_versions.py
   ```
   Expected outputs:
   - `docs/kmip-spec/kmip-all-versions-data.json` (canonical scraped data, ~575KB)
   - `docs/kmip-pending-implementation.md` (rewritten coverage report)

4. **Sanity check the diff.**
   ```bash
   git diff --stat docs/kmip-pending-implementation.md docs/kmip-spec/kmip-all-versions-data.json
   ```
   If the diff is empty, the scrape was a no-op (sources unchanged). If massive, summarize what changed.

5. **Re-chunk the new outputs.** The chunked files under `docs/kmip-spec/chunks/` are now stale — every downstream skill prefers them. Always run:
   ```bash
   python3 scripts/chunk_kmip_spec.py
   ```
   (Equivalently: invoke the `kmip-chunk-spec` skill.) Skipping this step leaves agents/skills reading the giant source files and burning tokens unnecessarily.

6. **Report to the user**:
   - How many enums / structures / operations are now marked MISSING.
   - What changed in this scrape vs. the previous report (use `git diff` on the markdown's §1, §2, §6, §7 tables).
   - Confirm chunks were regenerated.
   - Suggested next skill: `kmip-implementation-status` for a focused summary, or hand to the `kmip-pm` agent for a backlog.

## Hard rules

- **Never edit `kmip-pending-implementation.md` by hand** — the header says "Auto-generated". Hand edits will be wiped on the next scrape and create false confidence.
- **Never re-run the scraper without committing or stashing pending edits** to the generated files first — otherwise their git diff becomes hard to review.
- **The scraper detects implementation status by reading `src/main/java/.../model/`.** If the user adds a class in a non-standard location, the report will show it as MISSING even though it exists. Flag this when you spot a mismatch.
