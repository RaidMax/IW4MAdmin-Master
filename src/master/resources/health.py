from flask_restful import Resource
from datetime import datetime

class Health(Resource):
    def get(self):
        return {
           'time': datetime.utcnow().isoformat()
        }
