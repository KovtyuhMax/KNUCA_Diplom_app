import os
import io
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from dotenv import load_dotenv
import tempfile
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import json
import uuid
import csv
from routes.storage import storage_bp
from routes.inventory_report import inventory_report_bp
from routes.warehouse_stock import warehouse_stock_bp
from routes.client_stock import client_stock_bp

# Import forms
from forms import LoginForm, RegistrationForm, ItemForm, LogisticsItemDataForm, LogisticsImportForm, CustomerForm

# Import blueprints
from app_supplier import supplier_bp
from app_order import order_bp
from routes.tsd_emulator import tsd_emulator_bp
from routes.validation import validation_bp
from routes.scales import scales_bp
from routes.tsd_receiving import tsd_receiving_bp
from routes.tsd_batch_receiving import tsd_batch_receiving_bp
from routes.picking_location import picking_location_bp
from routes.orders import orders_bp
from routes.customer_orders import customer_orders_bp
from routes.picking import picking_bp
from routes.transfers import transfers_bp
from routes.chatbot import chatbot_bp
from routes.export_invoice import export_invoice_bp

# Import extensions and models
from extensions import db, position_required
from utils import audit_logger
from utils.audit_logger import auto_log
from models import User, Position, LogisticsItemData, Customer, AuditLog, Order, OrderItem, ReceivedInventory
from models.storage import StorageRow, StorageLocation

# Завантаження змінних середовища з .env файлу
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://warehouse_user:warehouse_password@localhost:5432/warehouse_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Register blueprints
app.register_blueprint(supplier_bp, url_prefix='/suppliers')
app.register_blueprint(order_bp, url_prefix='/orders')
app.register_blueprint(storage_bp, url_prefix='/storage')
app.register_blueprint(picking_location_bp, url_prefix='/picking_location_bp')
app.register_blueprint(tsd_emulator_bp)
app.register_blueprint(validation_bp)
app.register_blueprint(scales_bp)
app.register_blueprint(tsd_receiving_bp)
app.register_blueprint(tsd_batch_receiving_bp)
app.register_blueprint(inventory_report_bp, url_prefix='')
app.register_blueprint(warehouse_stock_bp, url_prefix='')
app.register_blueprint(orders_bp)
app.register_blueprint(customer_orders_bp)
app.register_blueprint(picking_bp)
app.register_blueprint(transfers_bp, url_prefix='/warehouse')
app.register_blueprint(client_stock_bp)
app.register_blueprint(chatbot_bp, url_prefix='/wms')
app.register_blueprint(export_invoice_bp)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bootstrap = Bootstrap(app)

# Initialize CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

from flask_wtf.csrf import generate_csrf
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User loader for Flask-Login

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Невірний логін чи пароль', 'danger')
    
    return render_template('login.html', form=form, title='Login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Define position access rights
FULL_ACCESS_POSITIONS = ['Оператор', 'Начальник зміни', 'Керівник']
RECEIVING_ACCESS_POSITIONS = ['Приймальник'] + FULL_ACCESS_POSITIONS
PICKING_ACCESS_POSITIONS = ['Комплектувальник'] + FULL_ACCESS_POSITIONS
REPORT_ACCESS_POSITIONS = ['Менеджер з закупівель', 'Аналітик'] + FULL_ACCESS_POSITIONS
TSD_ACCESS_POSITIONS = ['Приймальник', 'Комплектувальник', 'Оператор', 'Начальник зміни', 'Керівник']


# Customer Routes
@app.route('/customers')
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def customer_list():
    customers = Customer.query.all()
    return render_template('customers/list.html', customers=customers, title='Клієнти')

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def customer_add():
    form = CustomerForm()
    
    if form.validate_on_submit():
        # Check if customer code already exists
        existing_customer = Customer.query.filter_by(code=form.code.data).first()
        if existing_customer:
            flash('Клієнт з таким кодом вже існує', 'danger')
            return render_template('customers/form.html', form=form, title='Додати клієнта')
            
        customer = Customer(
            code=form.code.data,
            name=form.name.data,
            address=form.address.data
        )
        db.session.add(customer)
        db.session.commit()
        
        # Log the action
        log_action(current_user.id, f"Додано клієнта: {customer.code} - {customer.name}")
        
        flash('Клієнта успішно додано!', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('customers/form.html', form=form, title='Додати клієнта')

@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def customer_edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        # Check if customer code already exists and it's not this customer
        existing_customer = Customer.query.filter_by(code=form.code.data).first()
        if existing_customer and existing_customer.id != customer.id:
            flash('Клієнт з таким кодом вже існує', 'danger')
            return render_template('customers/form.html', form=form, title='Редагувати клієнта')
            
        old_code = customer.code
        
        customer.code = form.code.data
        customer.address = form.address.data
        customer.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log the action
        log_action(current_user.id, f"Оновлено клієнта: {old_code}. " \
                f"Новий код: {customer.code}, Назва: {customer.name}")
        
        flash('Клієнта успішно оновлено!', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('customers/form.html', form=form, title='Редагувати клієнта')

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def customer_delete(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Log the action before deletion
    log_action(current_user.id, f"Видалено клієнта: {customer.code} - {customer.name}")
    
    db.session.delete(customer)
    db.session.commit()
    flash('Клієнта успішно видалено!', 'success')
    return redirect(url_for('customer_list'))

# Audit Log model for tracking user actions


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    # Get all positions for the dropdown
    form.position_id.choices = [(p.id, p.name) for p in Position.query.all()]
    
    if form.validate_on_submit():
        # Check if this is the first user (make them admin)
        is_first_user = User.query.count() == 0
        
        user = User(
            username=form.username.data,
            full_name=form.full_name.data, 
            is_admin=is_first_user,
            position_id=form.position_id.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Реєстрація успішна. Можете входити.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form, title='Register')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get counts for dashboard
    total_items = ReceivedInventory.query.count()
    low_stock_items = ReceivedInventory.query.filter(ReceivedInventory.box_count < 2).count()
    total_locations = StorageLocation.query.count()
    
    # Log dashboard access
    log_action(current_user.id, 'Accessed dashboard')
    
    # Get user position for customized dashboard
    user_position = None
    if current_user.position:
        user_position = current_user.position.name
    
    return render_template('dashboard.html', 
                          title='Dashboard',
                          total_items=total_items,
                          low_stock_items=low_stock_items,
                          total_locations=total_locations,
                          user_position=user_position)

# Register blueprints
def register_blueprints(app):
    # TSD blueprint видалено
    pass

# Register blueprints after app initialization
register_blueprints(app)



# Inventory Routes
@app.route('/inventory')
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def inventory_list():
    # Redirect to the new inventory report
    return redirect(url_for('inventory_report.inventory_report'))



# Logistics Routes
@app.route('/logistics')
@login_required
def logistics_list():
    # Get query parameters for filtering
    sku = request.args.get('sku')
    storage_type = request.args.get('storage_type')
    
    # Base query
    query = LogisticsItemData.query
    
    # Apply filters if provided
    if sku:
        query = query.filter(LogisticsItemData.sku.ilike(f'%{sku}%'))
    if storage_type:
        query = query.filter_by(storage_type=storage_type)
    
    # Get all logistics items
    logistics_items = query.all()
    
    # Get unique storage types for filter dropdown
    storage_types = [('04', '04 - стандартний'), ('06', '06 - дистрибуція')]
    
    return render_template('logistics/list.html', 
                          logistics_items=logistics_items,
                          storage_types=storage_types,
                          selected_sku=sku,
                          selected_storage_type=storage_type,
                          title='Логістичні дані')

@app.route('/logistics/add', methods=['GET', 'POST'])
@login_required
def logistics_add():
    form = LogisticsItemDataForm()
    
    if form.validate_on_submit():
        logistics_item = LogisticsItemData(
            sku=form.sku.data,
            product_name=form.product_name.data,
            packaging_unit_type=form.packaging_unit_type.data,
            length=form.length.data,
            width=form.width.data,
            height=form.height.data,
            dimension_unit=form.dimension_unit.data,
            count=form.count.data,
            storage_type=form.storage_type.data,
            temperature_range=form.temperature_range.data,
            shelf_life=form.shelf_life.data
        )
        db.session.add(logistics_item)
        db.session.commit()
        flash('Логістичні дані додано успішно!', 'success')
        return redirect(url_for('logistics_list'))
    
    return render_template('logistics/form.html', form=form, title='Додати логістичні дані')

@app.route('/logistics/edit/<int:logistics_id>', methods=['GET', 'POST'])
@login_required
def logistics_edit(logistics_id):
    logistics_item = LogisticsItemData.query.get_or_404(logistics_id)
    form = LogisticsItemDataForm(obj=logistics_item)
    
    if form.validate_on_submit():
        logistics_item.sku = form.sku.data
        logistics_item.product_name = form.product_name.data
        logistics_item.packaging_unit_type = form.packaging_unit_type.data
        logistics_item.length = form.length.data
        logistics_item.width = form.width.data
        logistics_item.height = form.height.data
        logistics_item.dimension_unit = form.dimension_unit.data
        logistics_item.count = form.count.data
        logistics_item.storage_type = form.storage_type.data
        logistics_item.temperature_range = form.temperature_range.data
        logistics_item.shelf_life = form.shelf_life.data
        logistics_item.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Логістичні дані оновлено успішно!', 'success')
        return redirect(url_for('logistics_list'))
    
    return render_template('logistics/form.html', form=form, title='Редагувати логістичні дані')

@app.route('/logistics/delete/<int:logistics_id>', methods=['POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def logistics_delete(logistics_id):
    logistics_item = LogisticsItemData.query.get_or_404(logistics_id)
    db.session.delete(logistics_item)
    db.session.commit()
    flash('Логістичні дані успішно видалено!', 'success')
    return redirect(url_for('logistics_list'))

@app.route('/logistics/import', methods=['GET', 'POST'])
@login_required
@position_required(FULL_ACCESS_POSITIONS)
def logistics_import():
    form = LogisticsImportForm()
    results = None
    
    if form.validate_on_submit():
        # Save the uploaded file to a temporary location
        excel_file = form.excel_file.data
        fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
        excel_file.save(temp_path)
        
        try:
            # Process the Excel file
            df = pd.read_excel(temp_path)
            
            # Initialize counters for import results
            total_rows = len(df)
            success_count = 0
            duplicate_count = 0
            error_count = 0
            error_details = []
            
            # Process each row in the Excel file
            for index, row in df.iterrows():
                try:
                    # Extract data from the row with appropriate error handling
                    try:
                        sku = str(int(row.get('Матеріал', 0)))
                    except:
                        sku = str(row.get('Матеріал', ''))
                    
                    product_name = str(row.get('Назва', ''))
                    # Check if this SKU already exists
                    existing_item = LogisticsItemData.query.filter_by(
                        sku=sku
                    ).first()
                    
                    if existing_item:
                        duplicate_count += 1
                        continue
                    
                    # Create a new logistics item
                    logistics_item = LogisticsItemData(
                        sku=sku,
                        product_name=product_name,
                        packaging_unit_type=str(row.get('Базова Одиниця')),  # Default value
                        length=float(row.get('Довжина', 0)),
                        width=float(row.get('Ширина', 0)),
                        height=float(row.get('Висота', 0)),
                        dimension_unit=str(row.get('Одиниця розміру', 'СМ')),
                        count=int(row.get('Кратність', 1)),
                        storage_type=str(row.get('Тип зберігання', '04')),
                        temperature_range=row.get('Температура зберігання'),
                        shelf_life=row.get('Термін придатності')
                    )
                    
                    db.session.add(logistics_item)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    error_details.append({
                        'row': index + 2,  # +2 because Excel is 1-indexed and has a header
                        'sku': sku if 'sku' in locals() else 'Невідомо',
                        'message': str(e)
                    })
            
            # Commit all successful additions
            db.session.commit()
            
            # Prepare results summary
            results = {
                'total': total_rows,
                'success': success_count,
                'duplicates': duplicate_count,
                'errors': error_count,
                'error_details': error_details
            }
            
            # Log the action
            log_action(current_user.id, f"Імпортовано логістичні дані з Excel", 
                      f"Всього: {total_rows}, Успішно: {success_count}, Дублікати: {duplicate_count}, Помилки: {error_count}")
            
            if success_count > 0:
                flash(f'Успішно імпортовано {success_count} записів!', 'success')
            else:
                flash('Не вдалося імпортувати жодного запису.', 'warning')
                
        except Exception as e:
            flash(f'Помилка при обробці файлу: {str(e)}', 'danger')
        finally:
            # Clean up the temporary file
            os.close(fd)
            os.unlink(temp_path)
    
    return render_template('logistics/import.html', form=form, results=results, title='Імпорт логістичних даних')



# Audit logs route
@app.route('/audit_logs')
@login_required
@position_required(FULL_ACCESS_POSITIONS)
@auto_log('Перегляд журналу дій', lambda result: f"Фільтри: {request.args}" if request.args else "Повний журнал")
def audit_logs():
    # Отримання параметрів фільтрації
    page = request.args.get('page', 1, type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    user_id = request.args.get('user_id', '')
    action_type = request.args.get('action', '')
    export = request.args.get('export', '')
    
    # Базовий запит
    query = AuditLog.query
    
    # Застосування фільтрів
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= date_from)
        except ValueError:
            flash('Невірний формат дати початку', 'danger')
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            # Додаємо 1 день, щоб включити весь день до фільтру
            date_to = date_to + timedelta(days=1)
            query = query.filter(AuditLog.timestamp <= date_to)
        except ValueError:
            flash('Невірний формат дати кінця', 'danger')
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action_type:
        query = query.filter(AuditLog.action == action_type)
    
    # Сортування за датою (спочатку найновіші)
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Отримання унікальних типів дій для фільтра
    action_types = db.session.query(AuditLog.action).distinct().all()
    action_types = [action[0] for action in action_types]
    
    # Отримання списку користувачів для фільтра
    users = User.query.all()
    
    # Експорт в CSV
    if export == 'csv':
        return export_logs_to_csv(query)
    
    # Пагінація результатів
    logs = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('audit_logs.html', logs=logs, users=users, action_types=action_types, title='Журнал дій користувачів')

# Функція для експорту журналу дій в CSV
@auto_log('Експорт журналу дій в CSV', lambda result: f"Експортовано {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
def export_logs_to_csv(query):
    logs = query.all()
    
    # Створення CSV в пам'яті
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(['Дата та час', 'Користувач', 'Посада', 'Дія', 'Деталі'])
    
    # Дані
    for log in logs:
        position_name = log.user.position.name if log.user.position else '-'
        writer.writerow([
            log.timestamp.strftime('%d.%m.%Y %H:%M:%S'),
            log.user.username,
            position_name,
            log.action,
            log.details or '-'
        ])
    
    # Підготовка відповіді
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response


# Function to log user actions
from utils.audit_logger import log_action, auto_log

# Initialize the database
@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    
    # Create default positions if they don't exist
    positions = [
        {'name': 'Приймальник', 'description': 'Access only to receiving goods'},
        {'name': 'Комплектувальник', 'description': 'Access only to order picking'},
        {'name': 'Оператор', 'description': 'Full access'},
        {'name': 'Начальник зміни', 'description': 'Full access'},
        {'name': 'Керівник', 'description': 'Full access'},
        {'name': 'Менеджер з закупівель', 'description': 'Access to stock and order reports'},
        {'name': 'Аналітик', 'description': 'Access to stock and order reports'}
    ]
    
    for pos in positions:
        if not Position.query.filter_by(name=pos['name']).first():
            position = Position(name=pos['name'], description=pos['description'])
            db.session.add(position)
    
    db.session.commit()
    print('Initialized the database with default positions.')
    
# Context processor to make positions available in templates
@app.context_processor
def inject_positions():
    return {'positions': Position.query.all()}
    

# Create admin user command
@app.cli.command('create-admin')
def create_admin_command():
    username = input('Admin username: ')
    password = input('Admin password: ')
    
    admin = User(username=username, is_admin=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print('Admin user created successfully.')

# Error handlers
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# Main entry point
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
