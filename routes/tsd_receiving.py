from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db, position_required
from models import Order, OrderItem, LogisticsItemData, StorageLocation, ReceivedInventory
# Видалено імпорт SSCCBarcode
from datetime import datetime, timedelta

# Define position access rights for TSD receiving
RECEIVING_ACCESS_POSITIONS = ['Приймальник', 'Оператор', 'Начальник зміни', 'Керівник']

tsd_receiving_bp = Blueprint('tsd_receiving', __name__, url_prefix='/tsd-emulator/api')

@tsd_receiving_bp.route('/available-orders', methods=['GET'])
@login_required
@position_required(RECEIVING_ACCESS_POSITIONS)
def available_orders():
    """Get available supplier orders for receiving"""
    # Get orders with status 'created'
    orders = Order.query.filter_by(
        order_type='supplier',
        status='created'
    ).all()
    
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'invoice_number': order.items[0].invoice_number if order.items else '',
            'order_number': order.order_number,
            'supplier_name': order.supplier.name if order.supplier else 'Unknown',
            'created_at': order.created_at.strftime('%Y-%m-%d')
        })
    
    return jsonify({
        'success': True,
        'orders': orders_data
    })

@tsd_receiving_bp.route('/start-receiving', methods=['POST'])
@login_required
@position_required(RECEIVING_ACCESS_POSITIONS)
def start_receiving():
    """Start the receiving process for an order"""
    data = request.get_json()
    
    if not data or 'invoice_number' not in data:
        return jsonify({
            'success': False,
            'message': 'Неповні дані'
        }), 400
    
    invoice_number = data['invoice_number']
    invoice_number_supplier = data.get('invoice_number_supplier', '')
    receiving_date = data.get('receiving_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Find the order by invoice number
    order_item = OrderItem.query.filter_by(invoice_number=invoice_number).first()
    if not order_item:
        return jsonify({
            'success': False,
            'message': f'Замовлення з номером накладної {invoice_number} не знайдено'
        }), 404
    
    order = order_item.order
    
    # Перевірка статусу
    if order.status == 'created':
        order.status = 'processing'
        order.started_by_user_id = current_user.id  # фіксуємо хто почав обробку
        order.updated_at = datetime.now()

    elif order.status == 'processing':
        if order.started_by_user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': f"Замовлення {order.order_number} вже приймається іншим користувачем."
            }), 403  # Заборонено
    # Якщо current_user — той самий, хто вже обробляє, то дозволяємо

    else:
        return jsonify({
            'success': False,
            'message': f"Замовлення {order.order_number} має статус '{order.status}' і не може бути оброблене."
        }), 400


    if invoice_number_supplier:
        order.invoice_number_supplier = invoice_number_supplier
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Процес прийому для замовлення {order.order_number} розпочато',
        'order': {
            'id': order.id,
            'invoice_number': invoice_number,
            'order_number': order.order_number,
            'supplier_name': order.supplier.name if order.supplier else 'Unknown'
        }
    })

@tsd_receiving_bp.route('/order-items', methods=['GET'])
@login_required
@position_required(RECEIVING_ACCESS_POSITIONS)
def get_order_items():
    """Get items for a specific order by invoice number"""
    invoice_number = request.args.get('invoice_number')
    
    if not invoice_number:
        return jsonify({
            'success': False,
            'message': 'Номер накладної не вказано'
        }), 400
    
    # Find order items by invoice number
    order_items = OrderItem.query.filter_by(invoice_number=invoice_number).all()
    
    if not order_items:
        return jsonify({
            'success': False,
            'message': f'Товари для накладної {invoice_number} не знайдено'
        }), 404
    
    items_data = []
    for item in order_items:
        # Отримати логістичні дані для SKU
        logistics_data = LogisticsItemData.query.filter_by(sku=item.sku).first()

        # Отримати останній запис ReceivedInventory для цього SKU і накладної
        received_entry = ReceivedInventory.query.filter_by(
            invoice_number=invoice_number,
            sku=item.sku
        ).order_by(ReceivedInventory.received_at.desc()).first()

        # Отримати SSCC і вагу
        sscc_code = received_entry.sscc if received_entry else None
        gross_weight = 0
        if sscc_code:
            from models import SSCCBarcode  # імпортуй, якщо ще не імпортовано
            sscc_info = SSCCBarcode.query.filter_by(sscc=sscc_code).first()
            if sscc_info:
                gross_weight = sscc_info.gross_weight

        # Додати у відповідь
        items_data.append({
            'id': item.id,
            'sku': item.sku,
            'product_name': item.product_name,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'packaging_unit_type': logistics_data.packaging_unit_type if logistics_data else 'КГ',
            'box_weight': gross_weight,
            'count': logistics_data.count if logistics_data else 1
        })
    
    return jsonify({
        'success': True,
        'items': items_data
    })

@tsd_receiving_bp.route('/save-receiving', methods=['POST'])
@login_required
@position_required(RECEIVING_ACCESS_POSITIONS)
def save_receiving():
    """Save receiving data for a pallet"""
    data = request.get_json()
    
    if not data or 'sscc' not in data or 'item_id' not in data:
        return jsonify({
            'success': False,
            'message': 'Неповні дані'
        }), 400
    
    # Extract data
    sscc = data['sscc']
    item_id = data['item_id']
    box_count = data.get('box_count', 0)
    gross_weight = data.get('gross_weight', 0)
    pallet_weight = data.get('pallet_weight', 0)
    net_weight = data.get('net_weight', 0)
    storage_location_code = data.get('storage_location', '')
    
    # Get the order item
    order_item = OrderItem.query.get(item_id)
    if not order_item:
        return jsonify({
            'success': False,
            'message': f'Товар з ID {item_id} не знайдено'
        }), 404
    
    try:
        # If storage location not provided, determine it using the fixed picking location logic
        if not storage_location_code:
            # Оновлена логіка розміщення палет відповідно до нових вимог
            from models.storage import SkuPickingLocation, StorageRow
            sku_picking_location = SkuPickingLocation.query.filter_by(sku=order_item.sku).first()
            
            if sku_picking_location:
                # Отримуємо призначене місце відбору
                picking_location = StorageLocation.query.get(sku_picking_location.picking_location_id)
                
                if picking_location:
                    # Перевіряємо, чи місце відбору вже зайняте
                    has_items = ReceivedInventory.query.filter_by(storage_location_id=picking_location.id).first()
                    
                    # Якщо місце відбору порожнє - дозволяємо заселення
                    if not has_items:
                        storage_location_code = picking_location.location_code
                        print(f"[+] Using empty picking location {storage_location_code} for SKU {order_item.sku}")
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
                            storage_location_code = available_location.location_code
                            print(f"[+] Using upper level location {storage_location_code} in same row as picking location for SKU {order_item.sku}")
            else:
                # Якщо для SKU не вказано місце відбору, заселяємо тільки на верхні рівні
                # згідно температурного режиму
                logistics_data = LogisticsItemData.query.filter_by(sku=order_item.sku).first()
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
                            storage_location_code = available_location.location_code
                            print(f"[+] Using temperature-compatible upper level location {storage_location_code} for SKU {order_item.sku}")
                        else:
                            # Не знайдено підходящої локації
                            print(f"[!] No available upper level storage location found for SKU {order_item.sku} with temperature {temp_range}°C")
            
            # Якщо досі не знайдено локацію, шукаємо будь-яку доступну локацію на верхніх рівнях
            if not storage_location_code:
                available_location = StorageLocation.query.filter(
                    StorageLocation.level > '1',  # Тільки верхні рівні
                    ~StorageLocation.received_items.any()
                ).first()
                
                if available_location:
                    storage_location_code = available_location.location_code
                    print(f"[+] Using last resort upper level location {storage_location_code} for SKU {order_item.sku}")
                else:
                    # Якщо не знайдено жодної локації на верхніх рівнях, використовуємо зону прийому
                    storage_location_code = 'RECEIVING'
                    print(f"[!] No available upper level storage locations found, using RECEIVING for SKU {order_item.sku}")
        
        # Get storage location object from code
        storage_location = StorageLocation.query.filter_by(location_code=storage_location_code).first()
        if not storage_location:
            # Default to a receiving area if location not found
            storage_location = StorageLocation.query.filter_by(location_code='RECEIVING').first()
        
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
            sscc=sscc,
            storage_location_id=storage_location.id if storage_location else None,
            sku=order_item.sku,
            product_name=product_name,
            box_count=box_count,
            net_weight=net_weight,
            received_at=received_at,
            expiry_date=expiry_date,
            received_by=current_user.id,
            invoice_number=order_item.invoice_number
        )
        db.session.add(received_inventory)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Дані прийому збережено',
            'receiving_data': {
                'sscc': sscc,
                'item_sku': order_item.sku,
                'item_name': product_name,
                'box_count': box_count,
                'gross_weight': gross_weight,
                'net_weight': net_weight,
                'storage_location': storage_location_code if storage_location else 'RECEIVING',
                'expiry_date': expiry_date.strftime('%Y-%m-%d') if expiry_date else None
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Помилка при збереженні даних: {str(e)}'
        }), 500

@tsd_receiving_bp.route('/check-received-sscc', methods=['GET'])
def check_received_sscc():
    sscc = request.args.get('sscc')

    if not sscc:
        return jsonify({'exists': False})

    exists = db.session.query(ReceivedInventory.query.filter_by(sscc=sscc).exists()).scalar()

    return jsonify({'exists': exists})