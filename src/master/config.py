"""
Configuration module for IW4MAdmin Master API.
Loads settings from config/master_config.json with environment variable overrides.
"""

import json
import os
from typing import Any


class Config:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'master_config.json'
        )
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self._config = json.load(f)
        else:
            self._config = {}

        # Environment variable overrides (for container deployments)
        # Individual DB vars (preferred - handles special characters in passwords)
        if os.environ.get('DB_HOST'):
            self._config.setdefault('database', {})
            self._config['database']['host'] = os.environ.get('DB_HOST')
            self._config['database']['port'] = int(os.environ.get('DB_PORT', 5432))
            self._config['database']['name'] = os.environ.get('DB_NAME', 'iw4madmin_master')
            self._config['database']['user'] = os.environ.get('DB_USER', 'postgres')
            self._config['database']['password'] = os.environ.get('DB_PASSWORD', '')
        # DATABASE_URL fallback (for platforms like Heroku)
        elif os.environ.get('DATABASE_URL'):
            self._parse_database_url(os.environ['DATABASE_URL'])
        if os.environ.get('IW4MADMIN_AUTH_KEY'):
            self._config['jwt_secret_key'] = os.environ['IW4MADMIN_AUTH_KEY']
        if os.environ.get('GRAFANA_BASE_URL'):
            self._config.setdefault('grafana', {})['base_url'] = os.environ['GRAFANA_BASE_URL']
        if os.environ.get('LOG_LEVEL'):
            self._config.setdefault('logging', {})['level'] = os.environ['LOG_LEVEL']

    def _parse_database_url(self, url: str):
        """Parse DATABASE_URL format: postgresql://user:password@host:port/dbname"""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        self._config['database'] = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'name': parsed.path.lstrip('/') if parsed.path else 'iw4madmin_master',
            'user': parsed.username or 'postgres',
            'password': parsed.password or ''
        }

    def get(self, *keys, default: Any = None) -> Any:
        """Get nested config value. Example: config.get('database', 'host')"""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def database_host(self) -> str:
        return self.get('database', 'host', default='localhost')

    @property
    def database_port(self) -> int:
        return self.get('database', 'port', default=5432)

    @property
    def database_name(self) -> str:
        return self.get('database', 'name', default='iw4madmin_master')

    @property
    def database_user(self) -> str:
        return self.get('database', 'user', default='postgres')

    @property
    def database_password(self) -> str:
        return self.get('database', 'password', default='')

    @property
    def database_pool_min(self) -> int:
        """Minimum connections in pool. Override with DB_POOL_MIN env var."""
        env_val = os.environ.get('DB_POOL_MIN')
        if env_val:
            return int(env_val)
        return self.get('database', 'pool_min', default=5)

    @property
    def database_pool_max(self) -> int:
        """Maximum connections in pool. Override with DB_POOL_MAX env var."""
        env_val = os.environ.get('DB_POOL_MAX')
        if env_val:
            return int(env_val)
        return self.get('database', 'pool_max', default=20)

    @property
    def jwt_secret_key(self) -> str:
        return self.get('jwt_secret_key', default='change-this-in-production')

    @property
    def rate_limit_enabled(self) -> bool:
        return self.get('rate_limiting', 'enabled', default=True)

    @property
    def rate_limit_default(self) -> str:
        return self.get('rate_limiting', 'default_limit', default='100/minute')

    @property
    def rate_limit_write(self) -> str:
        return self.get('rate_limiting', 'write_limit', default='30/minute')

    @property
    def localization_url(self) -> str:
        return self.get('localization', 'google_sheets_url', default='')

    @property
    def localization_cache_ttl(self) -> int:
        return self.get('localization', 'cache_ttl_seconds', default=300)

    @property
    def log_level(self) -> str:
        return self.get('logging', 'level', default='INFO')

    @property
    def log_json_format(self) -> bool:
        return self.get('logging', 'json_format', default=True)

    @property
    def log_file(self) -> str:
        return self.get('logging', 'file', default='master.log')

    @property
    def history_sample_rate(self) -> int:
        return self.get('history', 'sample_rate_seconds', default=30)

    @property
    def history_max_days(self) -> int:
        return self.get('history', 'max_history_days', default=7)

    @property
    def grafana_base_url(self) -> str:
        return self.get('grafana', 'base_url', default='http://localhost:3000')


# Singleton instance
config = Config()
