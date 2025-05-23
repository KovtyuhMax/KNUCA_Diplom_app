from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SelectField, SubmitField, FieldList, FormField, Form
from wtforms.validators import DataRequired, NumberRange, Length

"""
Модуль форм для роботи з замовленнями клієнтів
Містить класи форм для створення та редагування замовлень та їх позицій
"""

class OrderItemSubForm(Form):
    """
    Підформа для позицій замовлення
    
    Використовується як частина форми замовлення для введення інформації
    про окремі товари, що входять до замовлення
    """
    sku = StringField('Артикул', validators=[DataRequired()])
    product_name = StringField('Назва товару', validators=[DataRequired()])
    quantity = IntegerField('Кількість', validators=[DataRequired(), NumberRange(min=1)])
    unit_price = FloatField('Ціна', validators=[DataRequired(), NumberRange(min=0.01)])

class CustomerOrderForm(FlaskForm):
    """
    Форма для створення та редагування замовлень клієнтів
    
    Дозволяє вибрати клієнта та додати список товарів до замовлення
    з можливістю динамічного додавання позицій
    """
    customer_id = SelectField('Клієнт', coerce=int, validators=[DataRequired()])
    items = FieldList(FormField(OrderItemSubForm), min_entries=1, max_entries=50)
    submit = SubmitField('Створити замовлення')