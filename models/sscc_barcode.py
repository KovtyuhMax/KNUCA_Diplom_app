from extensions import db
from datetime import datetime

class SSCCBarcode(db.Model):
    __tablename__ = 'sscc_barcode'
    id = db.Column(db.Integer, primary_key=True)
    sscc = db.Column(db.String(30), unique=True, nullable=False)
    gross_weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SSCCBarcode {self.sscc}>'