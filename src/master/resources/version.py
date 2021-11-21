from flask_restful import Resource, reqparse
from .. import app
import json


class Version(Resource):
    def __init__(self):
        self.config_folder = 'config'
        self.master_file_name = 'master'

    def get(self, api_version=0):
        with open('{0}/{1}.v{2}.json'.format(self.config_folder, self.master_file_name, api_version)) as config_file:
            config = json.load(config_file)
        return {
                   'current-version-stable': config['current-version-stable'],
                   'current-version-prerelease': config['current-version-prerelease']
               }, 200

    # @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('current-version-stable')
        parser.add_argument('current-version-prerelease')
        parser.add_argument('jwt-secret', help='jwt-secret is required', required=True)
        args = parser.parse_args()

        with open('{0}/{1}.v1.json'.format(self.config_folder, self.master_file_name)) as config_file:
            config = json.load(config_file)

        if args['current-version-stable'] is not None:
            config['current-version-stable'] = args['current-version-stable']

        if args['current-version-prerelease'] is not None:
            config['current-version-prerelease'] = args['current-version-prerelease']

        if args['jwt-secret'] == app.config['JWT_SECRET_KEY']:
            with open('{0}/{1}.v1.json'.format(self.config_folder, self.master_file_name), 'w') as out_json:
                json.dump(config, out_json, indent=4)

            return {'message': 'stable is {0}, prerelease is {1}'.format(config['current-version-stable'],
                                                                         config['current-version-prerelease'])}
        else:
            return {'message': 'invalid jwt secret'}, 401
