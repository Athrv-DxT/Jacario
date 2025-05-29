from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

# User roles
class Role:
    USER = 0
    MODERATOR = 1
    ADMIN = 2
    ROLE_NAMES = {
        USER: 'User',
        MODERATOR: 'Moderator',
        ADMIN: 'Admin'
    }

# User-Room association table (many-to-many)
user_rooms = db.Table('user_rooms',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('room_id', db.Integer, db.ForeignKey('rooms.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    """User model for storing user data"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    avatar = db.Column(db.String(200), default='default_avatar.png')
    role = db.Column(db.Integer, default=Role.USER)
    is_active = db.Column(db.Boolean, default=True)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='author', lazy='dynamic')
    owned_rooms = db.relationship('Room', backref='owner', lazy='dynamic')
    rooms = db.relationship('Room', secondary=user_rooms, lazy='dynamic',
                           backref=db.backref('members', lazy='dynamic'))
    
    def __init__(self, username, email, password, role=Role.USER):
        self.username = username
        self.email = email
        self.set_password(password)
        self.role = role
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == Role.ADMIN
    
    def is_moderator(self):
        return self.role == Role.MODERATOR or self.role == Role.ADMIN
    
    def get_role_name(self):
        return Role.ROLE_NAMES.get(self.role, 'User')
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))