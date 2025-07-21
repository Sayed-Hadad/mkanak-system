from models import db
from datetime import datetime

# نموذج حركة المنتج المتقدم
class ProductMovement(db.Model):
    __tablename__ = 'product_movements'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shift = db.Column(db.String(10), nullable=False)  # morning/evening
    type = db.Column(db.String(10), nullable=False)  # in/out/transfer
    quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.String(255))
    # الحقول الجديدة لدعم من/إلى
    source_type = db.Column(db.String(20), nullable=False)  # warehouse/branch/dealer
    source_id = db.Column(db.Integer, nullable=True)
    destination_type = db.Column(db.String(20), nullable=False)  # warehouse/branch/dealer
    destination_id = db.Column(db.Integer, nullable=True)

    product = db.relationship('Product', backref='movements')
    user = db.relationship('User', backref='movements')