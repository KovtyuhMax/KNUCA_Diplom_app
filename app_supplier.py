from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField, DateField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional
from datetime import datetime

from extensions import db, position_required
from models.supplier import Supplier, SupplierContract, ContractItem
from models import LogisticsItemData

# Define blueprint
supplier_bp = Blueprint('supplier', __name__)

# Define position access rights
FULL_ACCESS_POSITIONS = ['Оператор', 'Начальник зміни', 'Керівник']

# Forms
class SupplierForm(FlaskForm):
    name = StringField('Назва постачальника', validators=[DataRequired(), Length(min=2, max=100)])
    address = TextAreaField('Адреса', validators=[DataRequired(), Length(min=5, max=500)])
    edrpou_code = StringField('Код ЄДРПОУ', validators=[DataRequired(), Length(min=8, max=10)])
    submit = SubmitField('Зберегти')

class SupplierContractForm(FlaskForm):
    supplier_id = SelectField('Постачальник', coerce=int, validators=[DataRequired()])
    contract_number = StringField('Номер контракту', validators=[Optional(), Length(max=50)])
    valid_until = DateField('Дійсний до', format='%Y-%m-%d', validators=[Optional()])
    items = SelectMultipleField('Товари (SKU)', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Зберегти')

# Helper function for logging actions
def log_action(user_id, action, details=None):
    from models import AuditLog
    log = AuditLog(user_id=user_id, action=action, details=details)
    db.session.add(log)
    db.session.commit()

# Routes
@supplier_bp.route('/suppliers')
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def supplier_list():
    suppliers = Supplier.query.all()
    return render_template('suppliers/list.html', suppliers=suppliers, title='Постачальники')

@supplier_bp.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def supplier_add():
    form = SupplierForm()
    
    if form.validate_on_submit():
        # Check if supplier with this EDRPOU code already exists
        existing_supplier = Supplier.query.filter_by(edrpou_code=form.edrpou_code.data).first()
        if existing_supplier:
            flash('Постачальник з таким кодом ЄДРПОУ вже існує', 'danger')
            return render_template('suppliers/form.html', form=form, title='Додати постачальника')
            
        supplier = Supplier(
            name=form.name.data,
            address=form.address.data,
            edrpou_code=form.edrpou_code.data
        )
        db.session.add(supplier)
        db.session.commit()
        
        # Log the action
        log_action(current_user.id, f"Додано постачальника: {supplier.name}")
        
        flash('Постачальника успішно додано!', 'success')
        return redirect(url_for('supplier.supplier_list'))
    
    return render_template('suppliers/form.html', form=form, title='Додати постачальника')

@supplier_bp.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def supplier_edit(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    form = SupplierForm(obj=supplier)
    
    if form.validate_on_submit():
        # Check if supplier with this EDRPOU code already exists and it's not this supplier
        existing_supplier = Supplier.query.filter_by(edrpou_code=form.edrpou_code.data).first()
        if existing_supplier and existing_supplier.id != supplier.id:
            flash('Постачальник з таким кодом ЄДРПОУ вже існує', 'danger')
            return render_template('suppliers/form.html', form=form, title='Редагувати постачальника')
            
        old_name = supplier.name
        
        supplier.name = form.name.data
        supplier.address = form.address.data
        supplier.edrpou_code = form.edrpou_code.data
        supplier.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log the action
        log_action(current_user.id, f"Оновлено постачальника: {old_name}", 
                  f"Новий код ЄДРПОУ: {supplier.edrpou_code}")
        
        flash('Постачальника успішно оновлено!', 'success')
        return redirect(url_for('supplier.supplier_list'))
    
    return render_template('suppliers/form.html', form=form, title='Редагувати постачальника')

@supplier_bp.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def supplier_delete(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Log the action before deletion
    log_action(current_user.id, f"Видалено постачальника: {supplier.name}")
    
    db.session.delete(supplier)
    db.session.commit()
    flash('Постачальника успішно видалено!', 'success')
    return redirect(url_for('supplier.supplier_list'))

# Supplier Contract Routes
@supplier_bp.route('/supplier-contracts')
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def contract_list():
    contracts = SupplierContract.query.all()
    return render_template('suppliers/contract_list.html', contracts=contracts, title='Контракти постачальників')

@supplier_bp.route('/supplier-contracts/view/<int:contract_id>')
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def contract_detail(contract_id):
    contract = SupplierContract.query.get_or_404(contract_id)
    return render_template('suppliers/contract_detail.html', contract=contract, title=f'Контракт {contract.contract_number or contract.id}')

@supplier_bp.route('/supplier-contracts/add', methods=['GET', 'POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def contract_add():
    form = SupplierContractForm()
    form.supplier_id.choices = [(s.id, f"{s.name} ({s.edrpou_code})") for s in Supplier.query.all()]
    
    # Populate items dropdown with LogisticsItemData (deduplicated)
    # Use distinct query to get unique sku+product_name combinations
    unique_items = db.session.query(
        LogisticsItemData.id,
        LogisticsItemData.sku,
        LogisticsItemData.product_name
    ).distinct(LogisticsItemData.sku, LogisticsItemData.product_name).all()
    
    form.items.choices = [(item.id, f"{item.sku} - {item.product_name}") for item in unique_items]
    
    if form.contract_number.data:
        existing_contract = SupplierContract.query.filter_by(contract_number=form.contract_number.data).first()
        if existing_contract:
            flash('Контракт з таким номером вже існує.', 'danger')
            return render_template('suppliers/contract_form.html', form=form, title='Додати контракт')
    
    if form.validate_on_submit():
        contract = SupplierContract(
            supplier_id=form.supplier_id.data,
            contract_number=form.contract_number.data,
            valid_until=form.valid_until.data
        )
        db.session.add(contract)
        db.session.flush()  # Get the contract ID
        
        # Add contract items from multi-select dropdown using LogisticsItemData
        for item_id in form.items.data:
            logistics_item = LogisticsItemData.query.get(item_id)
            if logistics_item:
                
                contract_item = ContractItem(
                    contract_id=contract.id,
                    sku=logistics_item.sku,
                    product_name=logistics_item.product_name,
                    quantity=1,  # Default quantity
                    unit_price=None  # No price by default
                )
                db.session.add(contract_item)
        
        db.session.commit()
        
        # Log the action
        supplier = Supplier.query.get(form.supplier_id.data)
        log_action(current_user.id, f"Додано контракт постачальника: {supplier.name} - {contract.contract_number}")
        
        flash('Контракт успішно додано!', 'success')
        return redirect(url_for('supplier.contract_list'))
    
    return render_template('suppliers/contract_form.html', form=form, title='Додати контракт')

@supplier_bp.route('/supplier-contracts/edit/<int:contract_id>', methods=['GET', 'POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def contract_edit(contract_id):
    contract = SupplierContract.query.get_or_404(contract_id)
    form = SupplierContractForm(obj=contract)
    form.supplier_id.choices = [(s.id, f"{s.name} ({s.edrpou_code})") for s in Supplier.query.all()]
    
    # Populate items dropdown with LogisticsItemData (deduplicated)
    # Use distinct query to get unique sku+product_name combinations
    raw_items = db.session.query(
        LogisticsItemData.id,
        LogisticsItemData.sku,
        LogisticsItemData.product_name
    ).all()

    # Унікальні за SKU + product_name
    seen = set()
    unique_items = []
    for item in raw_items:
        key = (item.sku, item.product_name)
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    # Сортуємо по SKU
    unique_items.sort(key=lambda x: x.sku)
    
    form.items.choices = [(item.id, f"{item.sku} - {item.product_name}") for item in unique_items]
    
    # Pre-select current items
    if request.method == 'GET':
        # Знаходимо відповідні логістичні товари за SKU
        selected_items = []
        for contract_item in contract.items:
            logistics_item = LogisticsItemData.query.filter_by(sku=contract_item.sku).first()
            if logistics_item:
                selected_items.append(logistics_item.id)
        form.items.data = selected_items
    
    if form.contract_number.data:
        existing_contract = SupplierContract.query.filter_by(contract_number=form.contract_number.data).first()
        if existing_contract and existing_contract.id != contract.id:
            flash('Контракт з таким номером вже існує.', 'danger')
            return render_template('suppliers/contract_form.html', form=form, title='Редагувати контракт')

    if form.validate_on_submit():
        contract.supplier_id = form.supplier_id.data
        contract.contract_number = form.contract_number.data
        contract.valid_until = form.valid_until.data
        contract.updated_at = datetime.utcnow()
        
        # Remove existing items
        for item in contract.items:
            db.session.delete(item)
        
        # Add new items from multi-select dropdown using LogisticsItemData
        for item_id in form.items.data:
            logistics_item = LogisticsItemData.query.get(item_id)
            if logistics_item:
                
                contract_item = ContractItem(
                    contract_id=contract.id,
                    sku=logistics_item.sku,
                    product_name=logistics_item.product_name,
                    quantity=1,  # Default quantity
                    unit_price=None  # No price by default
                )
                db.session.add(contract_item)
        
        db.session.commit()
        
        # Log the action
        supplier = Supplier.query.get(form.supplier_id.data)
        log_action(current_user.id, f"Оновлено контракт постачальника: {supplier.name}", 
                  f"Контракт: {contract.contract_number}")
        
        flash('Контракт успішно оновлено!', 'success')
        return redirect(url_for('supplier.contract_list'))
    
    return render_template('suppliers/contract_form.html', form=form, title='Редагувати контракт')

@supplier_bp.route('/supplier-contracts/delete/<int:contract_id>', methods=['POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def contract_delete(contract_id):
    contract = SupplierContract.query.get_or_404(contract_id)
    supplier = contract.supplier
    
    # Log the action before deletion
    log_action(current_user.id, f"Видалено контракт постачальника: {supplier.name} - {contract.contract_number or f'Контракт #{contract.id}'}")
    
    db.session.delete(contract)
    db.session.commit()
    flash('Контракт успішно видалено!', 'success')
    return redirect(url_for('supplier.contract_list'))

@supplier_bp.route('/suppliers/<int:supplier_id>/contracts')
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def supplier_contracts(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    contracts = SupplierContract.query.filter_by(supplier_id=supplier_id).all()
    return render_template('suppliers/supplier_contracts.html', 
                          supplier=supplier, 
                          contracts=contracts, 
                          title=f'Контракти постачальника {supplier.name}')