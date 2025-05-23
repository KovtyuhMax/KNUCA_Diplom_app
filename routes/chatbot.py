from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Order, OrderItem, Customer, Supplier, StorageLocation, LogisticsItemData
from models.order_lot import OrderLot
from models.pending_transfer import PendingTransferRequest
from models.supplier import SupplierContract, ContractItem
from extensions import db
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import requests
import json
import os
import re

# Спробуємо імпортувати OpenAI, якщо бібліотека встановлена
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Створення Blueprint для чатбота
chatbot_bp = Blueprint('chatbot', __name__)

# Маршрут для відображення сторінки чатбота
@chatbot_bp.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot/chatbot.html')

# API маршрут для обробки запитів до чатбота
@chatbot_bp.route('/api/chatbot', methods=['POST'])
@login_required
def process_chatbot_query():
    data = request.get_json()
    user_query = data.get('query', '')
    
    # Спочатку спробуємо обробити запит локально
    local_response = process_query_locally(user_query)
    if local_response:
        return jsonify({'response': local_response})
    
    # Якщо локальна обробка не дала результату, використовуємо OpenAI
    response = get_chatbot_response(user_query)
    
    return jsonify({
        'response': response
    })

def get_system_prompt():
    return """
    Ви асистент для WMS (Warehouse Management System) системи, який відповідає українською мовою.
    Ви можете допомогти з наступними задачами:
    1. Пошук інформації по складу (товари, залишки, місця зберігання)
    2. Робота з замовленнями постачальників і клієнтів
    3. Відстеження лотів
    4. Переміщення товарів
    5. Аналітика та звіти
    6. Робота з постачальниками та контрактами
    Відповідайте коротко, інформативно та професійно.
    """

# Функція для локальної обробки запитів
def process_query_locally(query):
    # Нормалізуємо запит (видаляємо зайві пробіли, переводимо в нижній регістр)
    normalized_query = query.lower().strip()
    
    # Пошук товару за артикулом або назвою
    if re.search(r'знайти товар|пошук товару|інформація про товар', normalized_query):
        # Шукаємо артикул або назву товару в запиті
        sku_match = re.search(r'артикул[:\s]*(\w+)', normalized_query)
        name_match = re.search(r'назв[аоу][:\s]*([\w\s]+)', normalized_query)
        
        if sku_match:
            sku = sku_match.group(1)
            return get_product_info_by_sku(sku)
        elif name_match:
            name = name_match.group(1).strip()
            return get_product_info_by_name(name)
        else:
            # Шукаємо будь-який текст, який може бути артикулом або назвою
            words = normalized_query.split()
            for word in words:
                if len(word) >= 3 and word not in ['знайти', 'товар', 'пошук', 'інформація', 'про']:
                    result = get_product_info_by_sku(word) or get_product_info_by_name(word)
                    if result:
                        return result
    
    # Пошук інформації про замовлення
    if re.search(r'замовлення|статус замовлення', normalized_query):
        # Шукаємо номер замовлення в запиті
        order_match = re.search(r'замовлення[\s#№]*(\d+)', normalized_query) or re.search(r'№\s*(\d+)', normalized_query)
        if order_match:
            order_number = order_match.group(1)
            return get_order_info_response(order_number)
    
    # Пошук інформації про лот
    if re.search(r'лот|статус лоту', normalized_query):
        # Шукаємо номер лоту в запиті
        lot_match = re.search(r'лот[\s#№]*(\d+)', normalized_query) or re.search(r'№\s*(\d+)', normalized_query)
        if lot_match:
            lot_number = lot_match.group(1)
            return get_lot_info_response(lot_number)
    
    # Аналітика: топ товарів
    if re.search(r'топ|найпопулярніші|найбільше|статистика', normalized_query):
        # Шукаємо кількість товарів та період
        count_match = re.search(r'топ[\s-]*(\d+)', normalized_query)
        period_match = re.search(r'(день|тиждень|місяць|рік)', normalized_query)
        
        count = int(count_match.group(1)) if count_match else 5
        
        if period_match:
            period = period_match.group(1)
            days = 1 if period == 'день' else 7 if period == 'тиждень' else 30 if period == 'місяць' else 365
            return get_top_products_response(days, count)
        else:
            return get_top_products_response(7, count)  # За замовчуванням - за тиждень
    
    # Інформація про постачальника
    if re.search(r'постачальник|інформація про постачальника', normalized_query):
        # Шукаємо назву постачальника
        supplier_match = re.search(r'постачальник[аи]?[:\s]*([\w\s-]+)', normalized_query)
        if supplier_match:
            supplier_name = supplier_match.group(1).strip()
            return get_supplier_info(supplier_name)
    
    # Інформація про контракти
    if re.search(r'контракт|договір|угода', normalized_query):
        # Шукаємо номер або назву постачальника
        contract_match = re.search(r'контракт[\s#№]*(\d+)', normalized_query)
        supplier_match = re.search(r'постачальник[аи]?[:\s]*([\w\s-]+)', normalized_query)
        
        if contract_match:
            contract_number = contract_match.group(1)
            return get_contract_info_by_number(contract_number)
        elif supplier_match:
            supplier_name = supplier_match.group(1).strip()
            return get_contracts_by_supplier(supplier_name)
    
    # Якщо не знайдено відповідності, повертаємо None
    return None

# Функція для отримання відповіді від API чатбота
from openai import OpenAI

def get_chatbot_response(query):
    # Якщо OpenAI API активний — використовуємо його
    openai_key = os.environ.get('OPENAI_API_KEY')
    if OPENAI_AVAILABLE and openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            system_prompt = get_system_prompt()

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            current_app.logger.error(f"Помилка OpenAI: {str(e)}")

    # Якщо OpenRouter.ai API доступний — використовуємо його
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openrouter/openchat",
                "messages": [
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": query}
                ]
            }

            response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                     headers=headers, data=json.dumps(payload))

            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                current_app.logger.error(f"OpenRouter error {response.status_code}: {response.text}")

        except Exception as e:
            current_app.logger.error(f"Помилка OpenRouter.ai: {str(e)}")

    # Якщо нічого не вдалося — базова відповідь
    return f"⚠️ Я не зміг обробити запит автоматично: '{query}'. Спробуй пізніше або задай запит точніше."


# Допоміжні функції для роботи з даними WMS

# Пошук товару за артикулом
def get_product_info_by_sku(sku):
    product = LogisticsItemData.query.filter(LogisticsItemData.sku.ilike(f'%{sku}%')).first()
    if not product:
        return f"Товар з артикулом '{sku}' не знайдено."
    
    # Отримуємо інформацію про залишки
    storage_info = StorageLocation.query.filter_by(sku=product.sku).all()
    
    # Формуємо відповідь
    response = f"<h5>Інформація про товар</h5>"
    response += f"<p><strong>Артикул:</strong> {product.sku}</p>"
    response += f"<p><strong>Назва:</strong> {product.name}</p>"
    response += f"<p><strong>Категорія:</strong> {product.category or 'Не вказано'}</p>"
    response += f"<p><strong>Температурний режим:</strong> {product.temperature_mode or 'Не вказано'}</p>"
    
    if storage_info:
        response += f"<h5>Інформація про залишки</h5>"
        response += "<ul>"
        for location in storage_info:
            response += f"<li>Локація: {location.location_code}, Кількість: {location.quantity} {product.unit_of_measure or 'шт.'}</li>"
        response += "</ul>"
    else:
        response += "<p>Інформація про залишки відсутня.</p>"
    
    return response

# Пошук товару за назвою
def get_product_info_by_name(name):
    products = LogisticsItemData.query.filter(LogisticsItemData.name.ilike(f'%{name}%')).all()
    if not products:
        return f"Товари з назвою '{name}' не знайдено."
    
    if len(products) == 1:
        return get_product_info_by_sku(products[0].sku)
    
    # Якщо знайдено кілька товарів, показуємо список
    response = f"<h5>Знайдено {len(products)} товарів:</h5>"
    response += "<ul>"
    for product in products:
        response += f"<li><strong>{product.sku}</strong> - {product.name}</li>"
    response += "</ul>"
    response += "<p>Для отримання детальної інформації, вкажіть конкретний артикул.</p>"
    
    return response

# Отримання інформації про замовлення
def get_order_info_response(order_number):
    order = Order.query.filter_by(order_number=order_number).first()
    if not order:
        return f"Замовлення з номером '{order_number}' не знайдено."
    
    # Формуємо відповідь
    response = f"<h5>Інформація про замовлення #{order.order_number}</h5>"
    
    if hasattr(order, 'customer') and order.customer:
        response += f"<p><strong>Клієнт:</strong> {order.customer.name}</p>"
    elif hasattr(order, 'supplier') and order.supplier:
        response += f"<p><strong>Постачальник:</strong> {order.supplier.name}</p>"
    
    response += f"<p><strong>Статус:</strong> {get_status_name(order.status)}</p>"
    response += f"<p><strong>Дата створення:</strong> {order.created_at.strftime('%d.%m.%Y %H:%M')}</p>"
    
    # Додаємо інформацію про товари
    items = OrderItem.query.filter_by(order_id=order.id).all()
    if items:
        response += f"<h5>Товарні позиції ({len(items)}):</h5>"
        response += "<ul>"
        for item in items:
            response += f"<li>{item.sku} - {item.product_name}, Кількість: {item.quantity}</li>"
        response += "</ul>"
    else:
        response += "<p>Товарні позиції відсутні.</p>"
    
    return response

# Отримання інформації про лот
def get_lot_info_response(lot_number):
    lot = OrderLot.query.filter_by(lot_number=lot_number).first()
    if not lot:
        return f"Лот з номером '{lot_number}' не знайдено."
    
    # Формуємо відповідь
    response = f"<h5>Інформація про лот #{lot.lot_number}</h5>"
    response += f"<p><strong>Статус:</strong> {get_lot_status_name(lot.status)}</p>"
    response += f"<p><strong>Номер палети:</strong> {lot.pallet_number or 'Не вказано'}</p>"
    
    if lot.status == 'packed':
        response += f"<p><strong>Кількість ящиків:</strong> {lot.box_count or 'Не вказано'}</p>"
        response += f"<p><strong>Загальна вага:</strong> {lot.total_weight or 'Не вказано'} кг</p>"
        if hasattr(lot, 'picker') and lot.picker:
            response += f"<p><strong>Комплектувальник:</strong> {lot.picker.username}</p>"
        response += f"<p><strong>Дата завершення:</strong> {lot.completed_at.strftime('%d.%m.%Y %H:%M') if lot.completed_at else 'Не вказано'}</p>"
    
    # Додаємо інформацію про товари в лоті
    if hasattr(lot, 'order') and lot.order:
        items = OrderItem.query.filter_by(order_id=lot.order.id, lot_number=lot.lot_number).all()
        if items:
            response += f"<h5>Товари в лоті ({len(items)}):</h5>"
            response += "<ul>"
            for item in items:
                response += f"<li>{item.sku} - {item.product_name}, Кількість: {item.quantity}</li>"
            response += "</ul>"
        else:
            response += "<p>Інформація про товари в лоті відсутня.</p>"
    
    return response

# Отримання топ продуктів за вагою за період
def get_top_products_response(days=7, limit=5):
    start_date = datetime.now() - timedelta(days=days)
    
    try:
        top_products = (
            db.session.query(
                LogisticsItemData.sku,
                LogisticsItemData.name,
                func.sum(OrderItem.quantity).label('total_quantity')
            )
            .join(OrderItem, LogisticsItemData.sku == OrderItem.sku)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(Order.created_at >= start_date)
            .group_by(LogisticsItemData.sku, LogisticsItemData.name)
            .order_by(desc('total_quantity'))
            .limit(limit)
            .all()
        )
        
        if not top_products:
            return f"За останні {days} днів не знайдено даних для аналізу."
        
        period_name = "день" if days == 1 else "тиждень" if days == 7 else "місяць" if days == 30 else f"{days} днів"
        
        response = f"<h5>Топ-{limit} товарів за {period_name}</h5>"
        response += "<ol>"
        for i, (sku, name, quantity) in enumerate(top_products, 1):
            response += f"<li><strong>{sku}</strong> - {name}: {quantity} шт.</li>"
        response += "</ol>"
        
        return response
    except Exception as e:
        current_app.logger.error(f"Помилка при отриманні топ продуктів: {str(e)}")
        return "На жаль, виникла помилка при формуванні звіту. Будь ласка, спробуйте пізніше."

# Отримання інформації про постачальника
def get_supplier_info(supplier_name):
    supplier = Supplier.query.filter(Supplier.name.ilike(f'%{supplier_name}%')).first()
    if not supplier:
        return f"Постачальника з назвою '{supplier_name}' не знайдено."
    
    # Формуємо відповідь
    response = f"<h5>Інформація про постачальника</h5>"
    response += f"<p><strong>Назва:</strong> {supplier.name}</p>"
    response += f"<p><strong>Код ЄДРПОУ:</strong> {supplier.code or 'Не вказано'}</p>"
    response += f"<p><strong>Контактна особа:</strong> {supplier.contact_person or 'Не вказано'}</p>"
    response += f"<p><strong>Телефон:</strong> {supplier.phone or 'Не вказано'}</p>"
    response += f"<p><strong>Email:</strong> {supplier.email or 'Не вказано'}</p>"
    
    # Додаємо інформацію про контракти
    contracts = SupplierContract.query.filter_by(supplier_id=supplier.id).all()
    if contracts:
        response += f"<h5>Активні контракти ({len(contracts)}):</h5>"
        response += "<ul>"
        for contract in contracts:
            response += f"<li>Контракт #{contract.contract_number}, дійсний до {contract.valid_until.strftime('%d.%m.%Y') if contract.valid_until else 'безстроковий'}</li>"
        response += "</ul>"
    else:
        response += "<p>Активні контракти відсутні.</p>"
    
    return response

# Отримання інформації про контракт за номером
def get_contract_info_by_number(contract_number):
    contract = SupplierContract.query.filter_by(contract_number=contract_number).first()
    if not contract:
        return f"Контракт з номером '{contract_number}' не знайдено."
    
    # Формуємо відповідь
    response = f"<h5>Інформація про контракт #{contract.contract_number}</h5>"
    response += f"<p><strong>Постачальник:</strong> {contract.supplier.name if contract.supplier else 'Не вказано'}</p>"
    response += f"<p><strong>Дата початку:</strong> {contract.start_date.strftime('%d.%m.%Y') if contract.start_date else 'Не вказано'}</p>"
    response += f"<p><strong>Дата закінчення:</strong> {contract.valid_until.strftime('%d.%m.%Y') if contract.valid_until else 'Безстроковий'}</p>"
    
    # Додаємо інформацію про товари в контракті
    items = SupplierContractItem.query.filter_by(contract_id=contract.id).all()
    if items:
        response += f"<h5>Товари в контракті ({len(items)}):</h5>"
        response += "<ul>"
        for item in items:
            response += f"<li>{item.sku} - {item.product_name}, Ціна: {item.price} грн.</li>"
        response += "</ul>"
    else:
        response += "<p>Товари в контракті відсутні.</p>"
    
    return response

# Отримання контрактів постачальника
def get_contracts_by_supplier(supplier_name):
    supplier = Supplier.query.filter(Supplier.name.ilike(f'%{supplier_name}%')).first()
    if not supplier:
        return f"Постачальника з назвою '{supplier_name}' не знайдено."
    
    contracts = SupplierContract.query.filter_by(supplier_id=supplier.id).all()
    if not contracts:
        return f"Для постачальника '{supplier.name}' не знайдено активних контрактів."
    
    # Формуємо відповідь
    response = f"<h5>Контракти постачальника '{supplier.name}'</h5>"
    response += "<ul>"
    for contract in contracts:
        response += f"<li>Контракт #{contract.contract_number}, "
        response += f"дійсний з {contract.start_date.strftime('%d.%m.%Y') if contract.start_date else 'не вказано'} "
        response += f"до {contract.valid_until.strftime('%d.%m.%Y') if contract.valid_until else 'безстроково'}</li>"
    response += "</ul>"
    response += "<p>Для отримання детальної інформації про контракт, вкажіть його номер.</p>"
    
    return response

# Допоміжні функції для форматування

# Отримання назви статусу замовлення
def get_status_name(status):
    status_map = {
        'created': 'Створено',
        'processing': 'В обробці',
        'packed': 'Упаковано',
        'completed': 'Виконано',
        'cancelled': 'Скасовано',
        'assembling': 'Комплектується'
    }
    return status_map.get(status, status)

# Отримання назви статусу лоту
def get_lot_status_name(status):
    status_map = {
        'wait': 'Очікує комплектації',
        'start': 'В процесі комплектації',
        'packed': 'Зібрано'
    }
    return status_map.get(status, status)