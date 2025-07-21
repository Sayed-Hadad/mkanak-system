from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Optional

class DealerForm(FlaskForm):
    name = StringField('اسم التاجر', validators=[DataRequired()])
    phone = StringField('رقم الهاتف', validators=[Optional()])
    address = StringField('العنوان', validators=[Optional()])
    notes = StringField('ملاحظات', validators=[Optional()])
    submit = SubmitField('حفظ')