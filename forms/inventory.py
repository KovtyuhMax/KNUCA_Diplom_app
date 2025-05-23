from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, SelectField, FloatField, FileField, BooleanField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import DataRequired, Length, NumberRange, Optional

"""
Модуль форм для роботи з інвентаризацією та товарами
Містить класи форм для створення, редагування та імпорту інформації про товари
"""

class ItemForm(FlaskForm):
    """
    Базова форма для роботи з товарами
    
    Дозволяє вводити та редагувати основну інформацію про товари,
    включаючи артикул, назву, опис, кількість та місце зберігання
    """
    sku = StringField('SKU', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    quantity = IntegerField('Quantity', validators=[NumberRange(min=0)])
    min_stock_level = IntegerField('Minimum Stock Level', validators=[NumberRange(min=0)])
    unit_price = FloatField('Unit Price', validators=[NumberRange(min=0)])
    storage_location_id = SelectField('Storage Location', coerce=int)
    submit = SubmitField('Submit')

class LogisticsItemDataForm(FlaskForm):
    """
    Форма для введення логістичних даних товару
    
    Дозволяє вводити та редагувати детальну логістичну інформацію про товари,
    включаючи розміри, тип пакування, умови зберігання та термін придатності
    """
    sku = StringField('Артикул', validators=[DataRequired(), Length(min=1, max=50)])
    product_name = StringField('Назва', validators=[DataRequired(), Length(min=1, max=100)])
    packaging_unit_type = SelectField('Базова Одиниця', 
                                   choices=[('ШТ', 'ШТ (штука)'), ('КГ', 'КГ (кілограм)')], 
                                   validators=[DataRequired()])
    length = FloatField('Довжина', validators=[DataRequired(), NumberRange(min=0)])
    width = FloatField('Ширина', validators=[DataRequired(), NumberRange(min=0)])
    height = FloatField('Висота', validators=[DataRequired(), NumberRange(min=0)])
    dimension_unit = SelectField('Одиниця розміру', 
                              choices=[('СМ', 'СМ (сантиметр)'), ('М', 'М (метр)')], 
                              default='СМ',
                              validators=[DataRequired()])
    count = IntegerField('Кратність', validators=[DataRequired(), NumberRange(min=1)])
    storage_type = SelectField('Тип зберігання', 
                             choices=[('04', '04 - стандартний'), ('06', '06 - дистрибуція')], 
                             validators=[DataRequired()])
    temperature_range = IntegerField('Температура зберігання', validators=[Optional()])
    shelf_life = IntegerField('Термін придатності (днів)', validators=[Optional(), NumberRange(min=1)])
    submit = SubmitField('Зберегти')

class LogisticsImportForm(FlaskForm):
    """
    Форма для імпорту логістичних даних з Excel файлу
    
    Дозволяє завантажувати дані про товари з Excel файлу для масового імпорту
    """
    excel_file = FileField('Excel файл', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Дозволені тільки Excel файли (.xlsx, .xls)')
    ])
    submit = SubmitField('Імпортувати')