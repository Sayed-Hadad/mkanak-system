from models import db
from datetime import datetime

# نموذج مخزون الفروع
class BranchInventory(db.Model):
    __tablename__ = 'branch_inventory'
    id = db.Column(db.Integer, primary_key=True)

    # بيانات المخزون
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)

    # حدود المخزون
    min_quantity = db.Column(db.Integer, nullable=False, default=10)  # الحد الأدنى
    max_quantity = db.Column(db.Integer, nullable=False, default=100)  # الحد الأقصى

    # بيانات التحديث
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # ملاحظات
    notes = db.Column(db.String(255), nullable=True)

    # العلاقات
    branch = db.relationship('Branch', backref='inventory_items')
    product = db.relationship('Product', backref='branch_inventory')
    updater = db.relationship('User', backref='inventory_updates')

    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    def is_out_of_stock(self):
        return self.quantity == 0

    def get_stock_status(self):
        if self.is_out_of_stock():
            return 'out_of_stock'
        elif self.is_low_stock():
            return 'low_stock'
        else:
            return 'normal'

    def get_stock_status_display(self):
        status_map = {
            'out_of_stock': 'نفذ المخزون',
            'low_stock': 'مخزون منخفض',
            'normal': 'مخزون طبيعي'
        }
        return status_map.get(self.get_stock_status(), 'غير محدد')

    def get_stock_status_class(self):
        status_classes = {
            'out_of_stock': 'danger',
            'low_stock': 'warning',
            'normal': 'success'
        }
        return status_classes.get(self.get_stock_status(), 'secondary')

    def update_quantity(self, new_quantity, user_id=None):
        self.quantity = new_quantity
        self.last_updated = datetime.utcnow()
        if user_id:
            self.updated_by = user_id

    def add_quantity(self, amount, user_id=None):
        self.quantity += amount
        self.last_updated = datetime.utcnow()
        if user_id:
            self.updated_by = user_id

    def subtract_quantity(self, amount, user_id=None):
        if self.quantity >= amount:
            self.quantity -= amount
            self.last_updated = datetime.utcnow()
            if user_id:
                self.updated_by = user_id
            return True
        return False