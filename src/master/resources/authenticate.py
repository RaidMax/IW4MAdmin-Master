from flask_restful import Resource
from flask import request
from flask_jwt_extended import create_access_token
from datetime import timedelta
from .. import ctx


class Authenticate(Resource):
    def post(self):
        if not request.is_json:
            return {'message': 'Request body must be JSON'}, 400
        
        data = request.get_json(silent=True)
        if not data:
            return {'message': 'Invalid JSON body'}, 400
        
        instance_id = data.get('id')
        if not instance_id:
            return {'message': 'id is required'}, 400
        
        expires = timedelta(days=30)
        token = create_access_token(instance_id, expires_delta=expires)
        ctx.add_token(instance_id, token)
        return {'access_token': token}, 200
