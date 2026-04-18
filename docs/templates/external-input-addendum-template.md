# External Input Addendum: {Document Title}

---
doc_class: external_input
input_type: {product_doc|feedback|discussion_result|decision_proposal|other}
owner: {person_or_team}
canonical_source: {xlsx_or_original_source}
repo_role: {product_intent_input|feedback_input|discussion_record}
edit_policy: sync_only
use_for: product intent, feedback, discussion context
not_for: repo implementation status, completion claims
last_synced: {YYYY-MM-DD}
related_internal_docs:
  - {docs/feature-inventory.md}
  - {docs/specs/ID.md}
---

## 1. Purpose

{Explain what this document is, who owns it, and why it exists in the repo.}

## 2. Handling Rules

- Use this document for upstream intent, feedback, and shared discussion context.
- Do not use this document as proof that a feature is implemented in this repo.
- Preserve source meaning when syncing from the canonical source.
- Normalize accepted deltas into internal docs instead of overloading this file with repo-state tracking.

## 3. Accepted Deltas

| Area | Summary | Internal Target | Status |
|------|---------|-----------------|--------|
| {product_intent|repo_status|architecture|plan} | {accepted change} | `{target_doc}` | {pending|updated} |

## 4. Normalization Log

| Date | Change | Internal Docs Updated |
|------|--------|------------------------|
| {YYYY-MM-DD} | {summary} | `{doc1}`, `{doc2}` |

## 5. Open Questions

- {question_or_follow_up}
