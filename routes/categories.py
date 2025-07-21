from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models.category import Category
from forms.category_forms import CategoryForm
from models import db
from routes.auth import admin_required

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')

@categories_bp.route('/')
@login_required
def list_categories():
    categories = Category.query.all()
    return render_template('categories/list.html', title='الأصناف', categories=categories)

@categories_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        existing = Category.query.filter_by(name=form.name.data).first()
        if existing:
            flash('اسم الصنف مستخدم بالفعل', 'danger')
        else:
            category = Category(name=form.name.data)
            db.session.add(category)
            db.session.commit()
            flash('تمت إضافة الصنف بنجاح', 'success')
            return redirect(url_for('categories.list_categories'))
    return render_template('categories/add.html', title='إضافة صنف جديد', form=form)

@categories_bp.route('/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        existing = Category.query.filter(Category.name == form.name.data, Category.id != category.id).first()
        if existing:
            flash('اسم الصنف مستخدم بالفعل', 'danger')
        else:
            category.name = form.name.data
            db.session.commit()
            flash('تم تعديل الصنف بنجاح', 'success')
            return redirect(url_for('categories.list_categories'))
    return render_template('categories/add.html', title='تعديل صنف', form=form, edit=True)

@categories_bp.route('/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)

    # التحقق من وجود منتجات مرتبطة بالصنف
    from models.product import Product
    has_products = Product.query.filter_by(category_id=category_id).count() > 0

    if has_products:
        flash('لا يمكن حذف الصنف لوجود منتجات مرتبطة به!', 'danger')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('تم حذف الصنف بنجاح', 'success')

    return redirect(url_for('categories.list_categories'))

@categories_bp.route('/api/add', methods=['POST'])
def api_add_category():
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'اسم الصنف مطلوب'}), 400
    existing = Category.query.filter_by(name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'الصنف موجود بالفعل', 'id': existing.id, 'name': existing.name}), 200
    category = Category(name=name)
    db.session.add(category)
    db.session.commit()
    return jsonify({'success': True, 'id': category.id, 'name': category.name}), 201

@categories_bp.route('/api/list', methods=['GET'])
def api_list_categories():
    categories = Category.query.order_by(Category.name).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in categories])