from flask import Blueprint, render_template
from flask_login import login_required
from extensions import db, position_required
from models import Order, OrderLot, LogisticsItemData
from sqlalchemy import text

# Define blueprint
export_invoice_bp = Blueprint('export_invoice', __name__, url_prefix='/orders')

# Define position access rights
ORDER_ACCESS_POSITIONS = ['Оператор', 'Менеджер', 'Начальник зміни', 'Керівник']

@export_invoice_bp.route('/export-invoice/<int:order_id>')
@login_required
@position_required(ORDER_ACCESS_POSITIONS)
def export_invoice_view(order_id):
    """Відображення видаткової накладної для замовлення"""
    # Отримуємо замовлення
    order = Order.query.get_or_404(order_id)
    
    # Генеруємо номер видаткової накладної у форматі EXP + order.id
    export_invoice_number = f"EXP{order.id:08d}"
    
    # Отримуємо лоти зі статусом 'packed'
    lots = OrderLot.query.filter_by(order_id=order.id, status='packed').all()
    
    # Формуємо список товарів для відображення
    export_items = []
    for lot in lots:
        # Отримуємо деталі SKU для лоту
        lot_skus = db.session.execute(
            text("SELECT id, order_lot_id, sku, product_name, quantity, weight FROM order_lot_sku WHERE order_lot_id = :lot_id"),
            {"lot_id": lot.id}
        ).fetchall()
        
        picker_name = lot.picker.full_name if lot.picker else 'Н/Д'
        
        for sku_row in lot_skus:
            # Отримуємо одиницю виміру з LogisticsItemData
            logistics_data = LogisticsItemData.query.filter_by(sku=sku_row.sku).first()
            unit = logistics_data.packaging_unit_type if logistics_data else 'Н/Д'
            
            export_items.append({
                'lot_number': lot.lot_number,
                'sku': sku_row.sku,
                'product_name': sku_row.product_name,
                'quantity': sku_row.quantity,
                'weight': round(sku_row.weight or 0, 2),
                'unit': unit,
                'picker': picker_name
            })
    
    return render_template('orders/export_invoice.html', 
                           order=order, 
                           export_invoice_number=export_invoice_number,
                           export_items=export_items)