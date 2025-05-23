from extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Імпортуємо моделі
from models.inventory import Inventory
from models.supplier import Supplier, SupplierContract, ContractItem
from models.order import Order, OrderItem
from models.storage import StorageRow, StorageLocation, SkuPickingLocation
from models.sscc_barcode import SSCCBarcode
from models.received_inventory import ReceivedInventory
from models.picking import OrderPickingItem, InventoryTransfer, perform_picking
from models.audit import AuditLog
from models.customer import Customer
from models.client_stock import ClientStock
from models.order_lot import OrderLot, OrderLotSKU

# Database Models
class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    users = db.relationship('User', backref='position', lazy=True)
    
    def __repr__(self):
        return f'<Position {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    position_id = db.Column(db.Integer, db.ForeignKey('position.id'))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def has_access(self, required_positions):
        if self.is_admin:
            return True
        if not self.position:
            return False
        return self.position.name in required_positions


class LogisticsItemData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)  # Артикул
    product_name = db.Column(db.String(100), nullable=False)  # Назва продукту
    packaging_unit_type = db.Column(db.String(5), nullable=False)  # ШТ, КГ
    length = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)
    dimension_unit = db.Column(db.String(5), default='СМ', nullable=False)  # Одиниця розміру
    count = db.Column(db.Integer, nullable=False)  # Кратність (number of items in this packaging)
    storage_type = db.Column(db.String(5), nullable=False)  # 04, 06
    temperature_range = db.Column(db.Integer, nullable=True)  # e.g., 6 (numeric value only)
    shelf_life = db.Column(db.Integer, nullable=True)  # shelf life in days
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<LogisticsData for {self.product_name} - {self.sku}>'