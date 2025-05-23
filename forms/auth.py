from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import User

"""
Модуль форм автентифікації та реєстрації користувачів
Містить класи форм для входу в систему та реєстрації нових користувачів
"""

class LoginForm(FlaskForm):
    """
    Форма входу в систему
    Використовується для автентифікації користувачів у системі
    """
    username = StringField('Логін', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    """
    Форма реєстрації нових користувачів
    Дозволяє створювати нові облікові записи з перевіркою унікальності імені користувача
    """
    username = StringField('Логін', validators=[DataRequired(), Length(min=3, max=64)])
    full_name = StringField('ПІБ', validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Підтвердження паролю', validators=[DataRequired(), EqualTo('password')])
    position_id = SelectField('Посада', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Зареєструватись')
    
    def validate_username(self, username):
        """
        Перевірка валідності імені користувача
        
        Перевіряє, чи ім'я користувача складається лише з цифр та чи є унікальним
        
        Args:
            username: Поле з іменем користувача для перевірки
            
        Raises:
            ValidationError: Якщо ім'я користувача не відповідає вимогам або вже існує
        """
        # Перевірка, чи ім'я користувача містить лише цифри
        if not username.data.isdigit():
            raise ValidationError('Логін має містити лише цифри.')
        # Перевірка, чи ім'я користувача вже існує
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Даний логін вже існує, використайте інший.')