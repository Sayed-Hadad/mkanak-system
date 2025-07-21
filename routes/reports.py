from flask import Blueprint, render_template
from flask_login import login_required
from models import Sale
from datetime import datetime, timedelta
from flask import jsonify, request

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/advanced')
@login_required
def advanced_reports():
    return render_template('reports/advanced.html', title='التقارير والتحليلات المتقدمة')

@reports_bp.route('/api/sales_last_30_days')
@login_required
def api_sales_last_30_days():
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=29)
    sales = (
        Sale.query
        .filter(Sale.created_at >= start_date)
        .order_by(Sale.created_at)
        .all()
    )
    # تجميع المبيعات حسب اليوم
    sales_by_day = {}
    for i in range(30):
        day = start_date + timedelta(days=i)
        sales_by_day[day.strftime('%Y-%m-%d')] = 0
    for sale in sales:
        day = sale.created_at.date().strftime('%Y-%m-%d')
        sales_by_day[day] += sale.total_amount
    labels = list(sales_by_day.keys())
    data = list(sales_by_day.values())
    return jsonify({'labels': labels, 'data': data})