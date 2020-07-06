from flask import Flask
from flask_restful import Api
from flask_jwt_extended import JWTManager
from master.context.base import Base
from os import environ
import logging

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = environ['IA_AUTH_KEY']
app.config['PROPAGATE_EXCEPTIONS'] = True
jwt = JWTManager(app)
api = Api(app)
ctx = Base()
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

import master.flask.views
import master.flask.routes
from .util import filters
