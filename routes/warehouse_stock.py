from flask import Blueprint, render_template, jsonify, request, send_file
from sqlalchemy import func, text
from models import ReceivedInventory, StorageLocation
from extensions import db
import pandas as pd
import io
from datetime import datetime

warehouse_stock_bp = Blueprint('warehouse_stock', __name__)

@warehouse_stock_bp.route('/warehouse/stock', methods=['GET'])
def warehouse_stock():
    # Запит для агрегації даних інвентаризації з таблиці received_inventory
    stock_data = db.session.query(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        func.sum(ReceivedInventory.box_count).label('total_boxes'),
        func.sum(ReceivedInventory.net_weight).label('total_weight')
    ).group_by(
        ReceivedInventory.sku,
        ReceivedInventory.product_name
    ).all()
    
    # Форматування даних для шаблону
    report_data = [{
        'sku': item.sku,
        'product_name': item.product_name,
        'total_boxes': item.total_boxes or 0,
        'total_weight': item.total_weight or 0
    } for item in stock_data]
    
    return render_template('reports/warehouse_stock.html', items=report_data)

@warehouse_stock_bp.route('/warehouse/stock/details', methods=['GET'])
def warehouse_stock_details():
    # Отримання SKU з параметрів запиту
    sku = request.args.get('sku')
    
    if not sku:
        return jsonify({
            'success': False,
            'message': 'SKU не вказано'
        }), 400
    
    # Запит для отримання всіх палет (SSCC) для вказаного SKU
    pallets = ReceivedInventory.query.filter_by(sku=sku).all()
    
    # Форматування даних для відповіді
    pallets_data = [{
        'sscc': pallet.sscc,
        'product_name': pallet.product_name,
        'box_count': pallet.box_count,
        'net_weight': pallet.net_weight,
        'storage_location': pallet.storage_location.location_code if pallet.storage_location else 'Не призначено',
        'received_at': pallet.received_at.strftime('%Y-%m-%d %H:%M'),
        'expiry_date': pallet.expiry_date.strftime('%Y-%m-%d') if pallet.expiry_date else 'Не вказано',
        'invoice_number': pallet.invoice_number
    } for pallet in pallets]
    
    return jsonify({
        'success': True,
        'sku': sku,
        'pallets': pallets_data
    })

@warehouse_stock_bp.route('/warehouse/stock/export', methods=['GET'])
def export_warehouse_stock():
    # Запит для агрегації даних інвентаризації з таблиці received_inventory
    stock_data = db.session.query(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        func.sum(ReceivedInventory.box_count).label('total_boxes'),
        func.sum(ReceivedInventory.net_weight).label('total_weight')
    ).group_by(
        ReceivedInventory.sku,
        ReceivedInventory.product_name
    ).all()
    
    # Конвертація у DataFrame для експорту в Excel
    df = pd.DataFrame([
        {
            'SKU': item.sku,
            'Назва товару': item.product_name,
            'Загальна кількість ящиків': item.total_boxes or 0,
            'Загальна вага (кг)': item.total_weight or 0
        } for item in stock_data
    ])
    
    # Створення Excel файлу в пам'яті
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Залишки на складі', index=False)
    
    output.seek(0)
    
    # Генерація імені файлу з поточною датою
    filename = f"warehouse_stock_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )