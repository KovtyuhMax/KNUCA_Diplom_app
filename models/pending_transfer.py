from extensions import db
from datetime import datetime

class PendingTransferRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False)
    sscc = db.Column(db.String(50), nullable=False)
    from_location_id = db.Column(db.Integer, db.ForeignKey('storage_location.id'))
    to_location_id = db.Column(db.Integer, db.ForeignKey('storage_location.id'))
    box_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed = db.Column(db.Boolean, default=False)

    from_location = db.relationship('StorageLocation', foreign_keys=[from_location_id])
    to_location = db.relationship('StorageLocation', foreign_keys=[to_location_id])
    
    def __repr__(self):
        return f'<PendingTransferRequest {self.id} - {self.sku} ({self.box_count} boxes)>'
    
    @classmethod
    def get_pending_transfers_for_sku(cls, sku):
        """Отримати всі незавершені запити на переміщення для конкретного SKU"""
        return cls.query.filter_by(sku=sku, confirmed=False).all()
    
    def confirm_transfer(self):
        """Підтвердити переміщення товару"""
        from models.received_inventory import ReceivedInventory
        from models.picking import InventoryTransfer
        
        # Знаходимо відповідний запис в ReceivedInventory
        inventory_item = ReceivedInventory.query.filter_by(
            sku=self.sku,
            sscc=self.sscc,
            storage_location_id=self.from_location_id
        ).first()
        
        if not inventory_item:
            raise ValueError(f"Товар {self.sku} з SSCC {self.sscc} не знайдено в локації {self.from_location_id}")
        
        # Оновлюємо локацію товару
        old_location_id = inventory_item.storage_location_id
        inventory_item.storage_location_id = self.to_location_id
        
        # Створюємо запис про переміщення
        transfer = InventoryTransfer(
            sku=self.sku,
            from_location_id=old_location_id,
            to_location_id=self.to_location_id,
            box_count=self.box_count,
            sscc_from=self.sscc,
            sscc_to=self.sscc  # SSCC не змінюється
        )
        
        # Позначаємо запит як підтверджений
        self.confirmed = True
        
        # Зберігаємо зміни
        db.session.add(transfer)
        db.session.commit()
        
        return True