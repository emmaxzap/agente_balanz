from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

class LoginForm(FlaskForm):
    """
    Formulario de inicio de sesión
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class RegistroForm(FlaskForm):
    """
    Formulario de registro de usuario
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=12, message="La contraseña debe tener al menos 12 caracteres"),
        Regexp(r'.*[A-Z].*', message="La contraseña debe contener al menos una letra mayúscula"),
        Regexp(r'.*[a-z].*', message="La contraseña debe contener al menos una letra minúscula"),
        Regexp(r'.*[0-9].*', message="La contraseña debe contener al menos un número"),
        Regexp(r'.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\/-].*', message="La contraseña debe contener al menos un carácter especial")
    ])
    confirm_password = PasswordField('Confirmar Contraseña',
                                   validators=[DataRequired(), EqualTo('password')])
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    # Reemplaza la definición duplicada por esta única definición
    pais = SelectField('País', choices=[
        ('', 'Seleccione un país'),
        ('Argentina', 'Argentina'),
        ('Bolivia', 'Bolivia'),
        ('Brasil', 'Brasil'),
        ('Chile', 'Chile'),
        ('Colombia', 'Colombia'),
        ('Ecuador', 'Ecuador'),
        ('Guyana', 'Guyana'),
        ('Paraguay', 'Paraguay'),
        ('Perú', 'Perú'),
        ('Surinam', 'Surinam'),
        ('Uruguay', 'Uruguay'),
        ('Venezuela', 'Venezuela')
    ])
    telefono = StringField('Teléfono (opcional)')
    acepta_marketing = BooleanField('Acepto recibir novedades y ofertas')
    submit = SubmitField('Registrarse')

class VerificarCodeForm(FlaskForm):
    """
    Formulario para verificación de código 2FA
    """
    codigo = StringField('Código de verificación', 
                       validators=[
                           DataRequired(), 
                           Length(min=6, max=6, message="El código debe tener 6 dígitos")
                       ])
    submit = SubmitField('Verificar')

class VerificarSeguridadForm(FlaskForm):
    """
    Formulario para verificación de preguntas de seguridad
    """
    respuesta1 = StringField('Respuesta 1', validators=[DataRequired()])
    respuesta2 = StringField('Respuesta 2', validators=[DataRequired()])
    submit = SubmitField('Verificar')

class CambioPasswordForm(FlaskForm):
    """
    Formulario para cambio de contraseña
    """
    password_actual = PasswordField('Contraseña Actual', validators=[DataRequired()])
    password_nuevo = PasswordField('Nueva Contraseña', validators=[
        DataRequired(),
        Length(min=12, message="La contraseña debe tener al menos 12 caracteres"),
        Regexp(r'.*[A-Z].*', message="La contraseña debe contener al menos una letra mayúscula"),
        Regexp(r'.*[a-z].*', message="La contraseña debe contener al menos una letra minúscula"),
        Regexp(r'.*[0-9].*', message="La contraseña debe contener al menos un número"),
        Regexp(r'.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\/-].*', message="La contraseña debe contener al menos un carácter especial")
    ])
    confirmar_password = PasswordField('Confirmar Nueva Contraseña', 
                                     validators=[DataRequired(), EqualTo('password_nuevo')])
    submit = SubmitField('Cambiar Contraseña')

class RecuperarPasswordForm(FlaskForm):
    """
    Formulario para solicitar recuperación de contraseña
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar Enlace de Recuperación')

class RestablecerPasswordForm(FlaskForm):
    """
    Formulario para restablecer contraseña
    """
    password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(),
        Length(min=12, message="La contraseña debe tener al menos 12 caracteres"),
        Regexp(r'.*[A-Z].*', message="La contraseña debe contener al menos una letra mayúscula"),
        Regexp(r'.*[a-z].*', message="La contraseña debe contener al menos una letra minúscula"),
        Regexp(r'.*[0-9].*', message="La contraseña debe contener al menos un número"),
        Regexp(r'.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\/-].*', message="La contraseña debe contener al menos un carácter especial")
    ])
    confirm_password = PasswordField('Confirmar Contraseña', 
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Restablecer Contraseña')

class BuscarUsuarioForm(FlaskForm):
    """
    Formulario para buscar un usuario por email
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Continuar')

class NuevoPasswordForm(FlaskForm):
    """
    Formulario para establecer una nueva contraseña
    """
    password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(),
        Length(min=12, message="La contraseña debe tener al menos 12 caracteres"),
        Regexp(r'.*[A-Z].*', message="La contraseña debe contener al menos una letra mayúscula"),
        Regexp(r'.*[a-z].*', message="La contraseña debe contener al menos una letra minúscula"),
        Regexp(r'.*[0-9].*', message="La contraseña debe contener al menos un número"),
        Regexp(r'.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\/-].*', message="La contraseña debe contener al menos un carácter especial")
    ])
    confirm_password = PasswordField('Confirmar Contraseña', 
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Cambiar Contraseña')