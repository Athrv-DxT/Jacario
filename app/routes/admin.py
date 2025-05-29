from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models.user import User, Role
from app.models.room import Room
from app.models.message import Message
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required', 'danger')
            return redirect(url_for('chat.index'))
        return f(*args, **kwargs)
    return decorated_function

def moderator_required(f):
    """Decorator to require moderator or admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_moderator():
            flash('Moderator access required', 'danger')
            return redirect(url_for('chat.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with site statistics"""
    stats = {
        'total_users': User.query.count(),
        'online_users': User.query.filter_by(is_online=True).count(),
        'total_rooms': Room.query.count(),
        'total_messages': Message.query.count(),
        'recent_users': User.query.order_by(User.created_at.desc()).limit(10).all(),
        'active_rooms': Room.query.join(Message).group_by(Room.id).order_by(db.func.count(Message.id).desc()).limit(5).all()
    }
    
    return render_template('admin/dashboard.html', title='Admin Dashboard', stats=stats)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Manage users"""
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', title='Manage Users', users=users)

@admin_bp.route('/user/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Change user role"""
    user = User.query.get_or_404(user_id)
    new_role = request.json.get('role', Role.USER)
    
    if new_role not in [Role.USER, Role.MODERATOR, Role.ADMIN]:
        return jsonify({'success': False, 'message': 'Invalid role'}), 400
    
    # Don't allow changing own role
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot change your own role'}), 400
    
    user.role = new_role
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'User role changed to {user.get_role_name()}'
    })

@admin_bp.route('/user/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    # Don't allow deactivating own account
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot deactivate your own account'}), 400
    
    user.is_active = not user.is_active
    if not user.is_active:
        user.is_online = False
    
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    return jsonify({
        'success': True, 
        'message': f'User {status} successfully'
    })

@admin_bp.route('/rooms')
@login_required
@moderator_required
def rooms():
    """Manage rooms"""
    page = request.args.get('page', 1, type=int)
    rooms = Room.query.order_by(Room.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/rooms.html', title='Manage Rooms', rooms=rooms)

@admin_bp.route('/room/<int:room_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_room(room_id):
    """Delete a room"""
    room = Room.query.get_or_404(room_id)
    
    # Don't allow deleting default rooms
    if room.is_default:
        return jsonify({'success': False, 'message': 'Cannot delete default rooms'}), 400
    
    room_name = room.name
    db.session.delete(room)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Room "{room_name}" deleted successfully'
    })

@admin_bp.route('/messages')
@login_required
@moderator_required
def messages():
    """Manage messages"""
    page = request.args.get('page', 1, type=int)
    room_id = request.args.get('room_id', type=int)
    
    query = Message.query
    if room_id:
        query = query.filter_by(room_id=room_id)
    
    messages = query.order_by(Message.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    rooms = Room.query.all()
    
    return render_template('admin/messages.html', 
                          title='Manage Messages', 
                          messages=messages, 
                          rooms=rooms,
                          selected_room_id=room_id)

@admin_bp.route('/message/<int:message_id>/delete', methods=['POST'])
@login_required
@moderator_required
def delete_message(message_id):
    """Delete a message"""
    message = Message.query.get_or_404(message_id)
    
    message.soft_delete()
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Message deleted successfully'
    })