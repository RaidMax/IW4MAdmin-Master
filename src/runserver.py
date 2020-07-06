"""
This script runs the Master application using a development server.
"""

from os import environ
from master import app

if __name__ == '__main__':
    app.run(host=environ['IA_BIND_ADDRESS'], port=environ['IA_BIND_PORT'], debug=False)
