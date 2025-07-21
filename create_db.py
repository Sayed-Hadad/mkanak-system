from app import app, db
from models.user import User
from models.product import Product, Category
from models.branch import Branch, Dealer
from models.movement import ProductMovement, ProductRequest, BranchNotification, BranchInventory

def create_database():
    with app.app_context():
        # حذف جميع الجداول الموجودة
        db.drop_all()
        print("تم حذف قاعدة البيانات القديمة")

        # إنشاء جميع الجداول
        db.create_all()
        print("تم إنشاء قاعدة البيانات الجديدة")

        # إنشاء مستخدم admin افتراضي
        admin_user = User(
            username='admin',
            email='admin@mkanak.com',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)

        # إنشاء فروع افتراضية
        branches = [
            Branch(name='المخزن المركزي', location='القاهرة', phone='01000000000'),
            Branch(name='فرع عبد العزيز', location='الإسكندرية', phone='01000000001'),
            Branch(name='فرع محمد علي', location='الجيزة', phone='01000000002')
        ]

        for branch in branches:
            db.session.add(branch)

        # إنشاء فئات افتراضية
        categories = [
            Category(name='إلكترونيات'),
            Category(name='ملابس'),
            Category(name='أثاث'),
            Category(name='كتب')
        ]

        for category in categories:
            db.session.add(category)

        # إنشاء تجار افتراضيين
        dealers = [
            Dealer(name='شركة التقنية المتقدمة', phone='01000000003', email='tech@example.com'),
            Dealer(name='مؤسسة الأزياء العالمية', phone='01000000004', email='fashion@example.com'),
            Dealer(name='شركة الأثاث الحديث', phone='01000000005', email='furniture@example.com')
        ]

        for dealer in dealers:
            db.session.add(dealer)

        # حفظ التغييرات
        db.session.commit()
        print("تم إضافة البيانات الافتراضية")
        print("بيانات تسجيل الدخول:")
        print("اسم المستخدم: admin")
        print("كلمة المرور: admin123")

if __name__ == '__main__':
    create_database()