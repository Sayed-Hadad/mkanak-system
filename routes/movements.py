from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db
from models.product import Product
from models.category import Category
from models.branch import Branch
from models.dealer import Dealer
from models.movement import ProductMovement
from models.user import User
from forms.movement_forms import MovementForm
from routes.auth import admin_required
from datetime import datetime, timedelta
import pandas as pd
import io
import os
from routes.branch_dashboard import notify_low_stock

movements_bp = Blueprint('movements', __name__, url_prefix='/movements')

# Helper to get display name for source/destination
ENTITY_LABELS = {
    'warehouse': 'المخزن الرئيسي',
    'branch': 'فرع',
    'dealer': 'تاجر',
}

def get_entity_name(entity_type, entity_id):
    if entity_type == 'warehouse':
        return 'المخزن الرئيسي'
    elif entity_type == 'branch':
        branch = Branch.query.get(entity_id)
        return branch.name if branch else 'فرع غير معروف'
    elif entity_type == 'dealer':
        # يمكن لاحقاً ربط جدول تجار
        return f'تاجر رقم {entity_id}'
    return '-'



@movements_bp.route('/')
@login_required
def list_movements():
    # جلب خيارات الفلترة
    products = Product.query.order_by(Product.name).all()
    branches = Branch.query.order_by(Branch.name).all()
    dealers = Dealer.query.order_by(Dealer.name).all()
    users = User.query.order_by(User.username).all()

    # معاملات الفلترة
    product_id = request.args.get('product_id', type=int)
    type_ = request.args.get('type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    branch_id = request.args.get('branch_id', type=int)
    dealer_id = request.args.get('dealer_id', type=int)
    user_id = request.args.get('user_id', type=int)
    shift = request.args.get('shift')
    quantity_less = request.args.get('quantity_less', type=int)

    # بناء الاستعلام
    query = ProductMovement.query

    # تطبيق الفلاتر
    if product_id:
        query = query.filter_by(product_id=product_id)
    if type_:
        query = query.filter_by(type=type_)
    if date_from:
        query = query.filter(ProductMovement.timestamp >= date_from)
    if date_to:
        query = query.filter(ProductMovement.timestamp <= date_to + ' 23:59:59')
    if branch_id:
        query = query.filter(((ProductMovement.source_type == 'branch') & (ProductMovement.source_id == branch_id)) |
                             ((ProductMovement.destination_type == 'branch') & (ProductMovement.destination_id == branch_id)))
    if dealer_id:
        query = query.filter(((ProductMovement.source_type == 'dealer') & (ProductMovement.source_id == dealer_id)) |
                             ((ProductMovement.destination_type == 'dealer') & (ProductMovement.destination_id == dealer_id)))
    if user_id:
        query = query.filter_by(user_id=user_id)
    if shift:
        query = query.filter_by(shift=shift)
    if quantity_less:
        query = query.filter(ProductMovement.quantity < quantity_less)

    # ترتيب النتائج
    movements = query.order_by(ProductMovement.timestamp.desc()).all()

    return render_template('movements/list.html',
                         title='حركة المنتجات',
                         movements=movements,
                         get_entity_name=get_entity_name,
                         ENTITY_LABELS=ENTITY_LABELS,
                         products=products,
                         branches=branches,
                         dealers=dealers,
                         users=users,
                         selected_product_id=product_id,
                         selected_branch_id=branch_id,
                         selected_dealer_id=dealer_id)

@movements_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_movement():
    form = MovementForm()
    # Always set choices for all select fields and subforms
    products = Product.query.all()
    product_choices = [(p.id, p.name) for p in products]
    if not form.products.entries:
        form.products.append_entry()
    for subform in form.products:
        subform.product.choices = product_choices
    branches = Branch.query.all()
    branch_choices = [(b.id, b.name) for b in branches]
    form.source_id.choices = branch_choices
    form.destination_id.choices = branch_choices
    dealers = Dealer.query.all()
    dealer_choices = [(d.id, d.name) for d in dealers]
    form.dealer_source_id.choices = dealer_choices
    form.dealer_destination_id.choices = dealer_choices
    categories = Category.query.all()
    category_choices = [(c.id, c.name) for c in categories]
    form.new_product_category.choices = category_choices
    if request.method == 'POST':
        if form.source_type.data == 'branch':
            form.source_id.choices = branch_choices
        elif form.source_type.data == 'dealer':
            form.dealer_source_id.choices = dealer_choices
        if form.destination_type.data == 'branch':
            form.destination_id.choices = branch_choices
        elif form.destination_type.data == 'dealer':
            form.dealer_destination_id.choices = dealer_choices
        for subform in form.products:
            subform.product.choices = product_choices
    if form.validate_on_submit():
        for subform in form.products.entries:
            product = Product.query.get(subform.product.data)
            qty = subform.quantity.data
            if not product or qty is None or qty < 1:
                flash('يرجى اختيار منتج صحيح وكمية صحيحة لكل صف', 'danger')
                return render_template('movements/add.html', title='إضافة حركة منتجات', form=form)
            # Update product quantity logic
            if form.type.data == 'in':
                if form.destination_type.data == 'warehouse':
                    product.quantity += qty
                elif form.destination_type.data == 'branch':
                    product.quantity += qty
                elif form.destination_type.data == 'dealer':
                    product.quantity += qty
            elif form.type.data == 'out':
                if form.source_type.data == 'warehouse':
                    if product.quantity < qty:
                        flash(f'الكمية غير كافية في المخزن الرئيسي للمنتج {product.name}!', 'danger')
                        return render_template('movements/add.html', title='إضافة حركة منتجات', form=form)
                    product.quantity -= qty
                    notify_low_stock(None, product, product.quantity)
                elif form.source_type.data == 'branch':
                    if product.quantity < qty:
                        flash(f'الكمية غير كافية في الفرع للمنتج {product.name}!', 'danger')
                        return render_template('movements/add.html', title='إضافة حركة منتجات', form=form)
                    product.quantity -= qty
                    notify_low_stock(None, product, product.quantity)
                elif form.source_type.data == 'dealer':
                    if product.quantity < qty:
                        flash(f'الكمية غير كافية لدى التاجر للمنتج {product.name}!', 'danger')
                        return render_template('movements/add.html', title='إضافة حركة منتجات', form=form)
                    product.quantity -= qty
                    notify_low_stock(None, product, product.quantity)
            elif form.type.data == 'transfer':
                # تحويل: لا يؤثر على المخزن العام، فقط تسجيل الحركة
                # التحويل بين الفروع لا يغير الكمية الإجمالية في المخزن
                # الكميات في الفروع تُحسب من حركات التحويل

                # التحقق من الكمية المتوفرة في الفرع المصدر
                if form.source_type.data == 'branch' and form.source_id.data:
                    source_branch = Branch.query.get(form.source_id.data)
                    if source_branch:
                        available_qty = source_branch.get_product_quantity(product.id)
                        if available_qty < qty:
                            flash(f'الكمية غير كافية في الفرع "{source_branch.name}" للمنتج {product.name}. المتوفر: {available_qty}', 'danger')
                            return render_template('movements/add.html', title='إضافة حركة منتجات', form=form)
                        notify_low_stock(source_branch, product, available_qty)
                pass
            # Determine source_id/destination_id
            source_id = None
            destination_id = None
            if form.source_type.data == 'branch':
                source_id = form.source_id.data
            elif form.source_type.data == 'dealer':
                source_id = form.dealer_source_id.data
            if form.destination_type.data == 'branch':
                destination_id = form.destination_id.data
            elif form.destination_type.data == 'dealer':
                destination_id = form.dealer_destination_id.data
            movement = ProductMovement(
                product_id=product.id,
                user_id=current_user.id,
                shift=form.shift.data,
                type=form.type.data,
                quantity=qty,
                notes=form.notes.data,
                timestamp=datetime.utcnow(),
                source_type=form.source_type.data,
                source_id=source_id,
                destination_type=form.destination_type.data,
                destination_id=destination_id,
            )
            db.session.add(movement)
        db.session.commit()
        flash('تمت إضافة الحركات وتحديث الكميات بنجاح', 'success')
        return redirect(url_for('movements.list_movements'))
    return render_template('movements/add.html', title='إضافة حركة منتجات', form=form)

@movements_bp.route('/api/add', methods=['POST'])
@login_required
def api_add_movement():
    data = request.json or {}
    # التحقق من الحقول الأساسية
    products_data = data.get('products', [])
    type_ = data.get('type')
    shift = data.get('shift')
    source_type = data.get('source_type')
    destination_type = data.get('destination_type')
    source_id = data.get('source_id')
    destination_id = data.get('destination_id')
    notes = data.get('notes', '')
    errors = []
    if not products_data or not type_ or not shift or not source_type or not destination_type:
        return {"success": False, "message": "جميع الحقول مطلوبة"}, 400
    for prod in products_data:
        product_id = prod.get('product_id')
        qty = prod.get('quantity')
        product = Product.query.get(product_id)
        if not product or qty is None or qty < 1:
            errors.append(f"منتج غير صحيح أو كمية غير صحيحة (ID: {product_id})")
            continue
        # منطق تحديث الكميات
        if type_ == 'in':
            # دخول: إضافة للمخزن العام
            product.quantity += qty
        elif type_ == 'out':
            # خروج: خصم من المخزن العام
            if product.quantity < qty:
                errors.append(f"الكمية غير كافية للمنتج {product.name}")
                continue
            product.quantity -= qty
        elif type_ == 'transfer':
            # تحويل: لا يؤثر على المخزن العام، فقط تسجيل الحركة
            # التحويل بين الفروع لا يغير الكمية الإجمالية في المخزن
            # الكميات في الفروع تُحسب من حركات التحويل

            # التحقق من الكمية المتوفرة في الفرع المصدر
            if source_type == 'branch' and source_id:
                from models.branch import Branch
                source_branch = Branch.query.get(source_id)
                if source_branch:
                    available_qty = source_branch.get_product_quantity(product_id)
                    if available_qty < qty:
                        errors.append(f"الكمية غير كافية في الفرع '{source_branch.name}' للمنتج {product.name}. المتوفر: {available_qty}")
                        continue
            pass
        # إضافة الحركة
        movement = ProductMovement(
            product_id=product.id,
            user_id=current_user.id,
            shift=shift,
            type=type_,
            quantity=qty,
            notes=notes,
            timestamp=datetime.utcnow(),
            source_type=source_type,
            source_id=source_id,
            destination_type=destination_type,
            destination_id=destination_id,
        )
        db.session.add(movement)
    if errors:
        db.session.rollback()
        return {"success": False, "message": " ".join(errors)}, 400
    db.session.commit()
    return {"success": True, "message": "تمت إضافة الحركات وتحديث الكميات بنجاح"}, 201

@movements_bp.route('/delete/<int:movement_id>', methods=['POST'])
@login_required
@admin_required
def delete_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)

    try:
        # التحقق من أن الحركة حديثة (أقل من 24 ساعة)
        from datetime import datetime, timedelta
        time_limit = datetime.utcnow() - timedelta(hours=24)

        if movement.timestamp < time_limit:
            flash('لا يمكن حذف الحركات التي يزيد عمرها عن 24 ساعة!', 'danger')
            return redirect(url_for('movements.list_movements'))

        # عكس تأثير الحركة على المخزون
        product = movement.product

        if movement.type == 'in':
            # إذا كانت حركة دخول، نخصم الكمية
            # السماح بالخصم حتى لو وصل المخزون لصفر أو أقل
            product.quantity -= movement.quantity
            # التأكد من عدم وجود كمية سالبة
            if product.quantity < 0:
                product.quantity = 0

        elif movement.type == 'out':
            # إذا كانت حركة خروج، نضيف الكمية
            product.quantity += movement.quantity

        elif movement.type == 'transfer':
            # للتحويل، لا نحتاج لتغيير المخزون العام
            # السماح بحذف حركة التحويل حتى لو كانت الكمية في الفرع سالبة
            # لأن هذا قد يكون بسبب حركات أخرى تمت بعد هذه الحركة
            pass

        # حذف الحركة
        db.session.delete(movement)
        db.session.commit()

        flash(f'تم حذف الحركة بنجاح. تم عكس تأثيرها على المخزون.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف الحركة: {str(e)}', 'danger')

    return redirect(url_for('movements.list_movements'))

@movements_bp.route('/api/delete/<int:movement_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)

    try:
        # التحقق من أن الحركة حديثة (أقل من 24 ساعة)
        from datetime import datetime, timedelta
        time_limit = datetime.utcnow() - timedelta(hours=24)

        if movement.timestamp < time_limit:
            return jsonify({
                "success": False,
                "message": "لا يمكن حذف الحركات التي يزيد عمرها عن 24 ساعة!"
            }), 400

        # عكس تأثير الحركة على المخزون
        product = movement.product

        if movement.type == 'in':
            # إذا كانت حركة دخول، نخصم الكمية
            # السماح بالخصم حتى لو وصل المخزون لصفر أو أقل
            product.quantity -= movement.quantity
            # التأكد من عدم وجود كمية سالبة
            if product.quantity < 0:
                product.quantity = 0

        elif movement.type == 'out':
            # إذا كانت حركة خروج، نضيف الكمية
            product.quantity += movement.quantity

        elif movement.type == 'transfer':
            # للتحويل، لا نحتاج لتغيير المخزون العام
            # السماح بحذف حركة التحويل حتى لو كانت الكمية في الفرع سالبة
            # لأن هذا قد يكون بسبب حركات أخرى تمت بعد هذه الحركة
            pass

        # حذف الحركة
        db.session.delete(movement)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "تم حذف الحركة بنجاح. تم عكس تأثيرها على المخزون."
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"حدث خطأ أثناء حذف الحركة: {str(e)}"
        }), 500

@movements_bp.route('/export/excel')
@login_required
def export_movements_excel():
    """تصدير حركات المنتجات إلى ملف Excel"""
    try:
        # جلب نفس الفلاتر المستخدمة في قائمة الحركات
        product_id = request.args.get('product_id', type=int)
        movement_type = request.args.get('type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        branch_id = request.args.get('branch_id', type=int)
        dealer_id = request.args.get('dealer_id', type=int)
        user_id = request.args.get('user_id', type=int)
        shift = request.args.get('shift')
        quantity_less = request.args.get('quantity_less', type=int)

        # بناء الاستعلام
        query = ProductMovement.query

        if product_id:
            query = query.filter(ProductMovement.product_id == product_id)
        if movement_type:
            query = query.filter(ProductMovement.type == movement_type)
        if date_from:
            query = query.filter(ProductMovement.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(ProductMovement.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        if branch_id:
            query = query.filter(
                ((ProductMovement.source_id == branch_id) & (ProductMovement.source_type == 'branch')) |
                ((ProductMovement.destination_id == branch_id) & (ProductMovement.destination_type == 'branch'))
            )
        if dealer_id:
            query = query.filter(
                ((ProductMovement.source_id == dealer_id) & (ProductMovement.source_type == 'dealer')) |
                ((ProductMovement.destination_id == dealer_id) & (ProductMovement.destination_type == 'dealer'))
            )
        if user_id:
            query = query.filter(ProductMovement.user_id == user_id)
        if shift:
            query = query.filter(ProductMovement.shift == shift)
        if quantity_less:
            query = query.filter(ProductMovement.quantity < quantity_less)

        # ترتيب النتائج
        movements = query.order_by(ProductMovement.timestamp.desc()).all()

        # تحضير البيانات للتصدير
        data = []
        for movement in movements:
            # تحديد نوع الحركة بالعربية
            type_arabic = {
                'in': 'دخول',
                'out': 'خروج',
                'transfer': 'تحويل'
            }.get(movement.type, movement.type)

            # تحديد الوردية بالعربية
            shift_arabic = {
                'morning': 'صباحية',
                'evening': 'مسائية'
            }.get(movement.shift, movement.shift)

            # الحصول على أسماء الكيانات
            source_name = get_entity_name(movement.source_type, movement.source_id) if movement.source_id else '-'
            destination_name = get_entity_name(movement.destination_type, movement.destination_id) if movement.destination_id else '-'

            data.append({
                'رقم الحركة': movement.id,
                'المنتج': movement.product.name,
                'الصنف': movement.product.category.name if movement.product.category else 'غير محدد',
                'النوع': type_arabic,
                'الكمية': movement.quantity,
                'من': f"{get_entity_type_label(movement.source_type)} - {source_name}",
                'إلى': f"{get_entity_type_label(movement.destination_type)} - {destination_name}",
                'المستخدم': movement.user.username,
                'الوردية': shift_arabic,
                'التاريخ': movement.timestamp.strftime('%Y-%m-%d'),
                'الوقت': movement.timestamp.strftime('%H:%M:%S'),
                'ملاحظات': movement.notes or '-'
            })

        # إنشاء DataFrame
        df = pd.DataFrame(data)

        # إنشاء ملف Excel في الذاكرة
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='حركات المنتجات', index=False)

            # الحصول على ورقة العمل
            worksheet = writer.sheets['حركات المنتجات']
            workbook = writer.book

            # تنسيق العناوين
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1,
                'align': 'center'
            })

            # تطبيق التنسيق على العناوين
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # ضبط عرض الأعمدة
            for i, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                )
                worksheet.set_column(i, i, max_length + 2)

        output.seek(0)

        # إنشاء اسم الملف
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'حركات_المنتجات_{timestamp}.xlsx'

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        flash(f'حدث خطأ أثناء تصدير البيانات: {str(e)}', 'danger')
        return redirect(url_for('movements.list_movements'))

def get_entity_type_label(entity_type):
    """الحصول على تسمية نوع الكيان بالعربية"""
    labels = {
        'warehouse': 'مخزن',
        'branch': 'فرع',
        'dealer': 'تاجر'
    }
    return labels.get(entity_type, entity_type)