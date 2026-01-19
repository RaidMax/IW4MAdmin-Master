"""
IW4MAdmin Master API
Flask application initialization with rate limiting, structured logging, and database.
"""

import logging
import sys

from flask import Flask
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pythonjsonlogger import jsonlogger

from .config import config
from .database import db


def setup_logging():
    """Configure structured JSON logging."""
    log_handler = logging.FileHandler(config.log_file)
    
    if config.log_json_format:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')
    
    log_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    root_logger.addHandler(log_handler)
    
    # Also log to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce werkzeug noise
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = config.jwt_secret_key
app.config['PROPAGATE_EXCEPTIONS'] = True

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[config.rate_limit_default] if config.rate_limit_enabled else [],
    storage_uri="memory://"
)

# JWT
jwt = JWTManager(app)

# REST API
api = Api(app)

# Initialize database
try:
    db.initialize()
    db.record_service_event('startup', 'Master API started')
    logger.info("Database initialized successfully")
    
    # Register graceful shutdown handler
    import atexit
    def record_shutdown():
        if db.is_connected:
            try:
                db.record_service_event('shutdown', 'Master API stopped gracefully')
            except Exception:
                pass  # Ignore errors during shutdown
    atexit.register(record_shutdown)
    
except Exception as e:
    logger.warning(f"Database initialization failed: {e}. Running in memory-only mode.")

# Context (legacy support during migration)
from .context.base import Base
ctx = Base()

# Import routes and views
from .flask import views
from .flask import routes
from .util import filters

