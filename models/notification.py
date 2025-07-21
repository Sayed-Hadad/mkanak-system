from models import db
from datetime import datetime

# نموذج إشعارات الفروع
class BranchNotification(db.Model):
    __tablename__ = 'branch_notifications'
    id = db.Column(db.Integer, primary_key=True)

    # بيانات الإشعار
    from_branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    to_branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)

    # نوع الإشعار
    notification_type = db.Column(db.String(50), nullable=False)  # low_stock, request, delivery, etc.

    # محتوى الإشعار
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # حالة الإشعار
    is_read = db.Column(db.Boolean, default=False)
    is_urgent = db.Column(db.Boolean, default=False)

    # بيانات الإشعار
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

    # العلاقات
    from_branch = db.relationship('Branch', foreign_keys=[from_branch_id], backref='sent_notifications')
    to_branch = db.relationship('Branch', foreign_keys=[to_branch_id], backref='received_notifications')
    product = db.relationship('Product', backref='notifications')
    creator = db.relationship('User', backref='created_notifications')

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def get_notification_icon(self):
        icon_map = {
            'low_stock': 'bi-exclamation-triangle',
            'request': 'bi-cart-plus',
            'delivery': 'bi-truck',
            'urgent': 'bi-exclamation-circle',
            'info': 'bi-info-circle'
        }
        return icon_map.get(self.notification_type, 'bi-bell')

    def get_notification_class(self):
        class_map = {
            'low_stock': 'warning',
            'request': 'info',
            'delivery': 'success',
            'urgent': 'danger',
            'info': 'primary'
        }
        return class_map.get(self.notification_type, 'secondary')