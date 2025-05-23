from flask import Blueprint, render_template, jsonify, request, send_file
from sqlalchemy import func, text
from models import ReceivedInventory, StorageLocation
from extensions import db
import pandas as pd
import io
from datetime import datetime

inventory_report_bp = Blueprint('inventory_report', __name__)

@inventory_report_bp.route('/inventory/report', methods=['GET'])
def inventory_report():
    # Query to aggregate inventory data from received_inventory table
    inventory_data = db.session.query(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        func.sum(ReceivedInventory.box_count).label('total_boxes'),
        func.sum(ReceivedInventory.net_weight).label('total_net_weight'),
        StorageLocation.location_code
    ).outerjoin(
        StorageLocation, 
        ReceivedInventory.storage_location_id == StorageLocation.id
    ).group_by(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        StorageLocation.location_code
    ).all()
    
    # Format the data for the template
    report_data = [{
        'sku': item.sku,
        'product_name': item.product_name,
        'total_boxes': item.total_boxes or 0,
        'total_net_weight': item.total_net_weight or 0,
        'storage_location': item.location_code or 'Not Assigned'
    } for item in inventory_data]
    
    return render_template('reports/inventory_report.html', items=report_data)

@inventory_report_bp.route('/inventory/report/export', methods=['GET'])
def export_inventory_report():
    # Query to aggregate inventory data from received_inventory table
    inventory_data = db.session.query(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        func.sum(ReceivedInventory.box_count).label('total_boxes'),
        func.sum(ReceivedInventory.net_weight).label('total_net_weight'),
        StorageLocation.location_code
    ).outerjoin(
        StorageLocation, 
        ReceivedInventory.storage_location_id == StorageLocation.id
    ).group_by(
        ReceivedInventory.sku,
        ReceivedInventory.product_name,
        StorageLocation.location_code
    ).all()
    
    # Convert to DataFrame for Excel export
    df = pd.DataFrame([
        {
            'SKU': item.sku,
            'Product Name': item.product_name,
            'Total Boxes': item.total_boxes or 0,
            'Total Net Weight': item.total_net_weight or 0,
            'Storage Location': item.location_code or 'Not Assigned'
        } for item in inventory_data
    ])
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Inventory Report', index=False)
    
    output.seek(0)
    
    # Generate filename with current date
    filename = f"inventory_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )