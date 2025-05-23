import os
from dotenv import load_dotenv
from extensions import db
from app import app
from flask_migrate import upgrade

# Завантаження змінних середовища
load_dotenv()

if __name__ == '__main__':
    # Перевірка та оновлення бази даних за допомогою міграцій
    with app.app_context():
        try:
            # Застосування міграцій
            upgrade()
            print("Міграції бази даних успішно застосовані")
        except Exception as e:
            db_url = os.environ.get('DATABASE_URL', '')
            print(f"Помилка при застосуванні міграцій: {e}")
            if 'postgresql' in db_url.lower():
                print("Переконайтеся, що PostgreSQL запущений через Docker: docker-compose up -d")
            else:
                print("Переконайтеся, що шлях до бази даних вказаний правильно в змінній DATABASE_URL")
    
    # Запуск Flask додатку
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)