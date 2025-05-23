# Import and export blueprints to avoid circular imports
# Видалено імпорт tsd_bp
from routes.tsd_emulator import tsd_emulator_bp
from routes.validation import validation_bp
from routes.tsd_batch_receiving import tsd_batch_receiving_bp

# Export blueprints to be imported by app.py
__all__ = ['tsd_emulator_bp', 'validation_bp', 'tsd_batch_receiving_bp']