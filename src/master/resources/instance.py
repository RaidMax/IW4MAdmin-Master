import logging

from flask_restful import Resource
from flask import request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from ..schema.instanceschema import InstanceSchema
from .. import ctx
from netaddr import IPAddress, AddrFormatError


class Instance(Resource):
    def get(self, id=None):
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

    # @jwt_required
    def put(self, id):
        try:
            remote_ip = request.remote_addr
            for index in range(0, len(request.json['servers'])):
                server = request.json['servers'][index]

                parsed_ip = None
                try:
                    parsed_ip = IPAddress(server['ip'])
                except (AddrFormatError, KeyError):
                    pass

                if 'ip' not in server or parsed_ip is None or parsed_ip.is_private() or parsed_ip.is_loopback():
                    request.json['servers'][index]['ip'] = remote_ip
                if 'version' not in server:
                    request.json['servers'][index]['version'] = 'Unknown'
                request.json['servers'][index]['port'] = request.json['servers'][index]['port'] & 0xffff
            request.json['ip_address'] = remote_ip
            instance = InstanceSchema().load(request.json)
        except ValidationError as err:
            logging.warning(f'could not validate instance: {str(request.json)}', exc_info=err)
            return {'message': err.messages}, 400
        ctx.update_instance(instance)
        return {'message': 'instance updated successfully'}, 200

    @jwt_required
    def post(self):
        try:
            remote_ip = request.remote_addr
            for index in range(0, len(request.json['servers'])):
                server = request.json['servers'][index]

                parsed_ip = None
                try:
                    parsed_ip = IPAddress(server['ip'])
                except (AddrFormatError, KeyError):
                    pass

                if 'ip' not in server or parsed_ip is None or parsed_ip.is_private() or parsed_ip.is_loopback():
                    request.json['servers'][index]['ip'] = remote_ip
                if 'version' not in server:
                    request.json['servers'][index]['version'] = 'Unknown'
                request.json['servers'][index]['port'] = request.json['servers'][index]['port'] & 0xffff
            request.json['ip_address'] = remote_ip
            instance = InstanceSchema().load(request.json)
        except ValidationError as err:
            logging.warning(f'could not validate instance: {str(request.json)}', exc_info=err)
            return {'message': err.messages}, 400
        ctx.add_instance(instance)
        return {'message': 'instance added successfully'}, 200
