from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.storage import StorageLocation, SkuPickingLocation
from forms.picking_location import SkuPickingLocationForm

picking_location_bp = Blueprint('picking_location', __name__)

@picking_location_bp.route('/assign-picking', methods=['GET', 'POST'])
@login_required
def assign_picking_location():
    form = SkuPickingLocationForm()
    
    form.location_code.choices = [
        (loc.location_code, loc.location_code)
        for loc in StorageLocation.query.filter_by(level='1', location_type='picking').all()
    ]

    if form.validate_on_submit():
        # Get the location by code
        location = StorageLocation.query.filter_by(location_code=form.location_code.data).first()
        
        if not location:
            flash(f'Location with code {form.location_code.data} does not exist', 'danger')
            return render_template('picking_location.py/assign_picking.html', form=form)
        
        # Check if the SKU already has an assigned picking location
        existing_assignment = SkuPickingLocation.query.filter_by(sku=form.sku.data).first()
        
        if existing_assignment:
            # Update existing assignment
            existing_assignment.picking_location_id = location.id
            db.session.commit()
            flash(f'Updated picking location for SKU {form.sku.data} to {form.location_code.data}', 'success')
        else:
            # Create new assignment
            new_assignment = SkuPickingLocation(
                sku=form.sku.data,
                picking_location_id=location.id
            )
            db.session.add(new_assignment)
            db.session.commit()
            flash(f'Assigned picking location {form.location_code.data} to SKU {form.sku.data}', 'success')
        
        # Redirect back to the form
        return redirect(url_for('picking_location.assign_picking_location'))
    
    # Get all current assignments for display
    assignments = db.session.query(
        SkuPickingLocation, StorageLocation
    ).join(
        StorageLocation, SkuPickingLocation.picking_location_id == StorageLocation.id
    ).all()
    
    return render_template('picking_location.py/assign_picking.html', form=form, assignments=assignments)