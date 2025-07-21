from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models.dealer import Dealer
from forms.dealer_forms import DealerForm
from models import db
from routes.auth import admin_required

dealers_bp = Blueprint('dealers', __name__, url_prefix='/dealers')

@dealers_bp.route('/')
@login_required
def list_dealers():
    dealers = Dealer.query.order_by(Dealer.name).all()
    return render_template('dealers/list.html', title='إدارة التجار', dealers=dealers)

@dealers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_dealer():
    form = DealerForm()
    if form.validate_on_submit():
        dealer = Dealer(
            name=form.name.data,
            phone=form.phone.data,
            address=form.address.data,
            notes=form.notes.data
        )
        db.session.add(dealer)
        db.session.commit()
        flash('تمت إضافة التاجر بنجاح', 'success')
        return redirect(url_for('dealers.list_dealers'))
    return render_template('dealers/add.html', title='إضافة تاجر', form=form)

@dealers_bp.route('/edit/<int:dealer_id>', methods=['GET', 'POST'])
@login_required
def edit_dealer(dealer_id):
    dealer = Dealer.query.get_or_404(dealer_id)
    form = DealerForm(obj=dealer)
    if form.validate_on_submit():
        dealer.name = form.name.data
        dealer.phone = form.phone.data
        dealer.address = form.address.data
        dealer.notes = form.notes.data
        db.session.commit()
        flash('تم تعديل بيانات التاجر بنجاح', 'success')
        return redirect(url_for('dealers.list_dealers'))
    return render_template('dealers/add.html', title='تعديل تاجر', form=form)

@dealers_bp.route('/delete/<int:dealer_id>', methods=['POST'])
@login_required
@admin_required
def delete_dealer(dealer_id):
    dealer = Dealer.query.get_or_404(dealer_id)

    # التحقق من وجود حركات مرتبطة بالتاجر
    from models.movement import ProductMovement
    has_movements = ProductMovement.query.filter(
        ((ProductMovement.source_type == 'dealer') & (ProductMovement.source_id == dealer_id)) |
        ((ProductMovement.destination_type == 'dealer') & (ProductMovement.destination_id == dealer_id))
    ).count() > 0

    if has_movements:
        flash('لا يمكن حذف التاجر لوجود حركات مرتبطة به!', 'danger')
    else:
        db.session.delete(dealer)
        db.session.commit()
        flash('تم حذف التاجر بنجاح', 'success')

    return redirect(url_for('dealers.list_dealers'))

@dealers_bp.route('/api/add', methods=['POST'])
def api_add_dealer():
    data = request.json or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    notes = data.get('notes', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'اسم التاجر مطلوب'}), 400
    existing = Dealer.query.filter_by(name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'التاجر موجود بالفعل', 'id': existing.id, 'name': existing.name}), 200
    dealer = Dealer(name=name, phone=phone, address=address, notes=notes)
    db.session.add(dealer)
    db.session.commit()
    return jsonify({'success': True, 'id': dealer.id, 'name': dealer.name}), 201

@dealers_bp.route('/api/list', methods=['GET'])
def api_list_dealers():
    dealers = Dealer.query.order_by(Dealer.name).all()
    return jsonify([{'id': d.id, 'name': d.name} for d in dealers])