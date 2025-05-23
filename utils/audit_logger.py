from functools import wraps
from flask import request, session
from flask_login import current_user
from models import AuditLog, db

def auto_log(action_name, details_func=None):
    """
    Декоратор для автоматичного логування дій користувачів.
    
    Параметри:
    - action_name: Назва дії, яка буде записана в журнал
    - details_func: Функція, яка приймає результат декорованої функції та повертає рядок з деталями для запису
    
    Приклад використання:
    @auto_log('Перегляд товару', lambda result: f'Переглянуто товар з ID: {result["id"]}'))
    def view_product(product_id):
        # код функції
        return {'id': product_id, 'name': 'Product Name'}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Виконуємо оригінальну функцію
            result = func(*args, **kwargs)
            
            # Перевіряємо, чи користувач авторизований
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
                
                # Формуємо деталі, якщо передана функція details_func
                details = None
                if details_func:
                    try:
                        details = details_func(result)
                    except Exception as e:
                        details = f"Помилка при формуванні деталей: {str(e)}"
                
                # Записуємо дію в журнал
                log = AuditLog(user_id=user_id, action=action_name, details=details)
                db.session.add(log)
                db.session.commit()
            
            return result
        return wrapper
    return decorator


def log_action(user_id, action, details=None):
    """
    Функція для прямого логування дій користувачів.
    
    Параметри:
    - user_id: ID користувача
    - action: Назва дії
    - details: Додаткові деталі (опціонально)
    """
    log = AuditLog(user_id=user_id, action=action, details=details)
    db.session.add(log)
    db.session.commit()