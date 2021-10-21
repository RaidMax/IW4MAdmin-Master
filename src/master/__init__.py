import logging

from flask import Flask
from flask_restful import Api
from flask_jwt_extended import JWTManager
from .context.base import Base
from os import environ

logging.basicConfig(filename='master.log', format='%(asctime)s %(message)s', level=logging.WARNING)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = environ['IW4MADMIN_AUTH_KEY']
app.config['PROPAGATE_EXCEPTIONS'] = True
jwt = JWTManager(app)
api = Api(app)
ctx = Base()

from .flask import views
from .flask import routes
from .util import filters
