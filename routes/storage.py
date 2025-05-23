from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.storage import StorageRow, StorageLocation
from forms.storage import StorageRowForm, StorageLocationForm

storage_bp = Blueprint('storage', __name__)

# API endpoint for temperature information
@storage_bp.route('/api/storage_location/<int:location_id>/temperature')
@login_required
def get_location_temperature(location_id):
    location = StorageLocation.query.get_or_404(location_id)
    if location.row:
        return jsonify({
            'temperature_min': location.row.temperature_min,
            'temperature_max': location.row.temperature_max,
            'storage_type': location.row.storage_type
        })
    return jsonify({}), 404

# Storage Row routes
@storage_bp.route('/rows')
@login_required
def storage_row_list():
    rows = StorageRow.query.order_by(StorageRow.code).all()
    return render_template('storage/row_list.html', rows=rows)

@storage_bp.route('/rows/add', methods=['GET', 'POST'])
@login_required
def storage_row_add():
    form = StorageRowForm()
    if form.validate_on_submit():
        # Check if row with this code already exists
        existing_row = StorageRow.query.filter_by(code=form.code.data).first()
        if existing_row:
            flash(f'Row with code {form.code.data} already exists', 'danger')
            return render_template('storage/row_form.html', form=form, title='Add Storage Row')
        
        row = StorageRow(
            code=form.code.data,
            name=form.name.data,
            temperature_min=form.temperature_min.data,
            temperature_max=form.temperature_max.data,
            storage_type=form.storage_type.data
        )
        db.session.add(row)
        db.session.commit()
        flash('Ряд зберігання додано', 'success')
        return redirect(url_for('storage.storage_row_list'))
    return render_template('storage/row_form.html', form=form, title='Add Storage Row')

@storage_bp.route('/rows/<string:row_code>/edit', methods=['GET', 'POST'])
@login_required
def storage_row_edit(row_code):
    row = StorageRow.query.get_or_404(row_code)
    form = StorageRowForm(obj=row)
    
    if form.validate_on_submit():
        # If code is changed, check if new code already exists
        if form.code.data != row.code:
            existing_row = StorageRow.query.filter_by(code=form.code.data).first()
            if existing_row:
                flash(f'Ряд з кодом {form.code.data} вже існує', 'danger')
                return render_template('storage/row_form.html', form=form, title='Edit Storage Row')
        
        row.code = form.code.data
        row.name = form.name.data
        row.temperature_min = form.temperature_min.data
        row.temperature_max = form.temperature_max.data
        row.storage_type = form.storage_type.data
        db.session.commit()
        flash('Ряд зберігання успішно оновлено', 'success')
        return redirect(url_for('storage.storage_row_list'))
    
    return render_template('storage/row_form.html', form=form, title='Edit Storage Row')

@storage_bp.route('/rows/<string:row_code>/delete', methods=['POST'])
@login_required
def storage_row_delete(row_code):
    row = StorageRow.query.get_or_404(row_code)
    
    # Check if row has any locations
    if row.locations:
        flash(f"Неможливо видалити ряд {row.code} оскільки він має пов'язані місця розташування", 'danger')
        return redirect(url_for('storage.storage_row_list'))
    
    db.session.delete(row)
    db.session.commit()
    flash('Ряд зберігання видалено', 'success')
    return redirect(url_for('storage.storage_row_list'))

# Storage Location routes
@storage_bp.route('/locations')
@login_required
def storage_location_list():
    locations = StorageLocation.query.order_by(StorageLocation.location_code).all()
    return render_template('storage/location_list.html', locations=locations)

@storage_bp.route('/locations/add', methods=['GET', 'POST'])
@login_required
def storage_location_add():
    # Check if there are any rows first
    if StorageRow.query.count() == 0:
        flash('Спочатку потрібно створити принаймні один ряд сховища', 'warning')
        return redirect(url_for('storage.storage_row_add'))
    
    form = StorageLocationForm()
    if form.validate_on_submit():
        # Generate the location code
        location_code = f"{form.row_code.data}-{form.cell.data}-{form.level.data}"
        
        # Check if location with this code already exists
        existing_location = StorageLocation.query.filter_by(location_code=location_code).first()
        if existing_location:
            flash(f'Місце зберігання з кодом {location_code} вже існує', 'danger')
            return render_template('storage/location_form.html', form=form, title='Add Storage Location')
        
        location = StorageLocation(
            row_code=form.row_code.data,
            cell=form.cell.data,
            level=form.level.data,
            location_code=location_code,
            location_type=form.location_type.data,
            description=form.description.data
        )
        db.session.add(location)
        db.session.commit()
        flash('Місце зберігання додано успішно', 'success')
        return redirect(url_for('storage.storage_location_list'))
    
    return render_template('storage/location_form.html', form=form, title='Add Storage Location')

@storage_bp.route('/locations/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
def storage_location_edit(location_id):
    location = StorageLocation.query.get_or_404(location_id)
    form = StorageLocationForm(obj=location)
    
    if form.validate_on_submit():
        # Generate the new location code
        new_location_code = f"{form.row_code.data}-{form.cell.data}-{form.level.data}"
        
        # Check if the code would change and if it would conflict
        if new_location_code != location.location_code:
            existing_location = StorageLocation.query.filter_by(location_code=new_location_code).first()
            if existing_location:
                flash(f'Місце зберігання з кодом {new_location_code} вже існує', 'danger')
                return render_template('storage/location_form.html', form=form, title='Edit Storage Location')
        
        location.row_code = form.row_code.data
        location.cell = form.cell.data
        location.level = form.level.data
        location.location_code = new_location_code
        location.location_type = form.location_type.data
        location.description = form.description.data
        db.session.commit()
        flash('Місце зберігання оновлено', 'success')
        return redirect(url_for('storage.storage_location_list'))
    
    return render_template('storage/location_form.html', form=form, title='Edit Storage Location')

@storage_bp.route('/locations/<int:location_id>/delete', methods=['POST'])
@login_required
def storage_location_delete(location_id):
    location = StorageLocation.query.get_or_404(location_id)
    
    # Check if location has any items
    if location.items:
        flash(f"Неможливо видалити {location.location_code} ,оскільки він має пов'язані елементи", 'danger')
        return redirect(url_for('storage.storage_location_list'))
    
    db.session.delete(location)
    db.session.commit()
    flash('Місце зберігання видалено', 'success')
    return redirect(url_for('storage.storage_location_list'))

# Temperature compatibility check helpers
@storage_bp.route('/locations/check-compatibility')
@login_required
def check_temperature_compatibility():
    location_id = request.args.get('location_id', type=int)
    min_temp = request.args.get('min_temp', type=float)
    max_temp = request.args.get('max_temp', type=float)
    sku = request.args.get('sku', type=str)
    
    # If SKU is provided, check compatibility based on the item's logistics data
    if sku and location_id:
        from models import LogisticsItemData
        # Find the logistics data for this SKU
        logistics_data = LogisticsItemData.query.filter_by(sku=sku).first()
        
        if logistics_data and logistics_data.temperature_range is not None:
            # Convert single temperature value to a range (±2°C)
            item_temp = logistics_data.temperature_range
            min_temp = item_temp - 2
            max_temp = item_temp + 2
            
            location = StorageLocation.query.get_or_404(location_id)
            compatible = location.is_temperature_compatible(min_temp, max_temp)
            
            if compatible:
                message = f'Вимога до температури ({item_temp}°C) сумісна з місцем зберігання {location.location_code}'
            else:
                row_min, row_max = location.get_temperature_range()
                message = f'Вимога до температури ({item_temp}°C) не сумісна з місцем зберігання {location.location_code} ({row_min}°C to {row_max}°C)'
            
            return jsonify({
                'has_temp_requirements': True,
                'compatible': compatible, 
                'message': message
            })
        else:
            # No temperature requirements for this item
            return jsonify({
                'has_temp_requirements': False
            })
    
    # Original functionality - direct temperature range check
    elif all([location_id, min_temp is not None, max_temp is not None]):
        location = StorageLocation.query.get_or_404(location_id)
        compatible = location.is_temperature_compatible(min_temp, max_temp)
        
        if compatible:
            message = f'Температурний режим від ({min_temp}°C до {max_temp}°C) сумісний з місцем розташування {location.location_code}'
        else:
            row_min, row_max = location.get_temperature_range()
            message = f'Температурний режим від ({min_temp}°C до {max_temp}°C) не сумісний з місцем розташування {location.location_code} ({row_min}°C to {row_max}°C)'
        
        return jsonify({
            'has_temp_requirements': True,
            'compatible': compatible, 
            'message': message
        })
    
    return jsonify({'has_temp_requirements': False, 'compatible': False, 'message': 'Missing required parameters'})

# SKU Picking Location routes
@storage_bp.route('/sku-picking-locations')
@login_required
def sku_picking_location_list():
    from models.storage import SkuPickingLocation
    from models import LogisticsItemData
    
    # Get all SKU picking location assignments
    sku_locations = SkuPickingLocation.query.all()
    
    # Get product names for display
    sku_product_names = {}
    for loc in sku_locations:
        logistics_data = LogisticsItemData.query.filter_by(sku=loc.sku).first()
        if logistics_data:
            sku_product_names[loc.sku] = logistics_data.product_name
    
    return render_template('storage/sku_picking_location_list.html', 
                           sku_locations=sku_locations,
                           sku_product_names=sku_product_names,
                           title='SKU Picking Locations')

@storage_bp.route('/sku-picking-locations/add', methods=['GET', 'POST'])
@login_required
def sku_picking_location_add():
    from forms.storage import SkuPickingLocationForm
    from models.storage import SkuPickingLocation
    from models import LogisticsItemData
    
    form = SkuPickingLocationForm()
    
    location_in_use = SkuPickingLocation.query.filter_by(picking_location_id=form.picking_location_id.data).first()


    # Populate SKU dropdown with available SKUs from LogisticsItemData
    skus = LogisticsItemData.query.with_entities(LogisticsItemData.sku, LogisticsItemData.product_name).all()
    
    # Check if location already assigned to another SKU
    location_in_use = SkuPickingLocation.query.filter_by(
        picking_location_id=form.picking_location_id.data
    ).first()

    if location_in_use:
        existing_sku = location_in_use.sku
        flash(f'Комірка вже призначена для SKU {existing_sku}. Виберіть іншу комірку.', 'danger')
        return render_template('storage/sku_picking_location_form.html', form=form, skus=skus, title='Add SKU Picking Location')

    if form.validate_on_submit():
        # Check if SKU already has an assigned picking location
        existing = SkuPickingLocation.query.filter_by(sku=form.sku.data).first()
        if existing:
            flash(f'SKU {form.sku.data} вже має призначене місце відбору', 'danger')
            return render_template('storage/sku_picking_location_form.html', form=form, skus=skus, title='Add SKU Picking Location')
        
        # Create new SKU picking location assignment
        sku_location = SkuPickingLocation(
            sku=form.sku.data,
            picking_location_id=form.picking_location_id.data
        )
        db.session.add(sku_location)
        db.session.commit()
        flash('Місце відбору SKU успішно призначено', 'success')
        return redirect(url_for('storage.sku_picking_location_list'))
    
    return render_template('storage/sku_picking_location_form.html', form=form, skus=skus, title='Add SKU Picking Location')

@storage_bp.route('/sku-picking-locations/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def sku_picking_location_edit(id):
    from forms.storage import SkuPickingLocationForm
    from models.storage import SkuPickingLocation
    from models import LogisticsItemData
    
    sku_location = SkuPickingLocation.query.get_or_404(id)
    form = SkuPickingLocationForm(obj=sku_location)
    

    # Populate SKU dropdown with available SKUs from LogisticsItemData
    skus = LogisticsItemData.query.with_entities(LogisticsItemData.sku, LogisticsItemData.product_name).all()
    
        # Check if the selected location is already assigned to another SKU
    if form.picking_location_id.data != sku_location.picking_location_id:
        location_in_use = SkuPickingLocation.query.filter_by(
            picking_location_id=form.picking_location_id.data
        ).first()
        
        if location_in_use:
            flash(f'Комірка вже призначена для SKU {location_in_use.sku}. Виберіть іншу.', 'danger')
            return render_template('storage/sku_picking_location_form.html', form=form, skus=skus, title='Edit SKU Picking Location')

    if form.validate_on_submit():
        # Check if changing to a SKU that already has an assigned location
        if form.sku.data != sku_location.sku:
            existing = SkuPickingLocation.query.filter_by(sku=form.sku.data).first()
            if existing:
                flash(f'SKU {form.sku.data} вже має призначене місце відбору', 'danger')
                return render_template('storage/sku_picking_location_form.html', form=form, skus=skus, title='Edit SKU Picking Location')
        
        sku_location.sku = form.sku.data
        sku_location.picking_location_id = form.picking_location_id.data
        db.session.commit()
        flash('Місце відбору SKU успішно оновлено', 'success')
        return redirect(url_for('storage.sku_picking_location_list'))
    
    return render_template('storage/sku_picking_location_form.html', form=form, skus=skus, title='Edit SKU Picking Location')

@storage_bp.route('/sku-picking-locations/<int:id>/delete', methods=['POST'])
@login_required
def sku_picking_location_delete(id):
    from models.storage import SkuPickingLocation
    
    sku_location = SkuPickingLocation.query.get_or_404(id)
    db.session.delete(sku_location)
    db.session.commit()
    flash('Призначення місця відбору SKU успішно видалено', 'success')
    return redirect(url_for('storage.sku_picking_location_list'))