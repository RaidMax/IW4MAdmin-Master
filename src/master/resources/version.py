"""
Version resource for IW4MAdmin client version management.
"""

import json
import logging
import os

from flask import request
from flask_restful import Resource
from marshmallow import ValidationError

from .. import app
from ..schema.versionschema import VersionUpdateSchema

logger = logging.getLogger(__name__)


class Version(Resource):
    def __init__(self):
        self.config_folder = 'config'
        self.master_file_name = 'master'
        self._schema = VersionUpdateSchema()

    def get(self, api_version: int = 0):
        """Get current version information."""
        config_path = os.path.join(
            self.config_folder,
            f'{self.master_file_name}.v{api_version}.json'
        )
        
        try:
            with open(config_path) as config_file:
                config = json.load(config_file)
            return {
                'current-version-stable': config.get('current-version-stable'),
                'current-version-prerelease': config.get('current-version-prerelease')
            }, 200
        except FileNotFoundError:
            logger.warning(f"Version config not found: {config_path}")
            return {'message': f'Version {api_version} not found'}, 404
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in version config: {e}")
            return {'message': 'Configuration error'}, 500

    def post(self):
        """Update version information (requires jwt-secret)."""
        if not request.is_json:
            return {'message': 'Request body must be JSON'}, 400

        try:
            data = self._schema.load(request.get_json())
        except ValidationError as err:
            return {'message': err.messages}, 400

        config_path = os.path.join(
            self.config_folder,
            f'{self.master_file_name}.v1.json'
        )

        try:
            with open(config_path) as config_file:
                config = json.load(config_file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load version config: {e}")
            return {'message': 'Configuration error'}, 500

        if data.get('current_version_stable'):
            config['current-version-stable'] = data['current_version_stable']
        if data.get('current_version_prerelease'):
            config['current-version-prerelease'] = data['current_version_prerelease']

        if data['jwt_secret'] == app.config['JWT_SECRET_KEY']:
            try:
                with open(config_path, 'w') as out_json:
                    json.dump(config, out_json, indent=4)
                logger.info(f"Version updated: stable={config.get('current-version-stable')}, prerelease={config.get('current-version-prerelease')}")
                return {
                    'message': f"stable is {config.get('current-version-stable')}, prerelease is {config.get('current-version-prerelease')}"
                }, 200
            except IOError as e:
                logger.error(f"Failed to write version config: {e}")
                return {'message': 'Failed to save configuration'}, 500
        else:
            logger.warning("Invalid jwt-secret in version update request")
            return {'message': 'invalid jwt secret'}, 401

