from extensions import db
from datetime import datetime

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey('storage_location.id'), nullable=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    reserved_quantity = db.Column(db.Integer, default=0, nullable=False)  # Кількість зарезервованих товарів
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Зв'язки
    location = db.relationship('StorageLocation', backref='inventory_items')
    
    def __repr__(self):
        return f'<Inventory {self.sku}: {self.quantity} units>'
    
    @property
    def available_quantity(self):
        """Повертає доступну кількість товару (загальна кількість мінус зарезервована)"""
        return self.quantity - self.reserved_quantity
    
    def reserve(self, quantity):
        """Резервує вказану кількість товару"""
        if quantity <= 0:
            raise ValueError("Кількість для резервування має бути більше нуля")
            
        if self.available_quantity < quantity:
            raise ValueError(f"Недостатньо товару для резервування. Доступно: {self.available_quantity}, запитано: {quantity}")
            
        self.reserved_quantity += quantity
        db.session.commit()
        return True
    
    def unreserve(self, quantity):
        """Скасовує резервування вказаної кількості товару"""
        if quantity <= 0:
            raise ValueError("Кількість для скасування резервування має бути більше нуля")
            
        if self.reserved_quantity < quantity:
            raise ValueError(f"Неможливо скасувати резервування. Зарезервовано: {self.reserved_quantity}, запитано: {quantity}")
            
        self.reserved_quantity -= quantity
        db.session.commit()
        return True
        
    @classmethod
    def unreserve_by_sku(cls, sku, quantity):
        """Скасовує резервування вказаної кількості товару за SKU"""
        if quantity <= 0:
            raise ValueError("Кількість для скасування резервування має бути більше нуля")
            
        # Знаходимо всі записи за SKU
        items = cls.query.filter_by(sku=sku).order_by(cls.created_at).all()
        
        # Перевіряємо, чи достатньо зарезервовано
        total_reserved = sum(item.reserved_quantity for item in items)
        if total_reserved < quantity:
            raise ValueError(f"Неможливо скасувати резервування. Всього зарезервовано: {total_reserved}, запитано: {quantity}")
        
        # Скасовуємо резервування
        remaining = quantity
        for item in items:
            if item.reserved_quantity > 0:
                to_unreserve = min(item.reserved_quantity, remaining)
                item.reserved_quantity -= to_unreserve
                remaining -= to_unreserve
                
                if remaining <= 0:
                    break
        
        db.session.commit()
        return True
        
    def can_reserve(self, quantity):
        """Перевіряє, чи можна зарезервувати вказану кількість товару"""
        return self.available_quantity >= quantity
        
    @classmethod
    def can_reserve_total(cls, sku, quantity):
        """Перевіряє, чи можна зарезервувати вказану кількість товару за SKU"""
        available = cls.get_total_available(sku)
        return available >= quantity
        
    @classmethod
    def reserve_by_sku(cls, sku, quantity):
        """Резервує вказану кількість товару за SKU"""
        if quantity <= 0:
            raise ValueError("Кількість для резервування має бути більше нуля")
            
        available = cls.get_total_available(sku)
        if available < quantity:
            raise ValueError(f"Недостатньо товару для резервування. Доступно: {available}, запитано: {quantity}")
        
        # Знаходимо всі записи за SKU і резервуємо потрібну кількість
        items = cls.query.filter_by(sku=sku).order_by(cls.created_at).all()
        remaining = quantity
        
        for item in items:
            if item.available_quantity > 0:
                to_reserve = min(item.available_quantity, remaining)
                item.reserved_quantity += to_reserve
                remaining -= to_reserve
                
                if remaining <= 0:
                    break
        
        db.session.commit()
        return True
    
    @classmethod
    def get_by_sku(cls, sku):
        """Отримує всі записи інвентаря за SKU"""
        return cls.query.filter_by(sku=sku).order_by(cls.created_at).all()
    
    @classmethod
    def get_total_quantity(cls, sku):
        """Отримує загальну кількість товару за SKU"""
        from sqlalchemy import func
        result = db.session.query(func.sum(cls.quantity)).filter_by(sku=sku).scalar()
        return result or 0
    
    @classmethod
    def get_total_available(cls, sku):
        """Повертає загальну доступну кількість товару за SKU в місцях відбору (level = 1)"""
        from models.storage import StorageLocation
        
        # Отримуємо всі записи інвентаря для SKU в місцях відбору (level = 1)
        items = db.session.query(cls).join(
            StorageLocation, cls.location_id == StorageLocation.id
        ).filter(
            cls.sku == sku,
            StorageLocation.level == '1'
        ).all()
        
        return sum(item.available_quantity for item in items)
    
    @classmethod
    def get_total_available_all_levels(cls, sku):
        """Повертає загальну доступну кількість товару за SKU по всіх рівнях складу"""
        items = cls.query.filter_by(sku=sku).all()
        return sum(item.available_quantity for item in items)