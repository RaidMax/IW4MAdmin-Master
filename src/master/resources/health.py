from flask_restful import Resource
from datetime import datetime, timezone


class Health(Resource):
    def get(self):
        return {
            'time': datetime.now(timezone.utc).isoformat()
        }
