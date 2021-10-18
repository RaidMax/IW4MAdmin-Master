"""
This script runs the Master application using a development server.
"""

from os import environ
from master import app

if __name__ == '__main__':
    app.run(host=environ['IW4MADMIN_BIND_ADDRESS'], port=environ['IW4MADMIN_BIND_PORT'],
            debug=environ['TEMPLATES_AUTO_RELOAD'] or False)
