from models import db

# نموذج التاجر
class Dealer(db.Model):
    __tablename__ = 'dealers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(32))
    address = db.Column(db.String(255))
    notes = db.Column(db.String(255))