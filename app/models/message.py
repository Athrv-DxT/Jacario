from datetime import datetime
from app import db

class MessageType:
    TEXT = 0
    IMAGE = 1
    FILE = 2
    SYSTEM = 3
    
class Message(db.Model):
    """Message model for chat messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.Integer, default=MessageType.TEXT)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships for replies
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]),
                             lazy='dynamic')
    
    def __init__(self, content, user_id, room_id, message_type=MessageType.TEXT, parent_id=None):
        self.content = content
        self.user_id = user_id
        self.room_id = room_id
        self.message_type = message_type
        self.parent_id = parent_id
    
    def edit(self, new_content):
        """Edit message content and mark as edited"""
        self.content = new_content
        self.is_edited = True
        self.updated_at = datetime.utcnow()
        
    def soft_delete(self):
        """Soft delete the message (mark as deleted but keep in DB)"""
        self.is_deleted = True
        self.content = "[This message was deleted]"
        
    def to_dict(self):
        """Convert message to dictionary for JSON responses"""
        return {
            'id': self.id,
            'content': self.content,
            'message_type': self.message_type,
            'user_id': self.user_id,
            'username': self.author.username if self.author else "[deleted]",
            'avatar': self.author.avatar if self.author else "default_avatar.png",
            'room_id': self.room_id,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_edited': self.is_edited,
            'is_deleted': self.is_deleted
        }
    
    def __repr__(self):
        return f'<Message {self.id}>'