---
name: kmip-implementation-status
description: Summarize what is currently missing in the KMIP adapter — enums, structures, operations, breaking changes — from docs/kmip-pending-implementation.md. Trigger when the user says "what's missing in KMIP", "show implementation gaps", "KMIP implementation status", "what should I implement next", or "what KMIP work is outstanding".
---

# Report KMIP implementation gaps

Quick read-only summary of the current implementation status from `docs/kmip-pending-implementation.md`. Does not run the scraper — use the `kmip-scrape-spec` skill first if the report is stale.

## When to use
- The user wants a quick "what's left" snapshot.
- Preflight before invoking `kmip-add-enum` / `kmip-add-structure` / `kmip-add-operation` to confirm the chosen target is still missing.

## When NOT to use
- The user wants a *prioritized* plan, not just a list — delegate to the `kmip-pm` agent.
- The report itself is stale — run `kmip-scrape-spec` first.

## Steps

### 1. Staleness check
```bash
cd "$(git rev-parse --show-toplevel)"
git log -1 --format='%ai' docs/kmip-pending-implementation.md
git log -1 --format='%ai' src/main/java/org/purplebean/kmip/model/
```
If the model directory is newer than the report, warn the user that counts may be stale and suggest `kmip-scrape-spec`.

### 2. Parse the report sections
**Prefer the chunked per-section files** under `docs/kmip-spec/chunks/pending/` — each section is a few KB instead of the 140 KB full doc. Fall back to `docs/kmip-pending-implementation.md` only if `chunks/pending/` is missing (then run the `kmip-chunk-spec` skill).

Specifically:
- §1 → `chunks/pending/01-enumeration-status.md`
- §2 → `chunks/pending/02-missing-enumeration-classes.md`
- §6 → `chunks/pending/06-missing-operation-request-response-payloads.md` (or one-file-per-op under `chunks/operations/`)
- §7 → `chunks/pending/07-missing-and-changed-structures.md`

Extract these four counts/lists:

**§1 Enumeration Status** — count ❌ rows. Currently 3: `Data`, `Item Type`, `Unique Identifier`.

**§2 Missing Enumeration Classes** — for each missing enum, list (name, introduced version, value count).

**§6 Missing Operation Request/Response Payloads**:
- §6.1 Partially implemented (table)
- §6.2 Fully missing (table) — currently ~23 operations.

**§7 Missing and Changed Structures**:
- §7.1 missing structures table — currently 19 v3.0 structures.
- §7.2 structural breaking changes table — list affected types per version.

### 3. Render summary

```
## KMIP Implementation Gaps (snapshot as of <report timestamp>)

### Enumerations: <missing>/<total> missing
- Data (v2.0+, <N> values)
- Item Type (v2.0+, <N> values)
- Unique Identifier (v2.0+, <N> values)

### Operations: <fully-missing> fully missing, <partial> partially implemented
Partially:
- Poll — response missing
Fully:
- Import (v1.4) · Export (v1.4) · Log (v2.0) · ... [list all]

### Structures: <N> missing
v3.0 additions:
- PasswordCredential (0x4201A1)
- OtpCredential (0x4201A7)
- [list rest grouped by family — credentials, typed-links, other]

### Breaking changes to handle: <N>
- Custom Attribute (42002D) — reserved in v2.0+
- Generic Link (42004A/B/C) — reserved in v3.0; use typed-link family
- [list rest]

### Suggested next actions
1. Closest to ready: [1–2 items with rationale]
2. Highest blast radius / urgency: [1–2 items]
3. Recommended skill for each: kmip-add-enum / kmip-add-structure / kmip-add-operation
```

### 4. Optional: cross-reference source
If the user asks "is X really missing", run:
```bash
find src/main/java -name '<X>.java'
grep -rn 'class <X>' src/main/java/
```
to confirm before reporting. The report can lag behind source changes.

## Hard rules

- **Read-only.** This skill never modifies files.
- **Cite the report timestamp** in every summary, so the user knows how fresh the data is.
- **Do not prioritize** — that's the `kmip-pm` agent's job. This skill lists, doesn't sequence.
- **When counts disagree with source reality** (because the report is stale), flag the disagreement and recommend `kmip-scrape-spec` — do not silently override the report.
