"""
Instance resource for managing IW4MAdmin instances and their servers.
"""

import logging

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
import ipaddress

from .. import ctx, limiter
from ..config import config
from ..database import db
from ..schema.instanceschema import InstanceSchema

logger = logging.getLogger(__name__)


class Instance(Resource):
    decorators = [limiter.limit(config.rate_limit_default)]

    def __init__(self):
        pass

    def get(self, id=None):
        """Get instance(s) - all or by ID."""
        if id is None:
            schema = InstanceSchema(many=True)
            instances = schema.dump(ctx.get_instances())
            return instances
        else:
            try:
                instance = ctx.get_instance(id)
                return InstanceSchema().dump(instance)
            except KeyError:
                return {'message': 'instance not found'}, 404

    def _get_remote_ip(self) -> str:
        """Get the remote IP address, handling proxy headers."""
        return (
            request.headers.get('CF-Connecting-IP') or
            request.headers.get('X-Real-IP') or
            request.remote_addr
        )

    def _process_servers(self, data: dict, remote_ip: str) -> None:
        """Process and normalize server data."""
        servers = data.get('servers', [])
        for server in servers:
            # Handle IP address
            parsed_ip = None
            try:
                if 'ip' in server:
                    parsed_ip = ipaddress.ip_address(server['ip'])
            except ValueError:
                pass

            # Update IP if missing, private, or loopback
            if 'ip' not in server or (parsed_ip and (
                parsed_ip.is_private or parsed_ip.is_loopback or server['ip'] == '0.0.0.0'
            )):
                server['ip'] = remote_ip

            # Default version if not provided
            if 'version' not in server:
                server['version'] = 'Unknown'

            # Mask port to valid range
            if 'port' in server:
                server['port'] = server['port'] & 0xffff

    @limiter.limit(config.rate_limit_write)
    def put(self, id):
        """Update an existing instance (heartbeat)."""
        if not request.is_json:
            return {'message': 'Request body must be JSON'}, 400

        try:
            data = request.get_json(silent=True)
            if not data:
                return {'message': 'Invalid JSON body'}, 400

            remote_ip = self._get_remote_ip()
            self._process_servers(data, remote_ip)
            data['ip_address'] = remote_ip

            instance = InstanceSchema().load(data)
        except ValidationError as err:
            logger.warning(f'Instance validation failed: {err.messages}')
            return {'message': err.messages}, 400
        except Exception as e:
            logger.error(f'Error processing instance update: {e}')
            return {'message': 'Invalid request data'}, 400

        ctx.update_instance(instance)

        # Persist to database if available
        try:
            db.upsert_instance(
                instance_id=instance.id,
                version=instance.version,
                uptime=instance.uptime,
                ip_address=instance.ip_address,
                webfront_url=instance.webfront_url
            )
            for server in instance.servers:
                db.upsert_server(
                    server_id=server.id,
                    instance_id=instance.id,
                    ip=server.ip,
                    port=server.port,
                    version=server.version,
                    game=server.game,
                    hostname=server.hostname,
                    clientnum=server.clientnum,
                    maxclientnum=server.maxclientnum,
                    map_name=server.map,
                    gametype=server.gametype,
                    resolved_ip=server.resolved_external_ip_address
                )
        except Exception as e:
            logger.debug(f'Database persistence skipped: {e}')

        return {'message': 'instance updated successfully'}, 200

    @jwt_required()
    @limiter.limit(config.rate_limit_write)
    def post(self):
        """Add a new instance (requires JWT auth)."""
        if not request.is_json:
            return {'message': 'Request body must be JSON'}, 400

        try:
            data = request.get_json(silent=True)
            if not data:
                return {'message': 'Invalid JSON body'}, 400

            remote_ip = self._get_remote_ip()
            self._process_servers(data, remote_ip)
            data['ip_address'] = remote_ip

            instance = InstanceSchema().load(data)
        except ValidationError as err:
            logger.warning(f'Instance validation failed: {err.messages}')
            return {'message': err.messages}, 400
        except Exception as e:
            logger.error(f'Error processing new instance: {e}', exc_info=True)
            return {'message': f'Invalid request data: {str(e)}'}, 400

        ctx.add_instance(instance)

        # Persist to database if available
        try:
            db.upsert_instance(
                instance_id=instance.id,
                version=instance.version,
                uptime=instance.uptime,
                ip_address=instance.ip_address,
                webfront_url=instance.webfront_url
            )
            for server in instance.servers:
                db.upsert_server(
                    server_id=server.id,
                    instance_id=instance.id,
                    ip=server.ip,
                    port=server.port,
                    version=server.version,
                    game=server.game,
                    hostname=server.hostname,
                    clientnum=server.clientnum,
                    maxclientnum=server.maxclientnum,
                    map_name=server.map,
                    gametype=server.gametype,
                    resolved_ip=server.resolved_external_ip_address
                )
        except Exception as e:
            logger.debug(f'Database persistence skipped: {e}')

        return {'message': 'instance added successfully'}, 200

