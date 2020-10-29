from flask import Flask
from flask_restful import Api

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
api = Api(app)

import ecommerce.flask.views
import ecommerce.flask.routes
