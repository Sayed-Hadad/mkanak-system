from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    shift = SelectField('الوردية', choices=[('morning', 'صباحية'), ('evening', 'مسائية')], validators=[DataRequired()])
    submit = SubmitField('تسجيل الدخول')

class RegisterForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password', message='كلمة المرور غير متطابقة')])
    shift = SelectField('الوردية', choices=[('morning', 'صباحية'), ('evening', 'مسائية')], validators=[DataRequired()])
    submit = SubmitField('تسجيل حساب جديد')