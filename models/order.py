from extensions import db
from datetime import datetime
import math


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    order_type = db.Column(db.String(20), nullable=False)  # 'supplier' or 'customer'
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('supplier_contract.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(20), default='created', nullable=False)  # created, processing, packed, completed, cancelled
    pallets_count = db.Column(db.Integer, nullable=True)  # Кількість палет для замовлення
    started_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    invoice_number_supplier = db.Column(db.String(50), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    requires_transfer = db.Column(db.Boolean, default=False)  # Чи потребує замовлення переміщення товарів

    
    # Relationships
    supplier = db.relationship('Supplier', backref='orders')
    customer = db.relationship('Customer', backref='orders')
    contract = db.relationship('SupplierContract', backref='orders')
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    started_by_user = db.relationship('User', foreign_keys=[started_by_user_id], backref='orders_started')
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref='created_orders')
    
    def __repr__(self):
        return f'<Order {self.order_number}>'
        
    def complete_order(self):
        """Завершує замовлення та оновлює залишки товару клієнта"""
        if self.status == 'completed':
            return False
            
        self.status = 'completed'
        db.session.commit()
        
        # Якщо це замовлення клієнта, оновлюємо залишки товару
        if self.order_type == 'customer':
            from models.client_stock import ClientStock
            ClientStock.update_from_order(self)
            
        return True
        
    def calculate_pallets(self):
        """Розраховує кількість палет, необхідних для замовлення, на основі об'єму товарів"""
        from models import LogisticsItemData

        STANDARD_PALLET_VOLUME = 960000  # 120 * 80 * 100 см³
        total_volume = 0

        for item in self.items:
            if not all([item.length_cm, item.width_cm, item.height_cm]):
                logistics_data = LogisticsItemData.query.filter_by(sku=item.sku).first()
                if logistics_data:
                    item.length_cm = logistics_data.length
                    item.width_cm = logistics_data.width
                    item.height_cm = logistics_data.height
                    db.session.commit()
                else:
                    continue

            # Отримуємо логістичну інформацію
            logistics_data = LogisticsItemData.query.filter_by(sku=item.sku).first()
            if not logistics_data:
                continue

            unit_volume = item.length_cm * item.width_cm * item.height_cm

            if logistics_data.packaging_unit_type == "ШТ":
                # Рахуємо кількість ящиків
                multiplicity = logistics_data.count or 1
                box_count = item.quantity / multiplicity
            else:
                # Ваговий товар — 1 од = 1 упаковка
                box_count = item.quantity

            item_volume = unit_volume * box_count
            total_volume += item_volume

        # Розраховуємо кількість палет (округлюємо вгору)
        if total_volume > 0:
            self.pallets_count = math.ceil(total_volume / STANDARD_PALLET_VOLUME)
            db.session.commit()
            return self.pallets_count

        return 0

    
    def split_items_by_volume(self):
        """
        Розбиває товари по палетах з урахуванням спільного об'єму (жадібний алгоритм).
        Товари з різними SKU можуть бути на одній палеті, якщо вміщаються по об'єму.
        Ураховує кратність упаковки для штучного товару та доступність товару на складі.
        """
        from models import LogisticsItemData, OrderItem
        from models.inventory import Inventory

        PALLET_VOLUME = 960000
        pallets = []  # Список палет: [{'number': int, 'volume': float, 'items': []}]
        next_pallet_number = 1
        new_items = []
        skipped_items = []

        for item in self.items:
            # Перевіряємо загальний доступний залишок по всіх рівнях складу
            total_available = Inventory.get_total_available_all_levels(item.sku) if hasattr(Inventory, 'get_total_available_all_levels') else Inventory.get_total_available(item.sku)
            
            # Якщо товару немає в наявності, пропускаємо його
            if total_available <= 0:
                skipped_items.append({
                    'sku': item.sku,
                    'product_name': item.product_name,
                    'requested': item.quantity
                })
                print(f"Товар {item.sku} ({item.product_name}) пропущено: немає в наявності")
                continue
                
            # Обмежуємо кількість до фактично доступної
            if total_available < item.quantity:
                print(f"Кількість товару {item.sku} обмежена до {total_available} (було {item.quantity})")
                item.quantity = total_available
            
            logistics = LogisticsItemData.query.filter_by(sku=item.sku).first()
            if not logistics:
                continue

            # Якщо товар штучний, розрахунок іде на ящики (враховується кратність)
            multiplicity = logistics.count or 1  # кратність упаковки (напр., 10 шт = 1 ящик)
            
            # Перевіряємо, чи це ваговий товар (або з прапорця, або з типу упаковки)
            is_weight_based = item.is_weight_based or logistics.packaging_unit_type == "КГ"  # "КГ" або "ШТ"
            
            # Встановлюємо прапорець для подальшого використання
            item.is_weight_based = is_weight_based

            # Обʼєм одиниці для вагового товару — просто упаковка; для штучного — ящик
            unit_volume = logistics.length * logistics.width * logistics.height
            if is_weight_based:
                boxes_remaining = item.quantity  # для вагових товарів: 1 шт = 1 "ящик"
            else:
                boxes_remaining = math.ceil(item.quantity / multiplicity)  # кількість ящиків

            while boxes_remaining > 0:
                placed = False
                for pallet in pallets:
                    if pallet['volume'] + unit_volume <= PALLET_VOLUME:
                        qty_fit = min(
                            boxes_remaining,
                            int((PALLET_VOLUME - pallet['volume']) // unit_volume)
                        )
                        if qty_fit > 0:
                            actual_qty = qty_fit if is_weight_based else qty_fit * multiplicity
                            new_item = OrderItem(
                                sku=item.sku,
                                product_name=item.product_name,
                                quantity=actual_qty,
                                unit_price=item.unit_price,
                                pallet_number=pallet['number'],
                                length_cm=logistics.length,
                                width_cm=logistics.width,
                                height_cm=logistics.height,
                                is_weight_based=is_weight_based
                            )
                            pallet['volume'] += qty_fit * unit_volume
                            pallet['items'].append(new_item)
                            new_items.append(new_item)
                            boxes_remaining -= qty_fit
                            placed = True
                        break

                if not placed:
                    qty_fit = min(boxes_remaining, int(PALLET_VOLUME // unit_volume)) or 1
                    actual_qty = qty_fit if is_weight_based else qty_fit * multiplicity
                    new_item = OrderItem(
                        sku=item.sku,
                        product_name=item.product_name,
                        quantity=actual_qty,
                        unit_price=item.unit_price,
                        pallet_number=next_pallet_number,
                        length_cm=logistics.length,
                        width_cm=logistics.width,
                        height_cm=logistics.height,
                        is_weight_based=is_weight_based
                    )
                    pallets.append({
                        'number': next_pallet_number,
                        'volume': qty_fit * unit_volume,
                        'items': [new_item]
                    })
                    new_items.append(new_item)
                    boxes_remaining -= qty_fit
                    next_pallet_number += 1

        # Виводимо інформацію про пропущені товари
        if skipped_items:
            print(f"Пропущено {len(skipped_items)} товарів через відсутність на складі:")
            for item in skipped_items:
                print(f"  - {item['sku']} ({item['product_name']}): запитано {item['requested']}")

        self.items.clear()
        self.items.extend(new_items)
        self.pallets_count = len(pallets)
        db.session.commit()
        return True
    
    def create_lots(self):
        """Створює лоти для товарів на основі розподілу по палетах.
        Лоти створюються для всіх товарів, які мають призначений номер палети,
        незалежно від того, чи були вони зарезервовані та чи потребують переміщення."""
        # Спочатку розподіляємо товари по палетах, якщо ще не розподілені
        if not all(item.pallet_number for item in self.items):
            self.assign_items_to_pallets()
        
        # Генеруємо лоти для кожної палети
        from datetime import date
        from models.order_lot import OrderLot
        today = date.today()
        
        # Змінено: отримуємо всі товари з призначеним номером палети, незалежно від статусу резервування
        all_items_with_pallet = [item for item in self.items if item.pallet_number]
        
        # Визначаємо унікальні номери палет для всіх товарів
        pallet_numbers = set(item.pallet_number for item in all_items_with_pallet)
        
        for pallet_num in pallet_numbers:
            # Отримуємо всі товари для цієї палети
            pallet_items = [item for item in all_items_with_pallet if item.pallet_number == pallet_num]
            
            if not pallet_items:
                continue
                
            # Створюємо унікальний номер лота для цієї палети
            lot_number = f"LOT-{today.strftime('%Y%m%d')}-P{pallet_num}-{self.order_number}"
            
            # Призначаємо цей номер лота всім товарам на цій палеті
            for item in pallet_items:
                item.lot_number = lot_number
                quantity_info = f", кількість: {item.reserved_quantity}" if item.reserved_quantity > 0 else ", очікує переміщення"
                print(f"Створено лот {lot_number} для товару {item.sku} ({item.product_name}){quantity_info}")
            
            # Створюємо запис в таблиці OrderLot зі статусом 'wait'
            order_lot = OrderLot(
                lot_number=lot_number,
                order_id=self.id,
                status='wait',
                pallet_number=pallet_num
            )
            db.session.add(order_lot)
        
        # Підраховуємо кількість створених лотів
        created_lots_count = len(pallet_numbers)
        print(f"Створено {created_lots_count} лотів для замовлення {self.order_number}")
        
        db.session.commit()
        return True
    
    def process_order(self):
        """Обробляє замовлення: розраховує палети, створює лоти, резервує товари.
        Обробляє лише ту кількість товару, яка реально доступна на складі.
        Створює лоти незалежно від підтвердження переміщення."""
        try:
            # Крок 0: Адаптивна обробка вагових товарів
            self.adapt_weight_based_items()
            
            # Крок 1: Розрахунок кількості палет
            self.calculate_pallets()
            
            # Крок 2: Розподіл товарів по палетах з урахуванням доступності
            self.split_items_by_volume()
            
            # Крок 3: Резервування товарів та отримання списку оброблених товарів
            processed_items = self.reserve_inventory()
            
            # Якщо немає жодного обробленого товару, повертаємо помилку
            if not processed_items:
                print(f"Замовлення {self.order_number} не може бути оброблене: немає доступних товарів")
                return False
            
            # Крок 4: Створення лотів для всіх товарів, незалежно від підтвердження переміщення
            # Змінено: створюємо лоти навіть якщо товар знаходиться на верхніх рівнях і потребує переміщення
            self.create_lots()
            
            # Крок 5: Оновлення статусу замовлення
            self.status = 'processing'
            db.session.commit()
            
            # Виводимо інформацію про оброблене замовлення
            print(f"Замовлення {self.order_number} оброблено. Оброблено {len(processed_items)} товарів.")
            if len(processed_items) < len(self.items):
                print(f"Увага! {len(self.items) - len(processed_items)} товарів не оброблено через недостатню кількість на складі.")
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Помилка обробки замовлення: {str(e)}")
            raise e
            
    def adapt_weight_based_items(self):
        """Адаптивна обробка вагових товарів (packaging_unit_type == 'КГ')
        Конвертує вагу в приблизну кількість ящиків на основі середньої ваги"""
        from models import LogisticsItemData
        from models.inventory import Inventory
        from models.received_inventory import ReceivedInventory
        import math
        
        for item in self.items:
            # Отримуємо логістичні дані
            logistics_item = LogisticsItemData.query.filter_by(sku=item.sku).first()
            if not logistics_item or logistics_item.packaging_unit_type != 'КГ':
                continue
            
            # Отримуємо всі прийняті палети для SKU
            received_items = ReceivedInventory.query.filter_by(sku=item.sku).all()
            
            total_weight = sum(p.net_weight for p in received_items if p.net_weight)
            total_boxes = sum(p.box_count for p in received_items if p.box_count)

            if total_boxes == 0 or total_weight == 0:
                continue  # Уникаємо ділення на нуль

            avg_weight_per_box = total_weight / total_boxes

            requested_weight = item.quantity  # у КГ
            estimated_box_count = math.ceil(requested_weight / avg_weight_per_box)
            
            # Зберігаємо оригінальну запитану вагу для подальшого використання
            item.original_requested_quantity = item.quantity
            
            # Конвертуємо вагу в кількість ящиків
            item.quantity = estimated_box_count
            item.is_weight_based = True
            
            # Перевіряємо загальний доступний залишок по всіх рівнях складу
            total_available = Inventory.get_total_available_all_levels(item.sku)
            
            # Якщо доступно менше, ніж запитано, обмежуємо кількість
            if total_available < estimated_box_count:
                print(f"Для товару {item.sku} ({item.product_name}) доступно лише {total_available} з {estimated_box_count} необхідних ящиків")
                item.quantity = total_available

        db.session.commit()
    
    def reserve_inventory(self):
        """Резервує товари з інвентаря для цього замовлення та створює запити на переміщення при необхідності.
        Обробляє лише ту кількість товару, яка реально доступна на складі.
        Створює переміщення для різниці між потрібною та доступною кількістю товару."""
        from models.inventory import Inventory
        from models.inventory_management import check_picking_availability, create_pending_transfer
        from models.pending_transfer import PendingTransferRequest
        from models import LogisticsItemData, OrderItem
        
        # Список товарів, для яких створено запити на переміщення
        items_requiring_transfer = []
        transfer_requests_created = 0
        partially_reserved_items = []
        
        # Список товарів, які будуть оброблені (з урахуванням фактичної доступності)
        processed_items = []
        
        for item in self.items:
            # Перевіряємо загальний доступний залишок по всіх рівнях складу
            total_available_all_levels = Inventory.get_total_available_all_levels(item.sku) if hasattr(Inventory, 'get_total_available_all_levels') else Inventory.get_total_available(item.sku)
            
            # Якщо товару недостатньо сумарно по всіх рівнях, обмежуємо кількість
            if total_available_all_levels < item.quantity:
                print(f"Для товару {item.sku} ({item.product_name}) доступно лише {total_available_all_levels} з {item.quantity} необхідних одиниць")
                # Якщо товару немає взагалі, пропускаємо його
                if total_available_all_levels == 0:
                    print(f"Товар {item.sku} ({item.product_name}) недоступний і буде пропущений")
                    continue
                
                # Обмежуємо кількість до фактично доступної
                original_quantity = item.quantity
                item.quantity = total_available_all_levels
                print(f"Кількість товару {item.sku} обмежена до {item.quantity} (було {original_quantity})")
            
            # Отримуємо доступну кількість товару в місцях відбору (level = 1)
            available_at_picking = Inventory.get_total_available(item.sku)
            
            # Визначаємо, скільки можемо зарезервувати з місць відбору
            to_reserve = min(available_at_picking, item.quantity)
            
            # Додаємо товар до списку оброблених, навіть якщо він потребує переміщення
            # Це дозволить створити лоти для всіх товарів
            processed_items.append(item)
            
            # Якщо доступно менше, ніж потрібно, створюємо запит на переміщення для різниці
            if available_at_picking < item.quantity:
                # Розраховуємо різницю між потрібною та доступною кількістю
                difference = item.quantity - available_at_picking
                
                print(f"Товар {item.sku} ({item.product_name}) частково доступний. Доступно: {available_at_picking}, потрібно: {item.quantity}, різниця: {difference}")
                
                # Створюємо запит на переміщення для різниці
                transfer_result = create_pending_transfer(item.sku, difference)
                
                # Додаємо інформацію про переміщення
                items_requiring_transfer.append({
                    'sku': item.sku,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'available': available_at_picking,
                    'required': item.quantity,
                    'difference': difference,
                    'created_requests': transfer_result.get('created_requests', 0)
                })
                
                transfer_requests_created += transfer_result.get('created_requests', 0)
                
                # Позначаємо замовлення як таке, що потребує переміщення
                self.requires_transfer = True
                
                # Якщо є доступна кількість на місцях відбору, резервуємо її
                if to_reserve > 0:
                    try:
                        # Резервуємо доступну кількість
                        Inventory.reserve_by_sku(item.sku, to_reserve)
                        
                        # Оновлюємо інформацію про резервування в OrderItem
                        item.reserved_quantity = to_reserve
                        
                        # Встановлюємо статус резервування як частковий
                        item.reservation_status = 'partial'
                        partially_reserved_items.append({
                            'sku': item.sku,
                            'product_name': item.product_name,
                            'requested': item.quantity,
                            'reserved': to_reserve
                        })
                        print(f"Частково зарезервовано {to_reserve} з {item.quantity} одиниць товару {item.sku}")
                    except Exception as e:
                        print(f"Помилка резервування товару {item.sku}: {str(e)}")
                        item.reservation_status = 'unreserved'
                else:
                    # Якщо нічого не можемо зарезервувати
                    item.reservation_status = 'unreserved'
                    item.reserved_quantity = 0
                    print(f"Не вдалося зарезервувати товар {item.sku}: немає доступної кількості на місцях відбору")
            else:
                # Якщо доступно достатньо товару на місцях відбору
                try:
                    # Резервуємо всю потрібну кількість
                    Inventory.reserve_by_sku(item.sku, item.quantity)
                    
                    # Оновлюємо інформацію про резервування в OrderItem
                    item.reserved_quantity = item.quantity
                    
                    # Встановлюємо статус резервування як повний
                    item.reservation_status = 'full'
                    print(f"Повністю зарезервовано {item.quantity} одиниць товару {item.sku}")
                except Exception as e:
                    print(f"Помилка резервування товару {item.sku}: {str(e)}")
                    item.reservation_status = 'unreserved'
                    item.reserved_quantity = 0
        
        # Зберігаємо зміни
        db.session.commit()
        
        # Якщо є товари, для яких створено запити на переміщення, виводимо інформацію
        if items_requiring_transfer:
            self.requires_transfer = True
            print(f"Створено {transfer_requests_created} запитів на переміщення для замовлення {self.order_number}")
        
        # Якщо є частково зарезервовані товари, виводимо інформацію
        if partially_reserved_items:
            print(f"Увага! {len(partially_reserved_items)} товарів зарезервовано частково:")
            for item in partially_reserved_items:
                print(f"  - {item['sku']} ({item['product_name']}): зарезервовано {item['reserved']} з {item['requested']}")
        
        return processed_items
    
    def unreserve_inventory(self):
        """Скасовує резервування товарів для цього замовлення"""
        from models.inventory import Inventory
        
        for item in self.items:
            # Скасовуємо резервування тільки фактично зарезервованої кількості
            if item.reserved_quantity > 0:
                try:
                    Inventory.unreserve_by_sku(item.sku, item.reserved_quantity)
                    # Скидаємо інформацію про резервування
                    item.reserved_quantity = 0
                    item.reservation_status = 'unreserved'
                except ValueError as e:
                    # Якщо виникла помилка при скасуванні резервування, логуємо її, але продовжуємо
                    print(f"Помилка скасування резервування товару {item.sku}: {str(e)}")
                    continue
        
        db.session.commit()
        return True

    
    @classmethod
    def generate_order_number(cls, order_type):
        """Generate a unique order number based on order type
    
        For supplier orders: starts with prefix '300'
        For customer orders: starts with prefix '600'
        """
        prefix = '300' if order_type == 'supplier' else '600'

        # Отримуємо останнє замовлення цього типу
        last_order = cls.query.filter(
            cls.order_type == order_type,
            cls.order_number != None
        ).order_by(cls.order_number.desc()).first()

        if (
            last_order and
            isinstance(last_order.order_number, str) and
            last_order.order_number.startswith(prefix) and
            last_order.order_number[3:].isdigit()
        ):
            last_number_part = int(last_order.order_number[3:])
            print(f"[INFO] Last {order_type} order number: {last_order.order_number}")
            next_id = last_number_part + 1
        else:
            print(f"[INFO] No valid previous {order_type} order number found.")
            next_id = 1

        return f"{prefix}{next_id:07d}"
            
    @classmethod
    def generate_invoice_number(cls):
        """Generate a sequential invoice number starting from 000001"""
        # Find the highest invoice number in the order items
        from sqlalchemy import func
        from models import OrderItem
        
        # Get the highest invoice number
        highest_item = OrderItem.query.filter(
            OrderItem.invoice_number.isnot(None)
        ).order_by(OrderItem.invoice_number.desc()).first()
        
        if highest_item and highest_item.invoice_number and highest_item.invoice_number.isdigit():
            # Increment the highest invoice number
            next_number = int(highest_item.invoice_number) + 1
        else:
            # Start from 1 if no previous invoice numbers
            next_number = 1
            
        # Format as a 6-digit number with leading zeros
        return f"{next_number:06d}"

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(20), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reserved_quantity = db.Column(db.Integer, default=0, nullable=False)  # Фактично зарезервована кількість
    reservation_status = db.Column(db.String(20), default='unreserved', nullable=False)  # 'full', 'partial', 'unreserved'
    unit_price = db.Column(db.Float, nullable=True)
    invoice_number = db.Column(db.String(50), nullable=True)  # Added for TSD receiving workflow
    lot_number = db.Column(db.String(50), nullable=True)  # Номер лота для відстеження партій товару
    pallet_number = db.Column(db.Integer, nullable=True)  # Номер палети, до якої належить товар
    length_cm = db.Column(db.Float, nullable=True)  # Довжина в см
    width_cm = db.Column(db.Float, nullable=True)  # Ширина в см
    height_cm = db.Column(db.Float, nullable=True)  # Висота в см
    is_weight_based = db.Column(db.Boolean, default=False)  # Прапорець для вагових товарів (КГ)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    
    def __repr__(self):
        return f'<OrderItem {self.id} for Order {self.order_id}>'

    def get_volume(self):
        from models import LogisticsItemData
        logistics = LogisticsItemData.query.filter_by(sku=self.sku).first()
        if not logistics:
            return 0

        unit_volume = (self.length_cm or 0) * (self.width_cm or 0) * (self.height_cm or 0)

        # Для вагових товарів (КГ) використовуємо кількість як кількість ящиків
        # Для штучних товарів (ШТ) враховуємо кратність упаковки
        if self.is_weight_based or logistics.packaging_unit_type == "КГ":
            # Для вагових товарів кількість вже конвертована в кількість ящиків
            return unit_volume * self.quantity
        else:
            # Для штучних товарів враховуємо кратність
            count = logistics.count or 1
            return unit_volume * (self.quantity / count)