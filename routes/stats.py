from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db
from models.product import Product
from models.category import Category
from models.branch import Branch
from models.dealer import Dealer
from models.movement import ProductMovement
from models.user import User
from routes.auth import admin_required
from datetime import datetime, timedelta
import pandas as pd
import io
from sqlalchemy import func, and_

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')

@stats_bp.route('/')
@login_required
def stats_dashboard():
    # الإحصائيات العامة
    total_products = Product.query.count()
    total_stock_value = sum([p.price * p.quantity for p in Product.query.all()])
    total_branches = Branch.query.count()
    total_dealers = Dealer.query.count()
    total_categories = Category.query.count()
    total_users = User.query.count()

    # إحصائيات الحركة
    total_movements = ProductMovement.query.count()
    today_movements = ProductMovement.query.filter(
        func.date(ProductMovement.timestamp) == datetime.now().date()
    ).count()

    # إحصائيات الفروع
    branches_data = []
    branches = Branch.query.all()
    for branch in branches:
        # عدد المنتجات في الفرع
        branch_products = sum([1 for p in Product.query.all() if branch.get_product_quantity(p.id) > 0])
        # قيمة المخزون في الفرع
        branch_stock_value = sum([
            p.price * branch.get_product_quantity(p.id)
            for p in Product.query.all()
            if branch.get_product_quantity(p.id) > 0
        ])
        # عدد الحركات للفرع
        branch_movements = ProductMovement.query.filter(
            ((ProductMovement.source_type == 'branch') & (ProductMovement.source_id == branch.id)) |
            ((ProductMovement.destination_type == 'branch') & (ProductMovement.destination_id == branch.id))
        ).count()

        branches_data.append({
            'id': branch.id,
            'name': branch.name,
            'products_count': branch_products,
            'stock_value': branch_stock_value,
            'movements_count': branch_movements
        })

    # إحصائيات الحركة حسب النوع
    movements_by_type = db.session.query(
        ProductMovement.type,
        func.count(ProductMovement.id).label('count')
    ).group_by(ProductMovement.type).all()

    # إحصائيات الحركة في آخر 7 أيام
    last_week = datetime.now() - timedelta(days=7)
    weekly_movements = db.session.query(
        func.date(ProductMovement.timestamp).label('date'),
        func.count(ProductMovement.id).label('count')
    ).filter(ProductMovement.timestamp >= last_week).group_by(
        func.date(ProductMovement.timestamp)
    ).order_by(func.date(ProductMovement.timestamp)).all()

    # المنتجات الأكثر حركة
    top_products = db.session.query(
        Product.name,
        func.count(ProductMovement.id).label('movements_count')
    ).join(ProductMovement).group_by(Product.id, Product.name).order_by(
        func.count(ProductMovement.id).desc()
    ).limit(10).all()

    # المنتجات منخفضة المخزون (أقل من 10)
    low_stock_products = Product.query.filter(Product.quantity < 10).all()

    # إحصائيات الورديات
    shift_stats = db.session.query(
        ProductMovement.shift,
        func.count(ProductMovement.id).label('count')
    ).group_by(ProductMovement.shift).all()

    return render_template('stats/dashboard.html',
                         title='الإحصائيات',
                         total_products=total_products,
                         total_stock_value=total_stock_value,
                         total_branches=total_branches,
                         total_dealers=total_dealers,
                         total_categories=total_categories,
                         total_users=total_users,
                         total_movements=total_movements,
                         today_movements=today_movements,
                         branches_data=branches_data,
                         movements_by_type=movements_by_type,
                         weekly_movements=weekly_movements,
                         top_products=top_products,
                         low_stock_products=low_stock_products,
                         shift_stats=shift_stats)

@stats_bp.route('/api/branch/<int:branch_id>')
@login_required
def branch_stats(branch_id):
    branch = Branch.query.get_or_404(branch_id)

    # إحصائيات الفرع
    branch_products = []
    for product in Product.query.all():
        quantity = branch.get_product_quantity(product.id)
        if quantity > 0:
            branch_products.append({
                'name': product.name,
                'quantity': quantity,
                'value': product.price * quantity
            })

    # حركات الفرع في آخر 30 يوم
    last_month = datetime.now() - timedelta(days=30)
    branch_movements = ProductMovement.query.filter(
        and_(
            ((ProductMovement.source_type == 'branch') & (ProductMovement.source_id == branch_id)) |
            ((ProductMovement.destination_type == 'branch') & (ProductMovement.destination_id == branch_id)),
            ProductMovement.timestamp >= last_month
        )
    ).order_by(ProductMovement.timestamp.desc()).limit(20).all()

    return jsonify({
        'branch': {
            'id': branch.id,
            'name': branch.name,
            'products_count': len(branch_products),
            'total_value': sum(p['value'] for p in branch_products)
        },
        'products': branch_products,
        'movements': [{
            'id': m.id,
            'product': m.product.name,
            'type': m.type,
            'quantity': m.quantity,
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M')
        } for m in branch_movements]
    })

@stats_bp.route('/export/excel')
@login_required
@admin_required
def export_stats_excel():
    """تصدير الإحصائيات إلى ملف Excel"""
    try:
        # إنشاء ملف Excel في الذاكرة
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
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

            # تنسيق الأرقام
            number_format = workbook.add_format({
                'num_format': '#,##0',
                'border': 1
            })

            # تنسيق العملة
            currency_format = workbook.add_format({
                'num_format': '#,##0 ريال',
                'border': 1
            })

            # 1. إحصائيات عامة
            general_stats = [
                ['المؤشر', 'القيمة'],
                ['إجمالي المنتجات', Product.query.count()],
                ['إجمالي الأصناف', Category.query.count()],
                ['إجمالي الفروع', Branch.query.count()],
                ['إجمالي التجار', Dealer.query.count()],
                ['إجمالي المستخدمين', User.query.count()],
                ['إجمالي الحركات', ProductMovement.query.count()]
            ]

            df_general = pd.DataFrame(general_stats[1:], columns=general_stats[0])
            df_general.to_excel(writer, sheet_name='إحصائيات عامة', index=False)

            # تطبيق التنسيق
            worksheet = writer.sheets['إحصائيات عامة']
            for col_num, value in enumerate(df_general.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(0, 0, 20)
            worksheet.set_column(1, 1, 15)

            # 2. المنتجات الأكثر حركة
            top_products = db.session.query(
                Product.name,
                func.sum(ProductMovement.quantity).label('total_moved')
            ).join(ProductMovement).group_by(Product.id, Product.name).order_by(
                func.sum(ProductMovement.quantity).desc()
            ).limit(10).all()

            products_data = [[product.name, total_moved] for product, total_moved in top_products]
            df_products = pd.DataFrame(products_data, columns=['المنتج', 'إجمالي الحركة'])
            df_products.to_excel(writer, sheet_name='المنتجات الأكثر حركة', index=False)

            # تطبيق التنسيق
            worksheet = writer.sheets['المنتجات الأكثر حركة']
            for col_num, value in enumerate(df_products.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(0, 0, 30)
            worksheet.set_column(1, 1, 15, number_format)

            # 3. إحصائيات الفروع
            branches_data = []
            for branch in Branch.query.all():
                total_value = branch.get_total_stock_value()
                movements_stats = branch.get_movements_stats()
                branches_data.append([
                    branch.name,
                    len(branch.get_all_products_with_quantities()),
                    total_value,
                    movements_stats['today'],
                    movements_stats['week'],
                    movements_stats['month']
                ])

            df_branches = pd.DataFrame(branches_data, columns=[
                'اسم الفرع', 'عدد المنتجات', 'قيمة المخزون', 'حركات اليوم', 'حركات الأسبوع', 'حركات الشهر'
            ])
            df_branches.to_excel(writer, sheet_name='إحصائيات الفروع', index=False)

            # تطبيق التنسيق
            worksheet = writer.sheets['إحصائيات الفروع']
            for col_num, value in enumerate(df_branches.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(0, 0, 25)
            worksheet.set_column(1, 1, 15, number_format)
            worksheet.set_column(2, 2, 20, currency_format)
            worksheet.set_column(3, 5, 15, number_format)

            # 4. حركات الشهر الحالي
            current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_movements = ProductMovement.query.filter(
                ProductMovement.timestamp >= current_month
            ).order_by(ProductMovement.timestamp.desc()).all()

            movements_data = []
            for movement in monthly_movements:
                type_arabic = {'in': 'دخول', 'out': 'خروج', 'transfer': 'تحويل'}.get(movement.type, movement.type)
                shift_arabic = {'morning': 'صباحية', 'evening': 'مسائية'}.get(movement.shift, movement.shift)

                movements_data.append([
                    movement.id,
                    movement.product.name,
                    type_arabic,
                    movement.quantity,
                    movement.user.username,
                    shift_arabic,
                    movement.timestamp.strftime('%Y-%m-%d %H:%M'),
                    movement.notes or '-'
                ])

            df_movements = pd.DataFrame(movements_data, columns=[
                'رقم الحركة', 'المنتج', 'النوع', 'الكمية', 'المستخدم', 'الوردية', 'التاريخ', 'ملاحظات'
            ])
            df_movements.to_excel(writer, sheet_name='حركات الشهر', index=False)

            # تطبيق التنسيق
            worksheet = writer.sheets['حركات الشهر']
            for col_num, value in enumerate(df_movements.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(0, 0, 12, number_format)
            worksheet.set_column(1, 1, 25)
            worksheet.set_column(2, 2, 10)
            worksheet.set_column(3, 3, 10, number_format)
            worksheet.set_column(4, 4, 15)
            worksheet.set_column(5, 5, 10)
            worksheet.set_column(6, 6, 18)
            worksheet.set_column(7, 7, 30)

        output.seek(0)

        # إنشاء اسم الملف
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'تقرير_الإحصائيات_{timestamp}.xlsx'

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ أثناء تصدير البيانات: {str(e)}'
        }), 500