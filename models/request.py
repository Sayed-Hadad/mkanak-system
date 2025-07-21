from models import db
from datetime import datetime

# نموذج طلبات المنتجات بين الفروع
class ProductRequest(db.Model):
    __tablename__ = 'product_requests'
    id = db.Column(db.Integer, primary_key=True)

    # بيانات الطلب
    requesting_branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    # مصدر الطلب (مخزن مركزي أو فرع آخر)
    source_type = db.Column(db.String(20), nullable=False)  # 'warehouse' or 'branch'
    source_id = db.Column(db.Integer, nullable=True)  # معرف الفرع أو المخزن

    # حالة الطلب
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, accepted, rejected, delivered

    # بيانات الطلب
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)

    # بيانات الاستجابة
    responded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    response_notes = db.Column(db.String(255), nullable=True)

    # ملاحظات الطلب
    request_notes = db.Column(db.String(255), nullable=True)

    # العلاقات
    requesting_branch = db.relationship('Branch', foreign_keys=[requesting_branch_id], backref='outgoing_requests')
    product = db.relationship('Product', backref='requests')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='sent_requests')
    responder = db.relationship('User', foreign_keys=[responded_by], backref='responded_requests')

    def get_status_display(self):
        status_map = {
            'pending': 'قيد الانتظار',
            'accepted': 'مقبول',
            'rejected': 'مرفوض',
            'delivered': 'تم التوصيل'
        }
        return status_map.get(self.status, self.status)

    def get_status_badge_class(self):
        status_classes = {
            'pending': 'warning',
            'accepted': 'success',
            'rejected': 'danger',
            'delivered': 'info'
        }
        return status_classes.get(self.status, 'secondary')

    def can_be_cancelled(self):
        return self.status == 'pending'

    def can_be_responded(self):
        return self.status == 'pending'