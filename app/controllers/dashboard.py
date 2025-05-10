from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify
from app.utils.decorators import login_required
from app.utils.sanitization import sanitize_output
from app.models.user import User
from app.models.plan import Plan
from app.models.team import Team
from app.utils.logging import log_app_event, log_security_event
from app.services.payment_service import PaymentService
from app.models.database_pg import execute_query
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/repair_membership')
@login_required
def repair_membership():
    
    # ID del propietario (el que tiene el plan)
    owner_id = '47fc9b20-db22-41c2-b472-0e8bfc51bfcf'  # Este es el ID que vimos en la invitación
    
    # Arreglar la membresía manualmente
    result = Team.fix_membership_for_user(session['user_id'], session['email'], owner_id)
    
    if result:
        # Actualizar las variables de sesión directamente
        session['is_team_member'] = True
        session['team_owner_id'] = owner_id
        session['team_role'] = result['role']
        
        # Obtener información del propietario
        from app.models.user import User
        owner = User.get_by_id(owner_id)
        if owner:
            session['team_owner_name'] = owner.get('nombre', 'Propietario')
            session['team_owner_creditos'] = owner.get('creditos', 0)
        
        flash('¡Membresía de equipo reparada correctamente!', 'success')
    else:
        flash('No se pudo reparar la membresía. Por favor, contacte al administrador.', 'danger')
    
    return redirect(url_for('dashboard.index'))

# Añadir una nueva ruta para verificar y reparar la membresía de equipo automáticamente
@dashboard_bp.route('/repair_team_membership')
@login_required
def repair_team_membership():
    """
    Verifica y repara automáticamente la membresía del equipo basado en información de la BD
    """
    # Verificar si el usuario ya está marcado como miembro de equipo
    is_team_member = session.get('is_team_member', False)
    
    if is_team_member:
        flash('Ya estás correctamente registrado como miembro de un equipo.', 'info')
        return redirect(url_for('dashboard.index'))
    
    # Obtener información real de membresía desde la base de datos
    team_info = Team.get_member_info(session['user_id'])
    
    if team_info:
        # El usuario SÍ es miembro de un equipo, reparar la sesión
        session['is_team_member'] = True
        session['team_owner_id'] = team_info['owner_id']
        session['team_role'] = team_info['role']
        
        # Obtener información del propietario
        from app.models.user import User
        owner = User.get_by_id(team_info['owner_id'])
        if owner:
            session['team_owner_name'] = owner.get('nombre', 'Propietario')
            session['team_owner_creditos'] = owner.get('creditos', 0)
            
            # Mostrar mensaje informativo
            flash(f'¡Tu membresía ha sido reparada! Estás usando el plan de {owner.get("nombre", "Propietario")}', 'success')
            print(f"Membresía reparada automáticamente para: {session['user_id']}")
            print(f"- Propietario ID: {team_info['owner_id']}")
            print(f"- Rol: {team_info['role']}")
        
        return redirect(url_for('dashboard.index'))
    else:
        # El usuario no es miembro de ningún equipo
        flash('No se encontró información de membresía de equipo para este usuario.', 'warning')
        return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/check_team_status')
@login_required
def check_team_status():
    """Página diagnóstica para verificar el estado del equipo"""
    
    # Información de la sesión actual
    session_info = {
        'user_id': session.get('user_id'),
        'email': session.get('email'),
        'is_team_member': session.get('is_team_member'),
        'team_owner_id': session.get('team_owner_id'),
        'team_role': session.get('team_role'),
        'team_owner_name': session.get('team_owner_name'),
        'team_owner_creditos': session.get('team_owner_creditos')
    }
    
    # Consultar información real en la base de datos
    team_info = Team.get_member_info(session['user_id'])
    
    # Verificar plan activo
    try:
        if session.get('is_team_member') and session.get('team_owner_id'):
            owner_id = session.get('team_owner_id')
            plan_info = Plan.get_user_active_plan(owner_id)
        else:
            plan_info = Plan.get_user_active_plan(session['user_id'])
    except Exception as e:
        plan_info = None
        print(f"Error al verificar plan: {str(e)}")
    
    return render_template('check_team_status.html',
                          session_info=session_info,
                          team_info=team_info,
                          plan_info=plan_info)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """
    Página principal del dashboard del usuario
    Muestra información general y transacciones recientes
    """
    # Cargar datos actualizados del usuario
    user = User.get_by_id(session['user_id'])
    if user:
        session['creditos'] = user.get('creditos', 0)
    
    # Verificar si es miembro de un equipo (a través de consulta explícita)
    team_info = Team.get_member_info(session['user_id'])
    is_team_member = team_info is not None
    
    # Actualizar la sesión con la información correcta
    session['is_team_member'] = is_team_member
    if is_team_member:
        session['team_owner_id'] = team_info['owner_id']
        session['team_role'] = team_info['role']
        
        # Obtener información del propietario
        owner = User.get_by_id(team_info['owner_id'])
        if owner:
            session['team_owner_name'] = owner.get('nombre', 'Propietario')
            session['team_owner_creditos'] = owner.get('creditos', 0)
    else:
        # Si no es miembro de equipo, limpiar variables de sesión relacionadas
        if 'team_owner_id' in session:
            del session['team_owner_id']
        if 'team_role' in session:
            del session['team_role']
        if 'team_owner_name' in session:
            del session['team_owner_name']
        if 'team_owner_creditos' in session:
            del session['team_owner_creditos']
    
    owner_info = None
    
    # Verificar si es propietario de equipo (admin)
    is_team_owner = False
    team_members = []
    if not is_team_member:
        # Consultar si hay miembros del equipo donde el usuario es propietario
        team_members = Team.get_team_members(session['user_id'])
        is_team_owner = len(team_members) > 0
    
    # Cargar plan activo según si es miembro de equipo o no
    try:
        if is_team_member:
            # Si es miembro de un equipo, obtener la información del plan del propietario
            owner_info = Team.get_owner_plan_info(session['user_id'])
            if owner_info and 'plan' in owner_info:
                active_plan = owner_info['plan']
            else:
                active_plan = None
        else:
            # Si no es miembro de un equipo, obtener su propio plan
            active_plan = Plan.get_user_active_plan(session['user_id'])
    except Exception as e:
        print(f"Error al cargar plan activo: {str(e)}")
        active_plan = None
        flash('No se pudo cargar la información del plan activo.', 'warning')
    
    # NUEVO: Calcular miembros actuales y máximo permitido para mostrar en el dashboard
    current_users, max_users = 0, 0
    if active_plan and not is_team_member and is_team_owner:
        current_users, max_users = Team.count_team_members(session['user_id'])
    
    # Cargar historial de transacciones
    transacciones = User.get_transactions(session['user_id'])
    
    # Sanitizar datos para prevenir XSS
    sanitized_transactions = []
    for t in transacciones:
        sanitized_transactions.append({
            'transaction_id': t['transaction_id'],
            'monto': t['monto'],
            'creditos': t['creditos'],
            'metodo_pago': sanitize_output(t['metodo_pago']),
            'estado': sanitize_output(t['estado']),
            'fecha_transaccion': t['fecha_transaccion']
        })
    
    # Registrar evento de visualización del dashboard
    log_app_event(
        user_id=session['user_id'],
        module='dashboard',
        action='view',
        details={'is_team_member': is_team_member},
        ip_address=request.remote_addr
    )
    
    return render_template('dashboard.html', 
                          transacciones=sanitized_transactions,
                          active_plan=active_plan,
                          user=user,
                          is_team_member=is_team_member,
                          is_team_owner=is_team_owner,
                          team_members=team_members,
                          owner_info=owner_info,
                          current_users=current_users,  # NUEVO: Pasar el número actual de usuarios
                          max_users=max_users)  # NUEVO: Pasar el número máximo de usuarios

@dashboard_bp.route('/perfil')
@login_required
def perfil():
    """
    Página de perfil del usuario
    Muestra y permite editar información personal
    """
    # Cargar datos del usuario
    user = User.get_by_id(session['user_id'])
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='dashboard',
        action='view_profile',
        details={},
        ip_address=request.remote_addr
    )
    
    return render_template('perfil.html', user=user)

@dashboard_bp.route('/servicios')
@login_required
def servicios():
    """
    Página de servicios disponibles
    """
    # Verificar si es miembro de un equipo
    is_team_member = session.get('is_team_member', False)
    owner_info = None
    
    try:
        # Verificar que el usuario tenga un plan activo
        if is_team_member:
            # Si es miembro de un equipo, obtener la información del plan del propietario
            owner_info = Team.get_owner_plan_info(session['user_id'])
            if owner_info and 'plan' in owner_info:
                active_plan = owner_info['plan']
            else:
                active_plan = None
        else:
            # Si no es miembro de un equipo, obtener su propio plan
            active_plan = Plan.get_user_active_plan(session['user_id'])
            
        if not active_plan:
            flash('Necesitas tener un plan activo para acceder a los servicios.', 'warning')
            return redirect(url_for('payments.planes'))
    except AttributeError:
        # Manejar el caso donde el método no existe
        flash('No se pudo verificar tu plan activo. Contacta al soporte.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    # Cargar servicios disponibles
    from app.models.database_pg import servicios_table_id
    
    # Consulta para PostgreSQL
    query = f"""
    SELECT servicio_id, nombre, descripcion, costo_creditos, categoria
    FROM {servicios_table_id}
    WHERE activo = TRUE
    ORDER BY categoria, costo_creditos
    """
    
    # Ejecutar consulta usando la función para PostgreSQL
    results = execute_query(query, fetch=True, as_dict=True)
    
    servicios = []
    for row in results:
        servicios.append({
            'servicio_id': row['servicio_id'],
            'nombre': sanitize_output(row['nombre']),
            'descripcion': sanitize_output(row['descripcion']),
            'costo_creditos': row['costo_creditos'],
            'categoria': sanitize_output(row['categoria'])
        })
    
    # Agrupar servicios por categoría para mostrarlos mejor
    servicios_por_categoria = {}
    for servicio in servicios:
        categoria = servicio['categoria']
        if categoria not in servicios_por_categoria:
            servicios_por_categoria[categoria] = []
        servicios_por_categoria[categoria].append(servicio)
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='dashboard',
        action='view_services',
        details={'is_team_member': is_team_member},
        ip_address=request.remote_addr
    )
    
    return render_template('servicios.html', 
                          servicios=servicios,
                          servicios_por_categoria=servicios_por_categoria,
                          active_plan=active_plan,
                          is_team_member=is_team_member,
                          owner_info=owner_info)

@dashboard_bp.route('/historial')
@login_required
def historial():
    """
    Página de historial completo de transacciones y uso de créditos
    """
    # Cargar historial completo de transacciones
    from app.models.database_pg import transacciones_table_id
    
    # Parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    # Consulta para PostgreSQL - Contar total de transacciones
    count_query = f"""
    SELECT COUNT(*) as total
    FROM {transacciones_table_id}
    WHERE user_id = %s
    """
    
    count_results = execute_query(count_query, params=(session['user_id'],), fetch=True, as_dict=True)
    total = 0
    if count_results:
        total = count_results[0]['total']
    
    # Calcular total de páginas
    total_pages = (total + per_page - 1) // per_page
    
    # Consulta para PostgreSQL - Obtener transacciones paginadas
    query = f"""
    SELECT transaction_id, monto, creditos, metodo_pago, estado, fecha_transaccion, detalles
    FROM {transacciones_table_id}
    WHERE user_id = %s
    ORDER BY fecha_transaccion DESC
    LIMIT %s
    OFFSET %s
    """
    
    params = (session['user_id'], per_page, offset)
    results = execute_query(query, params=params, fetch=True, as_dict=True)
    
    transacciones = []
    for row in results:
        transacciones.append({
            'transaction_id': row['transaction_id'],
            'monto': row['monto'],
            'creditos': row['creditos'],
            'metodo_pago': sanitize_output(row['metodo_pago']),
            'estado': sanitize_output(row['estado']),
            'fecha_transaccion': row['fecha_transaccion'],
            'detalles': row['detalles']
        })
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='dashboard',
        action='view_history',
        details={'page': page},
        ip_address=request.remote_addr
    )
    
    return render_template('historial.html', 
                          transacciones=transacciones,
                          page=page,
                          total_pages=total_pages,
                          total=total)

@dashboard_bp.route('/team-credits')
@login_required
def team_credits():
    """
    Página para gestionar los créditos del equipo (solo para admin/propietario)
    """
    # Verificar si el usuario es propietario de equipo
    team_members = Team.get_team_members(session['user_id'])
    
    if not team_members:
        flash('Esta funcionalidad está disponible solo para propietarios de equipos.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    # Obtener información actualizada del usuario (admin)
    user = User.get_by_id(session['user_id'])
    if not user:
        flash('Error al cargar información del usuario.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Obtener información detallada de cada miembro
    members_with_info = []
    for member in team_members:
        if member['user_id']:
            member_user = User.get_by_id(member['user_id'])
            if member_user:
                members_with_info.append({
                    'member_id': member['member_id'],
                    'user_id': member['user_id'],
                    'nombre': member_user.get('nombre', 'Sin nombre'),
                    'apellido': member_user.get('apellido', ''),
                    'email': member['email'],
                    'role': member['role'],
                    'creditos': member_user.get('creditos', 0)
                })
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='dashboard',
        action='view_team_credits',
        details={'team_size': len(members_with_info)},
        ip_address=request.remote_addr
    )
    
    # Cargar plan activo del propietario
    active_plan = Plan.get_user_active_plan(session['user_id'])
    
    return render_template('team_credits.html',
                          team_members=members_with_info,
                          user=user,
                          active_plan=active_plan)

@dashboard_bp.route('/transfer-credits', methods=['POST'])
@login_required
def transfer_credits():
    """
    API para transferir créditos a un miembro del equipo
    """
    # Obtener datos de la solicitud
    member_id = request.form.get('member_id')
    cantidad = request.form.get('cantidad')
    
    # Validación básica
    if not member_id or not cantidad:
        return jsonify({
            'success': False,
            'message': 'Faltan datos requeridos para la transferencia'
        }), 400
    
    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            return jsonify({
                'success': False,
                'message': 'La cantidad debe ser un número positivo'
            }), 400
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'La cantidad debe ser un número válido'
        }), 400
    
    # Verificar que el usuario es propietario de un equipo
    team_members = Team.get_team_members(session['user_id'])
    if not team_members:
        return jsonify({
            'success': False,
            'message': 'No eres propietario de un equipo'
        }), 403
    
    # Buscar el miembro específico
    target_member = None
    for member in team_members:
        if member['member_id'] == member_id:
            target_member = member
            break
    
    if not target_member:
        return jsonify({
            'success': False,
            'message': 'Miembro no encontrado en tu equipo'
        }), 404
    
    # Verificar que el usuario tiene suficientes créditos
    user = User.get_by_id(session['user_id'])
    if not user or user.get('creditos', 0) < cantidad:
        return jsonify({
            'success': False,
            'message': 'No tienes suficientes créditos para realizar esta transferencia'
        }), 400
    
    # Realizar la transferencia
    try:
        success = PaymentService.transfer_credits(
            session['user_id'],  # Admin/propietario
            target_member['user_id'],  # Miembro del equipo
            cantidad
        )
        
        if success:
            # Obtener datos actualizados después de la transferencia
            admin_updated = User.get_by_id(session['user_id'])
            member_updated = User.get_by_id(target_member['user_id'])
            
            # Actualizar la sesión con los créditos del admin
            if admin_updated:
                session['creditos'] = admin_updated.get('creditos', 0)
            
            # Registrar evento
            log_security_event(
                user_id=session['user_id'],
                event_type='credit_transfer',
                details={
                    'to_user_id': target_member['user_id'],
                    'to_email': target_member['email'],
                    'cantidad': cantidad
                },
                ip_address=request.remote_addr
            )
            
            return jsonify({
                'success': True,
                'message': f'Transferencia de {cantidad} créditos realizada correctamente',
                'admin_credits': admin_updated.get('creditos', 0) if admin_updated else None,
                'member_credits': member_updated.get('creditos', 0) if member_updated else None
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error al procesar la transferencia'
            }), 500
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f"Error en transferencia de créditos: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno al procesar la transferencia'
        }), 500

# NUEVO: Verificar invitaciones pendientes para diagnóstico
@dashboard_bp.route('/check_invitations')
@login_required
def check_invitations():
    """Busca invitaciones pendientes para un email"""
    email = request.args.get('email', session.get('email'))
    if not email:
        flash('Email no especificado', 'warning')
        return redirect(url_for('dashboard.check_team_status'))
    
    # Buscar invitaciones
    invitations = Team.find_invitations_by_email(email)
    
    return render_template('check_team_status.html',
                         session_info={
                             'user_id': session.get('user_id'),
                             'email': session.get('email'),
                             'is_team_member': session.get('is_team_member'),
                             'team_owner_id': session.get('team_owner_id'),
                             'team_role': session.get('team_role')
                         },
                         team_info=Team.get_member_info(session['user_id']),
                         invitations=invitations)

# NUEVO: Procesar una invitación específica
@dashboard_bp.route('/process_invitation/<invitation_id>')
@login_required
def process_invitation(invitation_id):
    """Procesa manualmente una invitación pendiente"""
    try:
        result = Team.process_invitation_for_user(invitation_id, session['user_id'])
        if result:
            flash('Invitación procesada correctamente. Tu membresía de equipo ha sido actualizada.', 'success')
            # Actualizar la sesión
            return redirect(url_for('dashboard.repair_team_membership'))
        else:
            flash('No se pudo procesar la invitación. Puede que haya expirado o ya no sea válida.', 'warning')
    except Exception as e:
        flash(f'Error al procesar la invitación: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard.check_team_status'))

# NUEVO: Reparación por email
@dashboard_bp.route('/repair_by_email')
@login_required
def repair_by_email():
    """Intenta reparar la membresía buscando invitaciones por email"""
    try:
        # Buscar invitaciones para este email
        invitations = Team.find_invitations_by_email(session['email'])
        if invitations and len(invitations) > 0:
            # Tomar la primera invitación válida
            invitation = invitations[0]
            result = Team.process_invitation_for_user(invitation['invitation_id'], session['user_id'])
            if result:
                flash('¡Reparación exitosa! Se encontró y procesó una invitación pendiente.', 'success')
                return redirect(url_for('dashboard.repair_team_membership'))
            else:
                flash('Se encontró una invitación pero no se pudo procesar.', 'warning')
        else:
            flash('No se encontraron invitaciones pendientes para tu correo electrónico.', 'warning')
    except Exception as e:
        flash(f'Error durante la reparación: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard.check_team_status'))

# NUEVO: Reparación de emergencia
@dashboard_bp.route('/emergency_fix')
@login_required
def emergency_fix():
    """Última opción de reparación - creación forzada de membresía"""
    try:
        # Solo usar en casos donde realmente es necesario
        # Esta función debería requerir confirmación adicional en producción
        result = Team.create_emergency_membership(session['user_id'], session['email'])
        if result:
            flash('¡Reparación de emergencia completada! Se ha creado una nueva membresía.', 'success')
            return redirect(url_for('dashboard.repair_team_membership'))
        else:
            flash('No se pudo completar la reparación de emergencia.', 'danger')
    except Exception as e:
        flash(f'Error durante la reparación de emergencia: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard.check_team_status'))