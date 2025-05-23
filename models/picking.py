from extensions import db
from datetime import datetime
from models.order_lot import OrderLot, OrderLotSKU

class OrderPickingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    sku = db.Column(db.String(50), nullable=False)
    sscc = db.Column(db.String(50), nullable=False)
    requested_quantity = db.Column(db.Float, nullable=True)  # Запитана кількість (вага або штуки)
    actual_quantity = db.Column(db.Float, nullable=True)     # Фактична кількість (вага або штуки)
    picked_box_count = db.Column(db.Integer, nullable=False) # Кількість відібраних ящиків
    calculated_weight = db.Column(db.Float, nullable=False)  # Розрахована вага
    packaging_unit_type = db.Column(db.String(5), nullable=True)  # КГ або ШТ
    underpicked = db.Column(db.Boolean, default=False)      # Чи було відібрано менше ніж запитано
    picked_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    picked_at = db.Column(db.DateTime, default=datetime.utcnow)
    storage_location = db.Column(db.String(50), nullable=True)
    lot_number = db.Column(db.String(50), nullable=True)
    
    order = db.relationship('Order', backref='picking_items')
    picked_by_user = db.relationship('User')
    
    def __repr__(self):
        return f'<OrderPickingItem {self.id} - {self.sku}>'

class InventoryTransfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False)
    from_location_id = db.Column(db.Integer, db.ForeignKey('storage_location.id'))
    to_location_id = db.Column(db.Integer, db.ForeignKey('storage_location.id'))
    box_count = db.Column(db.Integer, nullable=False)
    sscc_from = db.Column(db.String(50), nullable=True)
    sscc_to = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    from_location = db.relationship('StorageLocation', foreign_keys=[from_location_id])
    to_location = db.relationship('StorageLocation', foreign_keys=[to_location_id])
    
    def __repr__(self):
        return f'<InventoryTransfer {self.id} - {self.sku}>'


def perform_picking(order_id, sku, requested_quantity, user_id, lot_number):
    """
    Виконує відбір товару для замовлення
    
    Args:
        order_id: ID замовлення
        sku: Артикул товару
        requested_quantity: Запитана кількість
        user_id: ID користувача, який виконує відбір
    
    Returns:
        dict: Результат операції з інформацією про відбір
    """
    from models.received_inventory import ReceivedInventory
    from models.storage import StorageLocation
    from models.order import Order, OrderItem
    from models import LogisticsItemData
    from models.pending_transfer import PendingTransferRequest
    import math
    
    # Перевіряємо наявність замовлення
    order = Order.query.get(order_id)
    if not order or order.status != 'assembling':
        return {
            'success': False,
            'message': 'Замовлення не знайдено або не в статусі комплектації'
        }
    
    # Перевіряємо наявність товару в замовленні
    order_item = OrderItem.query.filter_by(order_id=order_id, sku=sku, lot_number=lot_number).first()
    if not order_item:
        return {
            'success': False,
            'message': 'Товар не знайдено в замовленні'
        }
    
    # Перевіряємо наявність незавершених запитів на переміщення для цього SKU
    pending_transfers = PendingTransferRequest.get_pending_transfers_for_sku(sku)
    if pending_transfers:
        return {
            'success': False,
            'message': f'Для товару {sku} є незавершені запити на переміщення. Зачекайте на їх підтвердження перед відбором.',
            'pending_transfers': len(pending_transfers)
        }
    
    # Отримуємо дані про логістику товару
    logistics = LogisticsItemData.query.filter_by(sku=sku).first()
    if not logistics:
        return {
            'success': False,
            'message': 'Логістичні дані для товару не знайдено'
        }
    
    # Використовуємо безпосередньо запитану кількість
    target_box_count = requested_quantity
    
    # Знаходимо товар в комірках комплектації (level = 1)
    # Спочатку знаходимо SSCC, які вже відібрані для інших замовлень
    
    # Тепер знаходимо доступний інвентар, виключаючи вже відібрані SSCC
    picking_inventory = db.session.query(ReceivedInventory).join(
        StorageLocation, ReceivedInventory.storage_location_id == StorageLocation.id
    ).filter(
        ReceivedInventory.sku == sku,
        StorageLocation.level == '1',
        ReceivedInventory.box_count > 0,
        # Виключаємо SSCC, які вже відібрані для інших замовлень
    ).order_by(ReceivedInventory.expiry_date).all()
    
    # Виводимо діагностичну інформацію
    print(f"Знайдено {len(picking_inventory)} доступних позицій для SKU {sku} в комірках комплектації")
    
    # Перевіряємо загальну доступну кількість
    available_boxes = sum(item.box_count for item in picking_inventory)
    
    # Якщо недостатньо товару в комірках комплектації, перевіряємо наявність запитів на переміщення
    if available_boxes < target_box_count:
        from models.inventory_management import check_picking_availability
        from models.pending_transfer import PendingTransferRequest
        
        # Перевіряємо наявність товару та створюємо запити на переміщення при необхідності
        availability_result = check_picking_availability(sku, target_box_count)
        
        # Перевіряємо, чи є незавершені запити на переміщення
        pending_transfers = PendingTransferRequest.get_pending_transfers_for_sku(sku)
        
        if pending_transfers:
            return {
                'success': False,
                'message': f'Для товару {sku} є незавершені запити на переміщення. Зачекайте на їх підтвердження.',
                'pending_transfers': len(pending_transfers)
            }
        
        # Якщо потрібне переміщення, повертаємо повідомлення про необхідність підтвердження
        if availability_result.get('requires_transfer', False):
            return {
                'success': False,
                'message': f'Недостатньо товару в місцях відбору. {availability_result.get("message", "")}',
                'requires_transfer': True,
                'available': availability_result.get('available', 0),
                'required': availability_result.get('required', target_box_count)
            }
        
        # Оновлюємо доступну кількість
        available_boxes = availability_result.get('available', available_boxes)
    
    # Якщо доступна кількість менша за запитану, відбираємо те, що є
    actual_box_count = min(target_box_count, available_boxes)
    
    # Якщо немає доступних ящиків взагалі, повертаємо помилку
    if actual_box_count == 0:
        return {
            'success': False,
            'message': 'Немає доступного товару для відбору'
        }
    
    # Виконуємо відбір товару
    remaining_to_pick = actual_box_count
    picked_items = []
    
    # Зберігаємо інформацію про запитану кількість для логування
    requested_box_count = target_box_count
    total_picked_weight = 0
    total_picked_boxes = 0
    
    for item in picking_inventory:
        if remaining_to_pick <= 0:
            break
            
        pick_count = min(remaining_to_pick, item.box_count)
        
        # Розраховуємо вагу відібраного товару
        calculated_weight = (item.net_weight / item.box_count) * pick_count if item.box_count > 0 else 0
        
        # Зменшуємо кількість товару в комірці
        item.box_count -= pick_count
        item.net_weight -= calculated_weight
        
        # Зберігаємо інформацію про відбір
        location_code = StorageLocation.query.get(item.storage_location_id).location_code
        
        picking_item = OrderPickingItem(
            order_id=order_id,
            sku=sku,
            sscc=item.sscc,
            picked_box_count=pick_count,
            calculated_weight=calculated_weight,
            actual_quantity=calculated_weight if logistics.packaging_unit_type == 'КГ' else pick_count,
            packaging_unit_type=logistics.packaging_unit_type,
            picked_by_user_id=user_id,
            storage_location=location_code,
            lot_number=lot_number
        )
        
        # Виводимо діагностичну інформацію про створений запис
        print(f"Створено запис відбору: SKU={sku}, lot_number={lot_number}, кількість={pick_count}")
        
        db.session.add(picking_item)
        # Зберігаємо зміни одразу, щоб уникнути проблем з транзакціями
        db.session.flush()
        picked_items.append({
            'sscc': item.sscc,
            'location': location_code,
            'box_count': pick_count,
            'weight': calculated_weight
        })
        
        total_picked_weight += calculated_weight
        total_picked_boxes += pick_count
        remaining_to_pick -= pick_count
    
    # Розраховуємо фактичну кількість відібраного товару
    actual_picked_quantity = total_picked_boxes
    
    # Якщо не вдалося відібрати жодного ящика, повертаємо помилку
    if total_picked_boxes == 0:
        return {
            'success': False,
            'message': 'Не вдалося відібрати жодного ящика товару'
        }
    
    # Перевіряємо чи всі товари в замовленні зібрані
    all_items_picked = True
    underpicked = False
    
    # Отримуємо тільки товари з поточного лота
    lot_items = [item for item in order.items if item.lot_number == lot_number]
    print(f"Перевіряємо товари лота {lot_number}, знайдено {len(lot_items)} товарів")
    
    for item in lot_items:
        # Підраховуємо загальну кількість відібраних ящиків для цього SKU в цьому лоті
        picked_count = db.session.query(db.func.sum(OrderPickingItem.picked_box_count)).filter(
            OrderPickingItem.order_id == order_id,
            OrderPickingItem.sku == item.sku,
            OrderPickingItem.lot_number == lot_number
        ).scalar() or 0
        
        print(f"Перевірка товару {item.sku} в лоті {lot_number}: потрібно {item.quantity}, відібрано {picked_count}")
        
        # Якщо відібрано менше ніж потрібно, то не всі товари зібрані
        if picked_count < item.quantity:
            all_items_picked = False
            # Якщо це поточний товар і відібрано менше ніж запитано, фіксуємо недобір
            if item.sku == sku and actual_box_count < requested_box_count:
                underpicked = True
            break
    
    # Перевіряємо всі лоти цього замовлення
    all_lots = OrderLot.query.filter_by(order_id=order_id).all()
    all_lots_packed = all(lot.status == 'packed' for lot in all_lots)

    if all_lots_packed:
        order.status = 'packed'
    db.session.add(order)
    
    # Виводимо діагностичну інформацію перед збереженням змін
    print(f"Зберігаємо зміни в базі даних. Відібрано {total_picked_boxes} ящиків товару {sku} для лота {lot_number}")
    
    # Зберігаємо всі зміни в базі даних
    db.session.commit()
    
    # Перевіряємо, чи зберігся запис в базі даних
    verification = db.session.query(db.func.sum(OrderPickingItem.picked_box_count)).filter(
        OrderPickingItem.order_id == order_id,
        OrderPickingItem.sku == sku,
        OrderPickingItem.lot_number == lot_number
    ).scalar() or 0
    
    print(f"Перевірка після збереження: для SKU {sku} в лоті {lot_number} відібрано {verification} ящиків")
    
    all_lot_items = OrderItem.query.filter_by(order_id=order_id, lot_number=lot_number).all()
    lot_fully_picked = True
    for item in all_lot_items:
        picked_count = db.session.query(db.func.sum(OrderPickingItem.picked_box_count)).filter(
            OrderPickingItem.order_id == order_id,
            OrderPickingItem.sku == item.sku,
            OrderPickingItem.lot_number == lot_number
        ).scalar() or 0
        if picked_count < item.quantity:
            lot_fully_picked = False
            break

    if lot_fully_picked:

        lot = OrderLot.query.filter_by(order_id=order_id, lot_number=lot_number).first()
        if lot:
            lot.status = 'packed'
            lot.completed_at = datetime.utcnow()

            for item in all_lot_items:
                picked_count = db.session.query(db.func.sum(OrderPickingItem.picked_box_count)).filter(
                    OrderPickingItem.order_id == order_id,
                    OrderPickingItem.sku == item.sku,
                    OrderPickingItem.lot_number == lot_number
                ).scalar() or 0

                total_weight = db.session.query(db.func.sum(OrderPickingItem.calculated_weight)).filter(
                    OrderPickingItem.order_id == order_id,
                    OrderPickingItem.sku == item.sku,
                    OrderPickingItem.lot_number == lot_number
                ).scalar() or 0

                logistics = LogisticsItemData.query.filter_by(sku=item.sku).first()
                product_name = item.product_name or (logistics.product_name if logistics else item.sku)

                db.session.add(OrderLotSKU(
                    order_lot_id=lot.id,
                    sku=item.sku,
                    product_name=product_name,
                    quantity=picked_count,
                    weight=total_weight
                ))

            lot.box_count = sum(s.quantity for s in lot.sku_details)
            lot.total_weight = sum(s.weight for s in lot.sku_details)

            db.session.add(lot)
            db.session.commit()
    
    return {
        'success': True,
        'message': 'Товар успішно відібрано' + (' (частково)' if underpicked else ''),
        'picked_items': picked_items,
        'all_items_picked': all_items_picked,
        'requested_quantity': requested_quantity,
        'actual_quantity': actual_picked_quantity,
        'underpicked': underpicked,
        'is_last_item': lot_fully_picked
    }