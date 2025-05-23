from flask import Blueprint, request, jsonify
from models.order import Order, OrderItem
from models.order_lot import OrderLot
from models.picking import perform_picking, OrderPickingItem
from extensions import db
from datetime import datetime
from flask_login import current_user
from models import User

picking_bp = Blueprint('picking', __name__, url_prefix='/tsd-emulator/picking')

@picking_bp.route('/order', methods=['POST'])
def get_order_details():
    """Отримати деталі замовлення для комплектації за номером лота"""
    data = request.json
    lot_number = data.get('lot_number')
    
    if not lot_number:
        return jsonify({'success': False, 'message': 'Номер лота не вказано'})
    
    # Знаходимо лот
    lot = OrderLot.query.filter_by(lot_number=lot_number).first()
    if not lot:
        return jsonify({'success': False, 'message': 'Лот не знайдено'})
    
    # Перевіряємо статус лота
    if lot.status == 'packed':
        return jsonify({'success': False, 'message': 'Цей лот вже зібрано'})
    
    # Знаходимо всі товари з цим лотом
    order_items = OrderItem.query.filter_by(lot_number=lot_number).all()
    
    if not order_items:
        return jsonify({'success': False, 'message': 'Товари лота не знайдено'})
    
    order = order_items[0].order  # всі артикулі у лоті належать одному замовленню
    
    if not order:
        return jsonify({'success': False, 'message': 'Замовлення не знайдено'})
    
    # Перевірка статусу замовлення
    if order.status not in ['processing', 'assembling']:
        return jsonify({
            'success': False,
            'message': f'Замовлення має статус "{order.status}", який не дозволяє комплектацію',
        })

    # Якщо вже збирає інший користувач
    if order.status == 'assembling' and order.started_by_user_id and order.started_by_user_id != current_user.id:
        started_by_user = User.query.get(order.started_by_user_id)
        user_name = started_by_user.username if started_by_user else f'ID: {order.started_by_user_id}'
        
        return jsonify({
            'success': False,
            'message': f'Замовлення вже збирає інший користувач ({user_name})'
        })

    # Якщо статус все ще "processing", оновлюємо на "assembling"
    if order.status == 'processing':
        order.status = 'assembling'
    
    # Змінюємо статус лота на 'start' при початку відбору (F1)
    if lot.status == 'wait':
        lot.status = 'start'
        db.session.commit()
        order.started_by_user_id = current_user.id
        db.session.commit()
    
    # Імпортуємо SkuPickingLocation для отримання інформації про місце відбору
    from models.storage import SkuPickingLocation
    
    # Формуємо відповідь по кожному артикулу в цьому лоті
    items_data = []
    for item in order_items:
        picked_quantity = db.session.query(
            db.func.sum(OrderPickingItem.picked_box_count)
        ).filter(
            OrderPickingItem.order_id == order.id,
            OrderPickingItem.sku == item.sku,
            OrderPickingItem.lot_number == lot_number
        ).scalar() or 0
        
        # Отримуємо інформацію про місце відбору для цього SKU
        location_entry = SkuPickingLocation.query.filter_by(sku=item.sku).first()
        location_name = location_entry.location.location_code if location_entry else "Не вказано"

        items_data.append({
            'sku': item.sku,
            'product_name': item.product_name,
            'quantity': item.quantity,
            'picked_quantity': picked_quantity,
            'location': location_name
        })
    
    # Повертаємо весь лот
    return jsonify({
        'success': True,
        'order_id': order.id,
        'order_number': order.order_number,
        'lot_number': lot_number,
        'items': items_data
    })


@picking_bp.route('/perform', methods=['POST'])
def perform_picking_route():
    """Виконати відбір товару"""
    from models.order_lot import OrderLot
    data = request.json
    order_id = data.get('order_id')
    sku = data.get('sku')
    requested_quantity = data.get('requested_quantity')
    lot_number = data.get('lot_number')
    
    print(f"Отримано запит на відбір: order_id={order_id}, sku={sku}, requested_quantity={requested_quantity}, lot_number={lot_number}")
    
    if not all([order_id, sku, requested_quantity, lot_number]):
        return jsonify({
            'success': False,
            'message': 'Не вказані всі необхідні параметри'
        })
    
    try:
        # Виконуємо відбір товару
        result = perform_picking(order_id, sku, requested_quantity, current_user.id, lot_number)
        print(f"Результат відбору: {result}")
        
        if result['success']:
            # Перевіряємо, чи запис був створений в базі даних
            from models.picking import OrderPickingItem
            verification = db.session.query(db.func.sum(OrderPickingItem.picked_box_count)).filter(
                OrderPickingItem.order_id == order_id,
                OrderPickingItem.sku == sku,
                OrderPickingItem.lot_number == lot_number
            ).scalar() or 0
            
            print(f"Перевірка після відбору: для SKU {sku} в лоті {lot_number} відібрано {verification} ящиків")
            
            # Якщо це останній товар у лоті, оновлюємо статус лота на 'packed'
            if result.get('is_last_item', False):
                lot = OrderLot.query.filter_by(lot_number=lot_number).first()
                if lot:
                    print(f"Останній товар у лоті {lot_number}, оновлюємо статус на 'packed'")
                    # Зберігаємо додаткову інформацію про зібраний лот
                    lot.status = 'packed'
                    lot.completed_at = datetime.utcnow()
                    lot.picker_id = current_user.id
                    
                    # Отримуємо кількість зібраних ящиків та загальну вагу
                    picking_items = OrderPickingItem.query.filter_by(lot_number=lot_number).all()
                    lot.box_count = sum(item.picked_box_count for item in picking_items)
                    lot.total_weight = sum(item.calculated_weight for item in picking_items)
                    
                    db.session.commit()
                    print(f"Лот {lot_number} успішно оновлено, box_count={lot.box_count}, total_weight={lot.total_weight}")
                    
                    # Перевіряємо, чи всі лоти замовлення мають статус 'packed'
                    order = lot.order
                    all_lots = OrderLot.query.filter_by(order_id=order.id).all()
                    if all(l.status == 'packed' for l in all_lots):
                        order.status = 'packed'
                        db.session.commit()
                        print(f"Всі лоти замовлення {order.id} зібрані, статус замовлення оновлено на 'packed'")
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'is_last_item': result.get('is_last_item', False)
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            })
    except Exception as e:
        print(f"Помилка при відборі товару: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Помилка: {str(e)}'
        })

@picking_bp.route('/available-lots', methods=['GET'])
def get_available_lots():
    """Повертає доступні лоти з оброблюваних замовлень"""
    from models import OrderItem, Order
    from models.order_lot import OrderLot
    from sqlalchemy.orm import joinedload

    # Знаходимо всі лоти зі статусом 'wait' з замовлень у статусі "processing" або "assembling"
    lots = OrderLot.query.join(Order).filter(
        OrderLot.status == 'wait',
        Order.status.in_(["processing", "assembling"])
    ).all()

    lots_data = []
    for lot in lots:
        # Знаходимо всі товари для цього лота
        items = OrderItem.query.filter_by(lot_number=lot.lot_number).all()
        sku_list = [item.sku for item in items]
        
        lots_data.append({
            'lot_number': lot.lot_number,
            'order_number': lot.order.order_number,
            'status': lot.status,
            'sku_list': sku_list
        })

    return jsonify({'success': True, 'lots': lots_data})

@picking_bp.route('/complete-lot', methods=['POST'])
def complete_lot():
    data = request.get_json()
    lot_number = data.get('lot_number')

    if not lot_number:
        return jsonify({'success': False, 'message': 'Не вказано номер лота'})

    lot = OrderLot.query.filter_by(lot_number=lot_number).first()
    if not lot:
        return jsonify({'success': False, 'message': 'Лот не знайдено'})
        
    if lot.status == 'packed':
        return jsonify({'success': True})

    # Перевірка, чи всі товари з лота зібрані
    order_items = OrderItem.query.filter_by(order_id=lot.order_id, lot_number=lot_number).all()
    all_picked = True
    total_weight = 0
    total_boxes = 0

    # Виводимо детальну інформацію для діагностики
    print(f"Перевірка лота {lot_number} для замовлення {lot.order_id}")
    print(f"Знайдено {len(order_items)} товарів у лоті")
    
    # Перевіряємо всі записи відбору для цього лота
    all_picking_items = OrderPickingItem.query.filter_by(
        order_id=lot.order_id,
        lot_number=lot_number
    ).all()
    
    print(f"Знайдено {len(all_picking_items)} записів відбору для лота {lot_number}")
    
    for picking_item in all_picking_items:
        print(f"Запис відбору: SKU={picking_item.sku}, кількість={picking_item.picked_box_count}")
    
    for item in order_items:
        # Отримуємо суму відібраних товарів для цього SKU в цьому лоті
        picked_count = db.session.query(db.func.sum(OrderPickingItem.picked_box_count)).filter(
            OrderPickingItem.order_id == lot.order_id,
            OrderPickingItem.sku == item.sku,
            OrderPickingItem.lot_number == lot_number
        ).scalar() or 0
        
        print(f"SKU: {item.sku}, Потрібно: {item.quantity}, Відібрано: {picked_count}")

        # Округляємо значення для порівняння, щоб уникнути проблем з плаваючою точкою
        if round(picked_count) < round(item.quantity):
            all_picked = False
            print(f"Товар {item.sku} не повністю відібраний: {picked_count} < {item.quantity}")
            break

        total_boxes += picked_count

        weight = db.session.query(db.func.sum(OrderPickingItem.calculated_weight)).filter(
            OrderPickingItem.order_id == lot.order_id,
            OrderPickingItem.sku == item.sku,
            OrderPickingItem.lot_number == lot_number
        ).scalar() or 0
        total_weight += weight

    if not all_picked:
        return jsonify({'success': False, 'message': 'Не всі товари з лота зібрані'})

    # Оновлюємо статус
    lot.status = 'packed'
    lot.completed_at = datetime.utcnow()
    # Перевіряємо, чи користувач автентифікований
    try:
        if current_user.is_authenticated:
            lot.picker_id = current_user.id
        else:
            # Якщо користувач не автентифікований, встановлюємо значення за замовчуванням або None
            lot.picker_id = None
    except Exception as e:
        print(f"Помилка при отриманні current_user: {e}")
        lot.picker_id = None
        
    lot.box_count = total_boxes
    lot.total_weight = total_weight

    db.session.add(lot)
    db.session.commit()

    return jsonify({'success': True})
