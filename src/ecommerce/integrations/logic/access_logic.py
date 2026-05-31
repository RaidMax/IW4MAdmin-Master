"""
Subscription-access tracking + sharing detection.

Records which instances fetch which plugins for each subscription, so RaidMax can spot
people reusing one subscription across multiple installs (paying once, running many) and
see which plugins are in play. Privacy-focused:
  - emails are stored only as a keyed HMAC (ECOMMERCE_TRACKING_SECRET); the public content
    endpoint never persists raw email or raw IP. IPs are hashed too.
  - the reporting surface is admin-only (see PluginSharingReport) and returns aggregates,
    never raw emails.

Two sharing signals:
  - by EMAIL: one subscription (email_hash) seen on >= N CONCURRENTLY ACTIVE instances
    (last seen within a rolling window). Active-concurrent, not lifetime-distinct, because
    instance_id regenerates on reinstall / wiped config / ephemeral Docker.
  - by INSTANCE: one instance_id seen under >1 distinct subscription email_hash.

Each record also carries the set of plugin ids served, so the report shows what each
account/instance is using.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from os import environ

from ecommerce.integrations.data.access_data import AccessData

_ENV_TRACKING_SECRET = 'ECOMMERCE_TRACKING_SECRET'


class AccessLogic:
    def __init__(self, access_data: AccessData = None):
        self._logger = logging.getLogger(__name__)
        self._access_data = access_data or AccessData()
        self._secret = environ.get(_ENV_TRACKING_SECRET, '')

    @property
    def enabled(self) -> bool:
        return bool(self._secret)

    def _hash(self, value: str) -> str:
        return hmac.new(self._secret.encode('utf-8'), value.encode('utf-8'), hashlib.sha256).hexdigest()

    def record_access(self, subscription_id: str, instance_id: str, plugin_ids=None, ip: str = None) -> None:
        """Best-effort: record one content fetch. Never raises into the caller (delivery must
        not break because tracking failed)."""
        if not self.enabled or not subscription_id or not instance_id:
            return
        try:
            email_hash = self._hash(subscription_id)
            now = datetime.now(timezone.utc).isoformat()
            existing = self._access_data.get_record(email_hash, instance_id) or {}

            # plugins stored as a map (set semantics, Firebase-friendly), unioned over time.
            plugins = dict(existing.get('plugins') or {})
            for plugin_id in (plugin_ids or []):
                plugins[plugin_id] = True

            payload = {
                'first_seen': existing.get('first_seen', now),
                'last_seen': now,
                'count': int(existing.get('count', 0)) + 1,
                'ip_hash': self._hash(ip) if ip else existing.get('ip_hash'),
                'plugins': plugins,
            }
            self._access_data.set_record(email_hash, instance_id, payload)
        except Exception as ex:
            self._logger.error('could not record subscription access', exc_info=ex)

    def get_sharing_report(self, min_instances: int = 2, active_window_hours: int = 24) -> dict:
        """Returns both sharing views. `by_email` = subscriptions on multiple concurrently
        active instances; `by_instance` = instances used under multiple subscription emails."""
        all_data = self._access_data.get_all() or {}
        cutoff = datetime.now(timezone.utc).timestamp() - active_window_hours * 3600

        by_email = []
        instance_to_emails = {}      # instance_id -> set(email_hash)
        instance_plugins = {}        # instance_id -> set(plugin_id)

        for email_hash, instances in all_data.items():
            if not isinstance(instances, dict):
                continue
            active = 0
            ips = set()
            email_plugins = set()
            for instance_id, record in instances.items():
                if not isinstance(record, dict):
                    continue
                plugins = list((record.get('plugins') or {}).keys())
                email_plugins.update(plugins)
                instance_to_emails.setdefault(instance_id, set()).add(email_hash)
                instance_plugins.setdefault(instance_id, set()).update(plugins)
                if record.get('ip_hash'):
                    ips.add(record['ip_hash'])
                ts = self._parse_ts(record.get('last_seen'))
                if ts is not None and ts >= cutoff:
                    active += 1
            if active >= min_instances:
                by_email.append({
                    'account': email_hash,
                    'active_instances': active,
                    'total_instances': len(instances),
                    'distinct_ips': len(ips),
                    'plugins': sorted(email_plugins),
                })

        by_instance = [{
            'instance_id': instance_id,
            'account_count': len(emails),
            'accounts': sorted(emails),
            'plugins': sorted(instance_plugins.get(instance_id, set())),
        } for instance_id, emails in instance_to_emails.items() if len(emails) > 1]

        by_email.sort(key=lambda entry: entry['active_instances'], reverse=True)
        by_instance.sort(key=lambda entry: entry['account_count'], reverse=True)
        return {'by_email': by_email, 'by_instance': by_instance}

    @staticmethod
    def _parse_ts(iso_value):
        if not iso_value:
            return None
        try:
            return datetime.fromisoformat(iso_value).timestamp()
        except (ValueError, TypeError):
            return None
