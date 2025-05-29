from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user
from app import socketio, db
from app.models.message import Message, MessageType
from app.models.room import Room
from app.models.user import User
import bleach
from datetime import datetime

# Store connected users
connected_users = {}
typing_users = {}

def sanitize_input(text):
    """Sanitize input to prevent XSS attacks"""
    allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'code', 'pre']
    return bleach.clean(text, tags=allowed_tags, strip=True)

@socketio.on('connect')
def on_connect():
    """Handle user connection"""
    if current_user.is_authenticated:
        # Store user session
        connected_users[current_user.id] = {
            'session_id': request.sid,
            'username': current_user.username,
            'connected_at': datetime.utcnow()
        }
        
        # Update user online status
        current_user.is_online = True
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        print(f"User {current_user.username} connected")
        
        # Emit to all users that this user is online
        emit('user_status_change', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_online': True
        }, broadcast=True)
    else:
        disconnect()

@socketio.on('disconnect')
def on_disconnect():
    """Handle user disconnection"""
    if current_user.is_authenticated:
        # Remove from connected users
        if current_user.id in connected_users:
            del connected_users[current_user.id]
        
        # Remove from typing users
        for room_id in list(typing_users.keys()):
            if current_user.id in typing_users[room_id]:
                typing_users[room_id].remove(current_user.id)
                emit('typing_update', {
                    'room_id': room_id,
                    'typing_users': [User.query.get(uid).username for uid in typing_users[room_id]]
                }, room=f'room_{room_id}')
        
        # Update user online status
        current_user.is_online = False
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        print(f"User {current_user.username} disconnected")
        
        # Emit to all users that this user is offline
        emit('user_status_change', {
            'user_id': current_user.id,
            'username': current_user.username,
            'is_online': False
        }, broadcast=True)

@socketio.on('join_room')
def on_join_room(data):
    """Handle user joining a room"""
    if not current_user.is_authenticated:
        return
    
    room_id = data.get('room_id')
    if not room_id:
        return
    
    room = Room.query.get(room_id)
    if not room:
        emit('error', {'message': 'Room not found'})
        return
    
    # Check if user has access to this room
    if room.is_private and not room.is_member(current_user):
        emit('error', {'message': 'Access denied to this room'})
        return
    
    # Join the Socket.IO room
    join_room(f'room_{room_id}')
    
    # Notify others in the room
    emit('user_joined', {
        'username': current_user.username,
        'user_id': current_user.id,
        'room_id': room_id
    }, room=f'room_{room_id}', include_self=False)
    
    print(f"User {current_user.username} joined room {room.name}")

@socketio.on('leave_room')
def on_leave_room(data):
    """Handle user leaving a room"""
    if not current_user.is_authenticated:
        return
    
    room_id = data.get('room_id')
    if not room_id:
        return
    
    room = Room.query.get(room_id)
    if not room:
        return
    
    # Leave the Socket.IO room
    leave_room(f'room_{room_id}')
    
    # Remove from typing users
    if room_id in typing_users and current_user.id in typing_users[room_id]:
        typing_users[room_id].remove(current_user.id)
        emit('typing_update', {
            'room_id': room_id,
            'typing_users': [User.query.get(uid).username for uid in typing_users[room_id]]
        }, room=f'room_{room_id}')
    
    # Notify others in the room
    emit('user_left', {
        'username': current_user.username,
        'user_id': current_user.id,
        'room_id': room_id
    }, room=f'room_{room_id}', include_self=False)
    
    print(f"User {current_user.username} left room {room.name}")

@socketio.on('send_message')
def on_send_message(data):
    """Handle sending a message"""
    if not current_user.is_authenticated:
        return
    
    room_id = data.get('room_id')
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')  # For replies
    
    if not room_id or not content:
        emit('error', {'message': 'Missing room ID or message content'})
        return
    
    # Validate message length
    if len(content) > 500:  # MAX_MESSAGE_LENGTH from config
        emit('error', {'message': 'Message too long'})
        return
    
    room = Room.query.get(room_id)
    if not room:
        emit('error', {'message': 'Room not found'})
        return
    
    # Check if user has access to this room
    if room.is_private and not room.is_member(current_user):
        emit('error', {'message': 'Access denied to this room'})
        return
    
    # Sanitize message content
    content = sanitize_input(content)
    
    # Create and save message
    message = Message(
        content=content,
        user_id=current_user.id,
        room_id=room_id,
        parent_id=parent_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Remove user from typing if they were typing
    if room_id in typing_users and current_user.id in typing_users[room_id]:
        typing_users[room_id].remove(current_user.id)
        emit('typing_update', {
            'room_id': room_id,
            'typing_users': [User.query.get(uid).username for uid in typing_users[room_id]]
        }, room=f'room_{room_id}')
    
    # Emit message to all users in the room
    emit('new_message', message.to_dict(), room=f'room_{room_id}')
    
    print(f"Message sent by {current_user.username} in room {room.name}")

@socketio.on('typing_start')
def on_typing_start(data):
    """Handle user starting to type"""
    if not current_user.is_authenticated:
        return
    
    room_id = data.get('room_id')
    if not room_id:
        return
    
    # Add user to typing list for this room
    if room_id not in typing_users:
        typing_users[room_id] = []
    
    if current_user.id not in typing_users[room_id]:
        typing_users[room_id].append(current_user.id)
    
    # Emit updated typing list
    emit('typing_update', {
        'room_id': room_id,
        'typing_users': [User.query.get(uid).username for uid in typing_users[room_id] if uid != current_user.id]
    }, room=f'room_{room_id}', include_self=False)

@socketio.on('typing_stop')
def on_typing_stop(data):
    """Handle user stopping typing"""
    if not current_user.is_authenticated:
        return
    
    room_id = data.get('room_id')
    if not room_id:
        return
    
    # Remove user from typing list for this room
    if room_id in typing_users and current_user.id in typing_users[room_id]:
        typing_users[room_id].remove(current_user.id)
    
    # Emit updated typing list
    emit('typing_update', {
        'room_id': room_id,
        'typing_users': [User.query.get(uid).username for uid in typing_users[room_id]]
    }, room=f'room_{room_id}')

@socketio.on('edit_message')
def on_edit_message(data):
    """Handle message editing"""
    if not current_user.is_authenticated:
        return
    
    message_id = data.get('message_id')
    new_content = data.get('content', '').strip()
    
    if not message_id or not new_content:
        emit('error', {'message': 'Missing message ID or content'})
        return
    
    message = Message.query.get(message_id)
    if not message:
        emit('error', {'message': 'Message not found'})
        return
    
    # Check if user owns the message or is admin/moderator
    if message.user_id != current_user.id and not current_user.is_moderator():
        emit('error', {'message': 'Permission denied'})
        return
    
    # Sanitize new content
    new_content = sanitize_input(new_content)
    
    # Edit the message
    message.edit(new_content)
    db.session.commit()
    
    # Emit updated message to all users in the room
    emit('message_edited', message.to_dict(), room=f'room_{message.room_id}')

@socketio.on('delete_message')
def on_delete_message(data):
    """Handle message deletion"""
    if not current_user.is_authenticated:
        return
    
    message_id = data.get('message_id')
    if not message_id:
        emit('error', {'message': 'Missing message ID'})
        return
    
    message = Message.query.get(message_id)
    if not message:
        emit('error', {'message': 'Message not found'})
        return
    
    # Check if user owns the message or is admin/moderator
    if message.user_id != current_user.id and not current_user.is_moderator():
        emit('error', {'message': 'Permission denied'})
        return
    
    # Soft delete the message
    message.soft_delete()
    db.session.commit()
    
    # Emit deleted message to all users in the room
    emit('message_deleted', {'message_id': message_id}, room=f'room_{message.room_id}')

@socketio.on('get_online_users')
def on_get_online_users(data):
    """Get list of online users in a room"""
    if not current_user.is_authenticated:
        return
    
    room_id = data.get('room_id')
    if not room_id:
        return
    
    room = Room.query.get(room_id)
    if not room:
        return
    
    # Get online users in this room
    online_users = [
        {'id': user.id, 'username': user.username, 'avatar': user.avatar}
        for user in room.members if user.is_online
    ]
    
    emit('online_users_list', {
        'room_id': room_id,
        'users': online_users
    })