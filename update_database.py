#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script لتحديث قاعدة البيانات مع النماذج الجديدة
"""

from app import create_app
from models import db
from models.user import User
from models.branch import Branch
from models.product import Product
from models.category import Category
from models.dealer import Dealer
from models.movement import ProductMovement
from models.request import ProductRequest
from models.notification import BranchNotification
from models.branch_inventory import BranchInventory
from sqlalchemy import text

def update_database():
    """تحديث قاعدة البيانات مع النماذج الجديدة"""
    app = create_app()

    with app.app_context():
        print("🔄 جاري تحديث قاعدة البيانات...")

        # إنشاء جميع الجداول
        db.create_all()

        print("✅ تم إنشاء جميع الجداول بنجاح!")

        # التحقق من وجود المدير
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("👤 إنشاء حساب المدير...")
            admin = User(
                username='admin',
                role='admin',
                full_name='مدير النظام',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ تم إنشاء حساب المدير بنجاح!")
        else:
            print("✅ حساب المدير موجود بالفعل")

        # التحقق من وجود الفروع
        branches = Branch.query.all()
        if not branches:
            print("🏢 إنشاء الفروع الافتراضية...")
            default_branches = [
                Branch(name='المخزن المركزي', address='العنوان الرئيسي', phone='0123456789', manager='مدير المخزن المركزي'),
                Branch(name='فرع شارع عبد العزيز', address='شارع عبد العزيز', phone='0123456790', manager='مدير فرع شارع عبد العزيز'),
                Branch(name='فرع مكانك ستور', address='مكانك ستور', phone='0123456791', manager='مدير فرع مكانك ستور'),
                Branch(name='فرع كفر الشيخ', address='كفر الشيخ', phone='0123456792', manager='مدير فرع كفر الشيخ'),
                Branch(name='فرع شارع المركز', address='شارع المركز', phone='0123456793', manager='مدير فرع شارع المركز')
            ]

            for branch in default_branches:
                db.session.add(branch)

            db.session.commit()
            print("✅ تم إنشاء الفروع الافتراضية بنجاح!")
        else:
            print(f"✅ يوجد {len(branches)} فرع بالفعل")

        # إنشاء مديري الفروع دومًا إذا لم يكونوا موجودين
        print("👥 إنشاء مديري الفروع...")
        branches = Branch.query.filter(Branch.name != 'المخزن المركزي').all()

        branch_credentials = {
            'فرع شارع عبد العزيز': {'username': 'abdaziz_branch', 'password': '123abdaziz'},
            'فرع مكانك ستور': {'username': 'mkanak_store', 'password': '123mkanak'},
            'فرع كفر الشيخ': {'username': 'kafr_branch', 'password': '123kafr'},
            'فرع شارع المركز': {'username': 'markaz_branch', 'password': '123markaz'}
        }

        for branch in branches:
            if branch.name in branch_credentials:
                credentials = branch_credentials[branch.name]
                manager = User.query.filter_by(username=credentials['username']).first()
                if not manager:
                    manager = User(
                        username=credentials['username'],
                        role='branch_manager',
                        full_name=branch.manager,
                        branch_id=branch.id,
                        is_active=True
                    )
                    manager.set_password(credentials['password'])
                    db.session.add(manager)
                    print(f"✅ تم إنشاء مدير {branch.name}: {credentials['username']}")
                else:
                    # تأكد من ربط المدير بالفرع الصحيح وتحديث بياناته
                    manager.branch_id = branch.id
                    manager.full_name = branch.manager
                    manager.role = 'branch_manager'
                    manager.is_active = True
                    db.session.add(manager)
                    print(f"🔄 تم تحديث بيانات مدير {branch.name}: {credentials['username']}")
            else:
                print(f"⚠️  لا توجد بيانات لفرع: {branch.name}")
        db.session.commit()
        print("✅ تم إنشاء وتحديث جميع مديري الفروع بنجاح!")

        print("\n🎉 تم تحديث قاعدة البيانات بنجاح!")
        print("\n📋 معلومات الحسابات:")
        print("👑 المدير الرئيسي: admin / admin123")
        print("\n👥 مديري الفروع:")
        for branch_name, credentials in branch_credentials.items():
            print(f"🏢 {branch_name}: {credentials['username']} / {credentials['password']}")
        print("\n🚀 يمكنك الآن تشغيل النظام!")

def add_new_sale_columns():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # إضافة customer_name
            try:
                conn.execute(text("ALTER TABLE sales ADD COLUMN customer_name VARCHAR(128)"))
            except Exception as e:
                print('customer_name:', e)
            # إضافة sale_type
            try:
                conn.execute(text("ALTER TABLE sales ADD COLUMN sale_type VARCHAR(16) NOT NULL DEFAULT 'cash'"))
            except Exception as e:
                print('sale_type:', e)
            # إضافة note
            try:
                conn.execute(text("ALTER TABLE sales ADD COLUMN note VARCHAR(255)"))
            except Exception as e:
                print('note:', e)

def add_customers_table_and_column():
    with db.engine.connect() as conn:
        # إنشاء جدول العملاء إذا لم يكن موجودًا
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(128),
                    phone VARCHAR(32),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
        except Exception as e:
            print('customers table:', e)
        # إضافة customer_id إلى جدول sales
        try:
            conn.execute(text("ALTER TABLE sales ADD COLUMN customer_id INTEGER REFERENCES customers(id)"))
        except Exception as e:
            print('customer_id:', e)

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_database()
        add_new_sale_columns()
        add_customers_table_and_column()
        print('تم تحديث جدول المبيعات وجدول العملاء بنجاح.')