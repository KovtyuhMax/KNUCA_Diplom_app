from datetime import datetime
from models import db

class StorageRow(db.Model):
    __tablename__ = 'storage_row'
    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100))
    temperature_min = db.Column(db.Float, nullable=False)
    temperature_max = db.Column(db.Float, nullable=False)
    storage_type = db.Column(db.String(20), nullable=False)  # 'chilled', 'frozen', 'ambient'
    locations = db.relationship('StorageLocation', backref='row', lazy=True)
    
    def __repr__(self):
        return f'<StorageRow {self.code} ({self.storage_type})>'

class StorageLocation(db.Model):
    __tablename__ = 'storage_location'
    id = db.Column(db.Integer, primary_key=True)
    row_code = db.Column(db.String(10), db.ForeignKey('storage_row.code'), nullable=False)
    cell = db.Column(db.String(10), nullable=False)
    level = db.Column(db.String(10), nullable=False)
    location_code = db.Column(db.String(20), unique=True, nullable=False)  # Auto-generated: {row_code}-{cell}-{level}
    location_type = db.Column(db.String(20), nullable=False)  # 'picking', 'floor', 'upper'
    description = db.Column(db.String(200))
    sku_picking_locations = db.relationship('SkuPickingLocation', backref='location', lazy=True)
    
    def __repr__(self):
        return f'<StorageLocation {self.location_code}>'
    
    def generate_location_code(self):
        return f"{self.row_code}-{self.cell}-{self.level}"
    
    @property
    def name(self):
        """Compatibility property for existing code that uses location.name"""
        return self.location_code
    
    def get_temperature_range(self):
        """Return the temperature range for this location based on its row"""
        if self.row:
            return (self.row.temperature_min, self.row.temperature_max)
        return None
    
    def is_temperature_compatible(self, min_temp, max_temp):
        """Check if an item with the given temperature range is compatible with this location"""
        if not self.row:
            return False
        
        # Check if the item's temperature range overlaps with the location's range
        return not (min_temp > self.row.temperature_max or max_temp < self.row.temperature_min)
    
    def check_item_compatibility(self, item):
        """Check if an inventory item is compatible with this location based on its logistics data"""
        from models import LogisticsItemData
        
        # If the item has no SKU, we can't check compatibility
        if not item or not item.sku:
            return True
        
        # Find the logistics data for this item
        logistics_data = LogisticsItemData.query.filter_by(sku=item.sku).first()
        
        # If no logistics data or no temperature requirements, assume compatible
        if not logistics_data or logistics_data.temperature_range is None:
            return True
        
        # Convert single temperature value to a range (±2°C)
        item_temp = logistics_data.temperature_range
        min_temp = item_temp - 2
        max_temp = item_temp + 2
        
        # Check if the temperature range is compatible
        return self.is_temperature_compatible(min_temp, max_temp)


class SkuPickingLocation(db.Model):
    __tablename__ = 'sku_picking_location'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    picking_location_id = db.Column(db.Integer, db.ForeignKey('storage_location.id'), nullable=False)
    
    def __repr__(self):
        return f'<SkuPickingLocation {self.sku} -> {self.picking_location_id}>'