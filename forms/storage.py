from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from models.storage import StorageRow, StorageLocation

"""
Модуль форм для роботи зі складськими приміщеннями
Містить класи форм для створення та редагування інформації про складські ряди, локації та місця зберігання товарів
"""

class StorageRowForm(FlaskForm):
    """
    Форма для створення та редагування рядів складу
    
    Дозволяє вводити та редагувати інформацію про ряди складу,
    включаючи код, назву, температурний режим та тип зберігання
    """
    code = StringField('Код ряду', validators=[DataRequired(), Length(min=1, max=10)])
    name = StringField('Назва ряду', validators=[DataRequired(), Length(min=1, max=100)])
    temperature_min = FloatField('Мінімальна температура (°C)', validators=[DataRequired()])
    temperature_max = FloatField('Максимальна температура (°C)', validators=[DataRequired()])
    storage_type = SelectField('Тип зберігання', 
                             choices=[
                                 ('ambient', 'Ambient (15-25°C)'),
                                 ('chilled', 'Chilled (2-8°C)'),
                                 ('frozen', 'Frozen (-20°C)')
                             ],
                             validators=[DataRequired()])
    submit = SubmitField('Зберегти')

class StorageLocationForm(FlaskForm):
    """
    Форма для створення та редагування локацій зберігання
    
    Дозволяє вводити та редагувати інформацію про конкретні місця зберігання,
    включаючи ряд, комірку, рівень та тип локації
    """
    row_code = SelectField('Ряд зберігання', validators=[DataRequired()])
    cell = StringField('Номер комірки', validators=[DataRequired(), Length(min=1, max=10)])
    level = SelectField('Поверх', 
                      choices=[
                          ('01', '01 - Місце відбору'),
                          ('02', '02 - Level 2'),
                          ('03', '03 - Level 3'),
                          ('04', '04 - Level 4')
                      ],
                      validators=[DataRequired()])
    location_type = SelectField('Тип зберігання',
                              choices=[
                                  ('picking', 'Відбір'),
                                  ('storage', 'Зберігання'),
                                  ('receiving', 'Приймання'),
                                  ('shipping', 'Вивантаження')
                              ],
                              validators=[DataRequired()])
    description = TextAreaField('Опис', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Зберегти')
    
    def __init__(self, *args, **kwargs):
        """
        Ініціалізація форми з динамічним заповненням списку рядів складу
        
        Автоматично заповнює випадаючий список рядів складу на основі даних з бази даних
        """
        super(StorageLocationForm, self).__init__(*args, **kwargs)
        # Заповнюємо варіанти вибору для коду ряду
        self.row_code.choices = [(row.code, f"{row.code} - {row.name} ({row.storage_type})") 
                               for row in StorageRow.query.order_by(StorageRow.code).all()]

class SkuPickingLocationForm(FlaskForm):
    """
    Форма для призначення місця комплектації для товару
    
    Дозволяє призначати конкретні локації комплектації для товарів за їх артикулом
    """
    sku = StringField('SKU', validators=[DataRequired(), Length(min=1, max=50)])
    picking_location_id = SelectField('Picking Location', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save')
    
    def __init__(self, *args, **kwargs):
        """
        Ініціалізація форми з динамічним заповненням списку локацій комплектації
        
        Автоматично заповнює випадаючий список локацій комплектації на основі даних з бази даних
        """
        super(SkuPickingLocationForm, self).__init__(*args, **kwargs)
        self.picking_location_id.choices = [
            (loc.id, f"{loc.location_code} - {loc.row.name if loc.row else ''}")
            for loc in StorageLocation.query
                .filter(StorageLocation.level.in_(['1', '01']), StorageLocation.location_type == 'picking')
                .order_by(StorageLocation.location_code)
                .all()
        ]
