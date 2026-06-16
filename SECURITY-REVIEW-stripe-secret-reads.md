---
component: stripe-settings-secret-key
review_type: security
scope: recent change — Stripe Settings.secret_key Data→Password, encrypt into __Auth, all reads
date: 2026-06-16
reviewer: bmad-fb-review (security)
verdict: pass with notes
---

# Security Review — Stripe `secret_key` reads

## Change reviewed (uncommitted, ipconnex_stripe_payment working tree)
- `stripe_settings.json`: `secret_key` fieldtype `Data` → `Password` (encrypted in `__Auth`; table column holds only `*`).
- `stripe_settings.py`: removed custom `get()` masking override (now redundant — Password fields stripped from API/`as_dict` natively). `before_save`/`before_insert` keep RBAC write-gate.
- `patches/encrypt_stripe_secret_key.py`: migrates legacy plaintext column → `__Auth`, masks column. Idempotent.
- `payement.py`: new `_get_stripe_settings_rows()` helper decrypts each row via `get_decrypted_password`.

## Read sites audited — ALL SAFE
| Site | Mechanism | Verdict |
|---|---|---|
| ipconnex `payement.py` — 14 `_get_stripe_settings_rows(...)` calls | helper decrypts via `get_decrypted_password` | pass |
| ipconnex `payement.py:257/572/763/933` `get_doc` | `.get_password("secret_key")` | pass |
| dido `providers/stripe/api/checkout.py:42` `_get_stripe_settings` | `get_decrypted_password` | pass |
| dido `charger.py:49`, `provider.py:124` | source `settings` from `checkout._get_stripe_settings` | pass |
| dido `api/signup.py:583` `_get_stripe_settings` | `get_decrypted_password` | pass |
| dido `providers/stripe/_log.py:165` env-mode probe | `get_decrypted_password` | pass |
| `public/js/payement.js:9-11` | only toggles field `hidden` df — no value read | pass |

- No raw `frappe.db.get_all/get_value("Stripe Settings", ..., "secret_key")` that bypasses decrypt anywhere in either app.
- `_log.py:23` redaction list includes `secret_key`, `api_key`, `client_secret`, `Authorization` → secret never hits logs.
- Write path RBAC-gated (System Manager / Accounts Manager) in `before_save` + `before_insert`.
- No `secret_key` returned in any API response / `frappe.response`.

## Findings

### N1 — silent None on decrypt failure
- **severity:** minor
- **location:** `payement.py:29-31`; `checkout.py:42`; `signup.py:583` (all use `raise_exception=False`)
- **description:** if `__Auth` row is missing (key rotation, failed patch, restored DB), `get_decrypted_password` returns `None` → `stripe.api_key = None` → opaque Stripe SDK auth error instead of clear "secret not configured". dido `_log.py` already throws on empty; the charge/checkout paths do not.
- **suggestion:** after decrypt, `if not settings.secret_key: frappe.throw(_("Stripe secret key not configured / decrypt failed"))` on the charge + checkout fetchers, mirroring `_log.py:170`.
- **status:** FIXED 2026-06-16 — empty-guard added to `checkout.py:_get_stripe_settings` + `signup.py:_get_stripe_settings`. ipconnex `_get_stripe_settings_rows` deliberately left ungated (multi-field/multi-row helper; non-secret callers must not throw).

### N2 — patch leaks key length into plaintext column
- **severity:** minor (note)
- **location:** `patches/encrypt_stripe_secret_key.py:32` (`"*" * len(secret)`)
- **description:** masked column preserves the original secret's character length. Negligible (Stripe keys are fixed-format), but it discloses length to anyone with raw table read.
- **suggestion:** mask with a fixed-width sentinel (e.g. `"********"`). Optional.
- **status:** WONTFIX 2026-06-16 — declined by user.

### N3 — dead decrypt
- **severity:** minor
- **location:** `payement.py:235` fetches `secret_key` but the `api_key` assignment at ~`:238` is commented out
- **description:** unused decrypted secret materialised in memory. Harmless; tidy-up.
- **suggestion:** drop `secret_key` from that field list, or remove the dead block.
- **status:** FIXED 2026-06-16 — `secret_key` dropped from the field list and the commented `api_key` line deleted (`payement.py:235`).

## Deploy note (not a finding)
`patches/encrypt_stripe_secret_key.py` must run (bench migrate) before any read — decrypt helpers read `__Auth`, only populated by the patch. Registered in `patches.txt`. Order correct.

## Verdict
**pass with notes.** No critical, no major. Secret handling on the recent change is sound: every read decrypts, write is RBAC-gated, logs redact, Password field gives native API masking. N1–N3 are advisory hardening, non-blocking.
