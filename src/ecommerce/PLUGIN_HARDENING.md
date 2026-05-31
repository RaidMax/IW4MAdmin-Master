# Plugin hardening — store (ecommerce) side

Server-side pieces for protecting paid plugins (e.g. ZombieStatsPremium) that are streamed
to clients rather than shipped as DLLs. Pairs with client-side IL obfuscation (Tier 0) and
the in-plugin `EntitlementService` (Tier 1).

## What was added

| Tier | Endpoint / hook | File |
|------|-----------------|------|
| 1   | `GET /plugin/entitlement` — issues a short-lived **signed** entitlement | `resources/plugin_entitlement.py`, `encryption/signing_helper.py` |
| 1.5 | access logging on `GET /plugin_subscriptions` + admin report `GET /plugin/sharing_report` | `integrations/{data,logic}/access_*.py`, `resources/plugin_sharing_report.py` |

`CustomerLogic.get_entitled_plugin_ids()` resolves which plugins an email is actively
subscribed to (derived from the plan `content_url` basename).

## Tier 1 — entitlement gate

Delivery is already gated on an active ChargeBee subscription (the AES-GCM key derives from
the subscriber email). The gap: once a subscriber decrypts the DLL, a dumped copy runs
forever, anywhere. Tier 1 closes it — the plugin periodically fetches a signed entitlement
bound to its `instance_id` and **fails closed** when enforcement is enabled.

- Algorithm: **ECDSA P-256 / SHA-256**, signature in DER (RFC 3279). Chosen because both
  `cryptography` (here) and the .NET BCL (`ECDsa`, plugin side) support it with no extra dep.
- The endpoint signs the exact serialized `data` string and returns it verbatim with the
  signature, so the plugin verifies bytes it never has to re-serialize (no cross-language
  canonicalization risk).
- Returns `403 {entitled:false}` when the plugin is not covered → client fails closed.
- TTL: 12h (see `ENTITLEMENT_TTL_HOURS`); the plugin refreshes every 6h with a 48h offline
  grace window so a store outage never bricks paying subscribers.

### Keys

```
python -m ecommerce.encryption.generate_signing_keypair
```

- Set the printed **private** key as env `ECOMMERCE_SIGNING_KEY` (PKCS#8 PEM). Keep secret.
- Embed the printed **public** key in the plugin's `EntitlementService.PublicKeySpkiB64`.
- `signing_helper.py` ships a **DEV** key as a fallback for local testing only — production
  MUST set `ECOMMERCE_SIGNING_KEY`. The matching dev public key is currently in the plugin;
  both must be replaced together before release.

### Rollout (avoid bricking subscribers)

1. Deploy this endpoint + production keypair.
2. Ship the plugin with `EnforceEntitlement = false` (report-only: logs failures, keeps
   processing). Confirm all legitimate subscribers verify cleanly in the logs.
3. Flip `EnforceEntitlement = true` to enforce.

## Tier 1.5 — account-sharing detection

`GET /plugin_subscriptions` now records, per fetch, which `instance_id` pulled content for a
subscription. Privacy-focused:

- Emails are stored only as a keyed **HMAC-SHA256** (`ECOMMERCE_TRACKING_SECRET`); raw email
  and raw IP are never persisted. IP is stored as a hash too.
- Storage reuses the **existing Firebase provider** (same wiring as `MetaData`), path
  `subscription_access/{email_hash}/{instance_id}`. No new infrastructure or dependency —
  it uses the `IA_DATA_*` env vars the ecommerce app already requires.
- Tracking is **disabled** until `ECOMMERCE_TRACKING_SECRET` is set, so deploying this code
  changes nothing until you opt in.

Reporting is **admin-only** (the ecommerce app is internet-facing): `GET /plugin/sharing_report`
requires header `X-Admin-Key: <ECOMMERCE_ADMIN_KEY>` and returns aggregates keyed by HMAC'd
email, never raw emails:

```
GET /plugin/sharing_report?min_instances=2&window_hours=24
-> { "tracking_enabled": true,
     "accounts": [ {"account": "<email_hash>", "active_instances": 3,
                    "total_instances": 5, "distinct_ips": 2}, ... ] }
```

The heuristic flags **concurrently active** instances (last seen within `window_hours`), not
lifetime-distinct counts — `instance_id` regenerates on reinstall / wiped config / ephemeral
Docker, so lifetime counts over-report honest users. Distinct IP count is a secondary signal.

## Env vars summary

| Var | Purpose | Required |
|-----|---------|----------|
| `ECOMMERCE_SIGNING_KEY` | ECDSA P-256 PKCS#8 PEM private key for entitlement signing | Tier 1 (prod) |
| `ECOMMERCE_TRACKING_SECRET` | HMAC key for hashing emails/IPs in access tracking | Tier 1.5 |
| `ECOMMERCE_ADMIN_KEY` | shared secret for the `X-Admin-Key` header on the sharing report | Tier 1.5 |

## Open items for review

- **plugin_id scheme**: entitlement matches `plugin_id` against the `content_url` basename
  (`.../ZombieStatsPremium.dll` → `ZombieStatsPremium`). Confirm this matches the value the
  plugin sends (`EntitlementService.PluginId`).
- **Store URL**: the plugin defaults to `https://store.raidmax.org` for `/plugin/entitlement`
  (where `master.iw4.zip/plugin_subscriptions` already 302-redirects). Confirm correct.
