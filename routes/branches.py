from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db
from models.branch import Branch
from models.product import Product
from models.movement import ProductMovement
from forms.branch_forms import BranchForm
from routes.auth import admin_required
from datetime import datetime, timedelta

branches_bp = Blueprint('branches', __name__)

@branches_bp.route('/branches')
@login_required
def list_branches():
    branches = Branch.query.all()
    return render_template('branches/list.html', branches=branches)

@branches_bp.route('/branches/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_branch():
    form = BranchForm()
    if form.validate_on_submit():
        branch = Branch(name=form.name.data)
        db.session.add(branch)
        db.session.commit()
        flash('تم إضافة الفرع بنجاح!', 'success')
        return redirect(url_for('branches.list_branches'))
    return render_template('branches/add.html', form=form)

@branches_bp.route('/branches/<int:branch_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_branch(branch_id):
    branch = Branch.query.get_or_404(branch_id)
    form = BranchForm(obj=branch)
    if form.validate_on_submit():
        branch.name = form.name.data
        db.session.commit()
        flash('تم تحديث الفرع بنجاح!', 'success')
        return redirect(url_for('branches.list_branches'))
    return render_template('branches/edit.html', form=form, branch=branch)

@branches_bp.route('/branches/<int:branch_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_branch(branch_id):
    branch = Branch.query.get_or_404(branch_id)

    # التحقق من وجود حركات مرتبطة بالفرع
    has_movements = db.session.query(ProductMovement).filter(
        ((ProductMovement.source_id == branch.id) & (ProductMovement.source_type == 'branch')) |
        ((ProductMovement.destination_id == branch.id) & (ProductMovement.destination_type == 'branch'))
    ).count() > 0

    if has_movements:
        flash('لا يمكن حذف الفرع لوجود حركات مرتبطة به!', 'danger')
    else:
        db.session.delete(branch)
        db.session.commit()
        flash('تم حذف الفرع بنجاح!', 'success')

    return redirect(url_for('branches.list_branches'))

@branches_bp.route('/branches/<int:branch_id>')
@login_required
def branch_details(branch_id):
    branch = Branch.query.get_or_404(branch_id)

    # الحصول على المنتجات في الفرع
    branch_products = branch.get_all_products_with_quantities()

    # إحصائيات الفرع
    total_stock_value = branch.get_total_stock_value()
    movements_stats = branch.get_movements_stats()

    # حركات الفرع الأخيرة
    recent_movements = ProductMovement.query.filter(
        (ProductMovement.source_id == branch.id) |
        (ProductMovement.destination_id == branch.id)
    ).order_by(ProductMovement.timestamp.desc()).limit(10).all()

    # إحصائيات المنتجات الأكثر حركة
    from sqlalchemy import func
    top_products = db.session.query(
        Product.name,
        func.sum(ProductMovement.quantity).label('total_moved')
    ).join(ProductMovement, Product.id == ProductMovement.product_id).filter(
        (ProductMovement.source_id == branch.id) |
        (ProductMovement.destination_id == branch.id)
    ).group_by(Product.id, Product.name).order_by(
        func.sum(ProductMovement.quantity).desc()
    ).limit(5).all()

    return render_template('branches/details.html',
                         branch=branch,
                         branch_products=branch_products,
                         total_stock_value=total_stock_value,
                         movements_stats=movements_stats,
                         recent_movements=recent_movements,
                         top_products=top_products)

@branches_bp.route('/branches/<int:branch_id>/api/products')
@login_required
def branch_products_api(branch_id):
    branch = Branch.query.get_or_404(branch_id)
    branch_products = branch.get_all_products_with_quantities()

    products_data = []
    for item in branch_products:
        products_data.append({
            'id': item['product'].id,
            'name': item['product'].name,
            'category': item['product'].category.name if item['product'].category else 'غير محدد',
            'price': item['product'].price,
            'quantity': item['quantity'],
            'total_value': item['product'].price * item['quantity']
        })

    return jsonify({
        'branch_name': branch.name,
        'products': products_data,
        'total_products': len(products_data),
        'total_value': branch.get_total_stock_value()
    })

@branches_bp.route('/branches/api/list')
@login_required
def api_list_branches():
    branches = Branch.query.order_by(Branch.name).all()
    return jsonify([{'id': b.id, 'name': b.name} for b in branches])

@branches_bp.route('/branches/<int:branch_id>/remove-product', methods=['POST'])
@login_required
@admin_required
def remove_product_from_branch(branch_id):
    """حذف منتج من الفرع"""
    branch = Branch.query.get_or_404(branch_id)

    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        notes = data.get('notes', '')

        if not product_id or not quantity:
            return jsonify({
                'success': False,
                'message': 'معرف المنتج والكمية مطلوبان'
            }), 400

        if quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'يجب أن تكون الكمية أكبر من صفر'
            }), 400

        # التحقق من وجود المنتج
        product = Product.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'message': 'المنتج غير موجود'
            }), 404

        # حذف المنتج من الفرع
        movement = branch.remove_product(product_id, quantity, current_user.id, notes)

        # إضافة الحركة لقاعدة البيانات
        db.session.add(movement)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'تم حذف {quantity} من المنتج "{product.name}" من الفرع "{branch.name}" بنجاح'
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'حدث خطأ أثناء حذف المنتج: {str(e)}'
        }), 500

@branches_bp.route('/branches/<int:branch_id>/remove-product-form', methods=['GET', 'POST'])
@login_required
@admin_required
def remove_product_form(branch_id):
    """نموذج حذف منتج من الفرع"""
    branch = Branch.query.get_or_404(branch_id)

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        quantity = request.form.get('quantity')
        notes = request.form.get('notes', '')

        try:
            quantity = int(quantity)
            if quantity <= 0:
                flash('يجب أن تكون الكمية أكبر من صفر', 'danger')
                return redirect(url_for('branches.branch_details', branch_id=branch_id))

            # حذف المنتج من الفرع
            movement = branch.remove_product(product_id, quantity, current_user.id, notes)

            # إضافة الحركة لقاعدة البيانات
            db.session.add(movement)
            db.session.commit()

            flash(f'تم حذف {quantity} من المنتج من الفرع "{branch.name}" بنجاح', 'success')

        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء حذف المنتج: {str(e)}', 'danger')

        return redirect(url_for('branches.branch_details', branch_id=branch_id))

    # الحصول على المنتجات في الفرع
    branch_products = branch.get_all_products_with_quantities()

    return render_template('branches/remove_product.html',
                         branch=branch,
                         branch_products=branch_products)