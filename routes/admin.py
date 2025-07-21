from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from routes.auth import admin_required
from models.user import User
from models import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.all()
    return render_template('admin/users.html', title='إدارة المستخدمين', users=users)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('لا يمكنك حذف نفسك!', 'danger')
        return redirect(url_for('admin.list_users'))
    db.session.delete(user)
    db.session.commit()
    flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/users/toggle_role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('لا يمكنك تغيير صلاحيتك بنفسك!', 'danger')
        return redirect(url_for('admin.list_users'))
    if user.is_admin():
        user.role = 'user'
        flash('تم تخفيض المستخدم إلى مستخدم عادي', 'success')
    else:
        user.role = 'admin'
        flash('تم ترقية المستخدم إلى مدير', 'success')
    db.session.commit()
    return redirect(url_for('admin.list_users'))