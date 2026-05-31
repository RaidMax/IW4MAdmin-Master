# Subscription-access tracking (sharing detection) — store (ecommerce) side

Visibility into how subscriptions are being used, so RaidMax can spot people reusing one
subscription across multiple installs (paying once, running many) and see which plugins are
in play. Slots into the existing `ecommerce` app (Firebase + ChargeBee) with **no new
infrastructure or dependency**, and is a **no-op until `ECOMMERCE_TRACKING_SECRET` is set**.

## What was added

| Hook / endpoint | File |
|-----------------|------|
| access logging on `GET /plugin_subscriptions` (records instance + plugins + hashed IP) | `integrations/logic/customer_logic.py`, `integrations/{data,logic}/access_*.py` |
| admin report `GET /plugin/sharing_report` | `resources/plugin_sharing_report.py` |

`get_subscribed_content()` now records, per content fetch, which `instance_id` pulled which
plugins for a subscription (plugin ids derived from the `content_url` basename — no extra
ChargeBee call). Records live in Firebase under
`subscription_access/{email_hash}/{instance_id} = {first_seen, last_seen, count, ip_hash, plugins{}}`.

## Privacy

- Emails are stored only as a keyed **HMAC-SHA256** (`ECOMMERCE_TRACKING_SECRET`). Raw email
  and raw IP are never persisted (IP is hashed too).
- Reuses the existing Firebase provider (same `IA_DATA_*` env vars the app already needs).
- The report is **admin-only** (`X-Admin-Key` == `ECOMMERCE_ADMIN_KEY`) — the ecommerce app is
  internet-facing — and returns aggregates keyed by hashed email, never raw emails.

## Report

```
GET /plugin/sharing_report?min_instances=2&window_hours=24
    header: X-Admin-Key: <ECOMMERCE_ADMIN_KEY>
->
{
  "tracking_enabled": true,
  "by_email":    [ {"account": "<email_hash>", "active_instances": 3, "total_instances": 5,
                    "distinct_ips": 2, "plugins": ["ZombieStatsPremium", ...]}, ... ],
  "by_instance": [ {"instance_id": "<guid>", "account_count": 2,
                    "accounts": ["<email_hash>", ...], "plugins": [...]}, ... ]
}
```

- **by_email** — one subscription seen on `>= min_instances` **concurrently active** instances
  (last seen within `window_hours`). The bypass signal: one paid email, many installs.
- **by_instance** — one `instance_id` pulling content under more than one subscription email.

Active-concurrent (not lifetime-distinct) is deliberate: `instance_id` regenerates on
reinstall / wiped config / ephemeral Docker, so lifetime counts over-report honest users.
Distinct IP count is a secondary signal.

## Env vars

| Var | Purpose | Required |
|-----|---------|----------|
| `ECOMMERCE_TRACKING_SECRET` | HMAC key for hashing emails/IPs (tracking is **off** until set) | to enable tracking |
| `ECOMMERCE_ADMIN_KEY` | shared secret for the `X-Admin-Key` header on the report | to use the report |

Deploying with neither set leaves all existing behaviour unchanged.
