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
                minconn=config.database_pool_min,
                maxconn=config.database_pool_max,
                host=config.database_host,
                port=config.database_port,
                database=config.database_name,
                user=config.database_user,
                password=config.database_password,
                connect_timeout=10
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

            # Service events table - tracks API startups/shutdowns for annotations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_events (
                    id SERIAL PRIMARY KEY,
                    event_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    event_type VARCHAR(32) NOT NULL,
                    message VARCHAR(256)
                )
            """)

            # Server snapshots table - captures per-heartbeat state for trend analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_snapshots (
                    id SERIAL PRIMARY KEY,
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    server_id BIGINT NOT NULL,
                    instance_id VARCHAR(255) NOT NULL,
                    game VARCHAR(16),
                    map VARCHAR(128),
                    gametype VARCHAR(32),
                    clientnum INTEGER DEFAULT 0,
                    maxclientnum INTEGER DEFAULT 1,
                    fill_rate REAL GENERATED ALWAYS AS (
                        CASE WHEN maxclientnum > 0 THEN clientnum::real / maxclientnum ELSE 0 END
                    ) STORED
                )
            """)

            # Map metrics table - daily aggregated map statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS map_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_date DATE NOT NULL,
                    game VARCHAR(16) NOT NULL,
                    map VARCHAR(128) NOT NULL,
                    total_snapshots INTEGER DEFAULT 0,
                    total_weighted_players REAL DEFAULT 0,
                    avg_fill_rate REAL DEFAULT 0,
                    peak_players INTEGER DEFAULT 0,
                    unique_servers INTEGER DEFAULT 0,
                    UNIQUE(metric_date, game, map)
                )
            """)

            # Server metrics table - daily aggregated server statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_date DATE NOT NULL,
                    server_id BIGINT NOT NULL,
                    instance_id VARCHAR(255) NOT NULL,
                    game VARCHAR(16),
                    avg_fill_rate REAL DEFAULT 0,
                    peak_players INTEGER DEFAULT 0,
                    total_snapshots INTEGER DEFAULT 0,
                    map_changes INTEGER DEFAULT 0,
                    UNIQUE(metric_date, server_id, instance_id)
                )
            """)

            # Game metrics table - daily aggregated game statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_date DATE NOT NULL,
                    game VARCHAR(16) NOT NULL,
                    total_players INTEGER DEFAULT 0,
                    total_servers INTEGER DEFAULT 0,
                    avg_fill_rate REAL DEFAULT 0,
                    peak_players INTEGER DEFAULT 0,
                    peak_servers INTEGER DEFAULT 0,
                    UNIQUE(metric_date, game)
                )
            """)

            # ==================== Hourly Aggregation Tables ====================
            # These tables store pre-aggregated metrics for efficient Grafana queries

            # Hourly server metrics - per-server hourly aggregates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hourly_server_metrics (
                    id SERIAL PRIMARY KEY,
                    hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
                    server_id BIGINT NOT NULL,
                    instance_id VARCHAR(255) NOT NULL,
                    game VARCHAR(16),
                    
                    -- Core metrics
                    snapshot_count INTEGER DEFAULT 0,
                    total_players INTEGER DEFAULT 0,
                    max_players INTEGER DEFAULT 0,
                    total_capacity INTEGER DEFAULT 0,
                    
                    -- Normalized metrics (for fair server size comparison)
                    avg_fill_rate REAL DEFAULT 0,
                    player_minutes REAL DEFAULT 0,
                    weighted_minutes REAL DEFAULT 0,
                    
                    -- Map activity
                    primary_map VARCHAR(128),
                    map_changes INTEGER DEFAULT 0,
                    
                    UNIQUE(hour_bucket, server_id, instance_id)
                )
            """)

            # Hourly map metrics - per-map hourly aggregates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hourly_map_metrics (
                    id SERIAL PRIMARY KEY,
                    hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
                    game VARCHAR(16) NOT NULL,
                    map VARCHAR(128) NOT NULL,
                    
                    -- Popularity metrics
                    total_player_minutes REAL DEFAULT 0,
                    weighted_player_minutes REAL DEFAULT 0,
                    appearance_count INTEGER DEFAULT 0,
                    
                    -- Fill metrics
                    avg_fill_rate REAL DEFAULT 0,
                    peak_players INTEGER DEFAULT 0,
                    
                    -- Spread metrics
                    unique_servers INTEGER DEFAULT 0,
                    
                    UNIQUE(hour_bucket, game, map)
                )
            """)

            # Hourly game metrics - per-game hourly aggregates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hourly_game_metrics (
                    id SERIAL PRIMARY KEY,
                    hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
                    game VARCHAR(16) NOT NULL,
                    
                    -- Population
                    total_players INTEGER DEFAULT 0,
                    peak_players INTEGER DEFAULT 0,
                    total_capacity INTEGER DEFAULT 0,
                    
                    -- Server counts
                    active_servers INTEGER DEFAULT 0,
                    
                    -- Normalized
                    avg_fill_rate REAL DEFAULT 0,
                    total_player_minutes REAL DEFAULT 0,
                    
                    UNIQUE(hour_bucket, game)
                )
            """)

            # Hourly instance metrics - per-instance hourly aggregates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hourly_instance_metrics (
                    id SERIAL PRIMARY KEY,
                    hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
                    instance_id VARCHAR(255) NOT NULL,
                    
                    -- Counts
                    server_count INTEGER DEFAULT 0,
                    total_players INTEGER DEFAULT 0,
                    total_capacity INTEGER DEFAULT 0,
                    
                    -- Health
                    avg_fill_rate REAL DEFAULT 0,
                    
                    UNIQUE(hour_bucket, instance_id)
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
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_service_events_time 
                ON service_events(event_time DESC)
            """)

            # Indexes for server_snapshots
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_recorded_at 
                ON server_snapshots(recorded_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_map 
                ON server_snapshots(game, map)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_server 
                ON server_snapshots(server_id, instance_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_game 
                ON server_snapshots(game)
            """)
            
            # Critical composite index for Grafana analytics queries
            # Covers the common pattern: WHERE recorded_at AND game
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_recorded_at_game 
                ON server_snapshots(recorded_at DESC, game)
            """)
            
            # Covering index for analytics - includes commonly selected columns
            # Allows index-only scans without table lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_analytics_covering 
                ON server_snapshots(recorded_at DESC, game) 
                INCLUDE (clientnum, maxclientnum, map, gametype)
            """)

            # Tune autovacuum for high-churn server_snapshots table
            # Downsampling deletes ~95% of rows older than 6 hours every 6 hours
            cursor.execute("""
                ALTER TABLE server_snapshots SET (
                    autovacuum_vacuum_scale_factor = 0.05,
                    autovacuum_analyze_scale_factor = 0.02,
                    fillfactor = 90
                )
            """)

            # Indexes for aggregated metrics tables
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_map_metrics_date 
                ON map_metrics(metric_date DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_server_metrics_date 
                ON server_metrics(metric_date DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_game_metrics_date 
                ON game_metrics(metric_date DESC)
            """)

            # Indexes for hourly aggregation tables
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hourly_server_bucket 
                ON hourly_server_metrics(hour_bucket DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hourly_server_game 
                ON hourly_server_metrics(game, hour_bucket DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hourly_map_bucket 
                ON hourly_map_metrics(hour_bucket DESC, game)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hourly_game_bucket 
                ON hourly_game_metrics(hour_bucket DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hourly_instance_bucket 
                ON hourly_instance_metrics(hour_bucket DESC)
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

    def batch_upsert_servers(self, servers: List[Dict]) -> None:
        """Batch insert or update multiple servers efficiently using execute_values."""
        if not servers:
            return
        
        with self.get_cursor() as cursor:
            from psycopg2.extras import execute_values
            
            # Build values list - NOW() is added as a literal in the SQL
            values = [
                (
                    s['server_id'], s['instance_id'], s['ip'], s['port'],
                    s['version'], s['game'], s['hostname'], s['clientnum'],
                    s['maxclientnum'], s['map_name'], s['gametype'],
                    s.get('resolved_ip')
                ) for s in servers
            ]
            
            execute_values(
                cursor,
                """
                INSERT INTO servers (id, instance_id, ip, port, version, game, hostname,
                                    clientnum, maxclientnum, map, gametype, 
                                    resolved_external_ip_address, last_seen)
                VALUES %s
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
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())"
            )

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
        """Get all instances, optionally excluding stale ones.
        
        Optimized to use 2 queries instead of N+1:
        1. Fetch all matching instances
        2. Fetch all servers for those instances in one query
        """
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
            
            if not instances:
                return []
            
            # Build a map for fast lookup
            instance_map = {inst['id']: dict(inst) for inst in instances}
            for inst_id in instance_map:
                instance_map[inst_id]['servers'] = []
            
            # Fetch all servers for these instances in ONE query
            instance_ids = list(instance_map.keys())
            cursor.execute(
                "SELECT * FROM servers WHERE instance_id = ANY(%s)",
                (instance_ids,)
            )
            servers = cursor.fetchall()
            
            # Group servers by instance
            for server in servers:
                inst_id = server['instance_id']
                if inst_id in instance_map:
                    instance_map[inst_id]['servers'].append(dict(server))
            
            return list(instance_map.values())

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

    def is_history_empty(self) -> bool:
        """Check if history metrics table is empty."""
        with self.get_cursor(commit=False) as cursor:
            cursor.execute("SELECT 1 FROM history_metrics LIMIT 1")
            return cursor.fetchone() is None

    def batch_insert_history(self, history_data: List[Dict]) -> None:
        """Batch insert history metrics."""
        if not history_data:
            return

        with self.get_cursor() as cursor:
            # Use execute_values for efficient batch insertion
            from psycopg2.extras import execute_values
            
            execute_values(
                cursor,
                """
                INSERT INTO history_metrics (recorded_at, instance_count, server_count, client_count)
                VALUES %s
                """,
                [(
                    datetime.fromtimestamp(item['time'], timezone.utc),
                    item['instance_count'],
                    item['server_count'],
                    item['client_count']
                ) for item in history_data]
            )

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
            # Use f-string for interval since psycopg2 doesn't support parameter binding inside INTERVAL
            cursor.execute(f"""
                DELETE FROM history_metrics 
                WHERE recorded_at < NOW() - INTERVAL '{max_days} days'
                RETURNING id
            """)
            deleted = cursor.fetchall()
            return len(deleted)

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._pool is not None

    def record_service_event(self, event_type: str, message: str = None) -> None:
        """Record a service event (startup, shutdown, etc.) for annotations."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO service_events (event_type, message)
                VALUES (%s, %s)
            """, (event_type, message))
            logger.info(f"Recorded service event: {event_type}")

    # ==================== Analytics Functions ====================

    def record_server_snapshot(self, server_id: int, instance_id: str, game: str,
                                map_name: str, gametype: str, clientnum: int,
                                maxclientnum: int) -> None:
        """Record a server snapshot for trend analysis."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO server_snapshots 
                    (server_id, instance_id, game, map, gametype, clientnum, maxclientnum)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (server_id, instance_id, game, map_name, gametype, clientnum, maxclientnum))

    def batch_record_server_snapshots(self, snapshots: List[Dict]) -> None:
        """Batch record multiple server snapshots efficiently."""
        if not snapshots:
            return
        
        with self.get_cursor() as cursor:
            from psycopg2.extras import execute_values
            execute_values(
                cursor,
                """
                INSERT INTO server_snapshots 
                    (server_id, instance_id, game, map, gametype, clientnum, maxclientnum)
                VALUES %s
                """,
                [(
                    s['server_id'],
                    s['instance_id'],
                    s['game'],
                    s['map'],
                    s['gametype'],
                    s['clientnum'],
                    s['maxclientnum']
                ) for s in snapshots]
            )

    def get_map_trends(self, days: int = 7, game: Optional[str] = None) -> List[Dict]:
        """Get map popularity trends with normalized fill rates."""
        with self.get_cursor(commit=False) as cursor:
            # Set statement timeout to prevent runaway queries
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            
            game_filter = "AND game = %s" if game else ""
            params = [days, game] if game else [days]
            
            cursor.execute(f"""
                WITH map_stats AS (
                    SELECT 
                        game,
                        map,
                        COUNT(*) as appearance_count,
                        AVG(fill_rate) as avg_fill_rate,
                        MAX(clientnum) as peak_players,
                        SUM(clientnum) as total_players,
                        COUNT(DISTINCT (server_id, instance_id)) as unique_servers,
                        -- Calculate churn: variance in player counts (lower = stickier)
                        STDDEV(clientnum) / NULLIF(AVG(clientnum), 0) as churn_rate
                    FROM server_snapshots
                    WHERE recorded_at >= NOW() - INTERVAL '%s days'
                    {game_filter}
                    GROUP BY game, map
                    HAVING COUNT(*) >= 5  -- Minimum appearances for significance
                ),
                ranked AS (
                    SELECT *,
                        -- Popularity score: fill_rate × log(appearances) × (1 - churn)
                        avg_fill_rate * LN(appearance_count + 1) * (1 - COALESCE(churn_rate, 0)) as popularity_score
                    FROM map_stats
                )
                SELECT 
                    game,
                    map,
                    ROUND(avg_fill_rate::numeric, 3) as avg_fill_rate,
                    ROUND(popularity_score::numeric, 3) as popularity_score,
                    ROUND(COALESCE(churn_rate, 0)::numeric, 3) as churn_rate,
                    peak_players,
                    total_players,
                    appearance_count,
                    unique_servers
                FROM ranked
                ORDER BY popularity_score DESC
                LIMIT 50
            """, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_server_trends(self, days: int = 7) -> List[Dict]:
        """Get server utilization and reliability trends."""
        with self.get_cursor(commit=False) as cursor:
            # Set statement timeout to prevent runaway queries
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            
            cursor.execute("""
                WITH server_stats AS (
                    SELECT 
                        ss.server_id,
                        ss.instance_id,
                        ss.game,
                        s.hostname,
                        COUNT(*) as total_snapshots,
                        AVG(ss.fill_rate) as avg_fill_rate,
                        MAX(ss.clientnum) as peak_players,
                        MAX(ss.maxclientnum) as max_capacity,
                        -- Reliability: % of time online (snapshots / expected snapshots)
                        COUNT(*)::real / NULLIF(
                            EXTRACT(EPOCH FROM (NOW() - MIN(ss.recorded_at))) / 30, 0
                        ) as reliability_score,
                        -- Consistency: inverse of fill rate variance
                        1 - COALESCE(STDDEV(ss.fill_rate), 0) as consistency_score,
                        COUNT(DISTINCT ss.map) as unique_maps
                    FROM server_snapshots ss
                    LEFT JOIN servers s ON ss.server_id = s.id AND ss.instance_id = s.instance_id
                    WHERE ss.recorded_at >= NOW() - INTERVAL '%s days'
                    GROUP BY ss.server_id, ss.instance_id, ss.game, s.hostname
                    HAVING COUNT(*) >= 10
                )
                SELECT 
                    server_id,
                    instance_id,
                    game,
                    hostname,
                    ROUND(avg_fill_rate::numeric, 3) as avg_fill_rate,
                    peak_players,
                    max_capacity,
                    ROUND(LEAST(reliability_score, 1)::numeric, 3) as reliability_score,
                    ROUND(consistency_score::numeric, 3) as consistency_score,
                    -- Quality score: fill_rate × reliability × consistency
                    ROUND((avg_fill_rate * LEAST(reliability_score, 1) * consistency_score)::numeric, 3) as quality_score,
                    total_snapshots,
                    unique_maps
                FROM server_stats
                ORDER BY quality_score DESC
                LIMIT 50
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    def get_game_trends(self, days: int = 7) -> List[Dict]:
        """Get game distribution and health metrics."""
        with self.get_cursor(commit=False) as cursor:
            # Set statement timeout to prevent runaway queries
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            
            cursor.execute("""
                WITH game_stats AS (
                    SELECT 
                        game,
                        COUNT(DISTINCT (server_id, instance_id)) as unique_servers,
                        SUM(clientnum) as total_players,
                        MAX(clientnum) as peak_players,
                        SUM(maxclientnum) as total_capacity,
                        AVG(fill_rate) as avg_fill_rate
                    FROM server_snapshots
                    WHERE recorded_at >= NOW() - INTERVAL '%s days'
                    GROUP BY game
                ),
                current_stats AS (
                    SELECT 
                        game,
                        COUNT(DISTINCT (server_id, instance_id)) as current_servers,
                        SUM(clientnum) as current_players
                    FROM server_snapshots
                    WHERE recorded_at >= NOW() - INTERVAL '5 minutes'
                    GROUP BY game
                )
                SELECT 
                    gs.game,
                    gs.unique_servers as total_unique_servers,
                    COALESCE(cs.current_servers, 0) as current_servers,
                    gs.total_players,
                    COALESCE(cs.current_players, 0) as current_players,
                    gs.peak_players,
                    gs.total_capacity,
                    ROUND(gs.avg_fill_rate::numeric, 3) as avg_fill_rate,
                    -- Health index: (current_players / peak) × (current_servers / unique_servers)
                    ROUND((
                        COALESCE(cs.current_players::real / NULLIF(gs.peak_players, 0), 0) *
                        COALESCE(cs.current_servers::real / NULLIF(gs.unique_servers, 0), 0)
                    )::numeric, 3) as health_index
                FROM game_stats gs
                LEFT JOIN current_stats cs ON gs.game = cs.game
                ORDER BY gs.total_players DESC
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    def get_instance_trends(self, days: int = 7) -> List[Dict]:
        """Get instance growth and density trends."""
        with self.get_cursor(commit=False) as cursor:
            # Set statement timeout to prevent runaway queries
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            
            cursor.execute("""
                WITH daily_instances AS (
                    SELECT 
                        DATE(created_at) as day,
                        COUNT(*) as new_instances
                    FROM instances
                    WHERE created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(created_at)
                ),
                instance_density AS (
                    SELECT 
                        i.id as instance_id,
                        COUNT(DISTINCT s.id) as server_count,
                        COALESCE(SUM(s.clientnum), 0) as total_players
                    FROM instances i
                    LEFT JOIN servers s ON i.id = s.instance_id
                    WHERE i.last_heartbeat > NOW() - INTERVAL '5 minutes'
                    GROUP BY i.id
                )
                SELECT 
                    (SELECT json_agg(json_build_object('day', day, 'new_instances', new_instances) ORDER BY day)
                     FROM daily_instances) as daily_growth,
                    (SELECT COUNT(*) FROM instances 
                     WHERE last_heartbeat > NOW() - INTERVAL '5 minutes') as active_instances,
                    (SELECT ROUND(AVG(server_count)::numeric, 2) FROM instance_density) as avg_servers_per_instance,
                    (SELECT ROUND(AVG(total_players)::numeric, 2) FROM instance_density) as avg_players_per_instance,
                    (SELECT COUNT(*) FROM instances 
                     WHERE created_at >= NOW() - INTERVAL '%s days') as new_instances_period
            """, (days, days))
            result = cursor.fetchone()
            return dict(result) if result else {}

    def get_temporal_trends(self, days: int = 7) -> Dict:
        """Get temporal patterns: hour-of-day and day-of-week activity."""
        with self.get_cursor(commit=False) as cursor:
            # Set statement timeout to prevent runaway queries
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            
            # Hourly averages
            cursor.execute("""
                SELECT 
                    EXTRACT(HOUR FROM recorded_at) as hour,
                    ROUND(AVG(clientnum)::numeric, 2) as avg_players,
                    ROUND(AVG(fill_rate)::numeric, 3) as avg_fill_rate,
                    COUNT(*) as snapshot_count
                FROM server_snapshots
                WHERE recorded_at >= NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(HOUR FROM recorded_at)
                ORDER BY hour
            """, (days,))
            hourly = [dict(row) for row in cursor.fetchall()]

            # Day of week averages (0=Sunday, 6=Saturday)
            cursor.execute("""
                SELECT 
                    EXTRACT(DOW FROM recorded_at) as day_of_week,
                    ROUND(AVG(clientnum)::numeric, 2) as avg_players,
                    ROUND(AVG(fill_rate)::numeric, 3) as avg_fill_rate,
                    COUNT(*) as snapshot_count
                FROM server_snapshots
                WHERE recorded_at >= NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(DOW FROM recorded_at)
                ORDER BY day_of_week
            """, (days,))
            daily = [dict(row) for row in cursor.fetchall()]

            # Heatmap data: hour × day_of_week
            cursor.execute("""
                SELECT 
                    EXTRACT(DOW FROM recorded_at) as day_of_week,
                    EXTRACT(HOUR FROM recorded_at) as hour,
                    ROUND(AVG(clientnum)::numeric, 2) as avg_players
                FROM server_snapshots
                WHERE recorded_at >= NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(DOW FROM recorded_at), EXTRACT(HOUR FROM recorded_at)
                ORDER BY day_of_week, hour
            """, (days,))
            heatmap = [dict(row) for row in cursor.fetchall()]

            return {
                'hourly': hourly,
                'daily': daily,
                'heatmap': heatmap
            }

    def get_map_gametype_affinity(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get top map+gametype combinations by normalized popularity."""
        with self.get_cursor(commit=False) as cursor:
            # Set statement timeout to prevent runaway queries
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            
            cursor.execute("""
                SELECT 
                    game,
                    map,
                    gametype,
                    COUNT(*) as appearance_count,
                    ROUND(AVG(fill_rate)::numeric, 3) as avg_fill_rate,
                    MAX(clientnum) as peak_players,
                    COUNT(DISTINCT (server_id, instance_id)) as unique_servers
                FROM server_snapshots
                WHERE recorded_at >= NOW() - INTERVAL '%s days'
                GROUP BY game, map, gametype
                HAVING COUNT(*) >= 5
                ORDER BY AVG(fill_rate) DESC, appearance_count DESC
                LIMIT %s
            """, (days, limit))
            return [dict(row) for row in cursor.fetchall()]

    def aggregate_daily_metrics(self) -> None:
        """Roll up today's snapshots into daily aggregated metrics tables."""
        with self.get_cursor() as cursor:
            # Aggregate map metrics
            cursor.execute("""
                INSERT INTO map_metrics (metric_date, game, map, total_snapshots, 
                    total_weighted_players, avg_fill_rate, peak_players, unique_servers)
                SELECT 
                    CURRENT_DATE,
                    game,
                    map,
                    COUNT(*),
                    SUM(clientnum * fill_rate),
                    AVG(fill_rate),
                    MAX(clientnum),
                    COUNT(DISTINCT (server_id, instance_id))
                FROM server_snapshots
                WHERE DATE(recorded_at) = CURRENT_DATE
                GROUP BY game, map
                ON CONFLICT (metric_date, game, map) DO UPDATE SET
                    total_snapshots = EXCLUDED.total_snapshots,
                    total_weighted_players = EXCLUDED.total_weighted_players,
                    avg_fill_rate = EXCLUDED.avg_fill_rate,
                    peak_players = GREATEST(map_metrics.peak_players, EXCLUDED.peak_players),
                    unique_servers = EXCLUDED.unique_servers
            """)

            # Aggregate server metrics
            cursor.execute("""
                INSERT INTO server_metrics (metric_date, server_id, instance_id, game,
                    avg_fill_rate, peak_players, total_snapshots, map_changes)
                SELECT 
                    CURRENT_DATE,
                    server_id,
                    instance_id,
                    game,
                    AVG(fill_rate),
                    MAX(clientnum),
                    COUNT(*),
                    COUNT(DISTINCT map) - 1
                FROM server_snapshots
                WHERE DATE(recorded_at) = CURRENT_DATE
                GROUP BY server_id, instance_id, game
                ON CONFLICT (metric_date, server_id, instance_id) DO UPDATE SET
                    avg_fill_rate = EXCLUDED.avg_fill_rate,
                    peak_players = GREATEST(server_metrics.peak_players, EXCLUDED.peak_players),
                    total_snapshots = EXCLUDED.total_snapshots,
                    map_changes = EXCLUDED.map_changes
            """)

            # Aggregate game metrics
            cursor.execute("""
                INSERT INTO game_metrics (metric_date, game, total_players, total_servers,
                    avg_fill_rate, peak_players, peak_servers)
                SELECT 
                    CURRENT_DATE,
                    game,
                    SUM(clientnum),
                    COUNT(DISTINCT (server_id, instance_id)),
                    AVG(fill_rate),
                    MAX(clientnum),
                    COUNT(DISTINCT (server_id, instance_id))
                FROM server_snapshots
                WHERE DATE(recorded_at) = CURRENT_DATE
                GROUP BY game
                ON CONFLICT (metric_date, game) DO UPDATE SET
                    total_players = EXCLUDED.total_players,
                    total_servers = EXCLUDED.total_servers,
                    avg_fill_rate = EXCLUDED.avg_fill_rate,
                    peak_players = GREATEST(game_metrics.peak_players, EXCLUDED.peak_players),
                    peak_servers = GREATEST(game_metrics.peak_servers, EXCLUDED.peak_servers)
            """)

            logger.debug("Daily metrics aggregation completed")

    def cleanup_old_snapshots(self, max_days: int = 7) -> int:
        """Delete server snapshots older than max_days. Set to -1 for indefinite storage."""
        if max_days < 0:
            logger.debug("Snapshot cleanup skipped: indefinite storage enabled")
            return 0
        
        with self.get_cursor() as cursor:
            # Use f-string for interval since psycopg2 doesn't support parameter binding inside INTERVAL
            cursor.execute(f"""
                DELETE FROM server_snapshots 
                WHERE recorded_at < NOW() - INTERVAL '{max_days} days'
            """)
            deleted = cursor.rowcount
            if deleted:
                logger.info(f"Cleaned up {deleted} old server snapshots")
            return deleted

    def downsample_old_snapshots(self, hours_to_keep_full: int = 1) -> int:
        """Delete raw snapshots older than hours_to_keep_full.
        
        With hourly aggregation in place, raw snapshots are only needed for 
        real-time dashboard views. Older data is preserved in hourly_*_metrics tables.
        
        Args:
            hours_to_keep_full: Hours of raw snapshots to retain (default 1 hour)
        """
        with self.get_cursor() as cursor:
            cursor.execute(f"""
                DELETE FROM server_snapshots
                WHERE recorded_at < NOW() - INTERVAL '{hours_to_keep_full} hours'
            """)
            
            deleted = cursor.rowcount
            if deleted:
                logger.info(f"Deleted {deleted} raw snapshots older than {hours_to_keep_full} hour(s)")
            return deleted

    def get_analytics_summary(self) -> Dict:
        """Get a summary of all analytics data.
        
        Optimized to use a single table scan instead of 6 separate subqueries.
        """
        with self.get_cursor(commit=False) as cursor:
            # Set statement timeout to prevent runaway queries
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            
            # Single scan with all aggregates computed together
            cursor.execute("""
                SELECT 
                    COUNT(*) as snapshots_24h,
                    COUNT(DISTINCT map) as unique_maps_24h,
                    COUNT(DISTINCT game) as unique_games_24h,
                    COUNT(DISTINCT (server_id, instance_id)) as unique_servers_24h,
                    ROUND(AVG(fill_rate)::numeric, 3) as avg_fill_rate_24h,
                    MAX(clientnum) as peak_players_24h
                FROM server_snapshots
                WHERE recorded_at >= NOW() - INTERVAL '24 hours'
            """)
            result = cursor.fetchone()
            return dict(result) if result else {}

    def vacuum_analytics_tables(self) -> None:
        """Run VACUUM on high-churn analytics tables to reclaim space.
        
        Must be run outside a transaction block since VACUUM cannot run inside one.
        """
        conn = self._pool.getconn()
        old_isolation_level = conn.isolation_level
        try:
            conn.set_isolation_level(0)  # AUTOCOMMIT mode required for VACUUM
            cursor = conn.cursor()
            
            # VACUUM server_snapshots - high churn from downsampling
            logger.debug("Running VACUUM on server_snapshots...")
            cursor.execute("VACUUM ANALYZE server_snapshots")
            
            # VACUUM other analytics tables
            cursor.execute("VACUUM ANALYZE history_metrics")
            cursor.execute("VACUUM ANALYZE map_metrics")
            cursor.execute("VACUUM ANALYZE server_metrics")
            cursor.execute("VACUUM ANALYZE game_metrics")
            
            cursor.close()
        except Exception as e:
            logger.error(f"VACUUM failed: {e}")
            raise
        finally:
            conn.set_isolation_level(old_isolation_level)
            self._pool.putconn(conn)

    def analyze_analytics_tables(self) -> None:
        """Run ANALYZE on analytics tables to update query planner statistics.
        
        Should be called after bulk deletions (cleanup/downsampling) to ensure
        the query planner has accurate row count and data distribution stats.
        """
        with self.get_cursor() as cursor:
            cursor.execute("ANALYZE server_snapshots")
            cursor.execute("ANALYZE history_metrics")
            logger.debug("Updated analytics table statistics")

    # ==================== Hourly Aggregation Functions ====================

    def aggregate_hourly_metrics(self, heartbeat_seconds: int = 30) -> Dict[str, int]:
        """Roll up raw snapshots into all hourly aggregate tables.
        
        Should be called at minute 5 of each hour to aggregate the previous hour.
        Uses weighted metrics for fair comparison between different server sizes.
        
        Args:
            heartbeat_seconds: Expected heartbeat interval (default 30s)
        
        Returns:
            Dict with count of rows inserted into each table
        """
        minutes_per_snapshot = heartbeat_seconds / 60.0
        results = {}
        
        with self.get_cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '120s'")
            
            # 1. Server-level aggregates
            # Deduplicate to one snapshot per minute per server, then aggregate
            cursor.execute("""
                INSERT INTO hourly_server_metrics (
                    hour_bucket, server_id, instance_id, game,
                    snapshot_count, total_players, max_players, total_capacity,
                    avg_fill_rate, player_minutes, weighted_minutes,
                    primary_map, map_changes
                )
                WITH deduped_snapshots AS (
                    SELECT DISTINCT ON (server_id, instance_id, date_trunc('minute', recorded_at))
                        date_trunc('hour', recorded_at) as hour_bucket,
                        server_id, 
                        instance_id, 
                        game,
                        map,
                        clientnum,
                        maxclientnum,
                        fill_rate
                    FROM server_snapshots
                    WHERE recorded_at >= date_trunc('hour', NOW()) - INTERVAL '1 hour'
                      AND recorded_at < date_trunc('hour', NOW())
                    ORDER BY server_id, instance_id, date_trunc('minute', recorded_at), recorded_at DESC
                )
                SELECT 
                    hour_bucket,
                    server_id, 
                    instance_id, 
                    game,
                    COUNT(*),
                    AVG(clientnum),
                    MAX(clientnum),
                    MAX(maxclientnum),
                    AVG(fill_rate),
                    AVG(clientnum) * 60.0 * %s,
                    AVG(fill_rate) * 60.0 * %s,
                    MODE() WITHIN GROUP (ORDER BY map),
                    GREATEST(COUNT(DISTINCT map) - 1, 0)
                FROM deduped_snapshots
                GROUP BY hour_bucket, server_id, instance_id, game
                ON CONFLICT (hour_bucket, server_id, instance_id) DO UPDATE SET
                    snapshot_count = EXCLUDED.snapshot_count,
                    total_players = EXCLUDED.total_players,
                    max_players = EXCLUDED.max_players,
                    total_capacity = EXCLUDED.total_capacity,
                    avg_fill_rate = EXCLUDED.avg_fill_rate,
                    player_minutes = EXCLUDED.player_minutes,
                    weighted_minutes = EXCLUDED.weighted_minutes,
                    primary_map = EXCLUDED.primary_map,
                    map_changes = EXCLUDED.map_changes
            """, (minutes_per_snapshot, minutes_per_snapshot))
            results['server'] = cursor.rowcount

            # 2. Map-level aggregates
            # Deduplicate to one snapshot per server per map per minute
            cursor.execute("""
                INSERT INTO hourly_map_metrics (
                    hour_bucket, game, map,
                    total_player_minutes, weighted_player_minutes, appearance_count,
                    avg_fill_rate, peak_players, unique_servers
                )
                WITH deduped_snapshots AS (
                    SELECT DISTINCT ON (server_id, instance_id, map, date_trunc('minute', recorded_at))
                        date_trunc('hour', recorded_at) as hour_bucket,
                        game,
                        map,
                        date_trunc('minute', recorded_at) as minute_bucket,
                        server_id,
                        instance_id,
                        clientnum,
                        fill_rate
                    FROM server_snapshots
                    WHERE recorded_at >= date_trunc('hour', NOW()) - INTERVAL '1 hour'
                      AND recorded_at < date_trunc('hour', NOW())
                    ORDER BY server_id, instance_id, map, date_trunc('minute', recorded_at), recorded_at DESC
                ),
                per_minute_totals AS (
                    SELECT 
                        hour_bucket,
                        game,
                        map,
                        minute_bucket,
                        SUM(clientnum) as minute_players,
                        AVG(fill_rate) as minute_fill_rate,
                        COUNT(DISTINCT (server_id, instance_id)) as minute_servers
                    FROM deduped_snapshots
                    GROUP BY hour_bucket, game, map, minute_bucket
                )
                SELECT 
                    hour_bucket,
                    game,
                    map,
                    AVG(minute_players) * 60.0 * %s,
                    AVG(minute_fill_rate) * 60.0 * %s,
                    SUM(minute_servers),
                    AVG(minute_fill_rate),
                    MAX(minute_players),
                    MAX(minute_servers)
                FROM per_minute_totals
                GROUP BY hour_bucket, game, map
                ON CONFLICT (hour_bucket, game, map) DO UPDATE SET
                    total_player_minutes = EXCLUDED.total_player_minutes,
                    weighted_player_minutes = EXCLUDED.weighted_player_minutes,
                    appearance_count = EXCLUDED.appearance_count,
                    avg_fill_rate = EXCLUDED.avg_fill_rate,
                    peak_players = EXCLUDED.peak_players,
                    unique_servers = EXCLUDED.unique_servers
            """, (minutes_per_snapshot, minutes_per_snapshot))
            results['map'] = cursor.rowcount

            # 3. Game-level aggregates
            # Uses nested CTEs to correctly calculate peak concurrent players:
            # 1. Deduplicate to one snapshot per server per minute (latest one)
            # 2. Sum players across servers for each minute
            # 3. Take MAX of those sums for peak concurrent
            cursor.execute("""
                INSERT INTO hourly_game_metrics (
                    hour_bucket, game,
                    total_players, peak_players, total_capacity,
                    active_servers, avg_fill_rate, total_player_minutes
                )
                WITH deduped_snapshots AS (
                    -- Take ONE snapshot per server per minute (the latest one)
                    SELECT DISTINCT ON (server_id, instance_id, game, date_trunc('minute', recorded_at))
                        date_trunc('hour', recorded_at) as hour_bucket,
                        game,
                        date_trunc('minute', recorded_at) as minute_bucket,
                        clientnum,
                        maxclientnum,
                        fill_rate
                    FROM server_snapshots
                    WHERE recorded_at >= date_trunc('hour', NOW()) - INTERVAL '1 hour'
                      AND recorded_at < date_trunc('hour', NOW())
                    ORDER BY server_id, instance_id, game, date_trunc('minute', recorded_at), recorded_at DESC
                ),
                per_minute_totals AS (
                    -- Sum players across all servers for each minute
                    SELECT 
                        hour_bucket,
                        game,
                        minute_bucket,
                        SUM(clientnum) as minute_players,
                        SUM(maxclientnum) as minute_capacity,
                        AVG(fill_rate) as minute_fill_rate
                    FROM deduped_snapshots
                    GROUP BY hour_bucket, game, minute_bucket
                )
                SELECT 
                    hour_bucket,
                    game,
                    AVG(minute_players),
                    MAX(minute_players),
                    MAX(minute_capacity),
                    (SELECT COUNT(DISTINCT (server_id, instance_id)) 
                     FROM server_snapshots ss 
                     WHERE ss.game = pmt.game 
                       AND ss.recorded_at >= date_trunc('hour', NOW()) - INTERVAL '1 hour'
                       AND ss.recorded_at < date_trunc('hour', NOW())),
                    AVG(minute_fill_rate),
                    AVG(minute_players) * 60.0 * %s
                FROM per_minute_totals pmt
                GROUP BY hour_bucket, game
                ON CONFLICT (hour_bucket, game) DO UPDATE SET
                    total_players = EXCLUDED.total_players,
                    peak_players = EXCLUDED.peak_players,
                    total_capacity = EXCLUDED.total_capacity,
                    active_servers = EXCLUDED.active_servers,
                    avg_fill_rate = EXCLUDED.avg_fill_rate,
                    total_player_minutes = EXCLUDED.total_player_minutes
            """, (minutes_per_snapshot,))
            results['game'] = cursor.rowcount

            # 4. Instance-level aggregates
            # Uses same deduplication approach as game-level
            cursor.execute("""
                INSERT INTO hourly_instance_metrics (
                    hour_bucket, instance_id,
                    server_count, total_players, total_capacity, avg_fill_rate
                )
                WITH deduped_snapshots AS (
                    SELECT DISTINCT ON (server_id, instance_id, date_trunc('minute', recorded_at))
                        date_trunc('hour', recorded_at) as hour_bucket,
                        instance_id,
                        date_trunc('minute', recorded_at) as minute_bucket,
                        server_id,
                        clientnum,
                        maxclientnum,
                        fill_rate
                    FROM server_snapshots
                    WHERE recorded_at >= date_trunc('hour', NOW()) - INTERVAL '1 hour'
                      AND recorded_at < date_trunc('hour', NOW())
                    ORDER BY server_id, instance_id, date_trunc('minute', recorded_at), recorded_at DESC
                ),
                per_minute_totals AS (
                    SELECT 
                        hour_bucket,
                        instance_id,
                        minute_bucket,
                        COUNT(DISTINCT server_id) as minute_servers,
                        SUM(clientnum) as minute_players,
                        SUM(maxclientnum) as minute_capacity,
                        AVG(fill_rate) as minute_fill_rate
                    FROM deduped_snapshots
                    GROUP BY hour_bucket, instance_id, minute_bucket
                )
                SELECT 
                    hour_bucket,
                    instance_id,
                    MAX(minute_servers),
                    AVG(minute_players),
                    MAX(minute_capacity),
                    AVG(minute_fill_rate)
                FROM per_minute_totals
                GROUP BY hour_bucket, instance_id
                ON CONFLICT (hour_bucket, instance_id) DO UPDATE SET
                    server_count = EXCLUDED.server_count,
                    total_players = EXCLUDED.total_players,
                    total_capacity = EXCLUDED.total_capacity,
                    avg_fill_rate = EXCLUDED.avg_fill_rate
            """)
            results['instance'] = cursor.rowcount
            
            logger.info(f"Hourly aggregation complete: {results}")
            return results

    def cleanup_hourly_metrics(self, max_days: int = 7) -> Dict[str, int]:
        """Delete hourly metrics older than max_days.
        
        Args:
            max_days: Maximum age of hourly data to keep (default 7 days)
        
        Returns:
            Dict with count of rows deleted from each table
        """
        if max_days < 0:
            logger.debug("Hourly cleanup skipped: indefinite storage enabled")
            return {}
        
        results = {}
        with self.get_cursor() as cursor:
            for table in ['hourly_server_metrics', 'hourly_map_metrics', 
                          'hourly_game_metrics', 'hourly_instance_metrics']:
                cursor.execute(f"""
                    DELETE FROM {table} 
                    WHERE hour_bucket < NOW() - INTERVAL '{max_days} days'
                """)
                results[table] = cursor.rowcount
        
        total = sum(results.values())
        if total > 0:
            logger.info(f"Cleaned up {total} old hourly metric rows")
        return results

    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")



# Singleton instance
db = Database()
