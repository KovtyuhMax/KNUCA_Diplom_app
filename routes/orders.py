from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from extensions import db, position_required
from models import Order, OrderItem, ReceivedInventory, LogisticsItemData
from sqlalchemy import func

# Define position access rights
ORDER_ACCESS_POSITIONS = ['Менеджер з закупівель', 'Оператор', 'Начальник зміни', 'Керівник']

orders_bp = Blueprint('supplier_orders', __name__, url_prefix='/orders')

@orders_bp.route('/invoice/<int:order_id>')
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def invoice_view(order_id):
    """Відображення рахунку-фактури для замовлення"""
    # Отримуємо замовлення
    order = Order.query.get_or_404(order_id)
    
    # Генеруємо номер рахунку-фактури у форматі 540000000 + order.id
    invoice_number = f"540{order.id:08d}"
    
    # Отримуємо номер ВН постачальника з OrderItem
    invoice_number_supplier = ''
    if order.items:
        invoice_number_supplier = order.invoice_number_supplier
    
    # Отримуємо список прийнятих товарів, згрупованих по SKU
    received_items_query = db.session.query(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        func.sum(ReceivedInventory.box_count).label('total_box_count'),
        ReceivedInventory.invoice_number
    ).filter(
        ReceivedInventory.invoice_number == order.items[0].invoice_number
    ).group_by(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        ReceivedInventory.invoice_number
    ).all()
    
    # Створюємо список товарів з цінами та сумами
    invoice_items = []
    total_sum = 0
    
    for item in received_items_query:
        # Знаходимо відповідний OrderItem
        order_item = OrderItem.query.filter_by(
            order_id=order.id,
            sku=item.sku
        ).first()

        # Знаходимо логістичну інформацію для визначення типу пакування
        logistics_data = LogisticsItemData.query.filter_by(sku=item.sku).first()

        if order_item and logistics_data:
            unit_price = order_item.unit_price or 0
            unit_type = logistics_data.packaging_unit_type  # Очікується "КГ" або "ШТ"
            
            # Отримуємо всі прийняті палети для SKU + інвойс
            received_pallets = ReceivedInventory.query.filter_by(
                sku=item.sku,
                invoice_number=item.invoice_number
            ).all()

            if unit_type == 'КГ':
                total_weight = sum(p.net_weight or 0 for p in received_pallets)
                item_sum = unit_price * total_weight
                display_quantity = total_weight
            elif unit_type == 'ШТ':
                # Штуки = кількість коробок × кратність
                total_boxes = sum(p.box_count or 0 for p in received_pallets)
                item_sum = unit_price * total_boxes
                display_quantity = total_boxes
            else:
                # Фолбек на коробки
                display_quantity = item.total_box_count
                item_sum = unit_price * display_quantity

            total_sum += item_sum

            invoice_items.append({
                'sku': item.sku,
                'product_name': item.product_name,
                'quantity': round(display_quantity, 2),
                'unit_price': unit_price,
                'sum': round(item_sum, 2)
            })

    
    return render_template(
        'orders/invoice.html',
        order=order,
        invoice_number=invoice_number,
        invoice_number_supplier=invoice_number_supplier,
        invoice_items=invoice_items,
        total_sum=total_sum
    )