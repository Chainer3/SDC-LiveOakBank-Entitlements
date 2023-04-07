from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, RadioField
from wtforms.validators import InputRequired, Length


class CreateAccountForm(FlaskForm):
    accountId = StringField(
        "Account ID",
        validators=[InputRequired(), Length(min=1, max=100)],
    )
    balance = IntegerField("Account Balance", validators=[InputRequired()])
