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

    @staticmethod
    def _is_public_ipv4(ip_str) -> bool:
        """True if the value is a literal, publicly routable IPv4 address."""
        if not ip_str:
            return False
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        return ip.version == 4 and not (
            ip.is_private or ip.is_loopback or ip.is_link_local or
            ip.is_unspecified or ip.is_reserved or ip.is_multicast
        )

    @staticmethod
    def _resolve_webfront_ipv4(webfront_url) -> str:
        """Resolve the webfront hostname to a public IPv4 address (None if unavailable)."""
        if not webfront_url:
            return None
        try:
            from urllib.parse import urlparse
            import socket
            hostname = urlparse(webfront_url).hostname
            if not hostname:
                return None
            # getaddrinfo with AF_INET forces IPv4
            addrs = socket.getaddrinfo(hostname, None, socket.AF_INET)
            if addrs:
                webfront_ip = addrs[0][4][0]
                if Instance._is_public_ipv4(webfront_ip):
                    return webfront_ip
        except Exception:
            pass  # Ignore resolution errors
        return None

    def _process_servers(self, data: dict, remote_ip: str) -> None:
        """Process and normalize server data."""
        servers = data.get('servers', [])
        webfront_ip = False  # False = not looked up yet (resolution is deferred/cached)

        for server in servers:
            # Handle IP address
            parsed_ip = None
            try:
                if 'ip' in server:
                    parsed_ip = ipaddress.ip_address(server['ip'])
            except ValueError:
                pass

            # The address the instance reported for the game server itself
            server_is_public = self._is_public_ipv4(server.get('ip'))

            # Update IP if missing, private, or loopback
            if 'ip' not in server or (parsed_ip and (
                parsed_ip.is_private or parsed_ip.is_loopback or server['ip'] == '0.0.0.0'
            )):
                server['ip'] = remote_ip

            # Handle resolved_external_ip_address - this is the address clients
            # connect to, so the game server's own public address always wins.
            # The instance/webfront host address is only a fallback for servers
            # bound to internal or loopback addresses.
            # Priority:
            # 1. Server IP from the payload (if a public IPv4)
            # 2. Instance-supplied resolved address (if a public IPv4)
            # 3. Remote IP (if a public IPv4)
            # 4. Webfront URL hostname (if it resolves to a public IPv4)
            # 5. Remote IP (IPv6 / unknown fallback)

            candidate_ip = None

            # 1. Public game server address reported by the instance
            if server_is_public:
                candidate_ip = server['ip']

            # 2. Resolved address supplied by the instance
            resolved_ip = server.get('resolved_external_ip_address')
            if not candidate_ip and self._is_public_ipv4(resolved_ip):
                candidate_ip = resolved_ip

            # 3. Address the heartbeat came from
            if not candidate_ip and self._is_public_ipv4(remote_ip):
                candidate_ip = remote_ip

            # 4. Webfront hostname (resolved at most once per request)
            if not candidate_ip:
                if webfront_ip is False:
                    webfront_ip = self._resolve_webfront_ipv4(data.get('webfront_url'))
                candidate_ip = webfront_ip

            # 5. Fallback to whatever remote_ip is (even if IPv6) if we found nothing
            if not candidate_ip:
                candidate_ip = remote_ip

            server['resolved_external_ip_address'] = candidate_ip

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
            
            # Collect server and snapshot data for batch operations
            server_data = []
            snapshots = []
            for server in instance.servers:
                server_data.append({
                    'server_id': server.id,
                    'instance_id': instance.id,
                    'ip': server.ip,
                    'port': server.port,
                    'version': server.version,
                    'game': server.game,
                    'hostname': server.hostname,
                    'clientnum': server.clientnum,
                    'maxclientnum': server.maxclientnum,
                    'map_name': server.map,
                    'gametype': server.gametype,
                    'resolved_ip': server.resolved_external_ip_address
                })
                snapshots.append({
                    'server_id': server.id,
                    'instance_id': instance.id,
                    'game': server.game,
                    'map': server.map,
                    'gametype': server.gametype,
                    'clientnum': server.clientnum,
                    'maxclientnum': server.maxclientnum
                })
            
            # Batch upsert all servers in one DB call (instead of N calls)
            if server_data:
                db.batch_upsert_servers(server_data)
            
            # Batch insert all snapshots in one DB call
            if snapshots:
                db.batch_record_server_snapshots(snapshots)
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
            
            # Collect server and snapshot data for batch operations
            server_data = []
            snapshots = []
            for server in instance.servers:
                server_data.append({
                    'server_id': server.id,
                    'instance_id': instance.id,
                    'ip': server.ip,
                    'port': server.port,
                    'version': server.version,
                    'game': server.game,
                    'hostname': server.hostname,
                    'clientnum': server.clientnum,
                    'maxclientnum': server.maxclientnum,
                    'map_name': server.map,
                    'gametype': server.gametype,
                    'resolved_ip': server.resolved_external_ip_address
                })
                snapshots.append({
                    'server_id': server.id,
                    'instance_id': instance.id,
                    'game': server.game,
                    'map': server.map,
                    'gametype': server.gametype,
                    'clientnum': server.clientnum,
                    'maxclientnum': server.maxclientnum
                })
            
            # Batch upsert all servers in one DB call (instead of N calls)
            if server_data:
                db.batch_upsert_servers(server_data)
            
            # Batch insert all snapshots in one DB call
            if snapshots:
                db.batch_record_server_snapshots(snapshots)
        except Exception as e:
            logger.debug(f'Database persistence skipped: {e}')

        return {'message': 'instance added successfully'}, 200

