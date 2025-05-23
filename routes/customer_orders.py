from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from extensions import db, position_required
from models.order import Order, OrderItem
from forms.orders import CustomerOrderForm
from models import LogisticsItemData

# Define blueprint
customer_orders_bp = Blueprint('customer_orders', __name__, url_prefix='/orders')

# Define position access rights
ORDER_ACCESS_POSITIONS = ['Оператор', 'Менеджер']

@customer_orders_bp.route('/create-customer-order', methods=['GET', 'POST'])
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def create_customer_order():
    form = CustomerOrderForm()

    from models.customer import Customer
    form.customer_id.choices = [(c.id, f"{c.code} - {c.name}") for c in Customer.query.all()]

    # Отримуємо список логістичних даних для вибору товарів
    logistics_items = LogisticsItemData.query.all()

    if form.validate_on_submit():
        try:
            # КРОК 1: створюємо замовлення без order_number
            new_order = Order(
                order_type='customer',
                customer_id=form.customer_id.data,
                status='created',
                created_by=current_user.id,
                created_at=datetime.now()
            )
            db.session.add(new_order)
            db.session.commit()  # Отримаємо ID

            # КРОК 2: оновлюємо order_number використовуючи централізований метод
            new_order.order_number = Order.generate_order_number('customer')
            db.session.commit()  # Оновили поле

            # КРОК 3: додаємо товарні позиції
            for item_form in form.items.entries:
                # Отримуємо дані про розміри товару з LogisticsItemData
                logistics_item = LogisticsItemData.query.filter_by(sku=item_form.form.sku.data).first()
                
                order_item = OrderItem(
                    order_id=new_order.id,
                    sku=item_form.form.sku.data,
                    product_name=item_form.form.product_name.data,
                    quantity=item_form.form.quantity.data,
                    unit_price=item_form.form.unit_price.data
                )
                
                # Якщо є дані про розміри, додаємо їх до товарної позиції
                if logistics_item:
                    order_item.length_cm = logistics_item.length
                    order_item.width_cm = logistics_item.width
                    order_item.height_cm = logistics_item.height
                db.session.add(order_item)

            db.session.commit()
            flash(f"Замовлення створено: {new_order.order_number}", 'success')
            return redirect(url_for('customer_orders.customer_order_list'))

        except Exception as e:
            db.session.rollback()
            flash(f"Помилка створення замовлення: {str(e)}", 'danger')

    return render_template('orders/create_customer_order.html', form=form, logistics_items=logistics_items)

@customer_orders_bp.route('/customer-orders')
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def customer_order_list():
    orders = Order.query.filter_by(order_type='customer').all()
    return render_template('orders/customer_order_list.html', orders=orders, title='Клієнтські замовлення')

@customer_orders_bp.route('/customer-orders/<int:order_id>')
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def customer_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.order_type != 'customer':
        flash('Замовлення не знайдено', 'danger')
        return redirect(url_for('customer_orders.customer_order_list'))
    return render_template('orders/customer_order_detail.html', order=order, title='Деталі замовлення')

@customer_orders_bp.route('/customer-orders/<int:order_id>/process', methods=['POST'])
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def process_customer_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.order_type != 'customer':
        flash('Замовлення не знайдено', 'danger')
        return redirect(url_for('customer_orders.customer_order_list'))
    
    if order.status != 'created':
        flash('Замовлення вже в обробці або виконано', 'warning')
        return redirect(url_for('customer_orders.customer_order_detail', order_id=order.id))
    
    try:
        # Обробка замовлення: розрахунок палет, створення лотів, резервування товарів
        order.process_order()
        flash('Замовлення успішно оброблено. Створено лоти та зарезервовано товари.', 'success')
    except ValueError as e:
        flash(f'Помилка обробки замовлення: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Непередбачена помилка: {str(e)}', 'danger')
    
    return redirect(url_for('customer_orders.customer_order_detail', order_id=order.id))

@customer_orders_bp.route('/customer-orders/<int:order_id>/complete', methods=['POST'])
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def complete_customer_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.order_type != 'customer':
        flash('Замовлення не знайдено', 'danger')
        return redirect(url_for('customer_orders.customer_order_list'))
    
    if order.status != 'packed':
        flash('Замовлення не може бути завершено, оскільки воно не скомплектоване', 'warning')
        return redirect(url_for('customer_orders.customer_order_detail', order_id=order.id))
    
    try:
        # Завершуємо замовлення та оновлюємо залишки товару клієнта
        if order.complete_order():
            flash('Замовлення успішно завершено. Залишки товару клієнта оновлено.', 'success')
        else:
            flash('Помилка завершення замовлення.', 'danger')
    except Exception as e:
        flash(f'Непередбачена помилка: {str(e)}', 'danger')
    
    return redirect(url_for('customer_orders.customer_order_detail', order_id=order.id))

@customer_orders_bp.route('/api/logistics-item/<string:sku>')
@login_required
def get_logistics_item(sku):
    """API endpoint для отримання даних про товар за SKU"""
    item = LogisticsItemData.query.filter_by(sku=sku).first()
    if not item:
        return jsonify({'error': 'Товар не знайдено'}), 404
    
    return jsonify({
        'sku': item.sku,
        'product_name': item.product_name,
        'packaging_unit_type': item.packaging_unit_type
    })