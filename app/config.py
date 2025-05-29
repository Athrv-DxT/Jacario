import os

class Config:
    """Base configuration."""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_development')
    
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///jacario.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Default settings
    MAX_USERNAME_LENGTH = 25
    MAX_ROOM_NAME_LENGTH = 50
    MAX_MESSAGE_LENGTH = 500
    DEFAULT_ROOMS = ['General', 'Technology', 'Random', 'Support']

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Use stronger security settings in production
    WTF_CSRF_ENABLED = True
    SSL_REDIRECT = os.environ.get('SSL_REDIRECT', 'False') == 'True'
    
    @classmethod
    def init_app(cls, app):
        # Production specific settings
        # Log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Enable secure cookies
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['REMEMBER_COOKIE_SECURE'] = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Default config
Config = DevelopmentConfig if os.environ.get('FLASK_ENV') == 'development' else ProductionConfig