from extensions import db
from models.pending_transfer import PendingTransferRequest
from models.storage import StorageLocation, SkuPickingLocation
from models.received_inventory import ReceivedInventory

def create_pending_transfer(sku, required_box_count):
    """
    Створює запити на переміщення товару з комірок зберігання (level > 1) до місць відбору (level = 1)
    
    Args:
        sku: Артикул товару
        required_box_count: Необхідна кількість ящиків для переміщення
    
    Returns:
        dict: Результат операції з інформацією про створені запити
    """
    # Комірки з рівнем > 1, де є товар
    storage_locations = db.session.query(StorageLocation).join(
        ReceivedInventory, StorageLocation.id == ReceivedInventory.storage_location_id
    ).filter(
        ReceivedInventory.sku == sku,
        StorageLocation.level > '1',
        ReceivedInventory.box_count > 0
    ).order_by(StorageLocation.level).all()

    # Призначене місце відбору
    picking_location = db.session.query(StorageLocation).join(
        SkuPickingLocation, StorageLocation.id == SkuPickingLocation.picking_location_id
    ).filter(
        SkuPickingLocation.sku == sku,
        StorageLocation.level == '1'
    ).first()

    if not picking_location:
        # Вільна комірка level=1, якщо не задана
        picking_location = StorageLocation.query.filter(
            StorageLocation.level == '1',
            ~StorageLocation.id.in_(
                db.session.query(ReceivedInventory.storage_location_id).filter(
                    ReceivedInventory.box_count > 0
                )
            )
        ).first()

    if not picking_location:
        return {
            'success': False,
            'message': 'Не знайдено доступного місця відбору для товару',
            'created_requests': 0
        }

    remaining_required = required_box_count
    created_requests = 0

    for location in storage_locations:
        if remaining_required <= 0:
            break

        inventory_items = ReceivedInventory.query.filter(
            ReceivedInventory.sku == sku,
            ReceivedInventory.storage_location_id == location.id,
            ReceivedInventory.box_count > 0
        ).order_by(ReceivedInventory.expiry_date).all()

        for item in inventory_items:
            if remaining_required <= 0:
                break

            # Перевірка, чи для цього SSCC вже існує незавершене переміщення
            existing_request = PendingTransferRequest.query.filter_by(sscc=item.sscc, confirmed=False).first()
            if existing_request:
                continue

            # Переміщуємо всю палету
            transfer_request = PendingTransferRequest(
                sku=sku,
                sscc=item.sscc,
                from_location_id=location.id,
                to_location_id=picking_location.id,
                box_count=item.box_count  # Весь обсяг
            )

            db.session.add(transfer_request)
            created_requests += 1
            remaining_required -= item.box_count

    db.session.commit()
    
    return {
        'success': True,
        'message': f'Створено {created_requests} запитів на переміщення',
        'created_requests': created_requests,
        'remaining_required': remaining_required
    }

def check_picking_availability(sku, required_quantity):
    """
    Перевіряє наявність товару в місцях відбору (level = 1) та створює запити на переміщення при необхідності
    
    Args:
        sku: Артикул товару
        required_quantity: Необхідна кількість
    
    Returns:
        dict: Результат перевірки з інформацією про доступність та створені запити
    """
    from models.pending_transfer import PendingTransferRequest
    from models import LogisticsItemData
    
    # Перевіряємо наявність незавершених запитів на переміщення для цього SKU
    pending_transfers = PendingTransferRequest.get_pending_transfers_for_sku(sku)
    
    # Отримуємо логістичну інформацію для визначення кратності упаковки
    logistics_data = LogisticsItemData.query.filter_by(sku=sku).first()
    
    # Визначаємо кількість ящиків, яка потрібна
    if logistics_data and logistics_data.packaging_unit_type == "ШТ" and logistics_data.count:
        # Для штучного товару враховуємо кратність упаковки
        multiplicity = logistics_data.count
        required_boxes = (required_quantity + multiplicity - 1) // multiplicity  # Округлення вгору
    else:
        # Для вагового товару або якщо немає даних про кратність
        required_boxes = required_quantity
    
    # Якщо є незавершені запити на переміщення
    if pending_transfers:
        return {
            'success': False,
            'message': f'Для товару {sku} є незавершені запити на переміщення',
            'pending_transfers': len(pending_transfers),
            'requires_transfer': True
        }
    
    # Знаходимо товар в комірках комплектації (level = 1)
    picking_inventory = db.session.query(ReceivedInventory).join(
        StorageLocation, ReceivedInventory.storage_location_id == StorageLocation.id
    ).filter(
        ReceivedInventory.sku == sku,
        StorageLocation.level == '1',
        ReceivedInventory.box_count > 0
    ).all()
    
    # Перевіряємо загальну доступну кількість
    available_boxes = sum(item.box_count for item in picking_inventory)
    
    # Якщо недостатньо товару в комірках комплектації, створюємо запити на переміщення
    if available_boxes < required_boxes:
        transfer_result = create_pending_transfer(sku, required_boxes - available_boxes)
        
        return {
            'success': transfer_result['success'],
            'message': f'Доступно {available_boxes} з {required_boxes} необхідних ящиків. {transfer_result["message"]}',
            'available': available_boxes,
            'required': required_boxes,
            'requires_transfer': True,
            'created_requests': transfer_result.get('created_requests', 0)
        }
    
    return {
        'success': True,
        'message': f'Доступно {available_boxes} з {required_boxes} необхідних ящиків',
        'available': available_boxes,
        'required': required_boxes,
        'requires_transfer': False
    }