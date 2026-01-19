from flask_restful import Resource
from flask import request
from flask_jwt_extended import create_access_token
from datetime import timedelta
from .. import ctx


class Authenticate(Resource):
    def post(self):
        instance_id = request.json['id']
        # todo: see why this is failing
        # if ctx.get_token(instance_id) is not False:
        #    return { 'message' : 'that id already has a token'}, 401
        # else:
        expires = timedelta(days=30)
        token = create_access_token(instance_id, expires_delta=expires)
        ctx.add_token(instance_id, token)
        return {'access_token': token}, 200
