from extensions import db
from datetime import datetime

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    edrpou_code = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    contracts = db.relationship('SupplierContract', backref='supplier', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Supplier {self.name} ({self.edrpou_code})>'

class SupplierContract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    contract_number = db.Column(db.String(50), nullable=True)
    valid_until = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('ContractItem', back_populates='contract', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SupplierContract {self.contract_number}>'

class ContractItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('supplier_contract.id', ondelete='CASCADE'), nullable=False)
    sku = db.Column(db.String(20), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    contract = db.relationship('SupplierContract', back_populates='items')
    
    def __repr__(self):
        return f'<ContractItem {self.sku} - Qty: {self.quantity}>'