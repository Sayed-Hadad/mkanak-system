from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, StringField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, NumberRange, Optional

class ProductQtyForm(FlaskForm):
    product = SelectField('المنتج', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('الكمية', validators=[DataRequired(), NumberRange(min=1)])

class MovementForm(FlaskForm):
    products = FieldList(FormField(ProductQtyForm), min_entries=1)
    source_type = SelectField('نوع المصدر', choices=[('warehouse', 'المخزن الرئيسي'), ('branch', 'فرع'), ('dealer', 'تاجر')], validators=[DataRequired()])
    source_id = SelectField('المصدر', coerce=int, validators=[Optional()])
    destination_type = SelectField('نوع الوجهة', choices=[('branch', 'فرع'), ('dealer', 'تاجر'), ('warehouse', 'المخزن الرئيسي')], validators=[DataRequired()])
    destination_id = SelectField('الوجهة', coerce=int, validators=[Optional()])
    type = SelectField('نوع الحركة', choices=[('in', 'دخول'), ('out', 'خروج'), ('transfer', 'تحويل')], validators=[DataRequired()])
    shift = SelectField('الوردية', choices=[('morning', 'صباحية'), ('evening', 'مسائية')], validators=[DataRequired()])
    notes = StringField('ملاحظات', validators=[Optional()])
    submit = SubmitField('حفظ الحركة')
    dealer_source_id = SelectField('التاجر (مصدر)', coerce=int, validators=[Optional()])
    dealer_destination_id = SelectField('التاجر (وجهة)', coerce=int, validators=[Optional()])
    new_product_name = StringField('اسم المنتج الجديد', validators=[Optional()])
    new_product_category = SelectField('صنف المنتج الجديد', coerce=int, validators=[Optional()])
    new_product_price = StringField('سعر المنتج الجديد', validators=[Optional()])