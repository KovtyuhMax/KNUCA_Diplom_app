from flask import Blueprint, request, jsonify
from models import OrderItem
import re
from datetime import datetime
from models import OrderItem, ReceivedInventory

validation_bp = Blueprint('validation', __name__, url_prefix='/validation')

@validation_bp.route('/check-invoice', methods=['POST'])
def check_invoice():
    """Check if invoice number exists in the order_item table"""
    data = request.get_json()
    invoice_number = data.get('invoice_number')
    
    if not invoice_number:
        return jsonify({'valid': False, 'message': 'Номер накладної не вказано'})
    
    # Check if invoice number exists in the database
    order_item = OrderItem.query.filter_by(invoice_number=invoice_number).first()
    
    if order_item:
        return jsonify({'valid': True, 'message': 'Номер накладної існує'})
    else:
        return jsonify({'valid': False, 'message': 'Цей номер накладної не існує'})

@validation_bp.route('/validate-sscc', methods=['POST'])
def validate_sscc():
    """Validate SSCC code format"""
    data = request.get_json()
    sscc = data.get('sscc')
    
    if not sscc:
        return jsonify({'valid': False, 'message': 'SSCC код не вказано'})
    
    # Check SSCC format (18 digits starting with company prefix)
    if not re.match(r'^00381000000000\d{5}\d$', sscc):
        return jsonify({'valid': False, 'message': 'Невірний формат SSCC коду'})
    
    # Validate check digit (GS1 algorithm)
    sscc_without_check = sscc[:-1]
    check_digit = int(sscc[-1])
    
    # Calculate check digit
    sum_value = 0
    for i, digit in enumerate(sscc_without_check):
        sum_value += int(digit) * (3 if i % 2 == 0 else 1)
    calculated_check_digit = (10 - (sum_value % 10)) % 10
    
    if check_digit == calculated_check_digit:
        return jsonify({'valid': True, 'message': 'SSCC код валідний'})
    else:
        return jsonify({'valid': False, 'message': 'Невірна контрольна цифра SSCC коду'})

    existing_sscc = ReceivedInventory.query.filter_by(sscc=sscc).first()
    if existing_sscc:
        return jsonify({'valid': False, 'message': 'Такий SSCC вже існує в базі'})
    return jsonify({'valid': True, 'message': 'SSCC код валідний і унікальний'})

@validation_bp.route('/get-sscc-data', methods=['GET'])
def get_sscc_data():
    """Get SSCC data including weight"""
    sscc = request.args.get('sscc')
    
    if not sscc:
        return jsonify({
            'success': False,
            'message': 'SSCC код не вказано'
        })
    
    # In a real implementation, you would fetch this from a database
    # For now, we'll generate some sample data based on the SSCC code
    # to simulate different weights for different SSCCs
    
    # Generate a deterministic weight based on the SSCC code
    # This ensures the same SSCC always returns the same weight
    sscc_sum = sum(ord(c) for c in sscc)
    weight = 1000 + (sscc_sum % 1000)  # Weight between 1000-2000 kg
    
    sscc_data = {
        'sscc': sscc,
        'weight': weight,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify({
        'success': True,
        'message': 'SSCC дані отримано',
        'sscc_data': sscc_data
    })