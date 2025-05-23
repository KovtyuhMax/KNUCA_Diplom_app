from functools import wraps
from flask import redirect, url_for, request, render_template, flash
from flask_login import current_user

def position_required(positions):
    """Decorator to restrict access based on user position"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            if not current_user.has_access(positions):
                flash('У вас немає доступу до цієї сторінки', 'danger')
                return render_template('errors/403.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator