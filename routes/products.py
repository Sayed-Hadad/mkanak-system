from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models.product import Product
from models.category import Category
from forms.product_forms import ProductForm
from models import db
from routes.auth import admin_required
import random, string
try:
    import barcode
    from barcode.writer import ImageWriter
except ImportError:
    barcode = None

products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/')
@login_required
def list_products():
    products = Product.query.all()
    return render_template('products/list.html', title='المنتجات', products=products)

@products_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    form = ProductForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        import random, string
        try:
            import barcode
            from barcode.writer import ImageWriter
        except ImportError:
            barcode = None
        # توليد باركود رقمي فقط
        barcode_val = ''.join(random.choices(string.digits, k=12))
        product = Product(
            name=form.name.data,
            category_id=form.category.data,
            quantity=form.quantity.data,
            price=form.price.data,
            barcode=barcode_val
        )
        db.session.add(product)
        db.session.commit()
        # توليد صورة باركود إذا كانت المكتبة متوفرة
        if barcode:
            try:
                writer_options = {'module_width': 0.2, 'module_height': 15.0, 'font_size': 14, 'text_distance': 2, 'quiet_zone': 2, 'write_text': False}
                ean = barcode.get('code128', barcode_val, writer=ImageWriter())
                barcode_path = f'static/barcodes/{barcode_val}'
                ean.save(barcode_path, options=writer_options)
            except Exception as e:
                flash(f'فشل توليد صورة الباركود: {e}', 'warning')
        flash('تمت إضافة المنتج بنجاح', 'success')
        return redirect(url_for('products.list_products'))
    return render_template('products/add.html', title='إضافة منتج جديد', form=form)

@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        product.name = form.name.data
        product.category_id = form.category.data
        product.quantity = form.quantity.data
        product.price = form.price.data
        db.session.commit()
        flash('تم تعديل المنتج بنجاح', 'success')
        return redirect(url_for('products.list_products'))
    return render_template('products/edit.html', title='تعديل منتج', form=form)

@products_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    # التحقق من وجود حركات مرتبطة بالمنتج
    from models.movement import ProductMovement
    has_movements = ProductMovement.query.filter_by(product_id=product_id).count() > 0
    # التحقق من وجود فواتير بيع مرتبطة بالمنتج
    from models.sale import SaleItem
    has_sales = SaleItem.query.filter_by(product_id=product_id).count() > 0

    if has_movements:
        flash('لا يمكن حذف المنتج لوجود حركات مرتبطة به!', 'danger')
    elif has_sales:
        flash('لا يمكن حذف المنتج لوجود فواتير بيع مرتبطة به!', 'danger')
    else:
        db.session.delete(product)
        db.session.commit()
        flash('تم حذف المنتج بنجاح', 'success')

    return redirect(url_for('products.list_products'))

@products_bp.route('/api/add', methods=['POST'])
def api_add_product():
    data = request.json or {}
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    price = data.get('price')
    quantity = data.get('quantity')
    barcode_val = data.get('barcode')
    if not name or not category_id or not price or not quantity:
        return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'}), 400
    try:
        price = float(price)
        quantity = int(quantity)
    except Exception:
        return jsonify({'success': False, 'message': 'السعر والكمية يجب أن يكونا أرقاماً'}), 400
    existing = Product.query.filter_by(name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'المنتج موجود بالفعل', 'id': existing.id, 'name': existing.name}), 200
    # توليد باركود تلقائي إذا لم يتم إدخاله
    if not barcode_val:
        barcode_val = 'MK' + ''.join(random.choices(string.digits, k=10))
    product = Product(name=name, category_id=category_id, price=price, quantity=quantity, barcode=barcode_val)
    db.session.add(product)
    db.session.commit()
    # توليد صورة باركود إذا كانت المكتبة متوفرة
    if barcode:
        try:
            ean = barcode.get('code128', barcode_val, writer=ImageWriter())
            ean.save(f'static/barcodes/{barcode_val}')
        except Exception as e:
            pass
    return jsonify({'success': True, 'id': product.id, 'name': product.name, 'barcode': product.barcode}), 201

@products_bp.route('/api/list', methods=['GET'])
def api_list_products():
    products = Product.query.order_by(Product.name).all()
    return jsonify([{'id': p.id, 'name': p.name} for p in products])

@products_bp.route('/print_barcode/<int:product_id>')
@login_required
@admin_required
def print_barcode(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('products/print_barcode.html', product=product)