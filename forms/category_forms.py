from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class CategoryForm(FlaskForm):
    name = StringField('اسم الصنف', validators=[DataRequired()])
    submit = SubmitField('حفظ')