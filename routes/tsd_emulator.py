from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, login_user
from utils.decorators import position_required
from models import User
import random
from datetime import datetime

# Define position access rights for TSD
TSD_ACCESS_POSITIONS = ['Приймальник', 'Комплектувальник', 'Оператор', 'Начальник зміни', 'Керівник']

tsd_emulator_bp = Blueprint('tsd_emulator', __name__, url_prefix='/tsd-emulator')

@tsd_emulator_bp.route('/', methods=['GET'])
def tsd_emulator():
    """TSD emulator page with interactive UI"""
    return render_template('tsd/emulator.html', title='TSD Емулятор')

@tsd_emulator_bp.route('/login', methods=['POST'])
def tsd_login():
    """Handle TSD login requests"""
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'success': False, 'message': 'Код користувача не вказано'})
    
    # Check if username contains only digits
    if not username.isdigit():
        return jsonify({'success': False, 'message': 'Код користувача повинен містити тільки цифри'})
    
    # Find user with this username
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'success': False, 'message': 'Користувача не знайдено'})
    
    # Check if user has TSD access
    if not user.position or user.position.name not in TSD_ACCESS_POSITIONS:
        return jsonify({'success': False, 'message': 'У вас немає доступу до ТЗД'})
    
    # Log in the user
    login_user(user)
    
    return jsonify({
        'success': True, 
        'message': f'Вітаємо, {user.full_name}!',
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'position': user.position.name if user.position else None
        }
    })