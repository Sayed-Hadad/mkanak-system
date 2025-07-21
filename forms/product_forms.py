from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ProductForm(FlaskForm):
    name = StringField('اسم المنتج', validators=[DataRequired()])
    category = SelectField('الصنف', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('الكمية', validators=[DataRequired(), NumberRange(min=0)])
    price = FloatField('السعر', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('حفظ')