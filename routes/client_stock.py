from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from extensions import db, position_required
from models import ClientStock, Customer

# Створення блупрінту
client_stock_bp = Blueprint('client_stock', __name__, url_prefix='/client')

# Визначення доступу за посадами
CLIENT_ACCESS_POSITIONS = ['Оператор', 'Менеджер', 'Керівник']

@client_stock_bp.route('/stock')
@login_required
@position_required(CLIENT_ACCESS_POSITIONS)
def client_stock_list():
    """Відображення залишків товару для клієнта"""
    # Отримуємо параметри фільтрації
    sku_filter = request.args.get('sku', '')
    name_filter = request.args.get('name', '')
    type_filter = request.args.get('type', '')
    customer_id = request.args.get('customer_id', type=int)
    
    # Базовий запит
    query = ClientStock.query
    
    # Застосовуємо фільтри
    if customer_id:
        query = query.filter(ClientStock.customer_id == customer_id)
    if sku_filter:
        query = query.filter(ClientStock.sku.ilike(f'%{sku_filter}%'))
    if name_filter:
        query = query.filter(ClientStock.product_name.ilike(f'%{name_filter}%'))
    if type_filter in ['КГ', 'ШТ']:
        query = query.filter(ClientStock.packaging_unit_type == type_filter)
    
    # Отримуємо результати
    items = query.all()
    
    # Отримуємо список клієнтів для вибору
    customers = Customer.query.all()
    
    return render_template(
        'client/stock.html',
        items=items,
        customers=customers,
        selected_customer_id=customer_id,
        sku_filter=sku_filter,
        name_filter=name_filter,
        type_filter=type_filter,
        title='Залишки товару клієнта'
    )

@client_stock_bp.route('/api/stock/<int:customer_id>')
@login_required
def get_client_stock(customer_id):
    """API для отримання залишків товару клієнта"""
    # Перевіряємо наявність клієнта
    customer = Customer.query.get_or_404(customer_id)
    
    # Отримуємо залишки
    stocks = ClientStock.query.filter_by(customer_id=customer_id).all()
    
    # Форматуємо дані для відповіді
    result = []
    for stock in stocks:
        quantity = stock.quantity_kg if stock.packaging_unit_type == 'КГ' else stock.quantity_units
        result.append({
            'sku': stock.sku,
            'product_name': stock.product_name,
            'quantity': quantity,
            'packaging_unit_type': stock.packaging_unit_type
        })
    
    return jsonify(result)