from extensions import db
from datetime import datetime
from sqlalchemy import event

class ReceivedInventory(db.Model):
    __tablename__ = 'received_inventory'
    id = db.Column(db.Integer, primary_key=True)
    sscc = db.Column(db.String(30), unique=True, nullable=False)
    storage_location_id = db.Column(db.Integer, db.ForeignKey('storage_location.id'))
    sku = db.Column(db.String(20), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    box_count = db.Column(db.Integer, default=0)
    net_weight = db.Column(db.Float, default=0.0)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    received_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    invoice_number = db.Column(db.String(50), nullable=False)
    
    # Relationships
    storage_location = db.relationship('StorageLocation', backref='received_items')
    receiver = db.relationship('User', backref='received_items')
    
    def __repr__(self):
        return f'<ReceivedInventory {self.sscc} - {self.product_name}>'

    def update_inventory(self):
        """Оновлює або створює запис в таблиці Inventory після збереження ReceivedInventory"""
        from models.inventory import Inventory
        
        # Шукаємо запис Inventory за sku та location_id
        inventory = Inventory.query.filter_by(
            sku=self.sku, 
            location_id=self.storage_location_id
        ).first()
        
        if inventory:
            # Якщо запис існує, оновлюємо кількість
            inventory.quantity += self.box_count
        else:
            # Якщо запису немає, створюємо новий
            inventory = Inventory(
                sku=self.sku,
                location_id=self.storage_location_id,
                quantity=self.box_count,
                reserved_quantity=0
            )
            db.session.add(inventory)

# Обробники подій SQLAlchemy для автоматичного оновлення Inventory
@event.listens_for(db.session, 'after_flush')
def receive_after_flush(session, flush_context):
    """Викликається після flush операцій в сесії"""
    for instance in session.new:
        if isinstance(instance, ReceivedInventory):
            instance.update_inventory()

@event.listens_for(ReceivedInventory, 'before_delete')
def receive_before_delete(mapper, connection, target):
    """Викликається перед видаленням запису ReceivedInventory"""
    if isinstance(target, ReceivedInventory):
        from models.inventory import Inventory
        # Знаходимо відповідний запис в Inventory
        inventory = Inventory.query.filter_by(
            sku=target.sku, 
            location_id=target.storage_location_id
        ).first()
        
        if inventory:
            # Зменшуємо кількість товару
            inventory.quantity -= target.box_count
            # Якщо кількість стала від'ємною або нульовою, видаляємо запис
            if inventory.quantity <= 0:
                db.session.delete(inventory)

@event.listens_for(ReceivedInventory, 'before_update')
def receive_before_update(mapper, connection, target):
    """Викликається перед оновленням запису ReceivedInventory"""
    # Зберігаємо старі значення для порівняння
    if hasattr(target, '_sa_instance_state') and hasattr(target._sa_instance_state, 'committed_state'):
        old_values = target._sa_instance_state.committed_state
        
        # Якщо змінилася кількість або розташування
        if 'box_count' in old_values or 'storage_location_id' in old_values:
            from models.inventory import Inventory
            
            old_box_count = old_values.get('box_count', target.box_count)
            old_location_id = old_values.get('storage_location_id', target.storage_location_id)
            
            # Якщо змінилося розташування
            if old_location_id != target.storage_location_id:
                # Зменшуємо кількість у старому розташуванні
                old_inventory = Inventory.query.filter_by(sku=target.sku, location_id=old_location_id).first()
                if old_inventory:
                    old_inventory.quantity -= old_box_count
                    if old_inventory.quantity <= 0:
                        db.session.delete(old_inventory)
                
                # Збільшуємо кількість у новому розташуванні
                new_inventory = Inventory.query.filter_by(sku=target.sku, location_id=target.storage_location_id).first()
                if new_inventory:
                    new_inventory.quantity += target.box_count
                else:
                    new_inventory = Inventory(
                        sku=target.sku,
                        location_id=target.storage_location_id,
                        quantity=target.box_count,
                        reserved_quantity=0
                    )
                    db.session.add(new_inventory)
            
            # Якщо змінилася тільки кількість, але не розташування
            elif old_box_count != target.box_count:
                inventory = Inventory.query.filter_by(sku=target.sku, location_id=target.storage_location_id).first()
                if inventory:
                    # Оновлюємо кількість (віднімаємо стару, додаємо нову)
                    inventory.quantity = inventory.quantity - old_box_count + target.box_count
                    if inventory.quantity <= 0:
                        db.session.delete(inventory)