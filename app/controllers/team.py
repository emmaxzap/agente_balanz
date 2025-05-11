from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify
from app.utils.decorators import login_required
from app.models.team import Team
from app.models.user import User
from app.models.plan import Plan  
from app.utils.logging import log_security_event, log_app_event
from app.utils.sanitization import sanitize_output
from datetime import datetime  

# Crear el blueprint que se importa en __init__.py
team_bp = Blueprint('team', __name__)

@team_bp.route('/change_member_role', methods=['POST'])
@login_required
def change_member_role():
    """
    Alias para cambiar el rol de un miembro del equipo (para mantener compatibilidad)
    """
    return change_role()  # Redirigir a la función existente

@team_bp.route('/')
@login_required
def index():
    """
    Página principal de gestión de equipo
    """
    user_id = session.get('user_id')
    
    # Verificar si hay un plan activo
    active_plan = Plan.get_user_active_plan(user_id)
    if not active_plan:
        flash('Necesitas un plan activo para gestionar equipos.', 'warning')
        return redirect(url_for('payments.planes'))
    
    # SOLUCIÓN: Asegurarse de que la bandera is_team_member no esté activa para propietarios
    # El problema parece ser que esta bandera está impidiendo mostrar elementos del menú
    if 'is_team_member' in session:
        # Verificar si es propietario
        team_owner_check = Team.get_team_members(user_id)
        if team_owner_check:
            # Si es propietario, no debería tener la bandera is_team_member
            session.pop('is_team_member', None)
    
    # Obtener información del equipo
    team_members = Team.get_team_members(user_id)
    
    # Obtener miembros incluido el propietario
    if user_id:
        # Añadir al propietario como primer miembro con rol admin
        user_info = User.get_by_id(user_id)
        if user_info:
            owner_present = False
            for member in team_members:
                if member.get('user_id') == user_id:
                    owner_present = True
                    break
            
            if not owner_present:
                # Añadir propietario como miembro
                own_member = {
                    'member_id': 'owner-' + user_id,
                    'user_id': user_id,
                    'email': user_info.get('email'),
                    'role': 'admin',
                    'joined_at': datetime.now(),
                    'status': 'active'
                }
                team_members.insert(0, own_member)
    
    # Obtener estadísticas de uso del equipo si la función está disponible
    team_usage_stats = []
    if hasattr(Team, 'get_team_usage_stats'):
        team_usage_stats = Team.get_team_usage_stats(user_id) if team_members else []
    
    # Calcular miembros actuales y máximo permitido
    current_users, max_users = Team.count_team_members(user_id)
    
    # Determinar si puede invitar más miembros
    can_invite = current_users < max_users
    
    # Obtener invitaciones pendientes
    pending_invitations = Team.get_pending_invitations(user_id)
    
    # Registrar evento
    log_app_event(
        user_id=user_id,
        module='team',
        action='view_team_home',
        details={'has_active_plan': bool(active_plan)},
        ip_address=request.remote_addr
    )
    
    return render_template('team/index.html',
                          active_plan=active_plan,
                          team_members=team_members,
                          current_users=current_users,
                          max_users=max_users,
                          can_invite=can_invite,
                          pending_invitations=pending_invitations,
                          team_usage_stats=team_usage_stats)

@team_bp.route('/team')
@login_required
def team_home():
    """
    Página principal de gestión de equipo
    """
    # Verificar si el usuario es propietario de un equipo
    team_members = Team.get_team_members(session['user_id'])
    is_team_owner = len(team_members) > 0
    
    # Verificar si es miembro de un equipo
    team_info = Team.get_member_info(session['user_id'])
    is_team_member = team_info is not None
    
    # Solo propietarios o miembros pueden acceder a esta página
    if not is_team_owner and not is_team_member:
        flash('No tienes acceso a la gestión de equipos.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='team',
        action='view_team_home',
        details={'is_owner': is_team_owner, 'is_member': is_team_member},
        ip_address=request.remote_addr
    )
    
    return render_template('team.html', 
                          is_team_owner=is_team_owner,
                          is_team_member=is_team_member,
                          team_info=team_info,
                          team_members=team_members if is_team_owner else [])

@team_bp.route('/transfer_credits', methods=['POST'])
@login_required
def transfer_credits():
    """
    Transfiere créditos a un miembro del equipo
    """
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        cantidad = request.form.get('cantidad')
        
        # Validaciones básicas
        if not member_id or not cantidad:
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos'
            }), 400
        
        try:
            cantidad = int(cantidad)
            if cantidad <= 0:
                return jsonify({
                    'success': False,
                    'message': 'La cantidad debe ser mayor que cero'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Cantidad inválida'
            }), 400
        
        # Verificar si el usuario tiene suficientes créditos
        user_id = session.get('user_id')
        user = User.get_by_id(user_id)
        
        if not user or user.get('creditos', 0) < cantidad:
            return jsonify({
                'success': False,
                'message': 'No tienes suficientes créditos para esta transferencia'
            }), 400
        
        # Obtener información del miembro
        team_members = Team.get_team_members(user_id)
        target_member = None
        
        for member in team_members:
            if member.get('member_id') == member_id:
                target_member = member
                break
        
        if not target_member or not target_member.get('user_id'):
            return jsonify({
                'success': False,
                'message': 'Miembro no encontrado o inválido'
            }), 404
        
        # Realizar la transferencia
        success = User.transfer_credits(user_id, target_member['user_id'], cantidad)
        
        if success:
            # Obtener nuevos balances
            updated_user = User.get_by_id(user_id)
            updated_member = User.get_by_id(target_member['user_id'])
            
            return jsonify({
                'success': True,
                'message': f'Transferencia exitosa de {cantidad} créditos',
                'admin_credits': updated_user.get('creditos', 0),
                'member_credits': updated_member.get('creditos', 0)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error al procesar la transferencia'
            }), 500
    
    return jsonify({
        'success': False,
        'message': 'Método no permitido'
    }), 405                         

@team_bp.route('/members')
@login_required
def team_members():
    """
    Página de miembros del equipo
    """
    # Verificar si el usuario es propietario de equipo
    team_members = Team.get_team_members(session['user_id'])
    
    # Si no es propietario, redirigir al dashboard
    if not team_members:
        flash('Esta funcionalidad está disponible solo para propietarios de equipos.', 'warning')
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
                    'joined_at': member['joined_at']
                })
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='team',
        action='view_team_members',
        details={'member_count': len(members_with_info)},
        ip_address=request.remote_addr
    )
    
    return render_template('team_members.html', 
                          team_members=members_with_info)

@team_bp.route('/invitations')
@login_required
def team_invitations():
    """
    Página de invitaciones pendientes
    """
    # Verificar si el usuario es propietario de equipo
    team_members = Team.get_team_members(session['user_id'])
    
    # Si no es propietario, redirigir al dashboard
    if not team_members:
        flash('Esta funcionalidad está disponible solo para propietarios de equipos.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    # Obtener invitaciones pendientes
    invitations = Team.get_pending_invitations(session['user_id'])
    
    # Sanitizar datos para prevenir XSS
    sanitized_invitations = []
    for invitation in invitations:
        sanitized_invitations.append({
            'invitation_id': invitation['invitation_id'],
            'email': sanitize_output(invitation['email']),
            'role': sanitize_output(invitation['role']),
            'created_at': invitation['created_at'],
            'expires_at': invitation['expires_at'],
            'token': invitation['token']
        })
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='team',
        action='view_invitations',
        details={'invitation_count': len(sanitized_invitations)},
        ip_address=request.remote_addr
    )
    
    return render_template('team_invitations.html', 
                          invitations=sanitized_invitations)

@team_bp.route('/invite_member', methods=['POST'])
@login_required
def invite_member():
    """
    Procesa la invitación de un nuevo miembro
    """
    # Verificar si el usuario es propietario de equipo
    team_members = Team.get_team_members(session['user_id'])
    
    # Si no es propietario, redirigir al dashboard
    if not team_members:
        flash('No tienes permisos para invitar miembros', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Obtener datos de la solicitud
    email = request.form.get('email')
    role = request.form.get('role', 'viewer')
    
    # Validar datos
    if not email:
        flash('El email es requerido', 'danger')
        return redirect(url_for('team.index'))
    
    # Validar rol
    valid_roles = ['admin', 'manager', 'editor', 'viewer']
    if role not in valid_roles:
        flash(f'Rol inválido. Debe ser uno de: {", ".join(valid_roles)}', 'danger')
        return redirect(url_for('team.index'))
    
    try:
        # Verificar si puede invitar más miembros
        can_invite = Team.can_invite_members(session['user_id'])
        if not can_invite:
            flash('Has alcanzado el límite de miembros para tu plan', 'warning')
            return redirect(url_for('team.index'))
        
        # Crear invitación
        invitation = Team.invite_member(session['user_id'], email, role)
        
        # Generar URL de invitación
        # CAMBIO: usamos 'auth.unirse' en lugar de 'auth.register'
        invite_url = url_for('auth.unirse_equipo', token=invitation['token'], _external=True)
        
        # Guardar en la sesión para mostrar en la página
        session['last_invite_url'] = invite_url
        session['last_invite_email'] = email
        
        # Registrar evento de seguridad
        log_security_event(
            user_id=session['user_id'],
            event_type='team_invitation_created',
            details={'invitation_id': invitation['invitation_id'], 'email': email, 'role': role},
            ip_address=request.remote_addr
        )
        
        flash(f'Se ha generado un enlace de invitación para {email}', 'success')
        return redirect(url_for('team.index'))
        
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('team.index'))
    except Exception as e:
        print(f"Error al enviar invitación: {str(e)}")
        flash('Error interno al procesar la invitación', 'danger')
        return redirect(url_for('team.index'))

@team_bp.route('/cancel_invitation', methods=['POST'])  # Quita "team/" del inicio de la ruta
@login_required
def cancel_invitation():
    """
    Cancela una invitación pendiente
    """
    # Verificar si el usuario es propietario de equipo
    team_members = Team.get_team_members(session['user_id'])
    
    # Si no es propietario, redirigir al dashboard
    if not team_members:
        flash('No tienes permisos para cancelar invitaciones', 'danger')
        return redirect(url_for('team.index'))
    
    # Obtener datos de la solicitud
    invitation_id = request.form.get('invitation_id')
    
    # Validar datos
    if not invitation_id:
        flash('ID de invitación requerido', 'danger')
        return redirect(url_for('team.index'))
    
    try:
        # Cancelar invitación
        Team.cancel_invitation(session['user_id'], invitation_id)
        
        # Registrar evento de seguridad
        log_security_event(
            user_id=session['user_id'],
            event_type='team_invitation_cancelled',
            details={'invitation_id': invitation_id},
            ip_address=request.remote_addr
        )
        
        flash('Invitación cancelada correctamente', 'success')
        return redirect(url_for('team.index'))
        
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('team.index'))
    except Exception as e:
        print(f"Error al cancelar invitación: {str(e)}")
        flash('Error interno al cancelar la invitación', 'danger')
        return redirect(url_for('team.index'))



@team_bp.route('/remove_member', methods=['POST'])
@login_required
def remove_member():
    """
    Elimina un miembro del equipo
    """
    # Verificar si el usuario es propietario de equipo
    team_members = Team.get_team_members(session['user_id'])
    
    # Si no es propietario, redirigir al dashboard
    if not team_members:
        return jsonify({
            'success': False,
            'message': 'No tienes permisos para eliminar miembros'
        }), 403
    
    # Obtener datos de la solicitud
    member_id = request.form.get('member_id')
    
    # Validar datos
    if not member_id:
        return jsonify({
            'success': False,
            'message': 'ID de miembro requerido'
        }), 400
    
    try:
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
        
        # Eliminar miembro del equipo
        Team.remove_member(session['user_id'], member_id)
        
        # Registrar evento de seguridad
        log_security_event(
            user_id=session['user_id'],
            event_type='team_member_removed',
            details={'member_id': member_id, 'email': target_member['email']},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': 'Miembro eliminado correctamente del equipo'
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f"Error al eliminar miembro: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno al eliminar al miembro'
        }), 500

@team_bp.route('/change_role', methods=['POST'])
@login_required
def change_role():
    """
    Cambia el rol de un miembro del equipo
    """
    # Verificar si el usuario es propietario de equipo
    team_members = Team.get_team_members(session['user_id'])
    
    # Si no es propietario, redirigir al dashboard
    if not team_members:
        return jsonify({
            'success': False,
            'message': 'No tienes permisos para cambiar roles'
        }), 403
    
    # Obtener datos de la solicitud
    member_id = request.form.get('member_id')
    new_role = request.form.get('role')
    
    # Validar datos
    if not member_id or not new_role:
        return jsonify({
            'success': False,
            'message': 'ID de miembro y rol son requeridos'
        }), 400
    
    # Validar rol
    valid_roles = ['admin', 'manager', 'editor', 'viewer']
    if new_role not in valid_roles:
        return jsonify({
            'success': False,
            'message': f'Rol inválido. Debe ser uno de: {", ".join(valid_roles)}'
        }), 400
    
    try:
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
        
        # Cambiar rol del miembro
        Team.change_member_role(session['user_id'], member_id, new_role)
        
        # Registrar evento de seguridad
        log_security_event(
            user_id=session['user_id'],
            event_type='team_member_role_changed',
            details={
                'member_id': member_id, 
                'email': target_member['email'],
                'old_role': target_member['role'],
                'new_role': new_role
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Rol cambiado correctamente a {new_role}'
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f"Error al cambiar rol: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno al cambiar el rol'
        }), 500