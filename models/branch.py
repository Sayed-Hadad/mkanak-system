from models import db

# نموذج الفرع
class Branch(db.Model):
    __tablename__ = 'branches'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    manager = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<Branch {self.name}>'

    def get_product_quantity(self, product_id):
        """الحصول على كمية منتج معين في هذا الفرع"""
        from models.movement import ProductMovement

        # حساب الكمية من حركات المنتج
        incoming = db.session.query(db.func.sum(ProductMovement.quantity)).filter(
            ProductMovement.destination_id == self.id,
            ProductMovement.destination_type == 'branch',
            ProductMovement.product_id == product_id
        ).scalar() or 0

        outgoing = db.session.query(db.func.sum(ProductMovement.quantity)).filter(
            ProductMovement.source_id == self.id,
            ProductMovement.source_type == 'branch',
            ProductMovement.product_id == product_id
        ).scalar() or 0

        return incoming - outgoing

    def get_all_products_with_quantities(self):
        """الحصول على جميع المنتجات مع كمياتها في هذا الفرع"""
        from models.product import Product

        products = Product.query.all()
        branch_products = []

        for product in products:
            quantity = self.get_product_quantity(product.id)
            if quantity > 0:  # عرض المنتجات التي لها كمية فقط
                branch_products.append({
                    'product': product,
                    'quantity': quantity
                })

        return branch_products

    def get_total_stock_value(self):
        """حساب إجمالي قيمة المخزون في الفرع"""
        branch_products = self.get_all_products_with_quantities()
        total_value = sum(item['product'].price * item['quantity'] for item in branch_products)
        return total_value

    def get_movements_stats(self):
        """إحصائيات حركات المنتجات للفرع"""
        from datetime import datetime, timedelta
        from models.movement import ProductMovement

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # حركات اليوم
        today_movements = db.session.query(ProductMovement).filter(
            ProductMovement.destination_id == self.id,
            ProductMovement.destination_type == 'branch',
            db.func.date(ProductMovement.timestamp) == today
        ).count()

        # حركات الأسبوع
        week_movements = db.session.query(ProductMovement).filter(
            ProductMovement.destination_id == self.id,
            ProductMovement.destination_type == 'branch',
            ProductMovement.timestamp >= week_ago
        ).count()

        # حركات الشهر
        month_movements = db.session.query(ProductMovement).filter(
            ProductMovement.destination_id == self.id,
            ProductMovement.destination_type == 'branch',
            ProductMovement.timestamp >= month_ago
        ).count()

        return {
            'today': today_movements,
            'week': week_movements,
            'month': month_movements
        }

    def remove_product(self, product_id, quantity, user_id, notes=""):
        """حذف منتج من الفرع (إخراج كمية معينة)"""
        from models.movement import ProductMovement
        from datetime import datetime

        # التحقق من توفر الكمية
        available_quantity = self.get_product_quantity(product_id)
        if available_quantity < quantity:
            raise ValueError(f"الكمية المتوفرة ({available_quantity}) أقل من الكمية المطلوبة ({quantity})")

        # إنشاء حركة إخراج
        movement = ProductMovement(
            product_id=product_id,
            user_id=user_id,
            shift='morning',  # يمكن تعديلها حسب الحاجة
            type='out',
            quantity=quantity,
            notes=f"حذف من الفرع: {notes}" if notes else "حذف من الفرع",
            timestamp=datetime.utcnow(),
            source_type='branch',
            source_id=self.id,
            destination_type='warehouse',  # إرجاع للمخزن الرئيسي
            destination_id=None
        )

        return movement