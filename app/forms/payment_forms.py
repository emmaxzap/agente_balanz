from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField, SelectField, HiddenField
from wtforms.validators import DataRequired, NumberRange

class CompraForm(FlaskForm):
    """
    Formulario para compra de créditos
    """
    cantidad = IntegerField('Cantidad de créditos', 
                       validators=[
                           DataRequired(), 
                           NumberRange(min=1, max=500, message="La cantidad debe estar entre 1 y 500")
                       ])
    submit = SubmitField('Continuar')

class CompraPlanForm(FlaskForm):
    """
    Formulario para compra de planes de suscripción
    """
    plan_id = SelectField('Plan', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Comprar Plan')

class RecargaCreditosForm(FlaskForm):
    """
    Formulario para recarga de créditos (solo disponible con plan activo)
    """
    cantidad = IntegerField('Cantidad de créditos', 
                       validators=[
                           DataRequired(), 
                           NumberRange(min=1, max=500, message="La cantidad debe estar entre 1 y 500")
                       ])
    submit = SubmitField('Recargar Créditos')