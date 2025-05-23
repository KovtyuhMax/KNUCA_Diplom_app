from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import db, InventoryItem, Transaction, AuditLog, Location
from models.sscc_barcode import SSCCBarcode
from datetime import datetime

# Import position_required from a separate utils module
from utils.decorators import position_required

# Helper function to log TSD actions
def log_tsd_action(user_id, action, item_name, barcode):
    """Log TSD actions to the audit log"""
    action_type = 'Прийняття' if action == 'receive' else 'Відбір'
    log_entry = AuditLog(
        user_id=user_id,
        action=f"TSD {action_type}: {item_name}",
        details=f"Штрих-код: {barcode}"
    )
    db.session.add(log_entry)

tsd_bp = Blueprint('tsd', __name__, url_prefix='/tsd')

# Define position access rights for TSD
TSD_ACCESS_POSITIONS = ['Приймальник', 'Комплектувальник', 'Оператор', 'Начальник зміни', 'Керівник']

@tsd_bp.route('/', methods=['GET', 'POST'])
@login_required
@position_required(TSD_ACCESS_POSITIONS)
def tsd_index():
    """TSD emulator page for barcode-based operations"""
    if request.method == 'POST':
        barcode = request.form.get('barcode')
        action = request.form.get('action')
        
        if not barcode:
            flash('Будь ласка, введіть штрих-код', 'warning')
            return redirect(url_for('tsd.tsd_index'))
        
        # Find item by barcode (using SKU field)
        item = InventoryItem.query.filter_by(sku=barcode).first()
        
        if not item:
            flash(f'Товар зі штрих-кодом {barcode} не знайдено', 'danger')
            return redirect(url_for('tsd.tsd_index'))
        
        if action == 'receive':
            # Receive item (add to stock)
            item.quantity += 1
            transaction_type = 'tsd_receive'
            flash_message = f'Прийнято: {item.name}, нова кількість: {item.quantity}, місце: {item.location.name if item.location else "Не вказано"}', 'success'
        
        elif action == 'pick':
            # Pick item (subtract from stock)
            if item.quantity <= 0:
                flash(f'Недостатньо товару на складі: {item.name}', 'danger')
                return redirect(url_for('tsd.tsd_index'))
            
            item.quantity -= 1
            transaction_type = 'tsd_pick'
            flash_message = f'Відібрано: {item.name}, залишок: {item.quantity}, місце: {item.location.name if item.location else "Не вказано"}', 'success'
        
        # Update item in database
        item.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = Transaction(
            item_id=item.id,
            quantity=1,
            transaction_type=transaction_type,
            reference_number=f'TSD-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            notes = f"TSD операція: {'Прийняття' if action == 'receive' else 'Відбір'}",
            created_by=current_user.id
        )
        
        # Log the TSD action in audit log
        log_tsd_action(current_user.id, action, item.name, barcode)
        
        # Generate SSCC barcode for received items
        if action == 'receive':
            # Generate next SSCC
            sscc = SSCCBarcode.generate_next_sscc()
            
            # Create new SSCC barcode record
            sscc_barcode = SSCCBarcode(
                sscc=sscc,
                item_id=item.id,
                quantity=1,
                location_id=item.location_id,
                created_by=current_user.id
            )
            db.session.add(sscc_barcode)
            
            # Add SSCC info to flash message
            flash_message = (f'{flash_message[0]} SSCC: {sscc}', flash_message[1])
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(flash_message[0], flash_message[1])
        return redirect(url_for('tsd.tsd_index'))
    
    # Get recent TSD transactions for history display
    recent_transactions = Transaction.query.filter(
        Transaction.transaction_type.in_(['tsd_receive', 'tsd_pick'])
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    return render_template('tsd/index.html', transactions=recent_transactions, title='Імітатор ТЗД')

# AJAX endpoint for TSD operations
@tsd_bp.route('/process', methods=['POST'])
@login_required
@position_required(TSD_ACCESS_POSITIONS)
def tsd_process():
    """Process TSD operations via AJAX"""
    data = request.get_json()
    
    if not data or 'barcode' not in data or 'action' not in data:
        return jsonify({'status': 'error', 'message': 'Неповні дані'}), 400
    
    barcode = data['barcode']
    action = data['action']
    
    # Find item by barcode (using SKU field)
    item = InventoryItem.query.filter_by(sku=barcode).first()
    
    if not item:
        return jsonify({
            'status': 'error', 
            'message': f'Товар зі штрих-кодом {barcode} не знайдено'
        }), 404
    
    if action == 'receive':
        # Receive item (add to stock)
        item.quantity += 1
        transaction_type = 'tsd_receive'
        message = f'Прийнято: {item.name}, нова кількість: {item.quantity}'
        status = 'success'
    
    elif action == 'pick':
        # Pick item (subtract from stock)
        if item.quantity <= 0:
            return jsonify({
                'status': 'error', 
                'message': f'Недостатньо товару на складі: {item.name}'
            }), 400
        
        item.quantity -= 1
        transaction_type = 'tsd_pick'
        message = f'Відібрано: {item.name}, залишок: {item.quantity}'
        status = 'success'
    else:
        return jsonify({
            'status': 'error', 
            'message': 'Невідома дія'
        }), 400
    
    # Update item in database
    item.updated_at = datetime.utcnow()
    
    # Create transaction record
    transaction = Transaction(
        item_id=item.id,
        quantity=1,
        transaction_type=transaction_type,
        reference_number=f'TSD-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        notes = f"TSD операція: {'Прийняття' if action == 'receive' else 'Відбір'}",
        created_by=current_user.id
    )
    
    # Log the TSD action in audit log
    log_tsd_action(current_user.id, action, item.name, barcode)
    
    # Generate SSCC barcode for received items
    sscc_code = None
    if action == 'receive':
        # Generate next SSCC
        sscc_code = SSCCBarcode.generate_next_sscc()
        
        # Create new SSCC barcode record
        sscc_barcode = SSCCBarcode(
            sscc=sscc_code,
            item_id=item.id,
            quantity=1,
            location_id=item.location_id,
            created_by=current_user.id
        )
        db.session.add(sscc_barcode)
    
    db.session.add(transaction)
    db.session.commit()
    
    # Return item details for display
    response_data = {
        'status': status,
        'message': message,
        'item': {
            'name': item.name,
            'sku': item.sku,
            'quantity': item.quantity,
            'location': item.location.name if item.location else "Не вказано"
        }
    }
    
    # Add SSCC info to response if generated
    if action == 'receive' and sscc_code:
        response_data['sscc'] = {
            'code': sscc_code,
            'url': url_for('sscc.detail', sscc=sscc_code, _external=True)
        }
        response_data['message'] += f", SSCC: {sscc_code}"
    
    return jsonify(response_data)