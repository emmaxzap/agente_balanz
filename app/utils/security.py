import secrets
import hashlib
import requests
import pyotp
import qrcode
import io
import base64
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Configuración de Argon2 para hash de contraseñas
ph = PasswordHasher(
    time_cost=3,  # Número de iteraciones
    memory_cost=65536,  # 64MB
    parallelism=4,  # Número de hilos paralelos
    hash_len=32,  # Tamaño de la salida en bytes
    salt_len=16   # Tamaño de la sal en bytes
)

def generate_password_hash(password):
    """
    Genera un hash seguro de contraseña usando Argon2
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        str: Hash de la contraseña
    """
    return ph.hash(password)

def check_password_hash(hash_value, password):
    """
    Verifica una contraseña contra un hash Argon2
    
    Args:
        hash_value: Hash almacenado
        password: Contraseña en texto plano a verificar
        
    Returns:
        bool: True si la contraseña coincide con el hash
    """
    try:
        return ph.verify(hash_value, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Fallback para contraseñas antiguas (werkzeug)
        from werkzeug.security import check_password_hash as werkzeug_check
        return werkzeug_check(hash_value, password)

def generate_totp_secret():
    """
    Genera un secreto para TOTP (autenticación de dos factores)
    
    Returns:
        str: Secreto TOTP en formato base32
    """
    return pyotp.random_base32()

def get_totp_uri(secret, email, issuer_name="Sistema de Créditos"):
    """
    Genera un URI para TOTP que se puede usar para generar un código QR
    
    Args:
        secret: Secreto TOTP
        email: Email del usuario
        issuer_name: Nombre del emisor
        
    Returns:
        str: URI TOTP
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer_name)

def generate_qr_code(uri):
    """
    Genera un código QR como imagen en base64
    
    Args:
        uri: URI a codificar
        
    Returns:
        str: Imagen del código QR en formato base64
    """
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
    """
    Verifica un código TOTP con protección contra ataques de temporización
    
    Args:
        secret: Secreto TOTP
        code: Código a verificar
        
    Returns:
        bool: True si el código es válido
    """
    totp = pyotp.TOTP(secret)
    # Verifica el código actual y el anterior/siguiente para dar margen por desincronización
    return totp.verify(code, valid_window=1)

def generate_secure_token():
    """
    Genera un token seguro para recuperación de contraseña
    
    Returns:
        str: Token seguro
    """
    return secrets.token_urlsafe(32)

def is_password_pwned(password):
    """
    Verifica si una contraseña ha sido comprometida usando la API HaveIBeenPwned
    
    Args:
        password: Contraseña a verificar
        
    Returns:
        bool: True si la contraseña ha sido comprometida
    """
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