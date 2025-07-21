from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models.customer import Customer
import pandas as pd
from flask import send_file
from models import db

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
@login_required
def list_customers():
    if not (current_user.is_admin() or current_user.is_branch_user()):
        return 'غير مصرح', 403
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'created_at')
    customers = Customer.query
    if q:
        customers = customers.filter((Customer.name.contains(q)) | (Customer.phone.contains(q)))
    if sort == 'name':
        customers = customers.order_by(Customer.name)
    elif sort == 'phone':
        customers = customers.order_by(Customer.phone)
    else:
        customers = customers.order_by(Customer.created_at.desc())
    customers = customers.all()
    return render_template('customers/list.html', customers=customers, q=q, sort=sort)

@customers_bp.route('/export')
@login_required
def export_customers():
    if not (current_user.is_admin() or current_user.is_branch_user()):
        return 'غير مصرح', 403
    customers = Customer.query.order_by(Customer.created_at.desc()).all()
    data = [{
        'الاسم': c.name,
        'رقم الهاتف': c.phone,
        'تاريخ الإضافة': c.created_at.strftime('%Y-%m-%d %H:%M')
    } for c in customers]
    df = pd.DataFrame(data)
    file_path = 'customers_export.xlsx'
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@customers_bp.route('/delete/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    if not (current_user.is_admin() or current_user.is_branch_user()):
        return 'غير مصرح', 403
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    return 'success'

@customers_bp.route('/edit/<int:customer_id>', methods=['POST'])
@login_required
def edit_customer(customer_id):
    if not (current_user.is_admin() or current_user.is_branch_user()):
        return 'غير مصرح', 403
    customer = Customer.query.get_or_404(customer_id)
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    if name:
        customer.name = name
    if phone:
        customer.phone = phone
    db.session.commit()
    return 'success'