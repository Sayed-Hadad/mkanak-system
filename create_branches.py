from app import create_app
from models import db
from models.branch import Branch

branches = [
    'فرع شارع المركز',
    'فرع عبد العزيز',
    'فرع كفر الشيخ'
]

app = create_app()
with app.app_context():
    for name in branches:
        if not Branch.query.filter_by(name=name).first():
            db.session.add(Branch(name=name))
    db.session.commit()
    print('تمت إضافة الفروع الافتراضية بنجاح.')