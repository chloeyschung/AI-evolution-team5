# Architectural Decision Records

Records of significant cross-cutting technical decisions: why a technology, pattern, or design was chosen over alternatives.

**When to write an ADR:**
- Choosing a framework, library, or database
- Committing to an architectural pattern (async, ORM strategy, auth approach)
- Making a design choice that constrains multiple future features
- Reversing or superseding a past decision

**When NOT to write an ADR:**
- Feature-level decisions (those belong in `specs/{ID}.md`)
- Implementation details that can change without affecting other features

**Naming:** `ARCH-NNN-short-slug.md` (e.g., `ARCH-001-fastapi-over-flask.md`)

**Template:** `.local/adr-template.md`
