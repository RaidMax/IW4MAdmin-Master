"""
Localization resource for fetching translations from Google Sheets.
Uses caching to reduce API calls.
"""

import csv
import logging
import urllib.request
from io import StringIO
from typing import Optional, Dict, List, Tuple

from cachetools import TTLCache
from flask_restful import Resource

from ..config import config

logger = logging.getLogger(__name__)

# Cache for localization data - shared across all requests
_localization_cache = TTLCache(maxsize=10, ttl=config.localization_cache_ttl)


class Localization(Resource):
    def _fetch_csv_data(self) -> Optional[csv.DictReader]:
        """Fetch and parse CSV data from Google Sheets with caching."""
        cache_key = 'csv_data'
        
        if cache_key in _localization_cache:
            logger.debug("Using cached localization data")
            return _localization_cache[cache_key]
        
        try:
            url = config.localization_url
            if not url:
                logger.warning("Localization URL not configured")
                return None
            
            response = urllib.request.urlopen(url, timeout=10)
            data = response.read().decode('utf-8')
            # Store raw data in cache, create new DictReader each time
            _localization_cache['raw_data'] = data
            logger.info("Fetched fresh localization data from Google Sheets")
            return csv.DictReader(StringIO(data))
        except Exception as e:
            logger.error(f"Failed to fetch localization data: {e}")
            # Try to use cached raw data if available
            if 'raw_data' in _localization_cache:
                return csv.DictReader(StringIO(_localization_cache['raw_data']))
            return None

    def _get_csv_reader(self) -> Optional[csv.DictReader]:
        """Get a CSV reader, using cached raw data if available."""
        if 'raw_data' in _localization_cache:
            return csv.DictReader(StringIO(_localization_cache['raw_data']))
        return self._fetch_csv_data()

    def list(self) -> Tuple[List[Dict], int]:
        """Get all localizations."""
        csv_data = self._fetch_csv_data()
        if not csv_data:
            return [], 200

        localization = []
        for language in csv_data.fieldnames[1:]:
            localization.append({
                'LocalizationName': language,
                'LocalizationIndex': {'Set': {}}
            })

        for row in csv_data:
            localization_string = row['STRING']
            for idx, language in enumerate(csv_data.fieldnames[1:]):
                localization[idx]['LocalizationIndex']['Set'][localization_string] = row[language]

        return localization, 200

    def get(self, language_tag: Optional[str] = None) -> Tuple[Dict, int]:
        """Get localization for a specific language."""
        if language_tag is None:
            result = self.list()
            return result[0][0] if result[0] else {}, 200

        csv_data = self._get_csv_reader()
        if not csv_data:
            return {'message': 'Localization data unavailable'}, 503

        # Find matching language
        valid_language_tag = next(
            (lang for lang in csv_data.fieldnames[1:] if lang == language_tag),
            None
        )
        if not valid_language_tag:
            valid_language_tag = next(
                (lang for lang in csv_data.fieldnames[1:] if lang.startswith(language_tag[:2])),
                None
            )
        if not valid_language_tag:
            valid_language_tag = 'en-US'

        localization = {
            'LocalizationName': valid_language_tag,
            'LocalizationIndex': {'Set': {}}
        }

        for row in csv_data:
            localization_string = row['STRING']
            localization['LocalizationIndex']['Set'][localization_string] = row.get(valid_language_tag, '')

        return localization, 200

