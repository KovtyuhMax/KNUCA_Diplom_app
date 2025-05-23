from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired, ValidationError
from models.storage import StorageLocation, SkuPickingLocation

"""
Модуль форм для роботи з локаціями комплектації
Містить класи форм для призначення місць комплектації для товарів
"""

class SkuPickingLocationForm(FlaskForm):
    """
    Форма для призначення локації комплектації для товару
    
    Дозволяє вказати артикул товару та код локації для комплектації,
    з перевіркою існування локації та її відповідності вимогам комплектації
    """
    sku = StringField('SKU', validators=[DataRequired()])
    location_code = StringField('Location Code (e.g. A-1-1)', validators=[DataRequired()])
    submit = SubmitField('Assign Location')
    
    def validate_location_code(self, field):
        """
        Перевірка валідності коду локації
        
        Перевіряє, чи існує локація з вказаним кодом та чи є вона локацією комплектації
        
        Args:
            field: Поле з кодом локації для перевірки
            
        Raises:
            ValidationError: Якщо локація не існує або не є локацією комплектації
        """
        # Перевіряємо, чи існує локація
        location = StorageLocation.query.filter_by(location_code=field.data).first()
        if not location:
            raise ValidationError(f'Location with code {field.data} does not exist')
        
        # Перевіряємо, чи локація є локацією комплектації (рівень 01)
        if location.level != '01':
            raise ValidationError(f'Location {field.data} is not a picking location (level 01)')