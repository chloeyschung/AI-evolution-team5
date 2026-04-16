# ARCH-014: Multi-Provider Identity Table and Email/Password Authentication

**Date:** 2026-04-16
**Status:** accepted
**ADR Version:** 1.0.0
**Last Updated:** 2026-04-16
**Owners:** Briefly engineering team

---

## Context

Briefly's initial auth architecture used a single `google_sub` column on `UserProfile` to identify Google OAuth users. With the addition of email/password login and a roadmap including Kakao, Naver, and GitHub OAuth, this flat approach would require a new nullable column per provider — resulting in a sparse, hard-to-query table and scattered account-linking logic.

A provider-agnostic design is needed that can accommodate any number of auth methods per user without schema changes per provider.

## Decision

We will introduce a `user_auth_methods` table (the "identities" pattern) as the authoritative store for all authentication credentials. Each row represents one auth method for one user. `UserProfile` becomes provider-agnostic — it holds display identity only.

Key details:
- `provider` enum: `google`, `email_password`, `kakao`, `naver`, `github` (extendable)
- `provider_id`: `google_sub` for OAuth providers; `HMAC-SHA256(normalized_email, EMAIL_LOOKUP_KEY)` for `email_password` — deterministic, keyed, indexable
- `email_encrypted`: Fernet-encrypted email for `email_password` rows (display/recovery; non-deterministic, not used for lookup)
- `password_hash`: Argon2id (`time=3, mem=65536, par=4`) for `email_password` rows; NULL for OAuth
- Account linking: same-email conflict returns HTTP 409; user must re-authenticate both identities before accounts are merged
- Authlib used as OAuth2 transport layer for all providers; Briefly's JWT/session layer unchanged

`UserProfile.google_sub` is dropped and migrated to a `user_auth_methods` row.

## Rationale

- **Scalability:** Adding Kakao/Naver/GitHub requires only a config entry in `authlib_providers.py` — no schema change.
- **Correctness:** HMAC keyed lookup prevents rainbow-table attacks on the email index while remaining O(1) for lookups (unlike Fernet, which is non-deterministic and cannot be indexed).
- **Security:** Two-factor linking prevents account takeover via provider email spoofing.
- **Consistency:** Fernet encryption for stored email matches the existing `IntegrationTokens` pattern in ARCH-002.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Column-per-provider on `UserProfile` | Schema change required per new provider; sparse nullable columns; linking logic scattered |
| Separate `EmailCredential` table only | Leaves `google_sub` and future `kakao_sub` on `UserProfile`; same accumulation problem |
| `fastapi-users` library | Would override existing `UserProfile`, `AuthenticationToken`, and JWT infrastructure — too invasive |
| Deterministic (non-keyed) hash of email for `provider_id` | SHA-256 without key is vulnerable to rainbow tables; HMAC with `EMAIL_LOOKUP_KEY` resists this |
| Fernet-only storage for lookup | Fernet uses random IV per encryption — ciphertext differs each call, unusable as a UNIQUE index |

## Consequences

**Positive:**
- Clean provider-agnostic identity model; future providers cost near-zero schema work.
- Argon2id + HMAC + Fernet gives defense-in-depth for credential storage.
- Account linking is explicit and auditable.

**Negative / trade-offs:**
- Migration needed: `UserProfile.google_sub` → `user_auth_methods` row.
- `EMAIL_LOOKUP_KEY` is a new secret to manage in `.env` and key rotation procedures.
- Login lookup requires one DB query (HMAC index match) vs. previous Google flow which looked up by `google_sub` directly — equivalent performance.

## Related

- [ARCH-002](ARCH-002-hybrid-jwt-session-with-hashed-encrypted-tokens.md) — JWT/token infrastructure this extends
- [ARCH-006](ARCH-006-security-in-depth-perimeter-for-external-io.md) — Security-in-depth this builds on
- [AUTH-005.md](../specs/AUTH-005.md) — Feature spec implementing this decision
