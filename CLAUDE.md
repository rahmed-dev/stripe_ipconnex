# ipconnex_stripe_payment — Architecture Reference

> Code-validated. Every claim cites a file. When in doubt, read the cited file — code is the source of truth.

## Status — GUTTED

This app's **auto-charge surface is intentionally dead.** It used to own Stripe charging for the platform; that responsibility moved to `dido_erp.dido_payment` in f062. The hook registrations in `ipconnex_stripe_payment/hooks.py` are commented out — Frappe never invokes the auto-charge functions, even though the function bodies still exist on disk.

The app is kept on disk because `dido_erp.api.stripe_billing` still imports two SDK helpers from it (`getNewCardToken`, `updateCards`). Removing the app would break the Stripe checkout path. Removing the dead function bodies would risk breaking callers that haven't been audited yet. Treat this as a **dependency tombstone with two living helper imports**.

## Module Layout

```
ipconnex_stripe_payment/
├── hooks.py                                              # registrations — most are commented out
└── ipconnex_stripe_payment/
    ├── payement.py                                       # 17 functions; most dead (see table)
    ├── doctype/
    │   ├── stripe_settings/                              # Single — keys, account
    │   ├── stripe_account/
    │   ├── payment_method/
    │   └── ...
    └── public/js/payement.js                             # SI/SO/Stripe Settings client scripts
```

## What's Alive

| Surface | Status | Used by |
|---|---|---|
| `payement.setup_install` | **Live** — registered as `app_install` in `hooks.py` | Frappe install path; first-time setup of Stripe Settings doctype |
| `payement.getNewCardToken(customer_id, stripe_acc)` | **Live** — imported by dido | `dido_erp.api.stripe_billing` (SetupIntent flow) |
| `payement.updateCards(client_token)` | **Live** — imported by dido | `dido_erp.api.stripe_billing` (card list refresh) |
| `payement.getCustomer` / `getCustomerCards` / `getEmail` | **Live** — internal SDK glue | Called by other live helpers above |
| `Stripe Settings` doctype | **Live** — read by dido_erp | `dido_payment.stripe_charge.charger` reads keys via `stripe_billing._get_stripe_settings` |
| `public/js/payement.js` | **Live** — `doctype_js` registration | Form scripts for SI / SO / Stripe Settings / Payment Method |

## What's Dead (function bodies on disk, not registered)

| Function | Original purpose | Current state |
|---|---|---|
| `checkProcessInvoice(doc, method)` | SI/SO `on_submit` auto-charge | `doc_events` block commented in `hooks.py` — never fires |
| `hourly_process_payment()` | Hourly cron — retry failed charges | `scheduler_events` block commented — never fires |
| `daily_auto_subscription()` | Daily cron — recurring SI charge | `scheduler_events` block commented — never fires |
| `process_subscription(user_sub, sub_type)` | Helper for `daily_auto_subscription` | Reachable only from dead caller |
| `processPayment(doctype, docname)` | Manual button charge | No surviving registration |

These functions remain importable but have no scheduler or doc_event wiring. The verbatim disable note in `hooks.py`:

```python
# Auto-charge crons disabled — dido_erp owns Stripe charging via the
# daily 06:00 sweep at dido_erp.dido_payment.stripe_charge.sweep.
```

## Why Hold the App on Disk

1. **`dido_erp.api.stripe_billing` imports `getNewCardToken` and `updateCards`.** Those helpers wrap Stripe SDK quirks the dido path hasn't re-implemented. Removing the app breaks SetupIntent + card management in dido checkout.
2. **`Stripe Settings` doctype lives here.** dido reads it for API keys + account name. Moving the doctype is a separate migration.
3. **JS form scripts** registered via `doctype_js` decorate Sales Invoice / Sales Order forms. The "Charge Card" button on the SI form lives in this JS — it routes to the dido whitelisted endpoint, not the dead `payement.processPayment`.

## Charging Path — Where It Actually Runs Now

All Stripe auto-charging in production goes through `dido_erp.dido_payment.stripe_charge`:

- Daily 06:00 cron: `stripe_charge.sweep.charge_today_stripe_cohort`
- Per-SI entry: `stripe_charge.charger.charge_sales_invoice(si, source)`
- Manual retry button: `dido_erp.dido_payment.sales_invoice_hooks.retry_stripe_charge`
- SetupIntent / card management: `dido_erp.api.stripe_billing` (which imports the live helpers from this app)

See `apps/dido_erp/dido_erp/dido_payment/CLAUDE.md` § Stripe Charge subsystem for the live flow.

## Don't

- **Don't uncomment `scheduler_events` or `doc_events` in `hooks.py`.** Re-enabling either resurrects double-charge: dido already charges every Stripe-MoP SI on its `charge_day`; ipconnex resurrected on top would charge again. f062's whole point was to delete this overlap.
- **Don't delete `payement.py` outright.** `getNewCardToken`, `updateCards`, `getCustomer`, `getCustomerCards`, `getEmail`, `setup_install` are still called by live code. Deletion needs a careful audit pass per function.
- **Don't add new functionality here.** Anything new belongs in `dido_erp.dido_payment` or `dido_erp.api.stripe_billing`. This app is in maintenance-only mode.
- **Don't read `Customer.custom_auto_process` / `Stripe Customer.auto_process` as a charging gate.** That flag was the per-customer opt-in for the dead `daily_auto_subscription` cron. The dido sweep ignores it (rail-level decision: Stripe MoP = always auto-charge on `charge_day`). The flag is still persisted by signup + `confirm_card` as a UI preference but no live charging path consults it.
- **Don't pull upstream from the original ipconnex repo without re-checking the disabled blocks.** A naive merge will re-enable the commented-out registrations.
- **Don't read `Stripe Settings.secret_key` as a plain field.** It is a **Password** field (encrypted in `__Auth`; the table column holds only `*`). `payement.py` fetches go through `_get_stripe_settings_rows(fields=...)` which decrypts each row; `get_doc` callers use `doc.get_password("secret_key")`. A raw `frappe.db.get_all/get_value("Stripe Settings", ... "secret_key")` returns the mask. Patch `patches/encrypt_stripe_secret_key.py` migrated the legacy plaintext into `__Auth`.
