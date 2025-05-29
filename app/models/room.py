from datetime import datetime
from app import db

class Room(db.Model):
    """Room model for chat rooms"""
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(256))
    is_private = db.Column(db.Boolean, default=False)
    is_default = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='room', lazy='dynamic', 
                              cascade='all, delete-orphan')
    
    def __init__(self, name, description=None, owner_id=None, is_private=False, is_default=False):
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.is_private = is_private
        self.is_default = is_default
    
    def user_count(self):
        """Return the number of users in this room"""
        return self.members.count()
    
    def message_count(self):
        """Return the number of messages in this room"""
        return self.messages.count()
    
    def add_user(self, user):
        """Add a user to this room"""
        if not self.is_member(user):
            self.members.append(user)
            return True
        return False
    
    def remove_user(self, user):
        """Remove a user from this room"""
        if self.is_member(user):
            self.members.remove(user)
            return True
        return False
    
    def is_member(self, user):
        """Check if user is a member of this room"""
        return self.members.filter_by(id=user.id).first() is not None
    
    def to_dict(self):
        """Convert room to dictionary for JSON responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_private': self.is_private,
            'user_count': self.user_count(),
            'message_count': self.message_count(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Room {self.name}>'