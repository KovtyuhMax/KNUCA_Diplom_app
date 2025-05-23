from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

"""
Модуль форм для роботи з клієнтами
Містить класи форм для створення та редагування інформації про клієнтів
"""

class CustomerForm(FlaskForm):
    """
    Форма для створення та редагування клієнтів
    
    Дозволяє вводити та зберігати основну інформацію про клієнтів системи,
    включаючи код клієнта, назву та адресу
    """
    code = StringField('Код клієнта', validators=[DataRequired(), Length(min=1, max=20)])
    name = StringField('Назва клієнта', validators=[DataRequired(), Length(min=1, max=100)])
    address = TextAreaField('Адреса', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Зберегти')