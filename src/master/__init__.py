from flask import Flask
from flask_restful import Resource, Api
from flask_jwt_extended import JWTManager
from master.context.base import Base
from os import environ

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = environ['IW4MADMIN_AUTH_KEY']
app.config['PROPAGATE_EXCEPTIONS'] = True
jwt = JWTManager(app)
api = Api(app)
ctx = Base()

import master.flask.views
import ecommerce.views
import master.flask.routes
from .util import filters

import ecommerce.routes