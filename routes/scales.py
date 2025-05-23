from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import random
from extensions import db
from models import SSCCBarcode

scales_bp = Blueprint('scales', __name__, url_prefix='/scales')

@scales_bp.route('/simulate', methods=['GET'])
def simulate_scales():
    """Standalone scales simulation page"""
    return render_template('scales/simulate.html', title='Симуляція ваг')

@scales_bp.route('/get-sscc-data', methods=['GET'])
def get_sscc_data():
    """Get SSCC data including weight"""
    sscc = request.args.get('sscc')
    
    if not sscc:
        return jsonify({'success': False, 'message': 'SSCC not found'}), 404
    
    barcode = SSCCBarcode.query.filter_by(sscc=sscc).first()
    if not barcode:
        return jsonify({'success': False, 'message': 'SSCC not found'}), 404
    
    return jsonify({
        'success': True,
        'sscc': barcode.sscc,
        'gross_weight': barcode.gross_weight,
        'created_at': barcode.created_at.strftime('%Y-%m-%d %H:%M')
    })

@scales_bp.route('/generate-sscc', methods=['POST'])
def generate_sscc():
    """Generate SSCC code and label for weighing station"""
    data = request.get_json()
    weight = data.get('weight')
    
    if not weight:
        return jsonify({'success': False, 'message': 'Вага не вказана'})
    
    try:
        # Parse weight to ensure it's a valid number
        weight_value = float(weight)
        weight_formatted = f"{weight_value:.2f}"
        
        # Generate SSCC code
        company_prefix = '00381000000000'
        serial_number = random.randint(10000, 99999)
        sscc_without_check = f"{company_prefix}{serial_number}"
        
        # Calculate check digit (GS1 algorithm)
        sum_value = 0
        for i, digit in enumerate(sscc_without_check):
            sum_value += int(digit) * (3 if i % 2 == 0 else 1)
        check_digit = (10 - (sum_value % 10)) % 10
        
        # Complete SSCC
        sscc = f"{sscc_without_check}{check_digit}"
        
        # Get current date and time
        now = datetime.now()
        date_str = now.strftime('%d.%m.%Y')
        time_str = now.strftime('%H:%M')
        date_time_str = f"{date_str} {time_str}"
        
        # Store SSCC and weight in the database
        new_sscc = SSCCBarcode(
            sscc=sscc,
            gross_weight=weight_value
        )
        db.session.add(new_sscc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sscc': sscc,
            'weight': weight_formatted,
            'date_time': date_time_str
        })
        
    except ValueError:
        return jsonify({'success': False, 'message': 'Некоректне значення ваги'})