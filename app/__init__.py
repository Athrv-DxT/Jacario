import os
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Initialize Flask extensions
db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config=None):
    app = Flask(__name__)
    
    # Load default configuration
    app.config.from_object('app.config.Config')
    
    # Load environment variables
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
    
    # Override config with passed config object
    if config:
        app.config.from_object(config)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize SocketIO with CORS support
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Configure login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)
    
    # Import Socket.IO events
    from app.sockets import events
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app