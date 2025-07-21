from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.branch import Branch
from models.product import Product
from models.category import Category
from models.movement import ProductMovement
from models.request import ProductRequest
from models.notification import BranchNotification
from models.branch_inventory import BranchInventory
from datetime import datetime, timedelta
import json
from routes.auth import admin_required

branch_dashboard_bp = Blueprint('branch_dashboard', __name__, url_prefix='/branch')

@branch_dashboard_bp.before_request
def check_branch_access():
    """التحقق من أن المستخدم مرتبط بفرع"""
    if current_user.is_authenticated and current_user.is_branch_user():
        if not current_user.branch_id:
            flash('يجب ربط حسابك بفرع أولاً', 'warning')
            return redirect(url_for('auth.logout'))

@branch_dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """لوحة تحكم الفرع"""
    if not current_user.is_branch_user():
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard'))

    branch = current_user.branch

    # إحصائيات الفرع
    stats = get_branch_stats(branch)

    # المنتجات في الفرع
    branch_products = get_branch_products(branch)

    # الطلبات الحديثة
    recent_requests = get_recent_requests(branch)

    # الإشعارات غير المقروءة
    unread_notifications = get_unread_notifications(branch)

    # المنتجات منخفضة المخزون
    low_stock_products = get_low_stock_products(branch)

    return render_template('branch_dashboard/dashboard.html',
                         branch=branch,
                         stats=stats,
                         branch_products=branch_products,
                         recent_requests=recent_requests,
                         unread_notifications=unread_notifications,
                         low_stock_products=low_stock_products)

@branch_dashboard_bp.route('/inventory')
@login_required
def inventory():
    """مخزون الفرع"""
    if not current_user.is_branch_user():
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard'))

    branch = current_user.branch

    # البحث والفلترة
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', '')
    status = request.args.get('status', '')

    # الحصول على المنتجات
    products = get_filtered_products(branch, search, category_id, status)

    # الفئات للفلترة
    categories = Category.query.all()

    return render_template('branch_dashboard/inventory.html',
                         branch=branch,
                         products=products,
                         categories=categories,
                         search=search,
                         category_id=category_id,
                         status=status)

@branch_dashboard_bp.route('/requests')
@login_required
def requests():
    """طلبات الفرع"""
    if not current_user.is_branch_user():
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard'))

    branch = current_user.branch

    # فلترة الطلبات
    request_type = request.args.get('type', 'all')  # sent, received, all
    status = request.args.get('status', 'all')

    # الحصول على الطلبات
    requests = get_filtered_requests(branch, request_type, status)

    return render_template('branch_dashboard/requests.html',
                         branch=branch,
                         requests=requests,
                         request_type=request_type,
                         status=status)

@branch_dashboard_bp.route('/new-request', methods=['GET', 'POST'])
@login_required
def new_request():
    """طلب منتج جديد"""
    if not current_user.is_branch_user():
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard'))

    branch = current_user.branch

    if request.method == 'POST':
        return handle_new_request(branch)

    # الحصول على المنتجات المتاحة
    products = Product.query.all()

    # الحصول على الفروع الأخرى والمخزن المركزي
    available_sources = get_available_sources(branch)

    return render_template('branch_dashboard/new_request.html',
                         branch=branch,
                         products=products,
                         available_sources=available_sources)

@branch_dashboard_bp.route('/api/branch/stock_info')
@login_required
def api_stock_info():
    product_id = request.args.get('product_id', type=int)
    source_type = request.args.get('source_type')
    source_id = request.args.get('source_id', type=int)
    if not product_id or not source_type:
        return jsonify({'success': False, 'message': 'بيانات غير مكتملة'}), 400
    # تحديد المصدر
    if source_type == 'warehouse':
        # الكمية في المخزن المركزي = مجموع الكمية في الحركات (دخول - خروج - تحويل) وليس في الفروع
        from models.product import Product
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'المنتج غير موجود'}), 404
        # الكمية في المخزن المركزي = الكمية الكلية - مجموع الكميات في جميع الفروع
        total_quantity = product.quantity
        from models.branch_inventory import BranchInventory
        branches_stock = db.session.query(db.func.sum(BranchInventory.quantity)).filter_by(product_id=product_id).scalar() or 0
        warehouse_quantity = total_quantity - branches_stock
        return jsonify({'success': True, 'quantity': warehouse_quantity, 'source_name': 'المخزن المركزي'})
    elif source_type == 'branch' and source_id:
        from models.branch_inventory import BranchInventory
        branch_stock = BranchInventory.query.filter_by(branch_id=source_id, product_id=product_id).first()
        quantity = branch_stock.quantity if branch_stock else 0
        from models.branch import Branch
        branch = Branch.query.get(source_id)
        branch_name = branch.name if branch else f'فرع {source_id}'
        return jsonify({'success': True, 'quantity': quantity, 'source_name': branch_name})
    else:
        return jsonify({'success': False, 'message': 'مصدر غير معروف أو غير مدعوم'})

# دوال مساعدة
def get_branch_stats(branch):
    """إحصائيات الفرع"""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # عدد المنتجات في الفرع
    products_count = len(branch.get_all_products_with_quantities())

    # الطلبات الصادرة
    outgoing_requests = ProductRequest.query.filter_by(
        requesting_branch_id=branch.id
    ).count()

    # الطلبات الواردة
    incoming_requests = ProductRequest.query.filter(
        ProductRequest.source_type == 'branch',
        ProductRequest.source_id == branch.id
    ).count()

    # حركات اليوم
    today_movements = ProductMovement.query.filter(
        (ProductMovement.source_id == branch.id) | (ProductMovement.destination_id == branch.id),
        db.func.date(ProductMovement.timestamp) == today
    ).count()

    return {
        'products_count': products_count,
        'outgoing_requests': outgoing_requests,
        'incoming_requests': incoming_requests,
        'today_movements': today_movements
    }

def get_branch_products(branch):
    """المنتجات في الفرع"""
    return branch.get_all_products_with_quantities()

def get_recent_requests(branch):
    """الطلبات الحديثة"""
    return ProductRequest.query.filter_by(
        requesting_branch_id=branch.id
    ).order_by(ProductRequest.requested_at.desc()).limit(5).all()

def get_unread_notifications(branch):
    """الإشعارات غير المقروءة"""
    return BranchNotification.query.filter_by(
        to_branch_id=branch.id,
        is_read=False
    ).order_by(BranchNotification.created_at.desc()).limit(10).all()

def get_low_stock_products(branch):
    """المنتجات منخفضة المخزون"""
    branch_products = branch.get_all_products_with_quantities()
    return [item for item in branch_products if item['quantity'] <= 10]

def get_filtered_products(branch, search, category_id, status):
    """المنتجات المفلترة"""
    branch_products = branch.get_all_products_with_quantities()

    # فلترة حسب البحث
    if search:
        branch_products = [item for item in branch_products
                          if search.lower() in item['product'].name.lower()]

    # فلترة حسب الفئة
    if category_id:
        branch_products = [item for item in branch_products
                          if str(item['product'].category_id) == category_id]

    # فلترة حسب الحالة
    if status == 'low_stock':
        branch_products = [item for item in branch_products if item['quantity'] <= 10]
    elif status == 'out_of_stock':
        branch_products = [item for item in branch_products if item['quantity'] == 0]

    return branch_products

def get_filtered_requests(branch, request_type, status):
    query = ProductRequest.query
    if current_user.is_admin():
        # المدير يرى كل الطلبات
        pass
    else:
        if request_type == 'sent':
            query = query.filter_by(requesting_branch_id=branch.id)
        elif request_type == 'received':
            query = query.filter(
                ProductRequest.source_type == 'branch',
                ProductRequest.source_id == branch.id
            )
    if status != 'all':
        query = query.filter_by(status=status)
    return query.order_by(ProductRequest.requested_at.desc()).all()

def get_available_sources(branch):
    """المصادر المتاحة للطلب"""
    sources = []

    # المخزن المركزي
    sources.append({
        'type': 'warehouse',
        'id': None,
        'name': 'المخزن المركزي'
    })

    # الفروع الأخرى
    other_branches = Branch.query.filter(
        Branch.id != branch.id,
        Branch.is_active == True
    ).all()

    for other_branch in other_branches:
        sources.append({
            'type': 'branch',
            'id': other_branch.id,
            'name': other_branch.name
        })

    return sources

def handle_new_request(branch):
    """معالجة طلب جديد"""
    try:
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity'))
        source_type = request.form.get('source_type')
        source_id = request.form.get('source_id') if request.form.get('source_id') else None
        notes = request.form.get('notes', '')

        # التحقق من البيانات
        if not product_id or not quantity or not source_type:
            flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
            return redirect(url_for('branch_dashboard.new_request'))

        # إنشاء الطلب
        request_obj = ProductRequest(
            requesting_branch_id=branch.id,
            product_id=product_id,
            quantity=quantity,
            source_type=source_type,
            source_id=source_id,
            requested_by=current_user.id,
            request_notes=notes
        )

        db.session.add(request_obj)
        db.session.commit()
        notify_new_request(request_obj)

        flash('تم إرسال الطلب بنجاح', 'success')
        return redirect(url_for('branch_dashboard.requests'))

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء إرسال الطلب: {str(e)}', 'danger')
        return redirect(url_for('branch_dashboard.new_request'))

def create_notification(to_branch_id, title, message, notification_type, product_id=None, from_branch_id=None, is_urgent=False, created_by=None):
    from models.notification import BranchNotification
    notif = BranchNotification(
        to_branch_id=to_branch_id,
        from_branch_id=from_branch_id,
        product_id=product_id,
        title=title,
        message=message,
        notification_type=notification_type,
        is_urgent=is_urgent,
        created_by=created_by
    )
    db.session.add(notif)
    db.session.commit()
    return notif

# إشعار عند انخفاض الكمية في الفرع

def notify_low_stock(branch, product, quantity, threshold=10):
    if quantity <= threshold:
        title = f"تنبيه: مخزون منخفض - {product.name}"
        message = f"الكمية المتبقية من المنتج '{product.name}' في {branch.name}: {quantity}. يرجى إعادة الطلب أو التوريد."
        create_notification(
            to_branch_id=branch.id,
            title=title,
            message=message,
            notification_type='low_stock',
            product_id=product.id,
            from_branch_id=branch.id,
            is_urgent=True
        )

# إشعار عند وصول طلب جديد

def notify_new_request(request_obj):
    from_branch = request_obj.requesting_branch
    product = request_obj.product
    # إشعار للمدير (admin) عند كل طلب جديد
    admin_title = f"طلب جديد من {from_branch.name} على {product.name}"
    admin_message = f"تم إرسال طلب جديد من {from_branch.name} على المنتج '{product.name}' بكمية {request_obj.quantity}."
    create_notification(
        to_branch_id=None,  # None تعني موجه للمدير
        title=admin_title,
        message=admin_message,
        notification_type='request_admin',
        product_id=product.id,
        from_branch_id=from_branch.id,
        is_urgent=True
    )
    # إشعار للفرع المستلم أو المخزن
    if request_obj.source_type == 'warehouse':
        to_branch_id = None  # المخزن المركزي (يمكن تخصيصه لاحقًا)
        title = f"طلب جديد من {from_branch.name} على {product.name}"
        message = f"تم إرسال طلب جديد من {from_branch.name} على المنتج '{product.name}' بكمية {request_obj.quantity}."
    elif request_obj.source_type == 'branch':
        to_branch_id = request_obj.source_id
        title = f"طلب تحويل منتج من {from_branch.name}"
        message = f"تم إرسال طلب تحويل المنتج '{product.name}' بكمية {request_obj.quantity} من {from_branch.name} إلى فرعك."
    else:
        return
    create_notification(
        to_branch_id=to_branch_id,
        title=title,
        message=message,
        notification_type='request',
        product_id=product.id,
        from_branch_id=from_branch.id,
        is_urgent=False
    )

# إشعار عند تغيير حالة الطلب

def notify_request_status(request_obj, status):
    branch = request_obj.requesting_branch
    product = request_obj.product
    status_map = {
        'accepted': 'تم قبول الطلب',
        'rejected': 'تم رفض الطلب',
        'delivered': 'تم توصيل الطلب'
    }
    if status in status_map:
        title = f"{status_map[status]} - {product.name}"
        message = f"تم تحديث حالة طلب المنتج '{product.name}' إلى: {status_map[status]}. الكمية: {request_obj.quantity}."
        create_notification(
            to_branch_id=branch.id,
            title=title,
            message=message,
            notification_type=status,
            product_id=product.id,
            from_branch_id=request_obj.source_id,
            is_urgent=(status == 'rejected')
        )

@branch_dashboard_bp.route('/notifications', methods=['GET'])
@login_required
def notifications():
    if not current_user.is_branch_user():
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard'))
    branch = current_user.branch
    notif_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    query = BranchNotification.query.filter_by(to_branch_id=branch.id)
    if notif_type != 'all':
        query = query.filter_by(notification_type=notif_type)
    if status == 'unread':
        query = query.filter_by(is_read=False)
    elif status == 'read':
        query = query.filter_by(is_read=True)
    notifications = query.order_by(BranchNotification.created_at.desc()).all()
    return render_template('branch_dashboard/notifications.html', branch=branch, notifications=notifications, notif_type=notif_type, status=status)

@branch_dashboard_bp.route('/notifications/mark_read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = BranchNotification.query.get_or_404(notif_id)
    if notif.to_branch_id != current_user.branch_id:
        flash('غير مصرح لك بتعديل هذا الإشعار', 'danger')
        return redirect(url_for('branch_dashboard.notifications'))
    notif.mark_as_read()
    db.session.commit()
    flash('تم تأشير الإشعار كمقروء', 'success')
    return redirect(url_for('branch_dashboard.notifications', type=request.args.get('type', 'all'), status=request.args.get('status', 'all')))

@branch_dashboard_bp.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    branch = current_user.branch
    notifs = BranchNotification.query.filter_by(to_branch_id=branch.id, is_read=False).all()
    for notif in notifs:
        notif.mark_as_read()
    db.session.commit()
    flash('تم تأشير جميع الإشعارات كمقروءة', 'success')
    return redirect(url_for('branch_dashboard.notifications', type=request.args.get('type', 'all'), status=request.args.get('status', 'all')))

@branch_dashboard_bp.route('/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_request(request_id):
    req = ProductRequest.query.get_or_404(request_id)
    # فقط admin أو مدير الفرع المصدر يمكنه الموافقة
    if not (current_user.is_admin() or (current_user.is_branch_manager() and req.source_type == 'branch' and req.source_id == current_user.branch_id)):
        flash('ليس لديك صلاحية الموافقة على هذا الطلب', 'danger')
        return redirect(url_for('branch_dashboard.requests'))
    if req.status != 'pending':
        flash('لا يمكن الموافقة على طلب غير قيد الانتظار', 'warning')
        return redirect(url_for('branch_dashboard.requests'))
    req.status = 'accepted'
    req.responded_by = current_user.id
    req.responded_at = datetime.utcnow()
    if req.source_type == 'branch' and req.source_id:
        from models.movement import ProductMovement
        from models.product import Product
        from models.branch import Branch
        product = Product.query.get(req.product_id)
        source_branch = Branch.query.get(req.source_id)
        dest_branch = req.requesting_branch
        qty = req.quantity
        # خصم الكمية من مخزون الفرع المرسل
        available_qty = source_branch.get_product_quantity(product.id)
        if available_qty < qty:
            flash(f'الكمية غير كافية في الفرع {source_branch.name} (المتوفر: {available_qty})', 'danger')
            return redirect(url_for('branch_dashboard.requests'))
        # سجل حركة التحويل
        movement_transfer = ProductMovement(
            product_id=product.id,
            user_id=current_user.id,
            shift='morning',
            type='transfer',
            quantity=qty,
            notes=f'تحويل من {source_branch.name} إلى {dest_branch.name} (طلب رقم {req.id})',
            timestamp=datetime.utcnow(),
            source_type='branch',
            source_id=source_branch.id,
            destination_type='branch',
            destination_id=dest_branch.id
        )
        db.session.add(movement_transfer)
        # تحديث الكميات يدويًا (إضافة للفرع الطالب)
        # لا حاجة لتعديل الكمية في المخزن لأن get_product_quantity تعتمد على الحركات
        # لكن يمكن إضافة منطق branch_inventory إذا كان مستخدمًا
    db.session.commit()
    notify_request_status(req, 'accepted')
    flash('تمت الموافقة على الطلب بنجاح وتم نقل الكمية بين الفروع.', 'success')
    return redirect(url_for('branch_dashboard.requests'))

@branch_dashboard_bp.route('/requests/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_request(request_id):
    req = ProductRequest.query.get_or_404(request_id)
    # فقط admin أو مدير الفرع المصدر يمكنه الرفض
    if not (current_user.is_admin() or (current_user.is_branch_manager() and req.source_type == 'branch' and req.source_id == current_user.branch_id)):
        flash('ليس لديك صلاحية رفض هذا الطلب', 'danger')
        return redirect(url_for('branch_dashboard.requests'))
    if req.status != 'pending':
        flash('لا يمكن رفض طلب غير قيد الانتظار', 'warning')
        return redirect(url_for('branch_dashboard.requests'))
    req.status = 'rejected'
    req.responded_by = current_user.id
    req.responded_at = datetime.utcnow()
    db.session.commit()
    notify_request_status(req, 'rejected')
    flash('تم رفض الطلب', 'info')
    return redirect(url_for('branch_dashboard.requests'))

@branch_dashboard_bp.route('/requests/<int:request_id>/deliver', methods=['POST'])
@login_required
def deliver_request(request_id):
    req = ProductRequest.query.get_or_404(request_id)
    # فقط admin أو مدير الفرع المصدر يمكنه التوصيل
    if not (current_user.is_admin() or (current_user.is_branch_manager() and req.source_type == 'branch' and req.source_id == current_user.branch_id)):
        flash('ليس لديك صلاحية توصيل هذا الطلب', 'danger')
        return redirect(url_for('branch_dashboard.requests'))
    if req.status != 'accepted':
        flash('لا يمكن توصيل إلا الطلبات المقبولة فقط', 'warning')
        return redirect(url_for('branch_dashboard.requests'))
    req.status = 'delivered'
    req.responded_by = current_user.id
    req.responded_at = datetime.utcnow()
    db.session.commit()
    notify_request_status(req, 'delivered')
    flash('تم تأكيد توصيل الطلب', 'success')
    return redirect(url_for('branch_dashboard.requests'))

@branch_dashboard_bp.route('/requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_request(request_id):
    req = ProductRequest.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('لا يمكن إلغاء إلا الطلبات قيد الانتظار', 'warning')
        return redirect(url_for('branch_dashboard.requests'))
    if req.requested_by != current_user.id:
        flash('غير مصرح لك بإلغاء هذا الطلب', 'danger')
        return redirect(url_for('branch_dashboard.requests'))
    req.status = 'cancelled'
    req.responded_by = current_user.id
    req.responded_at = datetime.utcnow()
    db.session.commit()
    flash('تم إلغاء الطلب بنجاح', 'success')
    return redirect(url_for('branch_dashboard.requests'))

@branch_dashboard_bp.route('/admin-notifications', methods=['GET'])
@login_required
@admin_required
def admin_notifications():
    notif_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    query = BranchNotification.query.filter_by(to_branch_id=None)
    if notif_type != 'all':
        query = query.filter_by(notification_type=notif_type)
    if status == 'unread':
        query = query.filter_by(is_read=False)
    elif status == 'read':
        query = query.filter_by(is_read=True)
    notifications = query.order_by(BranchNotification.created_at.desc()).all()
    return render_template('admin/admin_notifications.html', notifications=notifications, notif_type=notif_type, status=status)

@branch_dashboard_bp.route('/admin-notifications/mark_read/<int:notif_id>', methods=['POST'])
@login_required
@admin_required
def admin_mark_read(notif_id):
    notif = BranchNotification.query.get_or_404(notif_id)
    if notif.to_branch_id != None: # Check if it's an admin notification
        flash('غير مصرح لك بتعديل هذا الإشعار', 'danger')
        return redirect(url_for('branch_dashboard.admin_notifications'))
    notif.mark_as_read()
    db.session.commit()
    flash('تم تأشير الإشعار كمقروء', 'success')
    return redirect(url_for('branch_dashboard.admin_notifications', type=request.args.get('type', 'all'), status=request.args.get('status', 'all')))

@branch_dashboard_bp.route('/admin-notifications/mark_all_read', methods=['POST'])
@login_required
@admin_required
def admin_mark_all_read():
    notifs = BranchNotification.query.filter_by(to_branch_id=None, is_read=False).all()
    for notif in notifs:
        notif.mark_as_read()
    db.session.commit()
    flash('تم تأشير جميع الإشعارات كمقروءة', 'success')
    return redirect(url_for('branch_dashboard.admin_notifications', type=request.args.get('type', 'all'), status=request.args.get('status', 'all')))