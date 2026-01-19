"""
PostgreSQL database module for IW4MAdmin Master API.
Handles connection pooling, schema initialization, and data access.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from .config import config

logger = logging.getLogger(__name__)


class Database:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize connection pool and create tables."""
        if self._pool is not None:
            return

        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                host=config.database_host,
                port=config.database_port,
                database=config.database_name,
                user=config.database_user,
                password=config.database_password
            )
            logger.info(f"Connected to PostgreSQL at {config.database_host}:{config.database_port}/{config.database_name}")
            self._create_tables()
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def _create_tables(self):
        """Create database tables if they don't exist."""
        with self.get_cursor() as cursor:
            # Instances table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instances (
                    id VARCHAR(255) PRIMARY KEY,
                    version VARCHAR(128),
                    uptime INTEGER,
                    ip_address VARCHAR(45),
                    webfront_url VARCHAR(512),
                    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            # Servers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id BIGINT,
                    instance_id VARCHAR(255) REFERENCES instances(id) ON DELETE CASCADE,
                    ip VARCHAR(45),
                    port INTEGER,
                    version VARCHAR(128),
                    game VARCHAR(16),
                    hostname VARCHAR(256),
                    clientnum INTEGER,
                    maxclientnum INTEGER,
                    map VARCHAR(128),
                    gametype VARCHAR(32),
                    resolved_external_ip_address VARCHAR(45),
                    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (id, instance_id)
                )
            """)

            # History metrics table - stores time-series data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history_metrics (
                    id SERIAL PRIMARY KEY,
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    instance_count INTEGER DEFAULT 0,
                    server_count INTEGER DEFAULT 0,
                    client_count INTEGER DEFAULT 0
                )
            """)

            # Reporting metrics table - aggregated stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reporting_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_date DATE UNIQUE DEFAULT CURRENT_DATE,
                    peak_instances INTEGER DEFAULT 0,
                    peak_servers INTEGER DEFAULT 0,
                    peak_clients INTEGER DEFAULT 0,
                    total_unique_instances INTEGER DEFAULT 0,
                    total_heartbeats INTEGER DEFAULT 0,
                    avg_servers_per_instance REAL DEFAULT 0,
                    avg_clients_per_server REAL DEFAULT 0
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_recorded_at 
                ON history_metrics(recorded_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_servers_game 
                ON servers(game)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_instances_last_heartbeat 
                ON instances(last_heartbeat DESC)
            """)

            logger.info("Database tables initialized")

    @contextmanager
    def get_cursor(self, commit: bool = True):
        """Context manager for database operations with auto-commit."""
        conn = self._pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
            self._pool.putconn(conn)

    # Instance operations
    def upsert_instance(self, instance_id: str, version: Any, uptime: int,
                        ip_address: str, webfront_url: Optional[str]) -> None:
        """Insert or update an instance."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO instances (id, version, uptime, ip_address, webfront_url, last_heartbeat)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    version = EXCLUDED.version,
                    uptime = EXCLUDED.uptime,
                    ip_address = EXCLUDED.ip_address,
                    webfront_url = EXCLUDED.webfront_url,
                    last_heartbeat = NOW()
            """, (instance_id, str(version) if version else None, uptime, ip_address, webfront_url))

    def upsert_server(self, server_id: int, instance_id: str, ip: str, port: int,
                      version: str, game: str, hostname: str, clientnum: int,
                      maxclientnum: int, map_name: str, gametype: str,
                      resolved_ip: Optional[str]) -> None:
        """Insert or update a server."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO servers (id, instance_id, ip, port, version, game, hostname,
                                    clientnum, maxclientnum, map, gametype, 
                                    resolved_external_ip_address, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id, instance_id) DO UPDATE SET
                    ip = EXCLUDED.ip,
                    port = EXCLUDED.port,
                    version = EXCLUDED.version,
                    game = EXCLUDED.game,
                    hostname = EXCLUDED.hostname,
                    clientnum = EXCLUDED.clientnum,
                    maxclientnum = EXCLUDED.maxclientnum,
                    map = EXCLUDED.map,
                    gametype = EXCLUDED.gametype,
                    resolved_external_ip_address = EXCLUDED.resolved_external_ip_address,
                    last_seen = NOW()
            """, (server_id, instance_id, ip, port, version, game, hostname,
                  clientnum, maxclientnum, map_name, gametype, resolved_ip))

    def get_instance(self, instance_id: str) -> Optional[Dict]:
        """Get instance by ID with its servers."""
        with self.get_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM instances WHERE id = %s", (instance_id,))
            instance = cursor.fetchone()
            if instance:
                cursor.execute("SELECT * FROM servers WHERE instance_id = %s", (instance_id,))
                instance['servers'] = cursor.fetchall()
            return dict(instance) if instance else None

    def get_all_instances(self, include_stale: bool = False) -> List[Dict]:
        """Get all instances, optionally excluding stale ones."""
        with self.get_cursor(commit=False) as cursor:
            if include_stale:
                cursor.execute("SELECT * FROM instances ORDER BY last_heartbeat DESC")
            else:
                cursor.execute("""
                    SELECT * FROM instances 
                    WHERE last_heartbeat > NOW() - INTERVAL '5 minutes'
                    ORDER BY last_heartbeat DESC
                """)
            instances = cursor.fetchall()
            for instance in instances:
                cursor.execute("SELECT * FROM servers WHERE instance_id = %s", (instance['id'],))
                instance['servers'] = cursor.fetchall()
            return [dict(i) for i in instances]

    def delete_stale_instances(self, max_age_seconds: int = 300) -> int:
        """Delete instances that haven't sent a heartbeat recently."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM instances 
                WHERE last_heartbeat < NOW() - INTERVAL '%s seconds'
                RETURNING id
            """, (max_age_seconds,))
            deleted = cursor.fetchall()
            return len(deleted)

    # History/metrics operations
    def record_history(self, instance_count: int, server_count: int, client_count: int) -> None:
        """Record a history data point."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO history_metrics (instance_count, server_count, client_count)
                VALUES (%s, %s, %s)
            """, (instance_count, server_count, client_count))

    def get_history(self, limit: int = 500, offset: int = 0) -> List[Dict]:
        """Get history data points."""
        with self.get_cursor(commit=False) as cursor:
            cursor.execute("""
                SELECT recorded_at, instance_count, server_count, client_count
                FROM history_metrics
                ORDER BY recorded_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def update_daily_metrics(self) -> None:
        """Update today's reporting metrics."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO reporting_metrics (metric_date, peak_instances, peak_servers, 
                    peak_clients, total_unique_instances, total_heartbeats,
                    avg_servers_per_instance, avg_clients_per_server)
                SELECT 
                    CURRENT_DATE,
                    COALESCE(MAX(instance_count), 0),
                    COALESCE(MAX(server_count), 0),
                    COALESCE(MAX(client_count), 0),
                    (SELECT COUNT(DISTINCT id) FROM instances 
                     WHERE DATE(last_heartbeat) = CURRENT_DATE),
                    (SELECT COUNT(*) FROM history_metrics 
                     WHERE DATE(recorded_at) = CURRENT_DATE),
                    COALESCE(AVG(NULLIF(server_count, 0)::real / NULLIF(instance_count, 0)), 0),
                    COALESCE(AVG(NULLIF(client_count, 0)::real / NULLIF(server_count, 0)), 0)
                FROM history_metrics
                WHERE DATE(recorded_at) = CURRENT_DATE
                ON CONFLICT (metric_date) DO UPDATE SET
                    peak_instances = GREATEST(reporting_metrics.peak_instances, EXCLUDED.peak_instances),
                    peak_servers = GREATEST(reporting_metrics.peak_servers, EXCLUDED.peak_servers),
                    peak_clients = GREATEST(reporting_metrics.peak_clients, EXCLUDED.peak_clients),
                    total_unique_instances = EXCLUDED.total_unique_instances,
                    total_heartbeats = EXCLUDED.total_heartbeats,
                    avg_servers_per_instance = EXCLUDED.avg_servers_per_instance,
                    avg_clients_per_server = EXCLUDED.avg_clients_per_server
            """)

    def get_reporting_metrics(self, days: int = 30) -> List[Dict]:
        """Get reporting metrics for the last N days."""
        with self.get_cursor(commit=False) as cursor:
            cursor.execute("""
                SELECT * FROM reporting_metrics
                WHERE metric_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY metric_date DESC
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_history(self, max_days: int = 7) -> int:
        """Delete history data older than max_days. Set max_days to -1 for indefinite storage."""
        if max_days < 0:
            logger.debug("History cleanup skipped: indefinite storage enabled")
            return 0
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM history_metrics 
                WHERE recorded_at < NOW() - INTERVAL '%s days'
                RETURNING id
            """, (max_days,))
            deleted = cursor.fetchall()
            return len(deleted)

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._pool is not None

    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")


# Singleton instance
db = Database()
