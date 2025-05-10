from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask import current_app as app
from app.models.team import Team
from app.forms.auth_forms import LoginForm, RegistroForm, RecuperarPasswordForm, RestablecerPasswordForm
from app.forms.auth_forms import VerificarCodeForm, CambioPasswordForm
from app.services.auth_service import AuthService
from app.utils.security import verify_totp, generate_totp_secret, get_totp_uri, generate_qr_code
from app.utils.logging import log_security_event
from app.utils.decorators import login_required
from app.middlewares.rate_limiting import limiter
from app.models.user import User
from app.models.database_pg import execute_query, team_invitations_table_id, team_members_table_id, invitation_actions_table_id
from datetime import datetime, timedelta
import uuid
import json
from app.models.plan import Plan

# Función de reemplazo para mantener compatibilidad con el código existente
def limpiar_email_especifico(email, solo_lectura=False):
    """
    Función placeholder que reemplaza la original de BigQuery
    Solo retorna None para mantener compatibilidad
    """
    print(f"Verificando email: {email} (función placeholder)")
    return None

auth_bp = Blueprint('auth', __name__)

def setup_team_session(user_id, owner_id, role):
    """
    Configura correctamente las variables de sesión relacionadas con el equipo
    """
    from app.models.user import User
    
    session['is_team_member'] = True
    session['team_owner_id'] = owner_id
    session['team_role'] = role
    

    owner = User.get_by_id(owner_id)
    if owner:
        owner_name = owner.get('nombre', 'Administrador')
        session['team_owner_name'] = owner_name
        session['team_owner_creditos'] = owner.get('creditos', 0)
        print(f"Información de propietario cargada en sesión: {owner_name}, {owner.get('creditos', 0)} créditos")
    else:
        print(f"No se pudo encontrar información del propietario {owner_id}")
        session['team_owner_name'] = 'Administrador'
        session['team_owner_creditos'] = 0
    
    print("Variables de sesión de equipo configuradas:")
    print(f"- is_team_member: {session['is_team_member']}")
    print(f"- team_owner_id: {session['team_owner_id']}")
    print(f"- team_role: {session['team_role']}")
    print(f"- team_owner_name: {session.get('team_owner_name', 'No definido')}")
    print(f"- team_owner_creditos: {session.get('team_owner_creditos', 'No definido')}")

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Verificación simplificada - no necesitamos verificar duplicados en PostgreSQL
        email = form.email.data
        print(f"Verificando usuario con email: {email}")
        mejor_registro = None
        
        # Autenticar usuario
        user = AuthService.authenticate(form.email.data, form.password.data)

        if not user:
            flash('Inicio de sesión fallido. Verifique su email y contraseña.', 'danger')
            return render_template('login.html', form=form)
            
        # Regenerar ID de sesión para prevenir fijación de sesión
        if hasattr(session, 'regenerate'):
            session.regenerate()
        else:
            new_session = {key: value for key, value in session.items()}
            session.clear()
            for key, value in new_session.items():
                session[key] = value

        # Establecer datos de sesión
        session['user_id'] = user['user_id']
        session['email'] = user['email']
        session['nombre'] = user['nombre']
        session['creditos'] = user['creditos']

        # Verificar si es miembro de un equipo con información detallada
        try:
            membership = Team.get_member_info(user['user_id'])
            print(f"Información de equipo encontrada: {membership}")
            
            if not membership:
                print("No se encontró información de membresía, buscando en equipo por email")
                # Buscar por email como fallback
                membership = Team.get_member_info_by_email(user['email'])
                
            if membership:
                print(f"Usuario es miembro del equipo con ID: {membership['member_id']}")
                setup_team_session(user['user_id'], membership['owner_id'], membership['role'])
            else:
                print(f"Usuario no es miembro de ningún equipo")
                session['is_team_member'] = False
                
                query = f"""
                SELECT i.invitation_id, i.owner_id, i.role, i.token
                FROM {team_invitations_table_id} i
                WHERE LOWER(i.email) = %s
                AND i.status = 'pending'
                LIMIT 1
                """
                results = execute_query(query, [user['email'].lower()])
                invitation = None

                if results:
                    invitation = {
                        'invitation_id': results[0]['invitation_id'],
                        'owner_id': results[0]['owner_id'],
                        'role': results[0]['role'],
                        'token': results[0]['token']
                    }

                    print(f"Invitación pendiente encontrada. Aceptando automáticamente: {invitation}")
                    team_info = Team.accept_invitation(invitation['token'], user['user_id'])

                    if team_info:
                        # Utilizar la función auxiliar para configurar la sesión
                        setup_team_session(user['user_id'], team_info['owner_id'], team_info['role'])
                        flash(f'Has sido añadido automáticamente al equipo.', 'success')
                
            print(f"Login - User ID: {user['user_id']}")
            print(f"Login - Es miembro: {session.get('is_team_member', False)}")
            print(f"Login - Propietario ID: {session.get('team_owner_id', None)}")
            print(f"Login - Rol: {session.get('team_role', None)}")
            print(f"Login - Nombre del propietario: {session.get('team_owner_name', None)}")
            print(f"Login - Créditos del propietario: {session.get('team_owner_creditos', None)}")

        except Exception as e:
            print(f"Error verificando equipo en login: {str(e)}")
            import traceback
            print(traceback.format_exc())
            session['is_team_member'] = False

        AuthService.log_login(user['user_id'], request.remote_addr)

        flash(f'¡Bienvenido de nuevo, {user["nombre"]}!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('login.html', form=form)

@auth_bp.route('/verificar_2fa', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def verificar_2fa():
    if 'pre_auth_user_id' not in session:
        flash('Sesión inválida. Por favor, inicia sesión nuevamente.', 'danger')
        return redirect(url_for('auth.login'))
    
    form = VerificarCodeForm()
    
    if request.method == 'POST':
        code = request.form.get('code')
        
        if AuthService.verify_2fa_code(session['pre_auth_user_id'], code):
            # No es necesario limpiar duplicados en PostgreSQL
            print(f"Verificación 2FA exitosa para email: {session['pre_auth_email']}")
                
            # Regenerar ID de sesión para prevenir fijación de sesión
            if hasattr(session, 'regenerate'):
                session.regenerate()
            else:
                new_session = {key: value for key, value in session.items()}
                session.clear()
                for key, value in new_session.items():
                    session[key] = value
                    
            # Autenticación exitosa, completar login
            session['user_id'] = session['pre_auth_user_id']
            session['email'] = session['pre_auth_email']
            session['nombre'] = session['pre_auth_nombre']
            
            # Cargar créditos del usuario
            user = User.get_by_id(session['user_id'])
            if user:
                session['creditos'] = user.get('creditos', 0)
            
            try:
                # Obtener información del miembro
                membership = Team.get_member_info(session['user_id'])
                
                if not membership:
                    print("No se encontró información de membresía, buscando en equipo por email")
                    # Buscar por email como fallback
                    membership = Team.get_member_info_by_email(session['email'])
                
                if membership:
                    # Utilizar la función auxiliar para configurar la sesión
                    setup_team_session(session['user_id'], membership['owner_id'], membership['role'])
                else:
                    session['is_team_member'] = False
            except Exception as e:
                # Si ocurre un error en la verificación de equipo, lo ignoramos
                print(f"Error verificando equipo en verificar_2fa: {str(e)}")
                session['is_team_member'] = False
            
            session.pop('pre_auth_user_id', None)
            session.pop('pre_auth_email', None)
            session.pop('pre_auth_nombre', None)
            
            # Registrar login
            AuthService.log_login(session['user_id'], request.remote_addr)
            
            # Registrar evento de seguridad
            log_security_event(
                user_id=session['user_id'],
                event_type='login_2fa_success',
                details={},
                ip_address=request.remote_addr
            )
            
            flash(f'¡Bienvenido de nuevo, {session["nombre"]}!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Código incorrecto. Intenta nuevamente.', 'danger')
    
    return render_template('verificar_2fa_login.html', form=form)

@auth_bp.route('/logout')
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
    return redirect(url_for('auth.login'))

@auth_bp.route('/registro', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def registro():
    # Verificar si es una invitación de equipo
    invitation_token = request.args.get('token', '')
    invitation = None
    
    if invitation_token:
        # Buscar la invitación por token
        try:
            invitation = Team.get_invitation_by_token(invitation_token)
            
            if not invitation:
                flash('Invitación no válida o expirada.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Imprimir información de la invitación para debug
            print(f"Invitación encontrada: {invitation}")
            
        except Exception as e:
            # Si ocurre un error al buscar la invitación, continuamos sin ella
            print(f"Error al buscar invitación: {str(e)}")
            pass
    
    form = RegistroForm()
    if form.validate_on_submit():
        try:
            # Preparar datos del usuario (pero no crear todavía)
            user_data = {
                'email': form.email.data,
                'password': form.password.data,
                'nombre': form.nombre.data,
                'apellido': form.apellido.data,
                'telefono': form.telefono.data if hasattr(form, 'telefono') and form.telefono.data else None,
                'pais': form.pais.data if hasattr(form, 'pais') and form.pais.data else None,
                'acepta_marketing': form.acepta_marketing.data if hasattr(form, 'acepta_marketing') else False,
            }
        
            # Si es una invitación, verificar que el email coincida
            if invitation and invitation['email'].lower() != user_data['email'].lower():
                flash(f'Debes registrarte con el email {invitation["email"]} para aceptar esta invitación.', 'danger')
                return render_template('registro.html', form=form, invitation=invitation)
            
            # Realizar validaciones preliminares pero no crear el usuario todavía
            AuthService.validate_registration_data(user_data)
            
            # Generar secreto TOTP para la configuración 2FA
            totp_secret = generate_totp_secret()
            
            session['registro_temp_data'] = user_data
            session['registro_totp_secret'] = totp_secret
            session.modified = True  # Forzar la persistencia de la sesión
            
            # Si es una invitación, guardar el token de invitación
            if invitation:
                session['registro_invitation_token'] = invitation_token
                # Guardamos también la información de la invitación para asegurar 
                # que esté disponible durante todo el proceso
                session['registro_invitation_info'] = {
                    'owner_id': invitation['owner_id'],
                    'email': invitation['email'],
                    'role': invitation['role']
                }
            
            # Redirigir a la página de configuración 2FA
            flash('Por favor, configure la autenticación de dos factores para completar el registro.', 'info')
            return redirect(url_for('auth.configurar_2fa_registro'))
            
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash('Error al procesar el registro. Por favor intente más tarde.', 'danger')
    
    # Si es una invitación, prellenar el email
    if invitation and not form.email.data:
        form.email.data = invitation['email']
    
    return render_template('registro.html', form=form, invitation=invitation)
    
@auth_bp.route('/unirse', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def unirse_equipo():
    """
    Ruta específica para unirse a un equipo mediante invitación
    """
    # Añadir depuración
    print(f"Procesando solicitud para unirse al equipo (método: {request.method})")
    
    # Obtener token de invitación
    token = request.args.get('token', '')
    print(f"Token recibido: {token}")
    
    if not token:
        flash('Enlace de invitación inválido. Se requiere un token.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verificar si el token es válido
    invitation = Team.get_invitation_by_token(token)
    
    if not invitation:
        flash('Invitación no válida o expirada.', 'danger')
        return redirect(url_for('auth.login'))
    
    print(f"Invitación encontrada: {invitation['invitation_id']}, email: {invitation['email']}")
    
    # Obtener información del propietario para mostrar en la página
    owner = User.get_by_id(invitation['owner_id'])
    owner_name = owner.get('nombre', 'Desconocido') if owner else 'Desconocido'
    
    # Verificar si el usuario ya existe (por email)
    existing_user = User.get_by_email(invitation['email'])
    print(f"Usuario existente: {existing_user is not None}")
    
    # Si el usuario ya está registrado, mostrar formulario de login
    if existing_user:
        form = LoginForm()
        
        if form.validate_on_submit():
            print("Formulario de login validado correctamente")
            user = AuthService.authenticate(form.email.data, form.password.data)
            
            if not user:
                flash('Inicio de sesión fallido. Verifique su email y contraseña.', 'danger')
                return render_template(
                    'unirse_equipo.html', 
                    form=form, 
                    invitation=invitation, 
                    owner_name=owner_name, 
                    existing_user=True
                )
            
            # Regenerar ID de sesión para prevenir fijación de sesión
            if hasattr(session, 'regenerate'):
                session.regenerate()
            else:
                new_session = {key: value for key, value in session.items()}
                session.clear()
                for key, value in new_session.items():
                    session[key] = value
            
            # Establecer datos de sesión
            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['nombre'] = user['nombre']
            session['creditos'] = user['creditos']
            
            # Aceptar la invitación
            try:
                print(f"Aceptando invitación para usuario existente: {user['user_id']}")
                team_info = Team.accept_invitation(token, user['user_id'])
                
                if team_info:
                    # Usar la función auxiliar para configurar la sesión
                    setup_team_session(user['user_id'], team_info['owner_id'], team_info['role'])
                    flash(f'Has sido añadido al equipo de {session.get("team_owner_name", "tu administrador")} correctamente.', 'success')
                
                # Registrar evento
                log_security_event(
                    user_id=user['user_id'],
                    event_type='team_invitation_accepted',
                    details={'invitation_id': invitation['invitation_id']},
                    ip_address=request.remote_addr
                )
                
                # Redireccionar al dashboard
                return redirect(url_for('dashboard.index'))
            
            except Exception as e:
                print(f"Error al aceptar invitación: {str(e)}")
                import traceback
                print(traceback.format_exc())
                flash(f'Error al aceptar la invitación: {str(e)}', 'danger')
                return redirect(url_for('dashboard.index'))
        else:
            if request.method == 'POST':
                print("Errores de validación del formulario de login:")
                for field, errors in form.errors.items():
                    print(f"- {field}: {', '.join(errors)}")
        
        # Mostrar formulario de login con mensaje contextual
        return render_template(
            'unirse_equipo.html', 
            form=form, 
            invitation=invitation, 
            owner_name=owner_name, 
            existing_user=True
        )
    
    # Si es un nuevo usuario, mostrar formulario de registro
    form = RegistroForm()
    
    # Prellenar el email de la invitación y bloquearlo
    form.email.data = invitation['email']
    readonly_email = True
    
    if form.validate_on_submit():
        print("Formulario de registro validado correctamente")
        try:
            # Preparar datos del usuario
            user_data = {
                'email': form.email.data,
                'password': form.password.data,
                'nombre': form.nombre.data,
                'apellido': form.apellido.data,
                'telefono': form.telefono.data if hasattr(form, 'telefono') and form.telefono.data else None,
                'pais': form.pais.data if hasattr(form, 'pais') and form.pais.data else None,
                'acepta_marketing': form.acepta_marketing.data if hasattr(form, 'acepta_marketing') else False,
            }
            
            print(f"Datos del formulario: {user_data}")
            
            # Validar datos sin crear usuario
            AuthService.validate_registration_data(user_data)
            
            # Guardar datos y token en sesión para proceso 2FA
            session['registro_temp_data'] = user_data
            session['registro_totp_secret'] = generate_totp_secret()
            session['registro_invitation_token'] = token
            session['registro_invitation_info'] = {
                'owner_id': invitation['owner_id'],
                'email': invitation['email'],
                'role': invitation['role'],
                'owner_name': owner_name
            }
            
            print("Datos guardados en sesión. Redirigiendo a configuración 2FA.")
            
            # Redireccionar a configuración 2FA
            flash('Por favor, configure la autenticación de dos factores para completar el registro.', 'info')
            return redirect(url_for('auth.configurar_2fa_registro'))
            
        except ValueError as e:
            print(f"Error de validación: {str(e)}")
            flash(str(e), 'danger')
        except Exception as e:
            print(f"Error al procesar el registro: {str(e)}")
            import traceback
            print(traceback.format_exc())
            flash(f'Error al procesar el registro: {str(e)}', 'danger')
    else:
        if request.method == 'POST':
            print("Errores de validación del formulario de registro:")
            for field, errors in form.errors.items():
                print(f"- {field}: {', '.join(errors)}")
    
    # Mostrar formulario de registro con contexto de invitación
    return render_template(
        'unirse_equipo.html', 
        form=form, 
        invitation=invitation, 
        owner_name=owner_name, 
        existing_user=False,
        readonly_email=readonly_email
    )
    
@auth_bp.route('/configurar_2fa_registro', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def configurar_2fa_registro():
    # Verificar que existen los datos temporales en la sesión
    if 'registro_temp_data' not in session:
        flash('Sesión inválida. Por favor, inicie el proceso de registro nuevamente.', 'danger')
        return redirect(url_for('auth.registro'))
    
    # Verificar si existe el secreto TOTP en la sesión, si no, generarlo
    if 'registro_totp_secret' not in session:
        session['registro_totp_secret'] = generate_totp_secret()
        print(f"Generado nuevo secret TOTP para registro: {session['registro_totp_secret']}")
    
    # Obtener el email para el URI TOTP
    user_email = session['registro_temp_data']['email']
    
    # Generar URI para código QR
    totp_uri = get_totp_uri(session['registro_totp_secret'], user_email)
    qr_code = generate_qr_code(totp_uri)
    
    # Si es POST, verificar el código ingresado y completar el registro
    if request.method == 'POST':
        code = request.form.get('code')
        
        try:
            # Verificar el código TOTP
            if not verify_totp(session['registro_totp_secret'], code):
                flash('Código incorrecto. Por favor, intente nuevamente.', 'danger')
                return render_template('configurar_2fa_registro.html', 
                                      qr_code=qr_code, 
                                      secret=session['registro_totp_secret'])
            
            # Si el código es válido, ahora sí crear el usuario con 2FA ya configurado
            user_data = session['registro_temp_data']
            totp_secret = session['registro_totp_secret']
            
            # Crear el usuario con el secreto TOTP ya establecido
            result = AuthService.create_user_with_2fa(user_data, totp_secret)
            
            if result and 'user_id' in result:
                # Datos del nuevo usuario
                user_id = result['user_id']
                email = user_data['email']
                nombre = user_data['nombre']
                
                # Si hay un token de invitación, procesar la aceptación
                team_info = None
                invitation_processed = False    

                if 'registro_invitation_token' in session:
                    try:
                        print(f"Procesando aceptación de invitación con token: {session['registro_invitation_token']}")
                        invitation_token = session['registro_invitation_token']
                        invitation_info = session.get('registro_invitation_info', {})
                        
                        # Primero, actualizar el estado de la invitación a 'accepted'
                        query = f"""
                        SELECT invitation_id, status, owner_id, role
                        FROM {team_invitations_table_id}
                        WHERE token = %s
                        LIMIT 1
                        """
                        
                        results = execute_query(query, [invitation_token])
                        
                        invitation_data = None
                        if results:
                            invitation_data = {
                                'invitation_id': results[0]['invitation_id'],
                                'status': results[0]['status'],
                                'owner_id': results[0]['owner_id'],
                                'role': results[0]['role']
                            }
                        
                        if invitation_data:
                            print(f"Invitación encontrada: {invitation_data['invitation_id']}, status: {invitation_data['status']}")
                            
                            # Actualizar el estado a 'accepted'
                            update_query = f"""
                            UPDATE {team_invitations_table_id}
                            SET 
                                accepted_at = CURRENT_TIMESTAMP,
                                status = 'accepted'
                            WHERE invitation_id = %s
                            """
                            
                            execute_query(update_query, [invitation_data['invitation_id']], fetch=False)
                            print(f"Estado de invitación actualizado a 'accepted' para {invitation_data['invitation_id']}")
                            
                            # Crear entrada en team_members
                            member_id = str(uuid.uuid4())
                            
                            # Obtener datos del propietario y usuario
                            owner_id = invitation_data['owner_id']
                            role = invitation_data['role']
                            
                            # Insertar en team_members
                            member_record = {
                                'member_id': member_id,
                                'owner_id': owner_id,
                                'user_id': user_id,
                                'email': user_email.lower(),
                                'role': role,
                                'invited_at': datetime.now().isoformat(),
                                'joined_at': datetime.now().isoformat(),
                                'status': 'active',
                                'invitation_token': invitation_token
                            }
                            
                            print(f"Insertando miembro en equipo: {member_record}")
                            
                            # Construir consulta de inserción
                            member_fields = list(member_record.keys())
                            placeholders = ["%s"] * len(member_fields)
                            member_values = [member_record[field] for field in member_fields]
                            
                            insert_query = f"""
                            INSERT INTO {team_members_table_id}
                            ({", ".join(member_fields)})
                            VALUES ({", ".join(placeholders)})
                            """
                            
                            errors = execute_query(insert_query, member_values, fetch=False)
                            
                            if isinstance(errors, list) and errors:
                                print(f"Error al insertar miembro: {errors}")
                                raise Exception(f"Error al insertar miembro: {errors}")
                                
                            # Registrar acción en invitation_actions
                            try:
                                action_id = str(uuid.uuid4())
                                action = {
                                    'action_id': action_id,
                                    'invitation_id': invitation_data['invitation_id'],
                                    'action_type': 'accept',
                                    'performed_by': user_id,
                                    'created_at': datetime.now().isoformat(),
                                    'details': json.dumps({'member_id': member_id})
                                }
                                
                                # Construir consulta de inserción
                                action_fields = list(action.keys())
                                action_placeholders = ["%s"] * len(action_fields)
                                action_values = [action[field] for field in action_fields]
                                
                                action_query = f"""
                                INSERT INTO {invitation_actions_table_id}
                                ({", ".join(action_fields)})
                                VALUES ({", ".join(action_placeholders)})
                                """
                                
                                execute_query(action_query, action_values, fetch=False)
                                print(f"Acción de aceptación registrada: {action_id}")
                            except Exception as e:
                                print(f"Error al registrar acción (no fatal): {str(e)}")
                            
                            # Establecer info de equipo en sesión usando la función auxiliar
                            setup_team_session(user_id, owner_id, role)
                            
                            print(f"Miembro añadido al equipo exitosamente. Member ID: {member_id}")
                            invitation_processed = True
                            
                        else:
                            print("No se encontró la invitación en la base de datos")
                            
                    except Exception as e:
                        print(f"Error procesando invitación: {str(e)}")
                        import traceback
                        print(traceback.format_exc())
                        
                        # Intento final de emergencia
                        try:
                            print("Realizando intento final de emergencia")
                            
                            # Definir ID de emergencia en este ámbito
                            emergency_owner_id = '47fc9b20-db22-41c2-b472-0e8bfc51bfcf'
                            
                            # Usar método de emergencia para arreglar membresía
                            backup_result = Team.fix_membership_for_user(
                                user_id, 
                                user_email, 
                                invitation_info.get('owner_id') if invitation_info else emergency_owner_id
                            )
                            
                            if backup_result:
                                print(f"Membresía creada por método alternativo: {backup_result}")
                                # Establecer info en sesión usando la función auxiliar
                                setup_team_session(user_id, backup_result['owner_id'], backup_result['role'])
                                invitation_processed = True
                        except Exception as e2:
                            print(f"Error en intento final de emergencia: {str(e2)}")
                    
                    # Limpiar token de invitación de la sesión
                    session.pop('registro_invitation_token', None)
                    if 'registro_invitation_info' in session:
                        session.pop('registro_invitation_info', None)
                
                # Limpiar datos temporales de registro
                session.pop('registro_temp_data', None)
                session.pop('registro_totp_secret', None)
                
                # Autenticar al usuario automáticamente
                session['user_id'] = user_id
                session['email'] = email
                session['nombre'] = nombre
                session['creditos'] = 0  # Usuario nuevo comienza con 0 créditos
                
                # Registrar login
                AuthService.log_login(user_id, request.remote_addr)
                
                # VERIFICACIÓN FINAL ANTES DE REDIRIGIR
                # Verificar si hay información de membresía
                if invitation_processed or session.get('is_team_member'):
                    # Verificar una vez más - si no hay valor establecido, forzar valores predeterminados
                    if not session.get('team_owner_id'):
                        emergency_owner_id = '47fc9b20-db22-41c2-b472-0e8bfc51bfcf'
                        print("ALERTA: Faltaba team_owner_id, forzando valor predeterminado")
                        session['is_team_member'] = True
                        session['team_owner_id'] = emergency_owner_id
                        session['team_role'] = 'viewer'
                    
                    # Si es miembro de equipo, redirigir al dashboard
                    flash('Registro completado con éxito. Bienvenido a la plataforma.', 'success')
                    
                    # Imprimir información final de sesión
                    print("Variables de sesión finales al redirigir:")
                    print(f"- user_id: {session.get('user_id')}")
                    print(f"- is_team_member: {session.get('is_team_member')}")
                    print(f"- team_owner_id: {session.get('team_owner_id')}")
                    print(f"- team_role: {session.get('team_role')}")
                    
                    return redirect(url_for('dashboard.index'))
                else:
                    # Si es un usuario normal, redirigir a selección de planes
                    flash('Registro completado con éxito. Por favor, selecciona un plan para comenzar.', 'success')
                    return redirect(url_for('payments.planes'))
            else:
                raise Exception("Error al crear el usuario")
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Error al completar el registro: {str(e)}', 'danger')
    
    # Mostrar página con código QR e instrucciones
    return render_template('configurar_2fa_registro.html', 
                      qr_code=qr_code, 
                      secret=session.get('registro_totp_secret', ''))

@auth_bp.route('/recuperar_password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def recuperar_password():
    form = RecuperarPasswordForm()
    
    if form.validate_on_submit():
        result = AuthService.initiate_password_recovery(form.email.data)
        
        # Si hay redirección específica
        if result.get('redirect') == 'espera_recuperacion':
            return render_template('espera_recuperacion.html', minutos_restantes=result.get('minutos_restantes', 90))
            
        if result.get('redirect') == 'verificar_2fa_recuperacion':
            return redirect(url_for('auth.verificar_2fa_recuperacion'))
        
        # Por defecto redirigir a login
        flash(result.get('message', 'Si tu email está registrado, recibirás instrucciones para restablecer tu contraseña.'), 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('recuperar_password.html', form=form)

@auth_bp.route('/verificar_2fa_recuperacion', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def verificar_2fa_recuperacion():
    if 'recovery_user_id' not in session:
        flash('Sesión inválida. Por favor, inicia el proceso nuevamente.', 'danger')
        return redirect(url_for('auth.recuperar_password'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        
        # Añadir información de depuración básica
        user_id = session['recovery_user_id']
        print(f"Código recibido: {code}, Usuario ID: {user_id}")
        
        # Verificación a través del servicio - más simple para evitar errores
        if AuthService.verify_2fa_code(user_id, code):
            # Crear token de recuperación
            token = AuthService.create_recovery_token(user_id)
            
            # Registrar evento de verificación exitosa
            log_security_event(
                user_id=user_id,
                event_type='2fa_recovery_verification',
                details={'success': True},
                ip_address=request.remote_addr
            )
            
            # Redireccionar al reseteo de contraseña
            session['recovery_verified'] = True
            session['recovery_token'] = token
            return redirect(url_for('auth.restablecer_password', token=token))
        else:
            flash('Código incorrecto. Intenta nuevamente.', 'danger')
    
    return render_template('verificar_2fa_recuperacion.html')

@auth_bp.route('/restablecer_password', methods=['GET', 'POST'])
def restablecer_password():
    token = request.args.get('token', '')
    
    # Verificar token
    token_data = AuthService.verify_recovery_token(token)
    if not token_data:
        flash('Token inválido o expirado. Por favor, solicita un nuevo enlace de recuperación.', 'danger')
        return redirect(url_for('auth.recuperar_password'))
    
    user_email = token_data['user'].get('email', '')
    
    form = RestablecerPasswordForm()
    
    if form.validate_on_submit():
        try:
            # Restablecer contraseña
            AuthService.reset_password(token_data, form.password.data)
            
            # Limpiar variables relacionadas de la sesión
            session.pop('recovery_user_id', None)
            session.pop('recovery_email', None)
            session.pop('recovery_verified', None)
            session.pop('recovery_token', None)
            
            flash('Tu contraseña ha sido restablecida con éxito. Ya puedes iniciar sesión con tu nueva contraseña.', 'success')
            return redirect(url_for('auth.login'))
            
        except ValueError as e:
            # Error de validación (contraseña en historial, etc.)
            flash(str(e), 'danger')
        except Exception as e:
            print(f"Error al restablecer contraseña: {str(e)}")
            flash('Ocurrió un error inesperado. Por favor, intenta nuevamente más tarde.', 'danger')
    
    return render_template('restablecer_password.html', form=form, email=user_email, token=token)        

@auth_bp.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    form = CambioPasswordForm()
    if form.validate_on_submit():
        try:
            # Intentar cambiar la contraseña
            success = AuthService.change_password(
                session['user_id'],
                form.password_actual.data,
                form.password_nuevo.data
            )
            
            if success:
                flash('Tu contraseña ha sido actualizada correctamente.', 'success')
                return redirect(url_for('dashboard.index'))
                
        except ValueError as e:
            flash(str(e), 'danger')
            print(f"Error de validación en cambio de contraseña: {str(e)}")
        except Exception as e:
            flash('Error al cambiar la contraseña. Por favor intente más tarde.', 'danger')
            print(f"Error inesperado en cambio de contraseña: {str(e)}")
    
    return render_template('cambiar_password.html', form=form)

@auth_bp.route('/configurar_2fa', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
@login_required
def configurar_2fa():
    # Verificar si ya tiene 2FA configurado
    from app.models.user import User
    user = User.get_by_id(session['user_id'])
    
    # Si ya tiene 2FA configurado
    if user and user.get('totp_secret'):
        log_security_event(
            user_id=session['user_id'],
            event_type='2fa_setup_attempt',
            details={'status': 'already_configured'},
            ip_address=request.remote_addr
        )
        flash('Ya tienes la autenticación de dos factores configurada.', 'info')
        return redirect(url_for('dashboard.index'))
    
    # Generar nuevo secreto
    if 'totp_secret' not in session:
        session['totp_secret'] = generate_totp_secret()
    
    # Generar URI para código QR
    totp_uri = get_totp_uri(session['totp_secret'], session['email'])
    qr_code = generate_qr_code(totp_uri)
    
    # Si es POST, verificar el código ingresado
    if request.method == 'POST':
        code = request.form.get('code')
        
        try:
            # Configurar 2FA
            AuthService.configure_2fa(session['user_id'], session['totp_secret'], code)
            
            # Limpiar el secreto de la sesión
            session.pop('totp_secret', None)
            
            flash('Autenticación de dos factores configurada con éxito.', 'success')
            return redirect(url_for('dashboard.index'))
            
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Error al guardar la configuración: {str(e)}', 'danger')
    
    # Mostrar página con código QR e instrucciones
    return render_template('configurar_2fa.html', 
                          qr_code=qr_code, 
                          secret=session['totp_secret'])