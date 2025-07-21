from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

# نموذج المستخدم
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # admin, user, branch_manager, branch_employee
    shift = db.Column(db.String(10), nullable=True)  # morning or evening
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)  # الفرع المرتبط به
    full_name = db.Column(db.String(128), nullable=True)  # الاسم الكامل
    phone = db.Column(db.String(20), nullable=True)  # رقم الهاتف
    is_active = db.Column(db.Boolean, default=True)  # حالة الحساب
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # العلاقات
    branch = db.relationship('Branch', backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_branch_manager(self):
        return self.role == 'branch_manager'

    def is_branch_employee(self):
        return self.role == 'branch_employee'

    def is_branch_user(self):
        return self.role in ['branch_manager', 'branch_employee']

    def can_manage_branch(self):
        return self.is_admin() or self.is_branch_manager()

    def get_branch_name(self):
        return self.branch.name if self.branch else 'غير محدد'