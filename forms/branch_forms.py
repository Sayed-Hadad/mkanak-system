from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class BranchForm(FlaskForm):
    name = StringField('اسم الفرع', validators=[DataRequired(), Length(max=64)])
    submit = SubmitField('حفظ الفرع')