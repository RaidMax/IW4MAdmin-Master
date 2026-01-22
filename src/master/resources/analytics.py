"""
Analytics resource for aggregate trend data.
Provides endpoints for map, server, game, instance, and temporal trends.
"""

import logging
import time
from threading import Lock

from flask import request
from flask_restful import Resource

from .. import limiter
from ..config import config
from ..database import db

logger = logging.getLogger(__name__)


class AnalyticsCache:
    """Simple time-based cache for analytics results."""
    
    def __init__(self, ttl_seconds: int = 60):
        self._cache = {}
        self._lock = Lock()
        self._ttl = ttl_seconds
    
    def get(self, key: str):
        """Get cached value if not expired."""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return value
                del self._cache[key]
        return None
    
    def set(self, key: str, value):
        """Cache a value with current timestamp."""
        with self._lock:
            self._cache[key] = (value, time.time())


# Singleton cache instance - 60 second TTL
_analytics_cache = AnalyticsCache(ttl_seconds=60)


class Analytics(Resource):
    decorators = [limiter.limit(config.rate_limit_default)]

    def get(self, trend_type=None):
        """Get analytics data by trend type."""
        days = request.args.get('days', 7, type=int)
        days = max(1, min(days, 90))  # Clamp to 1-90 days
        
        if trend_type is None or trend_type == 'summary':
            return self._get_summary()
        elif trend_type == 'maps':
            return self._get_map_trends(days)
        elif trend_type == 'servers':
            return self._get_server_trends(days)
        elif trend_type == 'games':
            return self._get_game_trends(days)
        elif trend_type == 'instances':
            return self._get_instance_trends(days)
        elif trend_type == 'temporal':
            return self._get_temporal_trends(days)
        elif trend_type == 'affinity':
            return self._get_map_gametype_affinity(days)
        else:
            return {'message': f'Unknown trend type: {trend_type}'}, 400

    def _get_summary(self):
        """Get overall analytics summary (cached)."""
        cache_key = 'summary'
        
        # Check cache first
        cached = _analytics_cache.get(cache_key)
        if cached is not None:
            return {
                'status': 'ok',
                'cached': True,
                'data': cached
            }, 200
        
        try:
            summary = db.get_analytics_summary()
            _analytics_cache.set(cache_key, summary)
            return {
                'status': 'ok',
                'cached': False,
                'data': summary
            }, 200
        except Exception as e:
            logger.error(f'Error fetching analytics summary: {e}')
            return {'message': 'Error fetching analytics summary'}, 500

    def _get_map_trends(self, days: int):
        """Get map popularity and stickiness trends (cached)."""
        game = request.args.get('game', None, type=str)
        cache_key = f'maps_{days}_{game}'
        
        cached = _analytics_cache.get(cache_key)
        if cached is not None:
            return {'status': 'ok', 'cached': True, 'days': days, 'game_filter': game, 'count': len(cached), 'data': cached}, 200
        
        try:
            trends = db.get_map_trends(days=days, game=game)
            _analytics_cache.set(cache_key, trends)
            return {'status': 'ok', 'cached': False, 'days': days, 'game_filter': game, 'count': len(trends), 'data': trends}, 200
        except Exception as e:
            logger.error(f'Error fetching map trends: {e}')
            return {'message': 'Error fetching map trends'}, 500

    def _get_server_trends(self, days: int):
        """Get server utilization and reliability trends (cached)."""
        cache_key = f'servers_{days}'
        
        cached = _analytics_cache.get(cache_key)
        if cached is not None:
            return {'status': 'ok', 'cached': True, 'days': days, 'count': len(cached), 'data': cached}, 200
        
        try:
            trends = db.get_server_trends(days=days)
            _analytics_cache.set(cache_key, trends)
            return {'status': 'ok', 'cached': False, 'days': days, 'count': len(trends), 'data': trends}, 200
        except Exception as e:
            logger.error(f'Error fetching server trends: {e}')
            return {'message': 'Error fetching server trends'}, 500

    def _get_game_trends(self, days: int):
        """Get game distribution and health metrics (cached)."""
        cache_key = f'games_{days}'
        
        cached = _analytics_cache.get(cache_key)
        if cached is not None:
            return {'status': 'ok', 'cached': True, 'days': days, 'count': len(cached), 'data': cached}, 200
        
        try:
            trends = db.get_game_trends(days=days)
            _analytics_cache.set(cache_key, trends)
            return {'status': 'ok', 'cached': False, 'days': days, 'count': len(trends), 'data': trends}, 200
        except Exception as e:
            logger.error(f'Error fetching game trends: {e}')
            return {'message': 'Error fetching game trends'}, 500

    def _get_instance_trends(self, days: int):
        """Get instance growth and density trends (cached)."""
        cache_key = f'instances_{days}'
        
        cached = _analytics_cache.get(cache_key)
        if cached is not None:
            return {'status': 'ok', 'cached': True, 'days': days, 'data': cached}, 200
        
        try:
            trends = db.get_instance_trends(days=days)
            _analytics_cache.set(cache_key, trends)
            return {'status': 'ok', 'cached': False, 'days': days, 'data': trends}, 200
        except Exception as e:
            logger.error(f'Error fetching instance trends: {e}')
            return {'message': 'Error fetching instance trends'}, 500

    def _get_temporal_trends(self, days: int):
        """Get hour-of-day and day-of-week activity patterns (cached)."""
        cache_key = f'temporal_{days}'
        
        cached = _analytics_cache.get(cache_key)
        if cached is not None:
            return {'status': 'ok', 'cached': True, 'days': days, 'data': cached}, 200
        
        try:
            trends = db.get_temporal_trends(days=days)
            _analytics_cache.set(cache_key, trends)
            return {'status': 'ok', 'cached': False, 'days': days, 'data': trends}, 200
        except Exception as e:
            logger.error(f'Error fetching temporal trends: {e}')
            return {'message': 'Error fetching temporal trends'}, 500

    def _get_map_gametype_affinity(self, days: int):
        """Get top map+gametype combinations (cached)."""
        limit = request.args.get('limit', 20, type=int)
        limit = max(1, min(limit, 100))
        cache_key = f'affinity_{days}_{limit}'
        
        cached = _analytics_cache.get(cache_key)
        if cached is not None:
            return {'status': 'ok', 'cached': True, 'days': days, 'count': len(cached), 'data': cached}, 200
        
        try:
            trends = db.get_map_gametype_affinity(days=days, limit=limit)
            _analytics_cache.set(cache_key, trends)
            return {'status': 'ok', 'cached': False, 'days': days, 'count': len(trends), 'data': trends}, 200
        except Exception as e:
            logger.error(f'Error fetching map-gametype affinity: {e}')
            return {'message': 'Error fetching map-gametype affinity'}, 500

