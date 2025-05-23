from extensions import db
from datetime import datetime
from models.order_lot import OrderLot

class ClientStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity_kg = db.Column(db.Float, nullable=True)       # для КГ
    quantity_units = db.Column(db.Integer, nullable=True)  # для ШТ
    packaging_unit_type = db.Column(db.String(10), nullable=False)  # 'КГ' або 'ШТ'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('Customer')
    
    def __repr__(self):
        return f'<ClientStock {self.id} - {self.sku}>'
    
    @classmethod
    def update_from_order(cls, order):
        """Оновлює або створює записи ClientStock після завершення замовлення"""
        if order.status != 'completed' or order.order_type != 'customer':
            return False
            
        # Отримуємо всі відібрані товари для замовлення
        from models.order_lot import OrderLot
        packed_lot_numbers = db.session.query(OrderLot.lot_number).filter_by(
            order_id=order.id,
            status='packed'
        ).all()

        # Преобразовуємо у звичайний список рядків
        lot_number_list = [lot.lot_number for lot in packed_lot_numbers]

        # Отримуємо лише відібрані позиції з цих лотів
        from models.picking import OrderPickingItem
        picking_items = db.session.query(OrderPickingItem).filter(
            OrderPickingItem.order_id == order.id,
            OrderPickingItem.lot_number.in_(lot_number_list)
        ).all()
        
        for item in picking_items:
            # Перевіряємо, чи існує запис для цього клієнта і SKU
            stock = cls.query.filter_by(
                customer_id=order.customer_id,
                sku=item.sku
            ).first()
            
            # Отримуємо назву товару з OrderItem
            from models.order import OrderItem
            order_item = OrderItem.query.filter_by(order_id=order.id, sku=item.sku).first()
            product_name = order_item.product_name if order_item else item.sku
            
            if stock:
                # Оновлюємо існуючий запис
                if item.packaging_unit_type == 'КГ':
                    if stock.quantity_kg is None:
                        stock.quantity_kg = 0
                    stock.quantity_kg += item.actual_quantity or item.calculated_weight
                else:  # 'ШТ'
                    if stock.quantity_units is None:
                        stock.quantity_units = 0
                    # Для штучного товару: кількість ящиків * кратність
                    from models import LogisticsItemData
                    logistics = LogisticsItemData.query.filter_by(sku=item.sku).first()
                    stock.quantity_units += item.picked_box_count
            else:
                # Створюємо новий запис
                packaging_type = item.packaging_unit_type
                if not packaging_type:
                    from models import LogisticsItemData
                    logistics = LogisticsItemData.query.filter_by(sku=item.sku).first()
                    packaging_type = logistics.packaging_unit_type if logistics and logistics.packaging_unit_type else 'ШТ'

                new_stock = cls(
                    customer_id=order.customer_id,
                    sku=item.sku,
                    product_name=product_name,
                    packaging_unit_type=packaging_type
                )
                
                if item.packaging_unit_type == 'КГ':
                    new_stock.quantity_kg = item.actual_quantity or item.calculated_weight
                else:  # 'ШТ'
                    from models import LogisticsItemData
                    logistics = LogisticsItemData.query.filter_by(sku=item.sku).first()
                    new_stock.quantity_units = item.picked_box_count
                
                db.session.add(new_stock)
        
        db.session.commit()
        return True