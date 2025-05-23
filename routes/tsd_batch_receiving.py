from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db, position_required
from models import Order, OrderItem, LogisticsItemData, StorageRow, StorageLocation, ReceivedInventory
from datetime import datetime, timedelta

# Define position access rights for TSD receiving
RECEIVING_ACCESS_POSITIONS = ['Приймальник', 'Оператор', 'Начальник зміни', 'Керівник']

tsd_batch_receiving_bp = Blueprint('tsd_batch_receiving', __name__, url_prefix='/tsd-emulator/api')

@tsd_batch_receiving_bp.route('/save-receiving-batch', methods=['POST'])
@login_required
@position_required(RECEIVING_ACCESS_POSITIONS)
def save_receiving_batch():
    """Save batch receiving data for multiple pallets"""
    try:
        data = request.get_json()
        
        if not data or 'pallets' not in data or not data['pallets']:
            return jsonify({
                'success': False,
                'message': 'Неповні дані або відсутні палети'
            }), 400
    
        # Extract data
        order_id = data.get('order_id')
        invoice_number = data.get('invoice_number')
        invoice_number_supplier = data.get('invoice_number_supplier', '')
        pallets = data['pallets']
    
        # Get the order
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': f'Замовлення з ID {order_id} не знайдено'
            }), 404
    
        # Process each pallet
        processed_pallets = []
        for pallet in pallets:
            # Get the order item
            item_id = pallet.get('item_id')
            order_item = OrderItem.query.get(item_id)
            if not order_item:
                continue
        
            # Get logistics data for storage location assignment
            logistics_data = LogisticsItemData.query.filter_by(sku=order_item.sku).first()
            
            # Оновлена логіка розміщення палет відповідно до нових вимог
            storage_location = None
            
            # Step 1: Перевіряємо, чи є призначене місце відбору для цього SKU
            from models.storage import SkuPickingLocation
            sku_picking_location = SkuPickingLocation.query.filter_by(sku=order_item.sku).first()
            
            if sku_picking_location:
                # Отримуємо призначене місце відбору
                picking_location = StorageLocation.query.get(sku_picking_location.picking_location_id)
                
                if picking_location:
                    # Перевіряємо, чи місце відбору вже зайняте
                    has_items = ReceivedInventory.query.filter_by(storage_location_id=picking_location.id).first()
                    
                    # Якщо місце відбору порожнє - дозволяємо заселення
                    if not has_items:
                        storage_location = picking_location.location_code
                        print(f"[+] Using empty picking location {storage_location} for SKU {order_item.sku}")
                    else:
                        # Якщо місце зайняте, шукаємо верхні рівні (level > '1') в тому ж ряду
                        row_code = picking_location.row_code
                        
                        # Знаходимо доступну комірку на верхніх рівнях у тому ж ряду
                        available_location = StorageLocation.query.filter(
                            StorageLocation.row_code == row_code,
                            StorageLocation.level > '1',  # Тільки верхні рівні
                            ~StorageLocation.received_items.any()
                        ).first()
                        
                        if available_location:
                            storage_location = available_location.location_code
                            print(f"[+] Using upper level location {storage_location} in same row as picking location for SKU {order_item.sku}")
            else:
                # Якщо для SKU не вказано місце відбору, заселяємо тільки на верхні рівні
                # згідно температурного режиму
                temp_range = logistics_data.temperature_range if logistics_data and hasattr(logistics_data, 'temperature_range') else None
                
                if temp_range is not None:
                    # Знаходимо сумісні ряди за температурою
                    compatible_rows = StorageRow.query.filter(
                        StorageRow.temperature_min <= temp_range,
                        StorageRow.temperature_max >= temp_range
                    ).all()
                    
                    if compatible_rows:
                        # Знаходимо доступну локацію з сумісною температурою на верхніх рівнях
                        available_location = StorageLocation.query.filter(
                            StorageLocation.row_code.in_([row.code for row in compatible_rows]),
                            StorageLocation.level > '1',  # Тільки верхні рівні
                            ~StorageLocation.received_items.any()
                        ).first()
                        
                        if available_location:
                            storage_location = available_location.location_code
                            print(f"[+] Using temperature-compatible upper level location {storage_location} for SKU {order_item.sku}")
                        else:
                            # Не знайдено підходящої локації
                            print(f"[!] No available upper level storage location found for SKU {order_item.sku} with temperature {temp_range}°C")
            
            # Якщо досі не знайдено локацію, шукаємо будь-яку доступну локацію на верхніх рівнях
            if not storage_location:
                available_location = StorageLocation.query.filter(
                    StorageLocation.level > '1',  # Тільки верхні рівні
                    ~StorageLocation.received_items.any()
                ).first()
                
                if available_location:
                    storage_location = available_location.location_code
                    print(f"[+] Using last resort upper level location {storage_location} for SKU {order_item.sku}")
                else:
                    print(f"[!] No available upper level storage locations found for SKU {order_item.sku}")
        
            # Update inventory item with storage location
            if storage_location:
                # Get the storage location record
                print(f"[!] storage_location assigned: {storage_location}")
                location_obj = StorageLocation.query.filter_by(location_code=storage_location).first()
                print(f"[!] location_obj is: {location_obj}")
                
                if location_obj:
                    # Get logistics data for product details and shelf life
                    logistics_data = LogisticsItemData.query.filter_by(sku=order_item.sku).first()
                    
                    # Get product name from logistics data if available
                    product_name = logistics_data.product_name if logistics_data else order_item.product_name
                    
                    # Calculate expiry date based on shelf life if available
                    received_at = datetime.now()
                    expiry_date = None
                    if logistics_data and logistics_data.shelf_life:
                        expiry_date = received_at + timedelta(days=logistics_data.shelf_life)
                    
                    # Create new received inventory entry with SSCC tracking
                    received_inventory = ReceivedInventory(
                        sscc=pallet.get('sscc'),
                        storage_location_id=location_obj.id,
                        sku=order_item.sku,
                        product_name=product_name,
                        box_count=pallet.get('box_count', 0),
                        net_weight=pallet.get('net_weight', 0),
                        received_at=received_at,
                        expiry_date=expiry_date,
                        received_by=current_user.id,
                        invoice_number=invoice_number
                    )
                    print(f"[+] Creating ReceivedInventory: SSCC={pallet.get('sscc')} LocationID={location_obj.id}")
                    db.session.add(received_inventory)
                    
            
            # Add to processed pallets
            processed_pallets.append({
                'sscc': pallet.get('sscc'),
                'item_sku': order_item.sku,
                'item_name': order_item.product_name,
                'box_count': pallet.get('box_count'),
                'gross_weight': pallet.get('gross_weight'),
                'net_weight': pallet.get('net_weight'),
                'storage_location': storage_location
            })
    
        # Update order status to completed and generate invoice number
        order.status = 'completed'
        order.updated_at = datetime.now()
        
        # Generate invoice number in format 540000000 + order.id
        invoice_number_generated = f"540{order.id:08d}"
        
        # Store the invoice number in the order (can be used for future reference)
        # You might need to add this field to the Order model if it doesn't exist
        # For now, we'll just generate it when needed
        
        db.session.commit()
    
        return jsonify({
            'success': True,
            'message': f'Дані прийому збережено для {len(processed_pallets)} палет',
            'processed_pallets': processed_pallets
        })
    
    except Exception as e:
        # Log the error
        print(f"Error in save_receiving_batch: {str(e)}")
        
        # Rollback any database changes
        db.session.rollback()
        
        # Return a proper JSON error response
        return jsonify({
            'success': False,
            'message': f'Помилка при збереженні даних: {str(e)}'
        }), 500