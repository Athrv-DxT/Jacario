# Import all models here to ensure they are registered with SQLAlchemy
from .user import User, Role, user_rooms
from .room import Room
from .message import Message, MessageType

__all__ = ['User', 'Role', 'Room', 'Message', 'MessageType', 'user_rooms']