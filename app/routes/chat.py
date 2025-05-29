from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.room import Room
from app.models.message import Message
from app.models.user import User
from app import db, config
import bleach

chat_bp = Blueprint('chat', __name__)

# Helper functions
def sanitize_input(text):
    """Sanitize input to prevent XSS attacks"""
    allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'code', 'pre']
    return bleach.clean(text, tags=allowed_tags, strip=True)

# Routes
@chat_bp.route('/')
@login_required
def index():
    """Main chat interface with room selection"""
    # Get all public rooms and user's private rooms
    public_rooms = Room.query.filter_by(is_private=False).all()
    private_rooms = current_user.rooms.filter_by(is_private=True).all()
    
    # Check if we need to create default rooms
    if not public_rooms:
        for room_name in config.DEFAULT_ROOMS:
            room = Room(name=room_name, description=f"Default {room_name} chat room", is_default=True)
            db.session.add(room)
        db.session.commit()
        public_rooms = Room.query.filter_by(is_private=False).all()
    
    # If user isn't in any room yet, add them to the General room
    if not current_user.rooms.count():
        general_room = Room.query.filter(Room.name == 'General').first()
        if general_room:
            general_room.add_user(current_user)
            db.session.commit()
    
    rooms = {
        'public': [room.to_dict() for room in public_rooms],
        'private': [room.to_dict() for room in private_rooms]
    }
    
    # If a room_id is specified, redirect to that room
    room_id = request.args.get('room_id')
    if room_id:
        return redirect(url_for('chat.room', room_id=room_id))
    
    return render_template('chat/index.html', title='Jacario', rooms=rooms)

@chat_bp.route('/room/<int:room_id>')
@login_required
def room(room_id):
    """Chat room view"""
    room = Room.query.get_or_404(room_id)
    
    # Check if user has access to this room
    if room.is_private and not room.is_member(current_user):
        flash('You do not have access to this room.', 'danger')
        return redirect(url_for('chat.index'))
    
    # Join room if not already a member
    if not room.is_member(current_user):
        room.add_user(current_user)
        db.session.commit()
    
    # Get recent messages for this room (most recent 100 messages)
    messages = (Message.query
                .filter_by(room_id=room_id, parent_id=None)
                .order_by(Message.created_at.desc())
                .limit(100)
                .all())
    
    messages = [msg.to_dict() for msg in reversed(messages)]
    
    # Get all rooms for the sidebar
    public_rooms = Room.query.filter_by(is_private=False).all()
    private_rooms = current_user.rooms.filter_by(is_private=True).all()
    
    rooms = {
        'public': [r.to_dict() for r in public_rooms],
        'private': [r.to_dict() for r in private_rooms]
    }
    
    # List of online users in this room
    online_users = [user for user in room.members if user.is_online]
    
    return render_template('chat/room.html', 
                          title=f'Jacario - {room.name}',
                          room=room.to_dict(),
                          messages=messages,
                          rooms=rooms,
                          online_users=online_users)

@chat_bp.route('/room/create', methods=['POST'])
@login_required
def create_room():
    """Create a new chat room"""
    name = sanitize_input(request.form.get('name', ''))
    description = sanitize_input(request.form.get('description', ''))
    is_private = request.form.get('is_private') == 'true'
    
    if not name or len(name) > 64:
        return jsonify({'success': False, 'message': 'Invalid room name'}), 400
    
    # Check if a room with this name already exists
    existing_room = Room.query.filter_by(name=name).first()
    if existing_room:
        return jsonify({'success': False, 'message': 'A room with this name already exists'}), 400
    
    # Create the room
    room = Room(
        name=name,
        description=description,
        owner_id=current_user.id,
        is_private=is_private
    )
    
    # Add the creator to the room
    db.session.add(room)
    db.session.commit()
    room.add_user(current_user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Room created successfully',
        'room': room.to_dict()
    })

@chat_bp.route('/room/<int:room_id>/join', methods=['POST'])
@login_required
def join_room(room_id):
    """Join a chat room"""
    room = Room.query.get_or_404(room_id)
    
    # Check if private and handle accordingly
    if room.is_private:
        # For now, only allow members to join private rooms
        return jsonify({'success': False, 'message': 'This is a private room'}), 403
    
    # Join the room
    if room.add_user(current_user):
        db.session.commit()
        return jsonify({'success': True, 'message': f'You joined {room.name}'})
    else:
        return jsonify({'success': False, 'message': 'You are already in this room'}), 400

@chat_bp.route('/room/<int:room_id>/leave', methods=['POST'])
@login_required
def leave_room(room_id):
    """Leave a chat room"""
    room = Room.query.get_or_404(room_id)
    
    # Cannot leave default rooms
    if room.is_default:
        return jsonify({'success': False, 'message': 'Cannot leave default rooms'}), 400
    
    if room.remove_user(current_user):
        db.session.commit()
        return jsonify({'success': True, 'message': f'You left {room.name}'})
    else:
        return jsonify({'success': False, 'message': 'You are not in this room'}), 400