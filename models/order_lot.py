from extensions import db
from datetime import datetime

class OrderLot(db.Model):
    __tablename__ = 'order_lot' 
    """Модель для зберігання інформації про лоти замовлень"""
    id = db.Column(db.Integer, primary_key=True)
    lot_number = db.Column(db.String(50), unique=True, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    status = db.Column(db.String(20), default='wait', nullable=False)  # 'wait', 'start', 'packed'
    pallet_number = db.Column(db.Integer, nullable=False)
    box_count = db.Column(db.Integer, nullable=True)  # Кількість зібраних ящиків
    total_weight = db.Column(db.Float, nullable=True)  # Загальна вага
    completed_at = db.Column(db.DateTime, nullable=True)  # Дата і час завершення
    picker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Логін комплектувальника
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Зв'язки
    order = db.relationship('Order', backref='lots')
    picker = db.relationship('User', backref='picked_lots')
    
    def __repr__(self):
        return f'<OrderLot {self.lot_number} - {self.status}>'



class OrderLotSKU(db.Model):
    __tablename__ = 'order_lot_sku'
    id = db.Column(db.Integer, primary_key=True)
    order_lot_id = db.Column(db.Integer, db.ForeignKey('order_lot.id'), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # кількість ящиків або одиниць
    weight = db.Column(db.Float, nullable=True)       # вага в кг, якщо КГ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Зв’язок з OrderLot
    order_lot = db.relationship('OrderLot', backref=db.backref('sku_details', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<OrderLotSKU {self.sku} – {self.quantity} шт., {self.weight:.2f} кг>'