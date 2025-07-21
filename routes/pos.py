from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from models.product import Product
from models.branch import Branch
from models.sale import Sale, SaleItem
from models import db
from models.movement import ProductMovement
from datetime import datetime

pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

@pos_bp.route('/')
@login_required
def pos_home():
    # يسمح فقط لموظفي ومديري الفروع بالدخول
    if not current_user.is_branch_user():
        flash('غير مصرح لك باستخدام نقطة البيع إلا لموظفي الفروع.', 'danger')
        return redirect(url_for('dashboard'))
    # حساب ملخص مبيعات اليوم
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    branch = current_user.branch
    sales_today = Sale.query.filter(
        Sale.branch_id == branch.id,
        Sale.created_at >= today,
        Sale.created_at < tomorrow
    ).all()
    total_sales = sum(s.total_amount for s in sales_today)
    total_paid = sum(s.paid_amount for s in sales_today)
    total_discount = sum(s.discount for s in sales_today)
    sales_count = len(sales_today)
    return render_template('pos/pos.html', title='نقطة البيع (POS)',
                          total_sales=total_sales, total_paid=total_paid, total_discount=total_discount, sales_count=sales_count)

@pos_bp.route('/api/products')
@login_required
def api_branch_products():
    if not current_user.is_branch_user():
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    branch = current_user.branch
    products = Product.query.all()
    result = []
    for p in products:
        qty = branch.get_product_quantity(p.id)
        if qty > 0:
            result.append({
                'id': p.id,
                'name': p.name,
                'barcode': getattr(p, 'barcode', ''),
                'price': p.price,
                'quantity': qty
            })
    return jsonify(result)

@pos_bp.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    if not current_user.is_branch_user():
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    branch = current_user.branch
    data = request.json or {}
    items = data.get('items', [])
    discount = float(data.get('discount', 0))
    paid = float(data.get('paid', 0))
    if not items:
        return jsonify({'success': False, 'message': 'السلة فارغة'}), 400
    # تحقق من الكميات
    for item in items:
        product_id = item.get('id')
        qty = int(item.get('quantity', 0))
        if qty < 1:
            return jsonify({'success': False, 'message': 'كمية غير صحيحة'}), 400
        available = branch.get_product_quantity(product_id)
        if qty > available:
            return jsonify({'success': False, 'message': f'الكمية غير متوفرة للمنتج (ID: {product_id})'}), 400
    # تسجيل البيع وخصم الكميات
    total = sum(float(item['price']) * int(item['quantity']) for item in items)
    customer_name = data.get('customer_name', '').strip()
    customer_phone = data.get('customer_phone', '').strip()
    customer_obj = None
    if customer_phone:
        from models.customer import Customer
        customer_obj = Customer.query.filter(Customer.phone == customer_phone).first()
    elif customer_name:
        from models.customer import Customer
        customer_obj = Customer.query.filter(Customer.name == customer_name).first()
    if not customer_obj and (customer_name or customer_phone):
        customer_obj = Customer(name=customer_name or None, phone=customer_phone or None)
        db.session.add(customer_obj)
        db.session.flush()
    sale = Sale(branch_id=branch.id, user_id=current_user.id, total_amount=total, paid_amount=paid, discount=discount, customer_id=customer_obj.id if customer_obj else None)
    db.session.add(sale)
    for item in items:
        sale_item = SaleItem(
            sale=sale,
            product_id=item['id'],
            quantity=int(item['quantity']),
            unit_price=float(item['price']),
            total_price=float(item['price']) * int(item['quantity'])
        )
        db.session.add(sale_item)
        # تسجيل حركة خروج من الفرع
        movement = ProductMovement(
            product_id=item['id'],
            user_id=current_user.id,
            shift='morning',
            type='out',
            quantity=int(item['quantity']),
            notes='بيع عبر نقطة البيع',
            timestamp=datetime.utcnow(),
            source_type='branch',
            source_id=branch.id,
            destination_type='customer',
            destination_id=None
        )
        db.session.add(movement)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تمت عملية البيع بنجاح'})

@pos_bp.route('/sales')
@login_required
def sales_list():
    if not current_user.is_branch_user():
        flash('غير مصرح لك بالوصول إلى الفواتير إلا لموظفي الفروع.', 'danger')
        return redirect(url_for('dashboard'))
    branch = current_user.branch
    sales = Sale.query.filter_by(branch_id=branch.id).order_by(Sale.created_at.desc()).all()
    return render_template('pos/sales_list.html', sales=sales, branch=branch)

@pos_bp.route('/sales/<int:sale_id>')
@login_required
def sale_detail(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    if not current_user.is_admin() and (not current_user.is_branch_user() or sale.branch_id != current_user.branch_id):
        flash('غير مصرح لك بعرض هذه الفاتورة.', 'danger')
        return redirect(url_for('pos.sales_list'))
    return render_template('pos/sale_detail.html', sale=sale)