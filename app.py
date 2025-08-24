import os
import time
import html
import atexit
import hashlib
import requests
from datetime import datetime, timedelta
from functools import wraps
import secrets
import uuid
import json
import smtplib
import io
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pyotp
import qrcode

# Seguridad y limitación de solicitudes
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from apscheduler.schedulers.background import BackgroundScheduler
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Flask y formularios
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

# Conexión a base de datos y servicios externos
from dotenv import load_dotenv
from app.models.database_pg import client, ScalarQueryParameter, QueryJobConfig, execute_query
from app.models.database_pg import (
    usuarios_table_id, logins_table_id, transacciones_table_id,
    planes_creditos_table_id, servicios_table_id, uso_creditos_table_id,
    logs_sistema_table_id, recovery_tokens_table_id, historial_passwords_table_id
)
from paypalrestsdk import Payment
import paypalrestsdk

# Cargar variables desde el archivo .env
load_dotenv()

# Configuración de la aplicación
app = Flask(__name__)
csrf = CSRFProtect(app)

# Configuración de seguridad para la sesión
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-temporal')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hora
app.config['SESSION_COOKIE_SECURE'] = True  # Solo HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No accesible via JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Protección contra CSRF
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Sesión expira en 1 hora
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_USE_SIGNER'] = True

# Configurar Jinja2 para escapar automáticamente
app.jinja_env.autoescape = True

# Configurar límites de solicitudes
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuración de seguridad con Talisman (cabeceras HTTP)
talisman = Talisman(
    app,
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "https://cdn.jsdelivr.net"],
        'style-src': ["'self'", "https://cdn.jsdelivr.net"],
        'img-src': ["'self'", "data:"],
        'font-src': ["'self'", "https://cdn.jsdelivr.net"],
    },
    force_https=True,  # Forzar HTTPS
    strict_transport_security=True,  # HSTS
    session_cookie_secure=True,
    session_cookie_http_only=True,
    feature_policy={
        'geolocation': "'none'",
        'microphone': "'none'",
        'camera': "'none'"
    }
)

# Desactivar algunas restricciones en desarrollo
if os.environ.get('FLASK_ENV') == 'development':
    talisman.content_security_policy_report_only = True
    talisman.force_https = False
    app.config['SESSION_COOKIE_SECURE'] = False

# Configuración de servidor
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SERVER_NAME'] = 'trackingdatax.com'
else:
    # No configurar SERVER_NAME en desarrollo
    pass

# Configuración de PayPal con enfoque directo
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": os.environ.get('PAYPAL_CLIENT_ID', ''),
    "client_secret": os.environ.get('PAYPAL_SECRET', '')
})

# Imprimir información de configuración para verificar
print("PayPal configurado en modo: sandbox")
print("Client ID configurado:", "Sí" if os.environ.get('PAYPAL_CLIENT_ID') else "No")
print("Secret configurado:", "Sí" if os.environ.get('PAYPAL_SECRET') else "No")

# Configuración de Argon2 para hash de contraseñas
ph = PasswordHasher(
    time_cost=3,  # Número de iteraciones
    memory_cost=65536,  # 64MB
    parallelism=4,  # Número de hilos paralelos
    hash_len=32,  # Tamaño de la salida en bytes
    salt_len=16   # Tamaño de la sal en bytes
)

# Configuración del planificador para rotación de claves
scheduler = BackgroundScheduler()

# Funciones de utilidad

def rotate_session_key():
    """Rota la clave de sesión periódicamente"""
    new_key = secrets.token_hex(32)
    app.config['SECRET_KEY'] = new_key
    log_security_event(
        user_id=None,
        event_type='key_rotation',
        details={'tipo': 'session_key'},
        ip_address='internal'
    )
    print("Clave de sesión rotada exitosamente")

# Programar rotación cada 24 horas
scheduler.add_job(rotate_session_key, 'interval', hours=24)
scheduler.start()

# Asegurar que el planificador se cierre correctamente
atexit.register(lambda: scheduler.shutdown())

def generate_password_hash(password):
    """Genera un hash seguro usando Argon2"""
    return ph.hash(password)

def check_password_hash(hash_value, password):
    """Verifica una contraseña contra un hash Argon2"""
    try:
        return ph.verify(hash_value, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Fallback para contraseñas antiguas (werkzeug)
        from werkzeug.security import check_password_hash as werkzeug_check
        return werkzeug_check(hash_value, password)

def generate_totp_secret():
    """Genera un secreto para TOTP"""
    return pyotp.random_base32()

def get_totp_uri(secret, email, issuer_name="Sistema de Créditos"):
    """Genera un URI para TOTP que se puede usar para generar un código QR"""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer_name)

def generate_qr_code(uri):
    """Genera un código QR como imagen en base64"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def verify_totp(secret, code):
    """Verifica un código TOTP con protección contra ataques de temporización"""
    totp = pyotp.TOTP(secret)
    # Verifica el código actual y el anterior/siguiente para dar margen por desincronización
    return totp.verify(code, valid_window=1)

def generate_secure_token():
    """Genera un token seguro para recuperación de contraseña"""
    return secrets.token_urlsafe(32)

def sanitize_output(text):
    """Sanitiza texto para prevenir XSS"""
    if text is None:
        return ""
    return html.escape(str(text))

def is_password_pwned(password):
    """Verifica si la contraseña ha sido comprometida usando la API HaveIBeenPwned"""
    # Calcular SHA-1 hash de la contraseña
    password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    # Usar los primeros 5 caracteres para consultar la API
    prefix = password_hash[:5]
    suffix = password_hash[5:]
    
    try:
        # Consultar la API
        response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}")
        if response.status_code == 200:
            # Buscar el sufijo en la respuesta
            for line in response.text.splitlines():
                if line.split(':')[0] == suffix:
                    # La contraseña ha sido comprometida
                    return True
        return False
    except Exception:
        # En caso de error, permitir la contraseña por defecto
        return False

def log_security_event(user_id, event_type, details, ip_address):
    """Registra eventos de seguridad en la tabla de logs"""
    log_id = str(uuid.uuid4())
    rows_to_insert = [{
        'log_id': log_id,
        'user_id': user_id,
        'tipo': 'security',
        'subtipo': event_type,
        'modulo': 'auth',
        'accion': event_type,
        'detalles': json.dumps(details),
        'fecha': datetime.now().isoformat(),
        'ip_address': ip_address
    }]
    
    try:
        client.insert_rows_json(logs_sistema_table_id, rows_to_insert)
        return True
    except Exception as e:
        print(f"Error al registrar evento de seguridad: {str(e)}")
        return False

def enviar_email_recuperacion(email, user_id):
    """Envía un email con token de recuperación de contraseña"""
    try:
        # Generar token único
        token = generate_secure_token()
        
        # Establecer tiempo de expiración (24 horas)
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=24)
        
        # Almacenar token en la base de datos
        token_id = str(uuid.uuid4())
        rows_to_insert = [{
            'token_id': token_id,
            'user_id': user_id,
            'token': token,
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'used': False
        }]
        
        client.insert_rows_json(recovery_tokens_table_id, rows_to_insert)
        
        # Configuración del email
        remitente = os.environ.get('EMAIL_SENDER', 'info@trackingdatax.com')
        password = os.environ.get('EMAIL_PASSWORD', '')
        
        # Opción 1: Usando SSL en puerto 465 (recomendado por Hostinger)
        servidor_smtp = 'smtp.hostinger.com'
        puerto_smtp = 465
        usar_ssl = True
        
        print(f"Intentando enviar email a {email} usando {servidor_smtp}:{puerto_smtp} con SSL={usar_ssl}")
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = f"Sistema de Créditos <{remitente}>"
        msg['To'] = email
        msg['Subject'] = 'Recuperación de contraseña - TrackingDataX'
        
        # URL para resetear la contraseña
        reset_url = url_for('restablecer_password', token=token, _external=True)
        
        # Cuerpo del mensaje
        text = f"""
        Recuperación de contraseña - TrackingDataX
        
        Has solicitado restablecer tu contraseña para tu cuenta en TrackingDataX.
        Para crear una nueva contraseña, visita el siguiente enlace:
        
        {reset_url}
        
        Este enlace es válido por 24 horas.
        
        Si no solicitaste este cambio, puedes ignorar este mensaje y tu contraseña seguirá siendo la misma.
        
        TrackingDataX
        """
        
        msg.attach(MIMEText(text, 'plain'))
        
        # Conectar al servidor
        try:
            if usar_ssl:
                print("Conectando con SSL...")
                server = smtplib.SMTP_SSL(servidor_smtp, puerto_smtp)
            else:
                print("Conectando con TLS...")
                server = smtplib.SMTP(servidor_smtp, puerto_smtp)
                server.starttls()
            
            print(f"Iniciando sesión con {remitente}...")
            server.login(remitente, password)
            print("Sesión iniciada correctamente")
            
            texto = msg.as_string()
            print("Enviando email...")
            server.sendmail(remitente, email, texto)
            print("Email enviado correctamente")
            server.quit()
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=user_id,
                event_type='password_recovery_email',
                details={'email': email},
                ip_address=request.remote_addr
            )
            
            return True
            
        except Exception as e:
            print(f"Error en la conexión SMTP: {str(e)}")
            print("Intentando método alternativo...")
            
            # Opción 2: Intentar con TLS en puerto 587
            try:
                servidor_smtp = 'smtp.hostinger.com'
                puerto_smtp = 587
                print(f"Intentando con TLS en puerto {puerto_smtp}...")
                
                server = smtplib.SMTP(servidor_smtp, puerto_smtp)
                server.starttls()
                server.login(remitente, password)
                server.sendmail(remitente, email, texto)
                server.quit()
                print("Email enviado correctamente con TLS")
                
                # Registrar evento de seguridad
                log_security_event(
                    user_id=user_id,
                    event_type='password_recovery_email',
                    details={'email': email, 'method': 'TLS'},
                    ip_address=request.remote_addr
                )
                
                return True
            except Exception as e2:
                print(f"Error en método alternativo: {str(e2)}")
                return False
                
    except Exception as e:
        print(f"Error general en envío de email: {str(e)}")
        return False

# Decorator para verificar si el usuario está autenticado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Formularios
class VerificarCodeForm(FlaskForm):
    codigo = StringField('Código de verificación', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verificar')

class VerificarSeguridadForm(FlaskForm):
    respuesta1 = StringField('Respuesta 1', validators=[DataRequired()])
    respuesta2 = StringField('Respuesta 2', validators=[DataRequired()])
    submit = SubmitField('Verificar')

class RegistroForm(FlaskForm):
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
    pais = StringField('País')
    telefono = StringField('Teléfono (opcional)')
    acepta_marketing = BooleanField('Acepto recibir novedades y ofertas')
    submit = SubmitField('Registrarse')

class BuscarUsuarioForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Continuar')

class NuevoPasswordForm(FlaskForm):
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

class CambioPasswordForm(FlaskForm):
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
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar Enlace de Recuperación')

class RestablecerPasswordForm(FlaskForm):
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

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class CompraForm(FlaskForm):
    cantidad = IntegerField('Cantidad de Créditos', validators=[DataRequired()])
    submit = SubmitField('Comprar Créditos')

# Rutas

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        # Verificar si la contraseña ha sido comprometida
        if is_password_pwned(form.password.data):
            flash('Esta contraseña ha aparecido en filtraciones de datos. Por favor, elija una contraseña más segura.', 'danger')
            return render_template('registro.html', form=form)
            
        # Verificar si el usuario ya existe
        query = f"SELECT email FROM {usuarios_table_id} WHERE email = %s"
        results = execute_query(query, [form.email.data])
        
        if len(results) > 0:
            flash('Este email ya está registrado. Por favor use otro.', 'danger')
            log_security_event(
                user_id=None,
                event_type='registration_duplicate',
                details={'email': form.email.data},
                ip_address=request.remote_addr
            )
            return render_template('registro.html', form=form)
        
        # Crear nuevo usuario con los campos actualizados
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(form.password.data)
        
        # Insertar en PostgreSQL con los campos adicionales
        query = f"""
        INSERT INTO {usuarios_table_id} 
        (user_id, email, password_hash, nombre, apellido, telefono, pais, 
         fecha_registro, ultimo_login, estado, creditos, tipo_usuario, acepta_marketing) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = [
            user_id,
            form.email.data,
            password_hash,
            form.nombre.data,
            form.apellido.data,
            form.telefono.data if hasattr(form, 'telefono') and form.telefono.data else None,
            form.pais.data if hasattr(form, 'pais') and form.pais.data else None,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            'activo',
            0,
            'normal',
            form.acepta_marketing.data if hasattr(form, 'acepta_marketing') else False
        ]
        
        try:
            execute_query(query, params, fetch=False)
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=user_id,
                event_type='user_registration',
                details={'email': form.email.data},
                ip_address=request.remote_addr
            )
            
            flash('¡Registro exitoso! Ahora puede iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error al registrar usuario: {str(e)}")
            flash('Error al registrar el usuario. Por favor intente más tarde.', 'danger')
            return render_template('registro.html', form=form)
    
    return render_template('registro.html', form=form)

@app.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    form = CambioPasswordForm()
    if form.validate_on_submit():
        # Verificar si la contraseña ha sido comprometida
        if is_password_pwned(form.password_nuevo.data):
            flash('Esta contraseña ha aparecido en filtraciones de datos. Por favor, elija una contraseña más segura.', 'danger')
            return render_template('cambiar_password.html', form=form)
            
        # Obtener el hash de la contraseña actual del usuario
        query = f"SELECT password_hash FROM {usuarios_table_id} WHERE user_id = %s"
        results = execute_query(query, [session['user_id']])
        
        if not results:
            flash('Error al verificar la contraseña. Por favor intente más tarde.', 'danger')
            return render_template('cambiar_password.html', form=form)
        
        user_data = results[0]
        
        # Verificar que la contraseña actual sea correcta
        if not check_password_hash(user_data['password_hash'], form.password_actual.data):
            # Registrar intento fallido
            log_security_event(
                user_id=session['user_id'],
                event_type='password_change_failed',
                details={'reason': 'incorrect_current_password'},
                ip_address=request.remote_addr
            )
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('cambiar_password.html', form=form)
        
        # Verificar que la nueva contraseña no esté en el historial (últimas 3)
        query = f"""
        SELECT password_hash 
        FROM {historial_passwords_table_id} 
        WHERE user_id = %s
        ORDER BY fecha_creacion DESC
        LIMIT 3
        """
        results = execute_query(query, [session['user_id']])
        
        for row in results:
            if check_password_hash(row['password_hash'], form.password_nuevo.data):
                flash('La nueva contraseña no puede ser igual a una de tus contraseñas anteriores.', 'danger')
                return render_template('cambiar_password.html', form=form)
        
        # Generar hash de la nueva contraseña
        new_password_hash = generate_password_hash(form.password_nuevo.data)
        
        # Guardar la contraseña actual en el historial
        historial_id = str(uuid.uuid4())
        query = f"""
        INSERT INTO {historial_passwords_table_id}
        (historial_id, user_id, password_hash, fecha_creacion)
        VALUES (%s, %s, %s, %s)
        """
        execute_query(
            query, 
            [historial_id, session['user_id'], user_data['password_hash'], datetime.now().isoformat()],
            fetch=False
        )
        
        # Actualizar la contraseña del usuario
        query = f"UPDATE {usuarios_table_id} SET password_hash = %s WHERE user_id = %s"
        execute_query(query, [new_password_hash, session['user_id']], fetch=False)
        
        # Registrar evento de seguridad
        log_security_event(
            user_id=session['user_id'],
            event_type='password_changed',
            details={},
            ip_address=request.remote_addr
        )
        
        flash('Tu contraseña ha sido actualizada correctamente.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('cambiar_password.html', form=form)

@app.route('/recuperar_password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def recuperar_password():
    form = RecuperarPasswordForm()
    
    if form.validate_on_submit():
        # Buscar al usuario por email
        query = f"""
        SELECT user_id, email, fecha_registro, totp_secret
        FROM {usuarios_table_id}
        WHERE email = %s
        """
        results = execute_query(query, [form.email.data])
        
        user_found = False
        user_data = None
        
        if results:
            user_found = True
            user_data = results[0]
        
        if user_found:
            # Verificar el tiempo transcurrido desde el registro
            fecha_registro = user_data['fecha_registro']
            if isinstance(fecha_registro, str):
                fecha_registro = datetime.fromisoformat(fecha_registro.replace('Z', '+00:00'))

            # Asegurarnos de que ambas fechas sean del mismo tipo
            if hasattr(fecha_registro, 'tzinfo') and fecha_registro.tzinfo is not None:
                fecha_registro = fecha_registro.replace(tzinfo=None)

            # Calcular diferencia
            tiempo_transcurrido = datetime.now() - fecha_registro
            minutos_transcurridos = tiempo_transcurrido.total_seconds() / 60
            
            # Verificar si han pasado al menos 90 minutos
            if minutos_transcurridos < 90:
                # Registrar evento de intento fallido por tiempo
                log_security_event(
                    user_id=user_data['user_id'],
                    event_type='password_recovery_attempt',
                    details={'reason': 'too_soon_after_registration'},
                    ip_address=request.remote_addr
                )
                minutos_restantes = 90 - minutos_transcurridos
                return render_template('espera_recuperacion.html', minutos_restantes=int(minutos_restantes))
            
            # Si tiene 2FA configurado, redirigir a verificación 2FA
            if user_data.get('totp_secret'):
                session['recovery_user_id'] = user_data['user_id']
                session['recovery_email'] = user_data['email']
                
                # Registrar intento válido
                log_security_event(
                    user_id=user_data['user_id'],
                    event_type='password_recovery_attempt',
                    details={'step': 'initiated_2fa_verification'},
                    ip_address=request.remote_addr
                )
                
                return redirect(url_for('verificar_2fa_recuperacion'))
            else:
                # Si no tiene 2FA, enviar email directamente
                # Generar y guardar token de recuperación
                token = generate_secure_token()
                token_id = str(uuid.uuid4())
                now = datetime.now()
                expires = now + timedelta(hours=24)
                
                query = f"""
                INSERT INTO {recovery_tokens_table_id}
                (token_id, user_id, token, created_at, expires_at, used)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                execute_query(
                    query,
                    [token_id, user_data['user_id'], token, now.isoformat(), expires.isoformat(), False],
                    fetch=False
                )
                
                # Enviar email con el token
                success = enviar_email_recuperacion(user_data['email'], user_data['user_id'])
                
                # Por seguridad, no indicar si el email existe o no
                flash('Si tu email está registrado, recibirás instrucciones para restablecer tu contraseña.', 'info')
                return redirect(url_for('login'))
        else:
            # Por seguridad, retrasamos la respuesta en caso de usuario no encontrado
            time.sleep(1)
            flash('Si tu email está registrado, recibirás instrucciones para restablecer tu contraseña.', 'info')
            
            # Registrar intento con correo inexistente
            log_security_event(
                user_id=None,
                event_type='password_recovery_attempt',
                details={'email': form.email.data, 'reason': 'user_not_found'},
                ip_address=request.remote_addr
            )
            
            return redirect(url_for('login'))
    
    return render_template('recuperar_password.html', form=form)

@app.route('/verificar_2fa_recuperacion', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def verificar_2fa_recuperacion():
    if 'recovery_user_id' not in session:
        flash('Sesión inválida. Por favor, inicia el proceso nuevamente.', 'danger')
        return redirect(url_for('recuperar_password'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        
        # Obtener el secreto TOTP del usuario
        query = f"SELECT totp_secret FROM {usuarios_table_id} WHERE user_id = %s"
        results = execute_query(query, [session['recovery_user_id']])
        
        totp_secret = None
        if results:
            totp_secret = results[0]['totp_secret']
        
        if totp_secret and verify_totp(totp_secret, code):
            # Autenticación exitosa
            # Generar y guardar token de recuperación
            token = generate_secure_token()
            token_id = str(uuid.uuid4())
            now = datetime.now()
            expires = now + timedelta(hours=24)
            
            query = f"""
            INSERT INTO {recovery_tokens_table_id}
            (token_id, user_id, token, created_at, expires_at, used)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            execute_query(
                query,
                [token_id, session['recovery_user_id'], token, now.isoformat(), expires.isoformat(), False],
                fetch=False
            )
            
            # Registrar evento de verificación exitosa
            log_security_event(
                user_id=session['recovery_user_id'],
                event_type='2fa_recovery_verification',
                details={'success': True},
                ip_address=request.remote_addr
            )
            
            # Redireccionar al reseteo de contraseña
            session['recovery_verified'] = True
            session['recovery_token'] = token
            return redirect(url_for('restablecer_password', token=token))
        else:
            # Registrar intento fallido
            log_security_event(
                user_id=session['recovery_user_id'],
                event_type='2fa_recovery_verification',
                details={'success': False},
                ip_address=request.remote_addr
            )
            flash('Código incorrecto. Intenta nuevamente.', 'danger')
    
    return render_template('verificar_2fa_recuperacion.html')

@app.route('/restablecer_password', methods=['GET', 'POST'])
def restablecer_password():
    token = request.args.get('token', '')
    
    # Verificación de token
    if not token:
        flash('Token inválido o expirado. Por favor, solicita un nuevo enlace de recuperación.', 'danger')
        return redirect(url_for('recuperar_password'))
    
    # Buscar token en la base de datos
    query = f"""
    SELECT token_id, user_id, expires_at, used
    FROM {recovery_tokens_table_id}
    WHERE token = %s
    """
    results = execute_query(query, [token])
    
    token_data = None
    if results:
        token_data = results[0]
    
    # Si el token no existe
    if not token_data:
        flash('Token inválido o expirado. Por favor, solicita un nuevo enlace de recuperación.', 'danger')
        log_security_event(
            user_id=None,
            event_type='password_reset_attempt',
            details={'reason': 'invalid_token'},
            ip_address=request.remote_addr
        )
        return redirect(url_for('recuperar_password'))
    
    # Si el token ya fue usado
    if token_data['used']:
        flash('Este enlace ya ha sido utilizado. Por favor, solicita un nuevo enlace de recuperación.', 'danger')
        log_security_event(
            user_id=token_data['user_id'],
            event_type='password_reset_attempt',
            details={'reason': 'token_already_used'},
            ip_address=request.remote_addr
        )
        return redirect(url_for('recuperar_password'))
    
    # Verificar si el token ha expirado
    expires_at = token_data['expires_at']
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

    # Asegurarnos de que ambas fechas sean del mismo tipo
    if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
        
    if datetime.now() > expires_at:
        flash('El enlace de recuperación ha expirado. Por favor, solicita un nuevo enlace.', 'danger')
        log_security_event(
            user_id=token_data['user_id'],
            event_type='password_reset_attempt',
            details={'reason': 'token_expired'},
            ip_address=request.remote_addr
        )
        return redirect(url_for('recuperar_password'))
    
    # Obtener información del usuario
    query = f"SELECT email FROM {usuarios_table_id} WHERE user_id = %s"
    results = execute_query(query, [token_data['user_id']])
    
    user_email = None
    if results:
        user_email = results[0]['email']
    
    if not user_email:
        flash('Usuario no encontrado. Por favor, contacta a soporte.', 'danger')
        return redirect(url_for('recuperar_password'))
    
    form = RestablecerPasswordForm()
    
    if form.validate_on_submit():
        # Verificar si la contraseña ha sido comprometida
        if is_password_pwned(form.password.data):
            flash('Esta contraseña ha aparecido en filtraciones de datos. Por favor, elija una contraseña más segura.', 'danger')
            return render_template('restablecer_password.html', form=form, email=user_email, token=token)
            
        # Obtener la contraseña actual para guardarla en historial
        query = f"SELECT password_hash FROM {usuarios_table_id} WHERE user_id = %s"
        results = execute_query(query, [token_data['user_id']])
        
        old_password_hash = None
        if results:
            old_password_hash = results[0]['password_hash']
        
        # Generar hash de la nueva contraseña
        new_password_hash = generate_password_hash(form.password.data)
        
        try:
            # Guardar la contraseña actual en el historial
            if old_password_hash:
                historial_id = str(uuid.uuid4())
                query = f"""
                INSERT INTO {historial_passwords_table_id}
                (historial_id, user_id, password_hash, fecha_creacion)
                VALUES (%s, %s, %s, %s)
                """
                execute_query(
                    query,
                    [historial_id, token_data['user_id'], old_password_hash, datetime.now().isoformat()],
                    fetch=False
                )
            
            # Actualizar la contraseña
            query = f"UPDATE {usuarios_table_id} SET password_hash = %s WHERE user_id = %s"
            execute_query(query, [new_password_hash, token_data['user_id']], fetch=False)
            
            # Marcar el token como usado
            query = f"UPDATE {recovery_tokens_table_id} SET used = %s WHERE token_id = %s"
            execute_query(query, [True, token_data['token_id']], fetch=False)
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=token_data['user_id'],
                event_type='password_reset_success',
                details={},
                ip_address=request.remote_addr
            )
            
            # Limpiar variables relacionadas de la sesión
            session.pop('recovery_user_id', None)
            session.pop('recovery_email', None)
            session.pop('recovery_verified', None)
            session.pop('recovery_token', None)
            
            flash('Tu contraseña ha sido restablecida con éxito. Ya puedes iniciar sesión con tu nueva contraseña.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            print(f"Error en recuperación de contraseña: {str(e)}")
            log_security_event(
                user_id=token_data['user_id'],
                event_type='password_reset_error',
                details={'error': str(e)},
                ip_address=request.remote_addr
            )
            flash('Ocurrió un error inesperado. Por favor, intenta nuevamente más tarde.', 'danger')
            return render_template('restablecer_password.html', form=form, email=user_email, token=token)
    
    return render_template('restablecer_password.html', form=form, email=user_email, token=token)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        query = f"""
        SELECT user_id, email, password_hash, nombre, apellido, creditos, totp_secret, estado 
        FROM {usuarios_table_id} 
        WHERE email = %s
        AND estado = 'activo'
        ORDER BY fecha_registro DESC
        LIMIT 1
        """
        results = execute_query(query, [form.email.data])
        
        user = None
        if results:
            row = results[0]
            user = {
                'user_id': row['user_id'],
                'email': row['email'],
                'password_hash': row['password_hash'],
                'nombre': row['nombre'],
                'apellido': row['apellido'],
                'creditos': row['creditos'],
                'totp_secret': row.get('totp_secret')  # Manejar si el campo no existe
            }
        
        if not user:
            # Registrar intento fallido - usuario no encontrado
            log_security_event(
                user_id=None,
                event_type='login_failed',
                details={'email': form.email.data, 'reason': 'user_not_found'},
                ip_address=request.remote_addr
            )
            # Tiempo de espera para prevenir timing attacks
            time.sleep(1)
            flash('Inicio de sesión fallido. Verifique su email y contraseña.', 'danger')
            return render_template('login.html', form=form)
            
        # Verificar contraseña
        if check_password_hash(user['password_hash'], form.password.data):
            # Si tiene 2FA configurado
            if user.get('totp_secret'):
                # Almacenar datos pre-autenticación
                session['pre_auth_user_id'] = user['user_id']
                session['pre_auth_email'] = user['email']
                session['pre_auth_nombre'] = user['nombre']
                
                # Registrar intento exitoso - primera etapa 2FA
                log_security_event(
                    user_id=user['user_id'],
                    event_type='login_2fa_requested',
                    details={'email': user['email']},
                    ip_address=request.remote_addr
                )
                
                return redirect(url_for('verificar_2fa'))
            
            # Regenerar ID de sesión para prevenir fijación de sesión
            if hasattr(session, 'regenerate'):
                session.regenerate()
            else:
                # Implementación manual para versiones anteriores de Flask
                new_session = {key: value for key, value in session.items()}
                session.clear()
                for key, value in new_session.items():
                    session[key] = value
                    
            # Establecer datos de sesión
            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['nombre'] = user['nombre']
            session['creditos'] = user['creditos']
            
            # Registrar login en PostgreSQL
            login_id = str(uuid.uuid4())
            ip_address = request.remote_addr
            
            query = f"""
            INSERT INTO {logins_table_id}
            (login_id, user_id, fecha_login, ip_address)
            VALUES (%s, %s, %s, %s)
            """
            execute_query(
                query,
                [login_id, user['user_id'], datetime.now().isoformat(), ip_address],
                fetch=False
            )
            
            # Registrar evento de login exitoso
            log_security_event(
                user_id=user['user_id'],
                event_type='login_success',
                details={'email': user['email']},
                ip_address=request.remote_addr
            )
            
            flash(f'¡Bienvenido de nuevo, {user["nombre"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Registrar intento fallido - contraseña incorrecta
            log_security_event(
                user_id=user['user_id'],
                event_type='login_failed',
                details={'email': user['email'], 'reason': 'incorrect_password'},
                ip_address=request.remote_addr
            )
            flash('Inicio de sesión fallido. Verifique su email y contraseña.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/verificar_2fa', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def verificar_2fa():
    if 'pre_auth_user_id' not in session:
        flash('Sesión inválida. Por favor, inicia sesión nuevamente.', 'danger')
        return redirect(url_for('login'))
    
    form = VerificarCodeForm()
    
    if request.method == 'POST':
        code = request.form.get('code')
        
        # Obtener el secreto TOTP del usuario
        query = f"SELECT totp_secret FROM {usuarios_table_id} WHERE user_id = %s"
        results = execute_query(query, [session['pre_auth_user_id']])
        
        totp_secret = None
        if results:
            totp_secret = results[0]['totp_secret']
        
        if totp_secret and verify_totp(totp_secret, code):
            # Regenerar ID de sesión para prevenir fijación de sesión
            if hasattr(session, 'regenerate'):
                session.regenerate()
            else:
                # Implementación manual para versiones anteriores de Flask
                new_session = {key: value for key, value in session.items()}
                session.clear()
                for key, value in new_session.items():
                    session[key] = value
                    
            # Autenticación exitosa, completar login
            session['user_id'] = session['pre_auth_user_id']
            session['email'] = session['pre_auth_email']
            session['nombre'] = session['pre_auth_nombre']
            
            # Obtener datos adicionales
            query = f"SELECT creditos FROM {usuarios_table_id} WHERE user_id = %s"
            results = execute_query(query, [session['user_id']])
            
            if results:
                session['creditos'] = results[0]['creditos']
            
            # Limpiar datos temporales
            session.pop('pre_auth_user_id', None)
            session.pop('pre_auth_email', None)
            session.pop('pre_auth_nombre', None)
            
            # Registrar login en PostgreSQL
            login_id = str(uuid.uuid4())
            ip_address = request.remote_addr
            
            query = f"""
            INSERT INTO {logins_table_id}
            (login_id, user_id, fecha_login, ip_address)
            VALUES (%s, %s, %s, %s)
            """
            execute_query(
                query,
                [login_id, session['user_id'], datetime.now().isoformat(), ip_address],
                fetch=False
            )
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=session['user_id'],
                event_type='login_2fa_success',
                details={},
                ip_address=request.remote_addr
            )
            
            flash(f'¡Bienvenido de nuevo, {session["nombre"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Registrar evento de seguridad
            log_security_event(
                user_id=session['pre_auth_user_id'],
                event_type='login_2fa_failed',
                details={},
                ip_address=request.remote_addr
            )
            flash('Código incorrecto. Intenta nuevamente.', 'danger')
    
    return render_template('verificar_2fa_login.html', form=form)

@app.route('/logout')
def logout():
    # Registrar evento de logout si hay usuario en sesión
    if 'user_id' in session:
        log_security_event(
            user_id=session['user_id'],
            event_type='logout',
            details={},
            ip_address=request.remote_addr
        )
    
    # Limpiar la sesión
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('index'))

@app.route('/configurar_2fa', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
@login_required
def configurar_2fa():
    # Verificar si ya tiene 2FA configurado
    query = f"SELECT totp_secret FROM {usuarios_table_id} WHERE user_id = %s"
    results = execute_query(query, [session['user_id']])
    
    # Verificar si ya existe un secreto TOTP para el usuario
    existing_secret = None
    if results:
        existing_secret = results[0]['totp_secret']
    
    # Si ya tiene 2FA configurado
    if existing_secret:
        log_security_event(
            user_id=session['user_id'],
            event_type='2fa_setup_attempt',
            details={'status': 'already_configured'},
            ip_address=request.remote_addr
        )
        flash('Ya tienes la autenticación de dos factores configurada.', 'info')
        return redirect(url_for('dashboard'))
    
    # Generar nuevo secreto
    if 'totp_secret' not in session:
        session['totp_secret'] = generate_totp_secret()
    
    # Generar URI para código QR
    totp_uri = get_totp_uri(session['totp_secret'], session['email'])
    qr_code = generate_qr_code(totp_uri)
    
    # Si es POST, verificar el código ingresado
    if request.method == 'POST':
        code = request.form.get('code')
        
        if verify_totp(session['totp_secret'], code):
            try:
                # Actualizar el usuario con el secreto TOTP
                query = f"UPDATE {usuarios_table_id} SET totp_secret = %s WHERE user_id = %s"
                execute_query(query, [session['totp_secret'], session['user_id']], fetch=False)
                
                # Registrar evento de configuración exitosa
                log_security_event(
                    user_id=session['user_id'],
                    event_type='2fa_setup',
                    details={'status': 'success'},
                    ip_address=request.remote_addr
                )
                session.pop('totp_secret', None)
                flash('Autenticación de dos factores configurada con éxito.', 'success')
                return redirect(url_for('dashboard'))
                    
            except Exception as e:
                log_security_event(
                    user_id=session['user_id'],
                    event_type='2fa_setup',
                    details={'status': 'failed', 'reason': str(e)},
                    ip_address=request.remote_addr
                )
                flash(f'Error al guardar la configuración: {str(e)}', 'danger')
        else:
            log_security_event(
                user_id=session['user_id'],
                event_type='2fa_setup',
                details={'status': 'failed', 'reason': 'invalid_code'},
                ip_address=request.remote_addr
            )
            flash('Código incorrecto. Intenta nuevamente.', 'danger')
    
    # Mostrar página con código QR e instrucciones
    return render_template('configurar_2fa.html', 
                           qr_code=qr_code, 
                           secret=session['totp_secret'])


@app.route('/dashboard')
@login_required
def dashboard():
    # Cargar datos actualizados del usuario
    query = f"SELECT creditos FROM {usuarios_table_id} WHERE user_id = %s"
    results = execute_query(query, [session['user_id']])
    
    if results:
        session['creditos'] = results[0]['creditos']
        
    # Cargar historial de transacciones
    query = f"""
    SELECT transaction_id, monto, creditos, metodo_pago, estado, fecha_transaccion
    FROM {transacciones_table_id}
    WHERE user_id = %s
    ORDER BY fecha_transaccion DESC
    LIMIT 10
    """
    transacciones = execute_query(query, [session['user_id']])
    
    # Sanitizar datos para prevenir XSS
    for t in transacciones:
        t['metodo_pago'] = sanitize_output(t['metodo_pago'])
        t['estado'] = sanitize_output(t['estado'])
    
    return render_template('dashboard.html', transacciones=transacciones)

@app.route('/comprar', methods=['GET', 'POST'])
@login_required
def comprar():
    form = CompraForm()
    if form.validate_on_submit():
        cantidad = form.cantidad.data
        # Calcular precio (por ejemplo, $1 por crédito)
        precio = cantidad * 1.0
        
        session['temp_cantidad'] = cantidad
        session['temp_precio'] = precio
        
        # Registrar intento de compra
        log_security_event(
            user_id=session['user_id'],
            event_type='purchase_attempt',
            details={'creditos': cantidad, 'monto': precio},
            ip_address=request.remote_addr
        )
        
        # Proceder directamente con PayPal ya que es el único método de pago
        return redirect(url_for('procesar_paypal'))
    
    return render_template('comprar.html', form=form)

@app.route('/procesar_paypal')
@login_required
def procesar_paypal():
    cantidad = session.get('temp_cantidad', 0)
    precio = session.get('temp_precio', 0)
    
    if cantidad <= 0 or precio <= 0:
        flash('Cantidad o precio inválido. Por favor intente nuevamente.', 'danger')
        return redirect(url_for('comprar'))
    
    payment = Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": url_for('confirmar_pago', _external=True),
            "cancel_url": url_for('cancelar_pago', _external=True)
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": f"{cantidad} Créditos",
                    "sku": "creditos",
                    "price": str(precio / cantidad),
                    "currency": "USD",
                    "quantity": cantidad
                }]
            },
            "amount": {
                "total": str(precio),
                "currency": "USD"
            },
            "description": f"Compra de {cantidad} créditos"
        }]
    })
    
    if payment.create():
        # Guardar ID de pago en la sesión
        session['paypal_payment_id'] = payment.id
        
        # Registrar evento de creación de pago
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_created',
            details={'payment_id': payment.id, 'creditos': cantidad, 'monto': precio},
            ip_address=request.remote_addr
        )
        
        # Redirigir a PayPal para completar el pago
        for link in payment.links:
            if link.rel == "approval_url":
                return redirect(link.href)
    
    # Registrar evento de error en pago
    log_security_event(
        user_id=session['user_id'],
        event_type='payment_error',
        details={'creditos': cantidad, 'monto': precio},
        ip_address=request.remote_addr
    )
    
    flash('Error al procesar el pago con PayPal. Intente nuevamente.', 'danger')
    return redirect(url_for('comprar'))

@app.route('/confirmar_pago')
@login_required
def confirmar_pago():
    payment_id = session.get('paypal_payment_id', '')
    payer_id = request.args.get('PayerID')
    
    if not payment_id or not payer_id:
        flash('No se pudo verificar el pago. Por favor intente nuevamente.', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_verification_failed',
            details={'reason': 'missing_params'},
            ip_address=request.remote_addr
        )
        return redirect(url_for('comprar'))
    
    payment = Payment.find(payment_id)
    
    if payment.execute({"payer_id": payer_id}):
        transaction_id = str(uuid.uuid4())
        cantidad = session.get('temp_cantidad', 0)
        precio = session.get('temp_precio', 0)
        
        # Registrar la transacción en PostgreSQL
        query = f"""
        INSERT INTO {transacciones_table_id}
        (transaction_id, user_id, monto, creditos, metodo_pago, estado, fecha_transaccion, detalles)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(
            query,
            [
                transaction_id, 
                session['user_id'], 
                precio, 
                cantidad, 
                'paypal', 
                'completado', 
                datetime.now().isoformat(), 
                json.dumps({'paypal_payment_id': payment_id})
            ],
            fetch=False
        )
        
        # Actualizar los créditos del usuario
        query = f"UPDATE {usuarios_table_id} SET creditos = creditos + %s WHERE user_id = %s"
        execute_query(query, [cantidad, session['user_id']], fetch=False)
        
        # Actualizar la sesión
        session['creditos'] = session.get('creditos', 0) + cantidad
        
        # Registrar evento de pago exitoso
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_success',
            details={'payment_id': payment_id, 'transaction_id': transaction_id, 'creditos': cantidad, 'monto': precio},
            ip_address=request.remote_addr
        )
        
        # Limpiar datos temporales
        if 'temp_cantidad' in session:
            del session['temp_cantidad']
        if 'temp_precio' in session:
            del session['temp_precio']
        if 'paypal_payment_id' in session:
            del session['paypal_payment_id']
        
        flash(f'¡Pago exitoso! Se han añadido {cantidad} créditos a tu cuenta.', 'success')
        return redirect(url_for('dashboard'))
    else:
        # Registrar evento de error en pago
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_execution_failed',
            details={'payment_id': payment_id},
            ip_address=request.remote_addr
        )
        flash('Hubo un error al ejecutar el pago. Por favor intente nuevamente.', 'danger')
        return redirect(url_for('comprar'))

@app.route('/cancelar_pago')
@login_required
def cancelar_pago():
    # Registrar evento de cancelación de pago
    payment_id = session.get('paypal_payment_id', '')
    log_security_event(
        user_id=session['user_id'],
        event_type='payment_canceled',
        details={'payment_id': payment_id},
        ip_address=request.remote_addr
    )
    
    # Limpiar datos temporales
    if 'temp_cantidad' in session:
        del session['temp_cantidad']
    if 'temp_precio' in session:
        del session['temp_precio']
    if 'paypal_payment_id' in session:
        del session['paypal_payment_id']
    
    flash('Has cancelado el proceso de pago.', 'info')
    return redirect(url_for('comprar'))

@app.route('/usar_creditos', methods=['POST'])
@login_required
def usar_creditos():
    # Ejemplo de cómo se podrían usar los créditos para otro servicio
    cantidad = int(request.form.get('cantidad', 1))
    
    # Verificar si el usuario tiene suficientes créditos
    if session.get('creditos', 0) < cantidad:
        log_security_event(
            user_id=session['user_id'],
            event_type='credits_usage_failed',
            details={'creditos_solicitados': cantidad, 'creditos_disponibles': session.get('creditos', 0)},
            ip_address=request.remote_addr
        )
        flash('No tienes suficientes créditos para esta operación.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Actualizar los créditos en PostgreSQL
    query = f"""
    UPDATE {usuarios_table_id}
    SET creditos = creditos - %s
    WHERE user_id = %s
    AND creditos >= %s
    """
    rows_affected = execute_query(query, [cantidad, session['user_id'], cantidad], fetch=False)
    
    if rows_affected == 0:
        log_security_event(
            user_id=session['user_id'],
            event_type='credits_usage_failed',
            details={'creditos': cantidad, 'reason': 'update_failed'},
            ip_address=request.remote_addr
        )
        flash('No se pudieron descontar los créditos. Verifica tu saldo.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Actualizar la sesión
    session['creditos'] = session.get('creditos', 0) - cantidad
    
    # Registrar el uso de créditos
    transaction_id = str(uuid.uuid4())
    query = f"""
    INSERT INTO {transacciones_table_id}
    (transaction_id, user_id, monto, creditos, metodo_pago, estado, fecha_transaccion, detalles)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_query(
        query,
        [
            transaction_id, 
            session['user_id'], 
            0,  # No hay monto de dinero
            -cantidad,  # Negativo para indicar uso
            'uso_servicio', 
            'completado', 
            datetime.now().isoformat(), 
            json.dumps({'servicio': 'nombre_del_servicio'})
        ],
        fetch=False
    )
    
    # Registrar evento de uso de créditos
    log_security_event(
        user_id=session['user_id'],
        event_type='credits_used',
        details={'creditos': cantidad, 'transaction_id': transaction_id},
        ip_address=request.remote_addr
    )
    
    flash(f'Has utilizado {cantidad} créditos correctamente.', 'success')
    return redirect(url_for('dashboard'))

# Manejadores de errores personalizados
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # Registrar error interno del servidor
    user_id = session.get('user_id')
    log_security_event(
        user_id=user_id,
        event_type='server_error',
        details={'url': request.path, 'method': request.method, 'error': str(e)},
        ip_address=request.remote_addr
    )
    return render_template('500.html'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    # Registrar intento de abuso por límite de velocidad
    user_id = session.get('user_id')
    log_security_event(
        user_id=user_id,
        event_type='rate_limit_exceeded',
        details={'url': request.path, 'method': request.method},
        ip_address=request.remote_addr
    )
    return render_template('429.html', mensaje=e.description), 429

# Inicializar la aplicación
def init_app():
    # Inicializar la base de datos PostgreSQL
    from app.models.database_pg import init_database
    init_database()
    
    # Registrar inicio de aplicación
    try:
        log_security_event(
            user_id=None,
            event_type='application_start',
            details={'environment': os.environ.get('FLASK_ENV', 'development')},
            ip_address='internal'
        )
    except Exception as e:
        print(f"Error al registrar inicio de aplicación: {str(e)}")
    
    return app

if __name__ == '__main__':
    # Inicializar la aplicación
    app = init_app()
    
    # Iniciar la aplicación
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))