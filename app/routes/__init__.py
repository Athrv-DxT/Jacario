# Import all route blueprints
from .auth import auth_bp
from .chat import chat_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'chat_bp', 'admin_bp']