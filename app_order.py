from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange
from extensions import db, position_required
from models import Order, OrderItem, Supplier, SupplierContract
from app_supplier import ContractItem

order_bp = Blueprint('order', __name__)

# Define position access rights
FULL_ACCESS_POSITIONS = ['Оператор', 'Начальник зміни', 'Керівник']
ORDER_ACCESS_POSITIONS = ['Менеджер з закупівель'] + FULL_ACCESS_POSITIONS

# Forms
class SupplierOrderForm(FlaskForm):
    edrpou_code = StringField('ЄДРПОУ постачальника', validators=[DataRequired()])
    contract_id = SelectField('Номер контракту', coerce=int, validators=[DataRequired()])
    submit_order = SubmitField('Створити замовлення')

# Routes
@order_bp.route('/select')
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def order_select():
    """Order type selection page"""
    return render_template('orders/select.html', title='Вибір типу замовлення')

@order_bp.route('/supplier/create', methods=['GET', 'POST'])
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def supplier_order_create():
    """Supplier order creation page"""
    form = SupplierOrderForm()
    

    if request.method == 'POST':
        edrpou_code = form.edrpou_code.data
        supplier = Supplier.query.filter_by(edrpou_code=edrpou_code).first()
        if supplier:
            contracts = SupplierContract.query.filter_by(supplier_id=supplier.id).all()
            form.contract_id.choices = [(c.id, c.contract_number or f"Контракт #{c.id}") for c in contracts]
        else:
            form.contract_id.choices = []
    

    if form.validate_on_submit():
        # Get the supplier and contract
        supplier = Supplier.query.filter_by(edrpou_code=form.edrpou_code.data).first()
        contract = SupplierContract.query.get(form.contract_id.data)
        
        if not supplier or not contract:
            flash('Постачальник або контракт не знайдено', 'danger')
            return render_template('orders/supplier_form.html', form=form, title='Створення замовлення постачальнику')
        
        # Get the items from the form
        items_data = []
        for key, value in request.form.items():
            if key.startswith('quantity_') and value and int(value) > 0:
                item_id = int(key.split('_')[1])
                # Get the price from the form if provided
                price_key = f'price_{item_id}'
                price = request.form.get(price_key)
                price = float(price) if price and price.strip() else None
                
                items_data.append({
                    'item_id': item_id,
                    'quantity': int(value),
                    'price': price
                })
        
        if not items_data:
            flash('Будь ласка, вкажіть кількість хоча б для одного товару', 'warning')
            return render_template('orders/supplier_form.html', form=form, title='Створення замовлення постачальнику')
        
        # Create the order
        order = Order(
            order_type='supplier',
            supplier_id=supplier.id,
            contract_id=contract.id,
            created_by=current_user.id,
            status='created'
        )
        
        # Generate order number
        order.order_number = Order.generate_order_number('supplier')

        # Add items to the order
        # Generate a single invoice number for all items in this order
        invoice_number = Order.generate_invoice_number()
        
        for item_data in items_data:
            item = ContractItem.query.get(item_data['item_id'])
            
            order_item = OrderItem(
                sku=item.sku,
                product_name=item.product_name,
                unit_price=item_data.get('price', item.unit_price),
                quantity=item_data['quantity'],
                invoice_number=invoice_number
            )
            order.items.append(order_item)
        
        # Save to database
        db.session.add(order)
        db.session.commit()
        
        flash(f'Замовлення №{order.order_number} успішно створено', 'success')
        return redirect(url_for('order.supplier_order_list'))
    
    return render_template('orders/supplier_form.html', form=form, title='Створення замовлення постачальнику')

@order_bp.route('/supplier/list')
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def supplier_order_list():
    """Supplier order list page"""
    orders = Order.query.filter_by(order_type='supplier').order_by(Order.created_at.desc()).all()
    return render_template('orders/supplier_list.html', orders=orders, title='Список замовлень постачальникам')

@order_bp.route('/supplier/view/<int:order_id>')
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def supplier_order_detail(order_id):
    """Supplier order detail page"""
    order = Order.query.get_or_404(order_id)
    if order.order_type != 'supplier':
        flash('Замовлення не знайдено', 'danger')
        return redirect(url_for('order.supplier_order_list'))
    
    return render_template('orders/supplier_detail.html', order=order, title=f'Замовлення №{order.order_number}')

@order_bp.route('/supplier/delete/<int:order_id>', methods=['POST'])
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def supplier_order_delete(order_id):
    """Delete supplier order"""
    order = Order.query.get_or_404(order_id)
    if order.order_type != 'supplier':
        flash('Замовлення не знайдено', 'danger')
        return redirect(url_for('order.supplier_order_list'))
    
    # Store order number for flash message
    order_number = order.order_number
    
    # Delete the order (cascade will delete order items)
    db.session.delete(order)
    db.session.commit()
    
    flash(f'Замовлення №{order_number} успішно видалено', 'success')
    return redirect(url_for('order.supplier_order_list'))

# API routes for AJAX
@order_bp.route('/api/get_contracts')
@login_required
def get_contracts():
    """Get contracts for a supplier by EDRPOU code"""
    edrpou_code = request.args.get('edrpou_code')
    if not edrpou_code:
        return jsonify({'error': 'ЄДРПОУ не вказано'}), 400
    
    supplier = Supplier.query.filter_by(edrpou_code=str(edrpou_code)).first()
    if not supplier:
        return jsonify({'error': 'Постачальника не знайдено'}), 404
    
    # Debug information
    print(f"Fetching contracts for supplier ID: {supplier.id}, Name: {supplier.name}")
    
    # Get all contracts for this supplier
    contracts = SupplierContract.query.filter_by(supplier_id=supplier.id).all()
    print(f"Found {len(contracts)} contracts")
    
    # Only include contracts that have at least one item
    valid_contracts = [c for c in contracts if len(c.items) > 0]
    print(f"Found {len(valid_contracts)} contracts with items")
    
    contracts_data = [{'id': c.id, 'number': c.contract_number or f'Контракт #{c.id}'} for c in valid_contracts]
    
    return jsonify({'contracts': contracts_data})

@order_bp.route('/api/get_contract_items')
@login_required
def get_contract_items():
    contract_id = request.args.get('contract_id')
    if not contract_id:
        return jsonify({'error': 'ID контракту не вказано'}), 400

    contract = SupplierContract.query.get(contract_id)
    if not contract:
        return jsonify({'error': 'Контракт не знайдено'}), 404

    contract_items = contract.items

    items_data = []
    for item in contract_items:
        items_data.append({
            'id': item.id,
            'sku': item.sku,
            'product_name': item.product_name,
            'price': item.unit_price,
            'quantity': item.quantity
        })

    return jsonify({'items': items_data})
