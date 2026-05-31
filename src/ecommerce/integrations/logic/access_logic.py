"""
Subscription-access tracking + sharing-detection logic (Tier 1.5).

Records which instances fetch content for each subscription so RaidMax can spot account
sharing. Privacy-focused:
  - emails are stored only as a keyed HMAC (ECOMMERCE_TRACKING_SECRET); the public content
    endpoint never persists raw email or instance IP in the clear.
  - the reporting surface is admin-only (see PluginSharingReport) and returns aggregates,
    never raw emails.

Sharing heuristic: count instances that are CONCURRENTLY ACTIVE (last seen within a rolling
window), not lifetime-distinct instances — instance_id regenerates on reinstall / wiped
config / ephemeral Docker, so lifetime counts over-report honest users. Distinct IP count is
included as a secondary signal.
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

    def record_access(self, subscription_id: str, instance_id: str, ip: str = None) -> None:
        """Best-effort: records one access. Never raises into the caller (delivery must not
        break because tracking failed)."""
        if not self.enabled or not subscription_id or not instance_id:
            return
        try:
            email_hash = self._hash(subscription_id)
            now = datetime.now(timezone.utc).isoformat()
            existing = self._access_data.get_record(email_hash, instance_id) or {}
            payload = {
                'first_seen': existing.get('first_seen', now),
                'last_seen': now,
                'count': int(existing.get('count', 0)) + 1,
                'ip_hash': self._hash(ip) if ip else existing.get('ip_hash'),
            }
            self._access_data.set_record(email_hash, instance_id, payload)
        except Exception as ex:
            self._logger.error('could not record subscription access', exc_info=ex)

    def get_sharing_report(self, min_instances: int = 2, active_window_hours: int = 24) -> list:
        """Returns accounts (by email_hash) with >= min_instances concurrently active."""
        report = []
        cutoff = datetime.now(timezone.utc).timestamp() - active_window_hours * 3600
        for email_hash, instances in (self._access_data.get_all() or {}).items():
            if not isinstance(instances, dict):
                continue
            active = 0
            ips = set()
            for _instance_id, record in instances.items():
                if not isinstance(record, dict):
                    continue
                ts = self._parse_ts(record.get('last_seen'))
                if ts is not None and ts >= cutoff:
                    active += 1
                if record.get('ip_hash'):
                    ips.add(record['ip_hash'])
            if active >= min_instances:
                report.append({
                    'account': email_hash,
                    'active_instances': active,
                    'total_instances': len(instances),
                    'distinct_ips': len(ips),
                })
        report.sort(key=lambda entry: entry['active_instances'], reverse=True)
        return report

    @staticmethod
    def _parse_ts(iso_value):
        if not iso_value:
            return None
        try:
            return datetime.fromisoformat(iso_value).timestamp()
        except (ValueError, TypeError):
            return None
