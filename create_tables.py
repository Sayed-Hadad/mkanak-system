from app import create_app
from models import db

app = create_app()

with app.app_context():
    db.create_all()
    print('تم إنشاء جميع الجداول بنجاح (بما فيها جداول المبيعات الجديدة).')