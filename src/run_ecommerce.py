from os import environ

import chargebee

from ecommerce import app

if __name__ == '__main__':
    chargebee.configure(environ['CHARGEBEE_SECRET'], environ['CHARGEBEE_PROJECT'])
    app.run(host=environ['IW4MADMIN_BIND_ADDRESS'], port=environ['IW4MADMIN_BIND_PORT'], debug=True)
