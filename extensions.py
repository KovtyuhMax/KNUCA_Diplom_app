from flask_sqlalchemy import SQLAlchemy
from utils.decorators import position_required

# Initialize SQLAlchemy instance
db = SQLAlchemy()