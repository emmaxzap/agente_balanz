from datetime import datetime, timedelta
import time
import uuid
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
from flask import request, url_for, session

from app.models.user import User
from app.models.database_pg import execute_query, recovery_tokens_table_id, historial_passwords_table_id, logins_table_id
from app.utils.security import generate_password_hash, check_password_hash, verify_totp
from app.utils.security import is_password_pwned, generate_secure_token
from app.utils.logging import log_security_event

class AuthService:
    @staticmethod
    def authenticate(email, password):
        """
        Autentica a un usuario verificando sus credenciales
        
        Args:
            email: El correo electrónico del usuario
            password: La contraseña del usuario
            
        Returns:
            dict: Los datos del usuario si la autenticación es exitosa, None en caso contrario
        """
        user = User.get_by_email(email)
        
        if not user:
            # Retraso para prevenir timing attacks
            time.sleep(1)
            # Registrar intento fallido
            log_security_event(
                user_id=None,
                event_type='login_failed',
                details={'email': email, 'reason': 'user_not_found'},
                ip_address=request.remote_addr
            )
            return None
            
        # Verificar contraseña
        if check_password_hash(user['password_hash'], password):
            return user
        
        # Registrar intento fallido
        log_security_event(
            user_id=user['user_id'],
            event_type='login_failed',
            details={'email': user['email'], 'reason': 'incorrect_password'},
            ip_address=request.remote_addr
        )
        
        return None
    
    @staticmethod
    def validate_registration_data(user_data):
        """
        Valida los datos de registro sin crear el usuario
        
        Args:
            user_data: Diccionario con los datos del usuario
                
        Raises:
            ValueError: Si los datos son inválidos
        """
        # Verificar si la contraseña ha sido comprometida
        if is_password_pwned(user_data['password']):
            raise ValueError("Esta contraseña ha aparecido en filtraciones de datos")
        
        # Validar email
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, user_data['email']):
            raise ValueError("El email proporcionado no es válido")
        
        # Validar país
        paises_validos = [
            'Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 
            'Ecuador', 'Guyana', 'Paraguay', 'Perú', 'Surinam', 
            'Uruguay', 'Venezuela'
        ]
        if user_data.get('pais') and user_data['pais'] not in paises_validos:
            raise ValueError("El país seleccionado no es válido")
        
        # Verificar si el email ya existe
        user = User.get_by_email(user_data['email'])
        if user:
            # Retraso para prevenir information disclosure
            time.sleep(1)
            raise ValueError(f"El email {user_data['email']} ya está registrado")
    
    @staticmethod
    def create_user_with_2fa(user_data, totp_secret):
        """
        Crea un nuevo usuario con 2FA ya configurado
        
        Args:
            user_data: Diccionario con los datos del usuario
            totp_secret: Secreto TOTP verificado
                
        Returns:
            dict: Información del usuario creado
                
        Raises:
            ValueError: Si ocurre un error al crear el usuario
        """
        try:
            # Validar los datos de nuevo por seguridad
            AuthService.validate_registration_data(user_data)
            
            # Generar hash de la contraseña
            password_hash = generate_password_hash(user_data['password'])
            
            # Generar ID de usuario
            user_id = str(uuid.uuid4())
            
            # Preparar la consulta de inserción
            query = f"""
            INSERT INTO {User.get_table_id()}
            (user_id, email, password_hash, nombre, apellido, telefono, pais, 
             fecha_registro, ultimo_login, estado, creditos, tipo_usuario, acepta_marketing, totp_secret)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Valores para la inserción
            params = (
                user_id,
                user_data['email'],
                password_hash,
                user_data['nombre'],
                user_data['apellido'],
                user_data.get('telefono'),
                user_data.get('pais'),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                'activo',
                0,
                'normal',
                user_data.get('acepta_marketing', False),
                totp_secret  # Incluir el secreto TOTP verificado
            )
            
            # Ejecutar la inserción
            execute_query(query, params=params, fetch=False)
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=user_id,
                event_type='user_registration_complete',
                details={'email': user_data['email'], '2fa_enabled': True},
                ip_address=request.remote_addr
            )
            
            return {
                'user_id': user_id,
                'email': user_data['email'],
                'nombre': user_data['nombre']
            }
            
        except Exception as e:
            log_security_event(
                user_id=None,
                event_type='registration_failed',
                details={'email': user_data['email'], 'error': str(e)},
                ip_address=request.remote_addr
            )
            raise ValueError(str(e))
    
    @staticmethod
    def register(user_data):
        """
        Registra un nuevo usuario en el sistema y prepara la configuración 2FA
        
        Args:
            user_data: Diccionario con los datos del usuario
                
        Returns:
            dict: Información del usuario y secreto TOTP para configuración
                
        Raises:
            ValueError: Si el usuario ya existe o la contraseña no es segura
        """
        # Verificar si la contraseña ha sido comprometida
        if is_password_pwned(user_data['password']):
            raise ValueError("Esta contraseña ha aparecido en filtraciones de datos")
        
        # Validar email
        import re
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, user_data['email']):
            raise ValueError("El email proporcionado no es válido")
        
        # Validar país
        paises_validos = [
            'Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 
            'Ecuador', 'Guyana', 'Paraguay', 'Perú', 'Surinam', 
            'Uruguay', 'Venezuela'
        ]
        if user_data.get('pais') and user_data['pais'] not in paises_validos:
            raise ValueError("El país seleccionado no es válido")
        
        try:
            # Crear usuario
            user_id = User.create(user_data)
            
            # Generar secreto TOTP para configuración 2FA
            from app.utils.security import generate_totp_secret
            totp_secret = generate_totp_secret()
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=user_id,
                event_type='user_registration',
                details={'email': user_data['email']},
                ip_address=request.remote_addr
            )
            
            # Devolver el ID del usuario y el secreto TOTP
            return {
                'user_id': user_id,
                'totp_secret': totp_secret
            }
        except Exception as e:
            log_security_event(
                user_id=None,
                event_type='registration_failed',
                details={'email': user_data['email'], 'error': str(e)},
                ip_address=request.remote_addr
            )
            raise ValueError(str(e))
    
    @staticmethod
    def log_login(user_id, ip_address):
        """
        Registra el inicio de sesión de un usuario
        
        Args:
            user_id: El ID del usuario
            ip_address: La dirección IP desde donde se inició sesión
        """
        login_id = str(uuid.uuid4())
        
        query = f"""
        INSERT INTO {logins_table_id}
        (login_id, user_id, fecha_login, ip_address, estado, intento)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        params = (
            login_id,
            user_id,
            datetime.now().isoformat(),
            ip_address,
            'activo',  # Campo estado requerido
            1          # Campo intento requerido (asumiendo 1 como valor predeterminado)
        )

        execute_query(query, params=params, fetch=False)
        
        # Registrar evento de seguridad
        log_security_event(
            user_id=user_id,
            event_type='login_success',
            details={},
            ip_address=ip_address
        )





    @staticmethod
    def change_password(user_id, current_password, new_password):
        """
        Cambia la contraseña de un usuario
        
        Args:
            user_id: El ID del usuario
            current_password: La contraseña actual
            new_password: La nueva contraseña
            
        Returns:
            bool: True si el cambio fue exitoso
            
        Raises:
            ValueError: Si la contraseña actual es incorrecta o la nueva no es segura
        """
        try:
            # Verificar si la contraseña ha sido comprometida
            if is_password_pwned(new_password):
                raise ValueError("La nueva contraseña ha aparecido en filtraciones de datos")
                
            user = User.get_by_id(user_id)
            if not user:
                print(f"Error: Usuario con ID {user_id} no encontrado")
                raise ValueError("Usuario no encontrado")
            
            # Verificar que la contraseña actual sea correcta
            if not check_password_hash(user['password_hash'], current_password):
                # Registrar intento fallido
                log_security_event(
                    user_id=user_id,
                    event_type='password_change_failed',
                    details={'reason': 'incorrect_current_password'},
                    ip_address=request.remote_addr
                )
                raise ValueError("Contraseña actual incorrecta")
            
            # Verificar que la nueva contraseña no esté en el historial (últimas 3)
            history = User.get_password_history(user_id, limit=3)
            
            for password_hash in history:
                if check_password_hash(password_hash, new_password):
                    print(f"Error: Contraseña en historial para usuario {user_id}")
                    raise ValueError("La nueva contraseña no puede ser igual a una de tus contraseñas anteriores")
            
            # Guardar la contraseña actual en el historial
            try:
                historial_id = str(uuid.uuid4())
                
                insert_query = f"""
                INSERT INTO {historial_passwords_table_id}
                (historial_id, user_id, password_hash, fecha_creacion)
                VALUES (%s, %s, %s, %s)
                """
                
                params = (
                    historial_id,
                    user_id,
                    user['password_hash'],
                    datetime.now().isoformat()
                )
                
                execute_query(insert_query, params=params, fetch=False)
                
            except Exception as e:
                print(f"Error al guardar historial: {str(e)}")
            
            # Generar hash de la nueva contraseña
            new_password_hash = generate_password_hash(new_password)
            
            # Actualizar la contraseña
            success = User.update_password(user_id, new_password_hash)
            if not success:
                print(f"Error: No se pudo actualizar la contraseña para usuario {user_id}")
                raise Exception("Error al actualizar la contraseña")
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=user_id,
                event_type='password_changed',
                details={},
                ip_address=request.remote_addr
            )
            
            return True
        
        except ValueError as e:
            # Reenviar ValueError
            raise
        except Exception as e:
            # Capturar y registrar cualquier otra excepción
            print(f"Error inesperado en change_password: {str(e)}")
            raise
    
    @staticmethod
    def initiate_password_recovery(email):
        """
        Inicia el proceso de recuperación de contraseña para un usuario
        
        Args:
            email: El correo electrónico del usuario
            
        Returns:
            dict: Información sobre el resultado del proceso
        """
        result = {
            'success': False,
            'message': 'Si tu email está registrado, recibirás instrucciones para restablecer tu contraseña.',
            'redirect': 'login'
        }
        
        # Buscar al usuario por email
        user = User.get_by_email(email)
        
        if not user:
            # Por seguridad, retrasamos la respuesta en caso de usuario no encontrado
            time.sleep(1)
            
            # Registrar intento con correo inexistente
            log_security_event(
                user_id=None,
                event_type='password_recovery_attempt',
                details={'email': email, 'reason': 'user_not_found'},
                ip_address=request.remote_addr
            )
            
            return result
        
        # Verificar el tiempo transcurrido desde el registro
        fecha_registro = user['fecha_registro']
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
                user_id=user['user_id'],
                event_type='password_recovery_attempt',
                details={'reason': 'too_soon_after_registration'},
                ip_address=request.remote_addr
            )
            minutos_restantes = 90 - minutos_transcurridos
            result.update({
                'message': 'Debes esperar para recuperar tu contraseña',
                'redirect': 'espera_recuperacion',
                'minutos_restantes': int(minutos_restantes)
            })
            return result
        
        # Si tiene 2FA configurado, redirigir a verificación 2FA
        if user.get('totp_secret'):
            # Agregar log para depuración
            print(f"Iniciando recuperación para usuario: {user['user_id']}, email: {user['email']}, TOTP secret presente: {user['totp_secret'] is not None}")
            
            session['recovery_user_id'] = user['user_id']
            session['recovery_email'] = user['email']
            
            # Registrar intento válido
            log_security_event(
                user_id=user['user_id'],
                event_type='password_recovery_attempt',
                details={'step': 'initiated_2fa_verification'},
                ip_address=request.remote_addr
            )
            
            result.update({
                'success': True,
                'has_2fa': True,
                'redirect': 'verificar_2fa_recuperacion'
            })
            return result
        else:
            # Caso para usuarios sin 2FA (aunque en este sistema todos deberían tenerlo)
            # Generar token de recuperación
            token = AuthService.create_recovery_token(user['user_id'])
            
            # Enviar email con token
            email_sent = AuthService.send_recovery_email(user['email'], user['user_id'], token)
            
            # Registrar el intento
            log_security_event(
                user_id=user['user_id'],
                event_type='password_recovery_attempt',
                details={'step': 'recovery_email_sent', 'success': email_sent},
                ip_address=request.remote_addr
            )
            
            return result
    
    @staticmethod
    def verify_2fa_code(user_id, code):
        """
        Verifica un código 2FA para un usuario
        
        Args:
            user_id: ID del usuario
            code: Código a verificar
            
        Returns:
            bool: True si el código es válido
        """
        # Logs de depuración
        print(f"Verificando código 2FA - user_id: {user_id}, code: {code}")
        
        # Obtener el secreto TOTP del usuario
        user = User.get_by_id(user_id)
        
        # Más logs
        if user is None:
            print(f"Error: Usuario con ID {user_id} no encontrado")
            log_security_event(
                user_id=user_id,
                event_type='2fa_verification_failed',
                details={'reason': 'user_not_found'},
                ip_address=request.remote_addr
            )
            return False
        
        if not user.get('totp_secret'):
            print(f"Error: Usuario {user_id} no tiene TOTP configurado")
            log_security_event(
                user_id=user_id,
                event_type='2fa_verification_failed',
                details={'reason': 'no_totp_secret'},
                ip_address=request.remote_addr
            )
            return False
            
        # Verificar el código
        print(f"Verificando código {code} con secret {user['totp_secret'][:5]}...")
        valid = verify_totp(user['totp_secret'], code)
        print(f"Resultado de verificación: {valid}")
        
        # Registrar el resultado
        log_security_event(
            user_id=user_id,
            event_type='2fa_verification',
            details={'success': valid},
            ip_address=request.remote_addr
        )
        
        return valid
    
    @staticmethod
    def create_recovery_token(user_id):
        """
        Crea un token de recuperación para un usuario
        
        Args:
            user_id: El ID del usuario
            
        Returns:
            str: El token generado
        """
        token = generate_secure_token()
        token_id = str(uuid.uuid4())
        now = datetime.now()
        expires = now + timedelta(hours=24)
        
        query = f"""
        INSERT INTO {recovery_tokens_table_id}
        (token_id, user_id, token, created_at, expires_at, used)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        params = (
            token_id,
            user_id,
            token,
            now.isoformat(),
            expires.isoformat(),
            False
        )
        
        execute_query(query, params=params, fetch=False)
        return token
    
    @staticmethod
    def verify_recovery_token(token):
        """
        Verifica si un token de recuperación es válido
        
        Args:
            token: El token a verificar
            
        Returns:
            dict: Información sobre el token y el usuario asociado, o None si no es válido
        """
        if not token:
            log_security_event(
                user_id=None,
                event_type='password_reset_attempt',
                details={'reason': 'missing_token'},
                ip_address=request.remote_addr
            )
            return None
            
        # Buscar token en la base de datos
        query = f"""
        SELECT token_id, user_id, expires_at, used
        FROM {recovery_tokens_table_id}
        WHERE token = %s
        """
        
        results = execute_query(query, params=(token,), fetch=True, as_dict=True)
        
        token_data = None
        if results:
            token_data = {
                'token_id': results[0]['token_id'],
                'user_id': results[0]['user_id'],
                'expires_at': results[0]['expires_at'],
                'used': results[0]['used']
            }
        
        # Si el token no existe
        if not token_data:
            log_security_event(
                user_id=None,
                event_type='password_reset_attempt',
                details={'reason': 'invalid_token'},
                ip_address=request.remote_addr
            )
            return None
        
        # Si el token ya fue usado
        if token_data['used']:
            log_security_event(
                user_id=token_data['user_id'],
                event_type='password_reset_attempt',
                details={'reason': 'token_already_used'},
                ip_address=request.remote_addr
            )
            return None
        
        # Verificar si el token ha expirado
        expires_at = token_data['expires_at']
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

        # Asegurarnos de que ambas fechas sean del mismo tipo
        if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
            
        if datetime.now() > expires_at:
            log_security_event(
                user_id=token_data['user_id'],
                event_type='password_reset_attempt',
                details={'reason': 'token_expired'},
                ip_address=request.remote_addr
            )
            return None
        
        # Obtener información del usuario
        user = User.get_by_id(token_data['user_id'])
        if not user:
            log_security_event(
                user_id=token_data['user_id'],
                event_type='password_reset_attempt',
                details={'reason': 'user_not_found'},
                ip_address=request.remote_addr
            )
            return None
            
        # El token es válido, incluir datos del usuario
        token_data['user'] = user
        return token_data
    
    @staticmethod
    def reset_password(token_data, new_password):
        """
        Restablece la contraseña de un usuario usando un token de recuperación
        
        Args:
            token_data: Datos del token de recuperación
            new_password: La nueva contraseña
            
        Returns:
            bool: True si el cambio fue exitoso
            
        Raises:
            ValueError: Si la nueva contraseña no es segura o está en el historial reciente
        """
        # Verificar si la contraseña ha sido comprometida
        if is_password_pwned(new_password):
            raise ValueError("Esta contraseña ha aparecido en filtraciones de datos")
        
        user_id = token_data['user_id']
        token_id = token_data['token_id']
        
        try:
            # Verificar si la nueva contraseña está en el historial reciente
            history = User.get_password_history(user_id, limit=3)
            for password_hash in history:
                if check_password_hash(password_hash, new_password):
                    raise ValueError("La nueva contraseña no puede ser igual a una de tus contraseñas anteriores")
            
            # Obtener la contraseña actual para guardarla en historial
            user = User.get_by_id(user_id)
            if user and 'password_hash' in user:
                # Guardar la contraseña actual en el historial
                historial_id = str(uuid.uuid4())
                
                history_query = f"""
                INSERT INTO {historial_passwords_table_id}
                (historial_id, user_id, password_hash, fecha_creacion)
                VALUES (%s, %s, %s, %s)
                """
                
                history_params = (
                    historial_id,
                    user_id,
                    user['password_hash'],
                    datetime.now().isoformat()
                )
                
                execute_query(history_query, params=history_params, fetch=False)
            
            # Generar hash de la nueva contraseña
            new_password_hash = generate_password_hash(new_password)
            
            # Actualizar la contraseña del usuario
            if not User.update_password(user_id, new_password_hash):
                raise Exception("Error al actualizar la contraseña")
            
            # Marcar el token como usado
            update_query = f"""
            UPDATE {recovery_tokens_table_id}
            SET used = %s
            WHERE token_id = %s
            """
            
            update_params = (True, token_id)
            
            execute_query(update_query, params=update_params, fetch=False)
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=user_id,
                event_type='password_reset_success',
                details={},
                ip_address=request.remote_addr
            )
            
            return True
            
        except ValueError as e:
            # Re-lanzar ValueError para que sea capturada en la capa superior
            log_security_event(
                user_id=user_id,
                event_type='password_reset_error',
                details={'error': str(e)},
                ip_address=request.remote_addr
            )
            raise
        except Exception as e:
            # Registrar error
            log_security_event(
                user_id=user_id,
                event_type='password_reset_error',
                details={'error': str(e)},
                ip_address=request.remote_addr
            )
            raise
    
    @staticmethod
    def configure_2fa(user_id, totp_secret, verification_code):
        """
        Configura 2FA para un usuario
        
        Args:
            user_id: ID del usuario
            totp_secret: Secreto TOTP generado
            verification_code: Código de verificación ingresado por el usuario
            
        Returns:
            bool: True si la configuración fue exitosa
            
        Raises:
            ValueError: Si el código de verificación es inválido
        """
        # Verificar el código
        if not verify_totp(totp_secret, verification_code):
            log_security_event(
                user_id=user_id,
                event_type='2fa_setup',
                details={'status': 'failed', 'reason': 'invalid_code'},
                ip_address=request.remote_addr
            )
            raise ValueError("Código incorrecto")
            
        try:
            # Actualizar el campo totp_secret del usuario
            success = User.update_totp_secret(user_id, totp_secret)
            
            if not success:
                raise Exception("Error al guardar la configuración")
                
            # Registrar evento de configuración exitosa
            log_security_event(
                user_id=user_id,
                event_type='2fa_setup',
                details={'status': 'success'},
                ip_address=request.remote_addr
            )
            
            return True
            
        except Exception as e:
            # Registrar error
            log_security_event(
                user_id=user_id,
                event_type='2fa_setup',
                details={'status': 'failed', 'reason': str(e)},
                ip_address=request.remote_addr
            )
            raise
    
    @staticmethod
    def send_recovery_email(email, user_id, token):
        """
        Envía un email con enlace de recuperación de contraseña
        
        Args:
            email: Correo electrónico del usuario
            user_id: ID del usuario
            token: Token de recuperación
            
        Returns:
            bool: True si el email se envió correctamente
        """
        try:
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
            from flask import url_for
            reset_url = url_for('auth.restablecer_password', token=token, _external=True)
            
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