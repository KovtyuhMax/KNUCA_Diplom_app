import os
import sys
import argparse
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade, stamp
from sqlalchemy import text
from dotenv import load_dotenv
from extensions import db

# Load environment variables
load_dotenv()

# Create a minimal Flask application
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://warehouse_user:warehouse_password@localhost:5432/warehouse_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Import models to ensure they are registered with SQLAlchemy
from models import User, Position, LogisticsItemData, Customer, AuditLog, Order, OrderItem, ReceivedInventory

# Initialize migration
migrate_instance = Migrate(app, db)

def check_alembic_version_table():
    """Check if alembic_version table exists and create it if needed"""
    with app.app_context():
        try:
            # Check if alembic_version table exists
            result = db.session.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
            if not result:
                print("Creating alembic_version table...")
                db.session.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL, 
                    PRIMARY KEY (version_num)
                )
                """))
                db.session.commit()
                print("Created alembic_version table successfully!")
            return True
        except Exception as e:
            print(f"Error checking/creating alembic_version table: {e}")
            return False

def update_alembic_version(version='head'):
    """Update alembic_version table to point to a specific version"""
    with app.app_context():
        try:
            # Delete existing version
            db.session.execute(text("DELETE FROM alembic_version"))
            # Insert new version
            db.session.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{version}')"))
            db.session.commit()
            print(f"Successfully updated alembic_version table to point to '{version}'")
            return True
        except Exception as e:
            print(f"Error updating alembic_version table: {e}")
            db.session.rollback()
            return False

def apply_migrations():
    """Apply all migrations using Alembic"""
    with app.app_context():
        try:
            print("Applying migrations...")
            upgrade()
            print("Migrations applied successfully!")
            return True
        except Exception as e:
            print(f"Error applying migrations: {e}")
            return False

def initialize_migrations():
    """Initialize the migrations directory and create the first migration"""
    with app.app_context():
        try:
            # Check if migrations directory exists
            if not os.path.exists('migrations'):
                print("Initializing migrations directory...")
                init()
                
                # Create initial migration
                print("Creating initial migration...")
                migrate(message="Initial migration")
                
                # Apply the migration
                print("Applying migration...")
                upgrade()
                
                # Mark the database as up-to-date
                print("Marking database as up-to-date...")
                stamp()
                
                print("Migration initialization complete!")
            else:
                print("Migrations directory already exists. Skipping initialization.")
            return True
        except Exception as e:
            print(f"Error initializing migrations: {e}")
            return False

def create_tables():
    """Create database tables directly if needed"""
    with app.app_context():
        try:
            # Create order table if it doesn't exist
            db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS "order" (
                id SERIAL PRIMARY KEY,
                order_number VARCHAR(20) UNIQUE NOT NULL,
                order_type VARCHAR(20) NOT NULL,
                supplier_id INTEGER REFERENCES supplier(id),
                customer_id INTEGER REFERENCES customer(id),
                contract_id INTEGER REFERENCES supplier_contract(id),
                status VARCHAR(20) NOT NULL DEFAULT 'created',
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                created_by INTEGER REFERENCES "user"(id)
            )
            """))
            
            # Create order_item table if it doesn't exist
            db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS order_item (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES "order"(id) ON DELETE CASCADE,
                -- inventory_item reference removed as part of simplification,
                quantity INTEGER NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
            )
            """))
            
            # Create position table if it doesn't exist
            db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS position (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT
            )
            """))
            
            db.session.commit()
            print("Tables created successfully!")
            return True
        except Exception as e:
            print(f"Error creating tables: {e}")
            db.session.rollback()
            return False

def create_initial_data():
    """Create initial data like default positions, users, etc."""
    with app.app_context():
        # Create default positions
        if Position.query.count() == 0:
            print("Creating default positions...")
            positions = [
                Position(name='Приймальник'),
                Position(name='Комплектувальник'),
                Position(name='Оператор'),
                Position(name='Начальник зміни'),
                Position(name='Керівник'),
                Position(name='Менеджер з закупівель'),
                Position(name='Аналітик')
            ]
            db.session.add_all(positions)
            db.session.commit()
            print("Default positions created successfully!")
        
        # Create admin user
        admin = User.query.filter_by(username='1612').first()
        if not admin:
            print("Creating admin user...")
            # Get manager position ID
            manager_position = Position.query.filter_by(name='Керівник').first()
            position_id = manager_position.id if manager_position else None
            
            admin = User(
                username='1612',
                full_name='Admin User',
                is_admin=True,
                position_id=position_id
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists")
        
        # Create default customers
        if Customer.query.count() == 0:
            print("Creating default customers...")
            customers = [
                Customer(code='1039', name='Магазин 1039', address='вул. Шевченка 10, м. Київ, 01001'),
                Customer(code='2045', name='Магазин 2045', address='вул. Лесі Українки 25, м. Львів, 79000'),
                Customer(code='3078', name='Магазин 3078', address='просп. Гагаріна 45, м. Харків, 61000')
            ]
            db.session.add_all(customers)
            db.session.commit()
            print("Default customers created successfully!")
        
        # Create storage rows and locations
        from models.storage import StorageRow, StorageLocation
        if StorageRow.query.count() == 0:
            print("Creating storage rows...")
            storage_rows = [
                StorageRow(code='A', name='Ряд А', temperature_min=-2, temperature_max=2, storage_type='frozen'),
                StorageRow(code='B', name='Ряд B', temperature_min=2, temperature_max=6, storage_type='frozen'),
                StorageRow(code='C', name='Ряд C', temperature_min=6, temperature_max=10, storage_type='chilled'),
                StorageRow(code='D', name='Ряд D', temperature_min=12, temperature_max=16, storage_type='ambient')
            ]
            db.session.add_all(storage_rows)
            db.session.commit()
            print("Storage rows created successfully!")
        
        if StorageLocation.query.count() == 0:
            print("Creating storage locations...")
            storage_locations = []
            
            # Create locations for each row
            for row_code in ['A', 'B', 'C', 'D']:
                for cell in range(1, 17):  # Cells 1-16
                    for level in range(1, 7):  # Levels 1-6
                        location_code = f"{row_code}-{cell}-{level}"
                        location_type = 'picking' if level == 1 else 'upper'
                        
                        storage_locations.append(
                            StorageLocation(
                                row_code=row_code,
                                cell=str(cell),
                                level=str(level),
                                location_code=location_code,
                                location_type=location_type,
                                description=f"Storage location at {row_code}-{cell}-{level}"
                            )
                        )
            
            db.session.add_all(storage_locations)
            db.session.commit()
            print("Storage locations created successfully!")
        
        print("Initial data creation complete!")
        return True

import pandas as pd
from models import LogisticsItemData
from extensions import db

def import_logistics_data_from_excel():
    import pandas as pd
    from models import LogisticsItemData

    with app.app_context():

        file_path = "LogisticsDate.xlsx"  # шлях до файлу (в корені проєкту або в папці data)
        if not os.path.exists(file_path):
            print(f"[INFO] Excel file '{file_path}' not found. Skipping import.")
            return

        df = pd.read_excel(file_path)

        # Очікувані назви колонок на основі скріншоту
        column_mapping = {
            'Матеріал': 'sku',
            'Назва': 'product_name',
            'Довжина': 'length',
            'Ширина': 'width',
            'Висота': 'height',
            'Одиниця розміру': 'dimension_unit',
            'Кратність': 'count',
            'Термін придатності': 'shelf_life',
            'Тип зберігання': 'storage_type',
            'Температура зберігання': 'temperature_range',
            'Базова Одиниця': 'packaging_unit_type'
        }

        df = df.rename(columns=column_mapping)

        for _, row in df.iterrows():
            sku = str(row['sku']).strip()

            logistics_item = LogisticsItemData.query.filter_by(sku=sku).first()
            if not logistics_item:
                logistics_item = LogisticsItemData(sku=sku)

            logistics_item.product_name = str(row['product_name']).strip()
            logistics_item.length = float(row['length'])
            logistics_item.width = float(row['width'])
            logistics_item.height = float(row['height'])
            logistics_item.dimension_unit = str(row['dimension_unit']).strip()
            logistics_item.count = int(float(str(row['count']).replace(',', '.')))
            logistics_item.shelf_life = int(row['shelf_life'])
            logistics_item.storage_type = str(row['storage_type'])
            logistics_item.temperature_range = int(row['temperature_range'])
            logistics_item.packaging_unit_type = str(row['packaging_unit_type']).strip()

            db.session.add(logistics_item)

        db.session.commit()
        print("[OK] Logistics item data imported successfully.")

def init_db(reset_alembic=False, force_tables=False):
    """Initialize the database with all required components"""
    print("Starting database initialization...")
    
    # Step 1: Check and create alembic_version table if needed
    if not check_alembic_version_table():
        print("Failed to check/create alembic_version table. Aborting.")
        return False
    
    # Step 2: Initialize migrations if needed
    if not os.path.exists('migrations'):
        if not initialize_migrations():
            print("Failed to initialize migrations. Aborting.")
            return False
    
    # Step 3: Apply migrations
    if not apply_migrations():
        print("Failed to apply migrations. Trying to create tables directly.")
        if force_tables and not create_tables():
            print("Failed to create tables directly. Aborting.")
            return False
    
    # Step 4: Reset alembic version if requested
    if reset_alembic:
        if not update_alembic_version('head'):
            print("Failed to update alembic version. Aborting.")
            return False
    
    # Step 5: Create initial data
    if not create_initial_data():
        print("Failed to create initial data. Aborting.")
        return False

    import_logistics_data_from_excel()
    
    print("Database initialization completed successfully!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize the database with all required components')
    parser.add_argument('--reset-alembic', action='store_true', help='Reset the alembic version to head')
    parser.add_argument('--force-tables', action='store_true', help='Force create tables directly if migrations fail')
    args = parser.parse_args()
    
    init_db(reset_alembic=args.reset_alembic, force_tables=args.force_tables)
    
    print("\nTo run your application with the updated database, use:")
    print("python run.py")