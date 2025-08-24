from functools import wraps
# Quitar la importación de Plan a nivel global: from app.models.plan import Plan
from flask import session, redirect, url_for, flash, request
from app.utils.logging import log_security_event

def login_required(f):
    """
    Decorador para verificar si el usuario está autenticado
    
    Si el usuario no está autenticado, redirecciona a la página de login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorador para verificar si el usuario es administrador
    
    Si el usuario no es administrador, redirecciona al dashboard
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        if session.get('tipo_usuario') != 'admin':
            flash('No tienes permisos para acceder a esta página.', 'danger')
            log_security_event(
                user_id=session['user_id'],
                event_type='unauthorized_access',
                details={'route': request.path},
                ip_address=request.remote_addr
            )
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def has_credits(min_credits=1):
    """
    Decorador para verificar si el usuario tiene suficientes créditos
    
    Args:
        min_credits: Cantidad mínima de créditos requeridos
        
    Si el usuario no tiene suficientes créditos, redirecciona a la página de compra
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor inicia sesión para acceder a esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            if session.get('creditos', 0) < min_credits:
                flash(f'Necesitas al menos {min_credits} créditos para acceder a esta función.', 'warning')
                return redirect(url_for('payments.recargar_creditos'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def active_plan_required(f):
    """
    Decorador para verificar si el usuario tiene un plan activo
    
    Si el usuario no tiene un plan activo, redirecciona a la página de planes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Verificar si el usuario es miembro de un equipo
        is_team_member = session.get('is_team_member', False)
        
        # Si es miembro de equipo, no necesita verificar plan propio
        if is_team_member and session.get('team_owner_id'):
            # Imprimir información de depuración
            print(f"Verificación de plan omitida: Usuario {session['user_id']} es miembro de equipo")
            print(f"Propietario ID: {session.get('team_owner_id')}")
            print(f"Rol: {session.get('team_role')}")
            
            # Verificar que la información del equipo todavía es válida
            try:
                from app.models.team import Team
                team_info = Team.get_member_info(session['user_id'])
                
                if not team_info:
                    # Intento adicional: buscar por email
                    user = None
                    try:
                        from app.models.user import User
                        user = User.get_by_id(session['user_id'])
                    except Exception as e:
                        print(f"Error al obtener usuario: {str(e)}")
                    
                    if user and user.get('email'):
                        # Buscar membresía por email
                        from app.models.database import client, team_members_table_id
                        from google.cloud import bigquery
                        
                        query = f"""
                        SELECT member_id, owner_id, role
                        FROM `{team_members_table_id}`
                        WHERE LOWER(email) = @email
                        AND status = 'active'
                        LIMIT 1
                        """
                        
                        job_config = bigquery.QueryJobConfig(
                            query_parameters=[
                                bigquery.ScalarQueryParameter("email", "STRING", user['email'].lower()),
                            ]
                        )
                        
                        results = client.query(query, job_config=job_config).result()
                        found_by_email = False
                        
                        for row in results:
                            # Actualizar la membresía con el ID de usuario correcto
                            update_query = f"""
                            UPDATE `{team_members_table_id}`
                            SET user_id = @user_id
                            WHERE member_id = @member_id
                            """
                            
                            update_job_config = bigquery.QueryJobConfig(
                                query_parameters=[
                                    bigquery.ScalarQueryParameter("user_id", "STRING", session['user_id']),
                                    bigquery.ScalarQueryParameter("member_id", "STRING", row.member_id),
                                ]
                            )
                            
                            client.query(update_query, update_job_config).result()
                            
                            # Recuperar teamInfo
                            team_info = {
                                'member_id': row.member_id,
                                'owner_id': row.owner_id,
                                'role': row.role
                            }
                            
                            found_by_email = True
                            print(f"Recuperada membresía por email: {team_info}")
                            break

                if not team_info:
                    # La información de equipo ya no es válida, limpiar
                    print("Información de equipo inválida, limpiando...")
                    session.pop('is_team_member', None)
                    session.pop('team_owner_id', None)
                    session.pop('team_role', None)
                    session.pop('team_owner_name', None)
                    session.pop('team_owner_creditos', None)
                    
                    # CÓDIGO NUEVO: Verificar reparación de emergencia
                    emergency_owner_id = '47fc9b20-db22-41c2-b472-0e8bfc51bfcf'  # ID fijo del propietario
                    
                    user = None
                    try:
                        from app.models.user import User
                        user = User.get_by_id(session['user_id'])
                    except Exception as e:
                        print(f"Error al obtener usuario: {str(e)}")
                    
                    if user and user.get('email'):
                        # Intento de reparación de emergencia
                        print(f"Intento de reparación de emergencia para: {user['email']}")
                        
                        from app.models.team import Team
                        emergency_fix = Team.fix_membership_for_user(
                            session['user_id'], 
                            user['email'], 
                            emergency_owner_id
                        )
                        
                        if emergency_fix:
                            print(f"Reparación de emergencia exitosa: {emergency_fix}")
                            session['is_team_member'] = True
                            session['team_owner_id'] = emergency_owner_id
                            session['team_role'] = emergency_fix['role']
                            
                            # Obtener información del propietario
                            from app.models.user import User
                            owner = User.get_by_id(emergency_owner_id)
                            if owner:
                                session['team_owner_name'] = f"{owner.get('nombre', '')} {owner.get('apellido', '')}".strip()
                                session['team_owner_creditos'] = owner.get('creditos', 0)
                            
                            # Obtener plan del propietario
                            from app.models.plan import Plan
                            active_plan = Plan.get_user_active_plan(emergency_owner_id)
                            
                            if active_plan:
                                print(f"Plan del propietario obtenido después de reparación")
                                session['active_plan'] = active_plan
                                return f(*args, **kwargs)
                            else:
                                flash('El propietario de tu equipo no tiene un plan activo. Contacta con ellos.', 'warning')
                                return redirect(url_for('dashboard.check_team_status'))
                    
                    # Ahora verificar si tiene un plan propio
                    from app.models.plan import Plan
                    active_plan = Plan.get_user_active_plan(session['user_id'])
                    if not active_plan:
                        flash('Necesitas tener un plan activo para acceder a esta función.', 'warning')
                        return redirect(url_for('payments.planes'))
                else:
                    # Cargar información del propietario
                    from app.models.plan import Plan
                    from app.models.user import User
                    
                    owner_id = team_info['owner_id']
                    active_plan = Plan.get_user_active_plan(owner_id)
                    
                    if not active_plan:
                        flash('El propietario de tu equipo no tiene un plan activo. Contacta con ellos.', 'warning')
                        return redirect(url_for('dashboard.check_team_status'))
                    
                    # Actualizar información del equipo en sesión
                    session['team_owner_id'] = owner_id
                    session['team_role'] = team_info['role']
                    
                    # Actualizar información del propietario
                    owner = User.get_by_id(owner_id)
                    if owner:
                        session['team_owner_name'] = f"{owner.get('nombre', '')} {owner.get('apellido', '')}".strip()
                        session['team_owner_creditos'] = owner.get('creditos', 0)
                    
                    # Guardar en sesión para esta solicitud
                    session['active_plan'] = active_plan
            except Exception as e:
                print(f"Error verificando información de equipo: {str(e)}")
                import traceback
                print(traceback.format_exc())
                # Si hay un error, verificar plan propio
                from app.models.plan import Plan
                active_plan = Plan.get_user_active_plan(session['user_id'])
                if not active_plan:
                    flash('Necesitas tener un plan activo para acceder a esta función.', 'warning')
                    return redirect(url_for('payments.planes'))
                
            return f(*args, **kwargs)
        
        # Verificar si el usuario tiene un plan activo
        from app.models.plan import Plan
        active_plan = Plan.get_user_active_plan(session['user_id'])
        if not active_plan:
            flash('Necesitas tener un plan activo para acceder a esta función.', 'warning')
            from app.utils.logging import log_security_event
            log_security_event(
                user_id=session['user_id'],
                event_type='access_attempt_no_plan',
                details={'route': request.path},
                ip_address=request.remote_addr
            )
            return redirect(url_for('payments.planes'))
        
        # Guardar el plan activo en la sesión para esta solicitud
        session['active_plan'] = active_plan
        return f(*args, **kwargs)
    return decorated_function

def team_permission_required(role='admin'):
    """
    Verifica si el usuario tiene permiso según su rol en el equipo
    
    Args:
        role: Rol mínimo requerido (admin, editor, viewer)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor inicia sesión para acceder a esta página.', 'warning')
                return redirect(url_for('auth.login'))
                
            # Si no es miembro de equipo y es propietario, siempre tiene acceso
            if not session.get('is_team_member', False):
                return f(*args, **kwargs)
                
            # Verificar rol
            user_role = session.get('team_role', '')
            
            if role == 'admin' and user_role != 'admin':
                flash('No tienes permisos para realizar esta acción', 'danger')
                log_security_event(
                    user_id=session['user_id'],
                    event_type='unauthorized_team_access',
                    details={'route': request.path, 'required_role': 'admin', 'user_role': user_role},
                    ip_address=request.remote_addr
                )
                return redirect(url_for('dashboard.index'))
                
            if role == 'editor' and user_role not in ['admin', 'editor']:
                flash('No tienes permisos para realizar esta acción', 'danger')
                log_security_event(
                    user_id=session['user_id'],
                    event_type='unauthorized_team_access',
                    details={'route': request.path, 'required_role': 'editor', 'user_role': user_role},
                    ip_address=request.remote_addr
                )
                return redirect(url_for('dashboard.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator