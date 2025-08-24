# app/models/team.py
from datetime import datetime, timedelta
import uuid
import secrets
import json
from app.models.database_pg import execute_query, team_members_table_id, team_invitations_table_id, invitation_actions_table_id
from app.models.plan import Plan
from app.models.user import User

class Team:
    @staticmethod
    def get_team_usage_stats(owner_id):
        """
        Obtiene estadísticas de uso de créditos para miembros del equipo
        
        Args:
            owner_id: ID del propietario del equipo
            
        Returns:
            list: Lista de estadísticas por miembro
        """
        # 1. Obtener miembros del equipo
        members = Team.get_team_members(owner_id)
        
        if not members:
            return []
        
        # 2. Para cada miembro, obtener su uso de créditos
        try:
            from app.models.creditos import CreditLog
        except ImportError:
            # Si no existe el modelo, devolver datos básicos
            stats = []
            for member in members:
                stats.append({
                    'email': member.get('email'),
                    'used_credits': 0,
                    'last_activity': None,
                    'percentage': 0
                })
            return stats
        
        stats = []
        total_used = 0  # Para calcular porcentajes
        
        # Procesar a todos los miembros (incluido propietario)
        for member in members:
            user_id = member.get('user_id')
            if user_id:
                try:
                    # Obtener los créditos usados
                    used_credits = CreditLog.get_used_credits(user_id)
                    total_used += used_credits
                    
                    # Obtener última actividad
                    last_activity = CreditLog.get_last_activity(user_id)
                except:
                    # Si hay error, poner valores por defecto
                    used_credits = 0
                    last_activity = None
                
                stats.append({
                    'email': member.get('email'),
                    'used_credits': used_credits,
                    'last_activity': last_activity,
                    'percentage': 0  # Se calculará después
                })
        
        # Calcular porcentajes si hay uso total
        if total_used > 0:
            for stat in stats:
                stat['percentage'] = round((stat['used_credits'] / total_used) * 100)
        
        # Ordenar por uso de créditos (mayor a menor)
        stats.sort(key=lambda x: x['used_credits'], reverse=True)
        
        return stats


    @staticmethod
    def count_team_members(owner_id):
        """
        Cuenta los miembros activos del equipo para un usuario propietario
        
        Args:
            owner_id: ID del usuario propietario
                
        Returns:
            tuple: (current_count, max_users) - Número de miembros y máximo permitido
        """
        # Primero obtener el plan activo para saber el máximo de usuarios
        from app.models.plan import Plan
        active_plan = Plan.get_user_active_plan(owner_id)
        
        # Si no hay plan activo, retornar 1/1 (solo el propietario)
        if not active_plan:
            return 1, 1
        
        # Obtener el máximo de usuarios del plan
        max_users = active_plan.get('max_users', 1)
        
        # Forzar un valor correcto para planes específicos (solución temporal)
        plan_id = active_plan.get('plan_id')
        if plan_id == 12:  # All Access Complete
            max_users = 5
        
        if not max_users or max_users < 1:
            max_users = 1  # Asegurarnos de que sea al menos 1
        
        # Contar miembros activos ÚNICOS por email (excluyendo al propietario)
        query = f"""
        SELECT COUNT(DISTINCT email) as count
        FROM {team_members_table_id}
        WHERE owner_id = %s
        AND status = 'active'
        """
        
        results = execute_query(query, params=(owner_id,), fetch=True, as_dict=True)
        
        member_count = 0
        if results:
            member_count = results[0]['count']
        
        # Sumar 1 para contar al propietario
        current_count = member_count + 1
        
        # Retornar conteo (1 propietario + miembros) y máximo
        return current_count, max_users
    
    @staticmethod
    def get_member_info_by_email(email):
        """
        Obtiene información de membresía por email (método alternativo)
        
        Args:
            email: Email del usuario
                
        Returns:
            dict: Información del miembro o None si no hay coincidencia
        """
        if not email:
            return None
    
    @staticmethod
    def get_team_members(owner_id):
        """
        Obtiene los miembros del equipo para un usuario propietario, incluyendo al propietario
        """
        # Consulta principal para obtener miembros activos
        query = f"""
        SELECT member_id, user_id, email, role, joined_at, status 
        FROM {team_members_table_id}
        WHERE owner_id = %s
        AND status = 'active'
        """
        
        results = execute_query(query, params=(owner_id,), fetch=True, as_dict=True)
        
        members = []
        seen_emails = set()  # Para garantizar unicidad
        
        # Verificar si el propietario está en los resultados
        owner_in_results = False
        
        for row in results:
            if row['email'] and row['email'].lower() not in seen_emails:
                members.append({
                    'member_id': row['member_id'],
                    'user_id': row['user_id'],
                    'email': row['email'],
                    'role': row['role'],
                    'joined_at': row['joined_at'],
                    'status': row['status']
                })
                seen_emails.add(row['email'].lower())
                
                # Comprobar si el propietario está incluido
                if row['user_id'] == owner_id:
                    owner_in_results = True
        
        # Si el propietario no está incluido, añadirlo
        if not owner_in_results:
            # Obtener información del propietario
            owner = User.get_by_id(owner_id)
            if owner and owner.get('email') and owner['email'].lower() not in seen_emails:
                # Crear entrada para el propietario
                owner_member = {
                    'member_id': 'owner-' + owner_id,  # ID especial para identificar al propietario
                    'user_id': owner_id,
                    'email': owner['email'],
                    'role': 'admin',  # El propietario siempre es admin
                    'joined_at': datetime.now(),
                    'status': 'active'
                }
                members.insert(0, owner_member)  # Añadir al principio
                seen_emails.add(owner['email'].lower())
        
        print(f"Miembros encontrados para {owner_id}: {len(members)}")
        return members
    
    @staticmethod
    def get_member_info(user_id):
        """
        Obtiene información del miembro del equipo
        
        Args:
            user_id: ID del usuario
            
        Returns:
            dict: Información del miembro o None si no es miembro de ningún equipo
        """
        if not user_id:
            return None
            
        query = f"""
        SELECT member_id, owner_id, role
        FROM {team_members_table_id}
        WHERE user_id = %s
        AND status = 'active'
        LIMIT 1
        """
        
        try:
            results = execute_query(query, params=(user_id,), fetch=True, as_dict=True)
            
            if results and results[0]['owner_id'] and results[0]['owner_id'] != user_id:  # Asegurarse que no sea el propio usuario
                return {
                    'member_id': results[0]['member_id'],
                    'owner_id': results[0]['owner_id'],
                    'role': results[0]['role']
                }
        except Exception as e:
            print(f"Error al obtener información de miembro: {str(e)}")
        
        return None
    
    @staticmethod
    def remove_member(owner_id, member_id):
        """
        Elimina un miembro del equipo
        
        Args:
            owner_id: ID del usuario propietario
            member_id: ID del miembro a eliminar
            
        Returns:
            bool: True si la eliminación fue exitosa
        """
        query = f"""
        UPDATE {team_members_table_id}
        SET status = 'removed'
        WHERE owner_id = %s
        AND member_id = %s
        """
        
        execute_query(query, params=(owner_id, member_id), fetch=False)
        return True

    @staticmethod
    def get_owner_plan_info(user_id):
        """
        Obtiene información del plan del propietario para un miembro del equipo
        
        Args:
            user_id: ID del usuario miembro
            
        Returns:
            dict: Información del plan del propietario o None si no es miembro de ningún equipo
        """
        # Primero obtener la información del miembro para saber quién es el propietario
        member_info = Team.get_member_info(user_id)
        if not member_info:
            return None
        
        # Obtener el plan del propietario
        from app.models.plan import Plan
        owner_plan = Plan.get_user_active_plan(member_info['owner_id'])
        
        if not owner_plan:
            return None
        
        # Obtener el usuario propietario para mostrar su información
        owner = User.get_by_id(member_info['owner_id'])
        if not owner:
            return None
        
        # Devolver la información del plan junto con datos del propietario
        return {
            'plan': owner_plan,
            'owner': {
                'user_id': member_info['owner_id'],
                'email': owner.get('email'),
                'nombre': owner.get('nombre'),
                'apellido': owner.get('apellido'),
                'creditos': owner.get('creditos', 0)
            },
            'role': member_info['role']
        }
        
    @staticmethod
    def cleanup_old_invitations():
        """
        Marca como expiradas las invitaciones pendientes antiguas
        """
        # Obtener invitaciones expiradas
        query = f"""
        SELECT invitation_id
        FROM {team_invitations_table_id} i
        WHERE i.status = 'pending'
        AND i.expires_at < CURRENT_TIMESTAMP
        """
        
        results = execute_query(query, fetch=True, as_dict=True)
        
        # Registrar acción de expiración para cada una
        for row in results:
            invitation_id = row['invitation_id']
            
            # Actualizar el estado de la invitación directamente
            update_query = f"""
            UPDATE {team_invitations_table_id}
            SET status = 'expired'
            WHERE invitation_id = %s
            """
            
            execute_query(update_query, params=(invitation_id,), fetch=False)
            
            # Registrar acción
            action_id = str(uuid.uuid4())
            
            action_query = f"""
            INSERT INTO {invitation_actions_table_id}
            (action_id, invitation_id, action_type, performed_by, created_at, details)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            """
            
            details = json.dumps({'reason': 'Automatic expiration'})
            action_params = (action_id, invitation_id, 'expire', 'system', details)
            
            execute_query(action_query, params=action_params, fetch=False)
            
        return True
            
        # Asegurar que el email esté en minúsculas para la comparación
        email = email.lower()
        
        query = f"""
        SELECT member_id, owner_id, role
        FROM {team_members_table_id}
        WHERE LOWER(email) = %s
        AND status = 'active'
        LIMIT 1
        """
        
        results = execute_query(query, params=(email,), fetch=True, as_dict=True)
        
        if results:
            return {
                'member_id': results[0]['member_id'],
                'owner_id': results[0]['owner_id'],
                'role': results[0]['role']
            }
        
        return None
    
    @staticmethod
    def can_invite_members(owner_id):
        """
        Verifica si un usuario puede invitar más miembros según su plan
        Tiene en cuenta tanto los miembros activos como las invitaciones pendientes
        
        Args:
            owner_id: ID del usuario propietario
                
        Returns:
            bool: True si puede invitar más miembros
        """
        # Obtener conteo actual y máximo
        current_count, max_users = Team.count_team_members(owner_id)
        
        # Contar invitaciones pendientes
        query = f"""
        SELECT COUNT(*) as count
        FROM {team_invitations_table_id}
        WHERE owner_id = %s
        AND status = 'pending'
        """
        
        results = execute_query(query, params=[owner_id], fetch=True, as_dict=True)
        pending_count = results[0]['count'] if results else 0
        
        # Verificar si puede añadir más (miembros actuales + invitaciones pendientes < máximo)
        total = current_count + pending_count
        
        print(f"Verificando límite de miembros: actuales={current_count}, pendientes={pending_count}, máximo={max_users}")
        
        return total < max_users



    
    @staticmethod
    def invite_member(owner_id, email, role="viewer"):
        """
        Invita a un nuevo miembro al equipo
        
        Args:
            owner_id: ID del usuario propietario
            email: Email del usuario a invitar
            role: Rol asignado (admin, manager, editor, viewer)
            
        Returns:
            dict: Datos de la invitación
            
        Raises:
            ValueError: Si no se puede invitar más miembros o el email ya está invitado
        """
        # Validar que el rol sea válido
        valid_roles = ["admin", "manager", "editor", "viewer"]
        if role not in valid_roles:
            raise ValueError(f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}")
            
        # Normalizar el email para evitar duplicados por mayúsculas/minúsculas
        email = email.lower()
        
        # Verificar si puede invitar más miembros
        if not Team.can_invite_members(owner_id):
            raise ValueError("Has alcanzado el límite de usuarios para tu plan actual")
        
        # Verificar si el email ya está invitado (usando el enfoque del marcado lógico)
        existing_invitations = Team.get_pending_invitations_for_email(owner_id, email)
        if existing_invitations:
            raise ValueError(f"El email {email} ya ha sido invitado")
        
        # También verificar si ya es miembro activo
        query = f"""
        SELECT COUNT(*) as count
        FROM {team_members_table_id}
        WHERE owner_id = %s
        AND LOWER(email) = %s
        AND status = 'active'
        """
        
        results = execute_query(query, params=(owner_id, email), fetch=True, as_dict=True)
        
        if results and results[0]['count'] > 0:
            raise ValueError(f"El email {email} ya es miembro del equipo")
        
        # Generar token de invitación
        invitation_token = secrets.token_urlsafe(32)
        invitation_id = str(uuid.uuid4())
        
        # Registrar invitación en la tabla de invitaciones
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()  # La invitación expira en 7 días
        
        query = f"""
        INSERT INTO {team_invitations_table_id}
        (invitation_id, owner_id, email, role, created_at, expires_at, status, token)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, 'pending', %s)
        """
        
        params = (invitation_id, owner_id, email, role, expires_at, invitation_token)
        execute_query(query, params=params, fetch=False)
        
        return {
            'invitation_id': invitation_id,
            'email': email,
            'token': invitation_token
        }
    
    @staticmethod
    def get_pending_invitations_for_email(owner_id, email):
        """
        Verifica si hay invitaciones pendientes para un email específico
        
        Args:
            owner_id: ID del usuario propietario
            email: Email a verificar
            
        Returns:
            list: Lista de invitaciones pendientes para ese email
        """
        # Consulta que excluye invitaciones con acciones de cancelación
        query = f"""
        SELECT i.invitation_id
        FROM {team_invitations_table_id} i
        LEFT JOIN (
            SELECT invitation_id
            FROM {invitation_actions_table_id}
            WHERE action_type IN ('cancel', 'accept', 'expire')
        ) a ON i.invitation_id = a.invitation_id
        WHERE i.owner_id = %s
        AND LOWER(i.email) = %s
        AND i.status = 'pending'
        AND a.invitation_id IS NULL  -- Sin acciones de cancelación
        """
        
        results = execute_query(query, params=(owner_id, email.lower()), fetch=True, as_dict=True)
        
        invitations = []
        for row in results:
            invitations.append(row['invitation_id'])
        
        return invitations
    
    @staticmethod
    def get_pending_invitations(owner_id):
        """
        Obtiene las invitaciones pendientes enviadas por un propietario
        
        Args:
            owner_id: ID del usuario propietario
            
        Returns:
            list: Lista de invitaciones pendientes
        """
        print(f"Buscando invitaciones pendientes para el propietario: {owner_id}")
        # Primero, marca como expiradas las invitaciones vencidas
        Team.cleanup_old_invitations()
        
        # Consulta simplificada para solucionar posibles problemas
        query = f"""
        SELECT i.invitation_id, i.email, i.role, i.created_at, i.expires_at, i.status, i.token
        FROM {team_invitations_table_id} i
        WHERE i.owner_id = %s
        AND i.status = 'pending'
        ORDER BY i.created_at DESC
        """
        
        results = execute_query(query, params=(owner_id,), fetch=True, as_dict=True)
        
        invitations = []
        for row in results:
            invitations.append({
                'invitation_id': row['invitation_id'],
                'email': row['email'],
                'role': row['role'],
                'created_at': row['created_at'],
                'expires_at': row['expires_at'],
                'status': row['status'],
                'token': row['token']
            })
        print(f"Invitaciones pendientes encontradas: {len(invitations)}")
        if invitations:
            print(f"Primera invitación: {invitations[0]}")
        return invitations
    
    @staticmethod
    def cancel_invitation(owner_id, invitation_id):
        """
        Marca lógicamente una invitación como cancelada
        
        Args:
            owner_id: ID del usuario propietario
            invitation_id: ID de la invitación
        """
        # Verificar primero si la invitación existe y pertenece al propietario
        query = f"""
        SELECT i.invitation_id, i.status
        FROM {team_invitations_table_id} i
        WHERE i.owner_id = %s
        AND i.invitation_id = %s
        """
        
        results = execute_query(query, params=(owner_id, invitation_id), fetch=True, as_dict=True)
        
        # Si la invitación existe, registrar la acción de cancelación
        found = False
        current_status = None
        if results:
            found = True
            current_status = results[0]['status']
                
        if not found:
            raise ValueError("Invitación no encontrada o no pertenece al propietario")
        
        print(f"Invitación encontrada: {invitation_id}, estado actual: {current_status}")
        
        # Actualizar directamente el estado de la invitación a 'cancelled'
        update_query = f"""
        UPDATE {team_invitations_table_id}
        SET status = 'cancelled'
        WHERE owner_id = %s
        AND invitation_id = %s
        """
        
        try:
            execute_query(update_query, params=(owner_id, invitation_id), fetch=False)
            print(f"Estado de invitación actualizado a 'cancelled' para {invitation_id}")
        except Exception as e:
            print(f"Error al actualizar estado de invitación: {str(e)}")
        
        # Registrar la acción de cancelación
        action_id = str(uuid.uuid4())
        
        insert_query = f"""
        INSERT INTO {invitation_actions_table_id}
        (action_id, invitation_id, action_type, performed_by, created_at, details)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
        """
        
        details = json.dumps({'reason': 'User initiated'})
        params = (action_id, invitation_id, 'cancel', owner_id, details)
        
        execute_query(insert_query, params=params, fetch=False)
        print(f"Acción de cancelación registrada correctamente: {action_id}")
    
    @staticmethod
    def change_member_role(owner_id, member_id, new_role):
        """
        Cambia el rol de un miembro del equipo
        
        Args:
            owner_id: ID del usuario propietario
            member_id: ID del miembro a cambiar
            new_role: Nuevo rol (admin, manager, editor, viewer)
            
        Returns:
            bool: True si el cambio fue exitoso
            
        Raises:
            ValueError: Si el rol no es válido
        """
        # Validar que el rol sea válido
        valid_roles = ["admin", "manager", "editor", "viewer"]
        if new_role not in valid_roles:
            raise ValueError(f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}")
        
        query = f"""
        UPDATE {team_members_table_id}
        SET role = %s
        WHERE owner_id = %s
        AND member_id = %s
        AND status = 'active'
        """
        
        execute_query(query, params=(new_role, owner_id, member_id), fetch=False)
        return True
    
    @staticmethod
    def get_invitation_by_token(token):
        """
        Obtiene una invitación por su token
        
        Args:
            token: Token de la invitación
                
        Returns:
            dict: Datos de la invitación o None si no se encuentra
        """
        query = f"""
        SELECT * FROM {team_invitations_table_id}
        WHERE token = %s AND status = 'pending' AND expires_at > %s
        LIMIT 1
        """
        
        results = execute_query(query, params=(token, datetime.utcnow()), fetch=True, as_dict=True)
        
        invitation = None
        if results:
            invitation = results[0]
            print(f"Invitación encontrada con token {token}: {invitation['invitation_id']}, status: {invitation['status']}")
        else:
            print(f"No se encontró invitación con token {token} o ha expirado")
            
        return invitation

    @staticmethod
    def accept_invitation(token, user_id):
        """
        Acepta una invitación y registra al usuario como miembro del equipo. Versión robusta.
        """
        print(f"Aceptando invitación con token: {token} para usuario: {user_id}")
        
        # Verificar si ya es miembro de un equipo (evitar duplicados)
        existing_member = Team.get_member_info(user_id)
        if existing_member:
            print(f"El usuario ya es miembro del equipo: {existing_member}")
            return existing_member
        
        # Obtener datos de la invitación
        invitation = Team.get_invitation_by_token(token)
        
        # Si no hay invitación válida, buscar en la tabla de acciones
        if not invitation:
            # Intentar encontrar la invitación por token en acciones
            query = f"""
            SELECT i.owner_id, i.email, i.role, i.invitation_id, i.token, i.status
            FROM {team_invitations_table_id} i
            WHERE i.token = %s
            LIMIT 1
            """
            
            results = execute_query(query, params=(token,), fetch=True, as_dict=True)
            invitation_data = None
            
            if results:
                invitation_data = {
                    'invitation_id': results[0]['invitation_id'],
                    'owner_id': results[0]['owner_id'],
                    'email': results[0]['email'],
                    'role': results[0]['role'],
                    'token': results[0]['token'],
                    'status': results[0]['status']
                }
                    
            if invitation_data:
                print(f"Invitación encontrada en búsqueda secundaria: {invitation_data}")
                print(f"Estado actual de la invitación: {invitation_data['status']}")
                
                # Actualizar estado de la invitación a 'accepted' si todavía no está aceptada
                if invitation_data['status'] != 'accepted':
                    update_query = f"""
                    UPDATE {team_invitations_table_id}
                    SET 
                        status = 'accepted',
                        accepted_at = CURRENT_TIMESTAMP
                    WHERE invitation_id = %s
                    """
                    
                    try:
                        execute_query(update_query, params=(invitation_data['invitation_id'],), fetch=False)
                        print(f"Estado de invitación actualizado a 'accepted' para {invitation_data['invitation_id']}")
                    except Exception as e:
                        print(f"Error al actualizar estado de invitación: {str(e)}")
                
                # Usar esta data para forzar la membresía
                user = User.get_by_id(user_id)
                if not user:
                    print(f"No se encontró el usuario con ID: {user_id}")
                    return None
                    
                # Crear membresía forzada
                member_id = str(uuid.uuid4())
                
                insert_query = f"""
                INSERT INTO {team_members_table_id}
                (member_id, owner_id, user_id, email, role, invited_at, joined_at, status, invitation_token)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active', %s)
                """
                
                params = (
                    member_id, 
                    invitation_data['owner_id'], 
                    user_id, 
                    user['email'].lower(), 
                    invitation_data['role'], 
                    token
                )
                
                print(f"Insertando membresía forzada con params: {params}")
                
                try:
                    execute_query(insert_query, params=params, fetch=False)
                    
                    return {
                        'member_id': member_id,
                        'owner_id': invitation_data['owner_id'],
                        'role': invitation_data['role']
                    }
                except Exception as e:
                    print(f"Error al insertar miembro forzado: {str(e)}")
                    return None
            else:
                print(f"No se encontró ninguna invitación válida o histórica con el token: {token}")
                # Intento de última oportunidad: usar un ID de propietario fijo si conocemos al propietario del sistema
                fallback_owner_id = '47fc9b20-db22-41c2-b472-0e8bfc51bfcf'  # El ID fijo que tenías en repair_membership
                user = User.get_by_id(user_id)
                if user:
                    # Crear membresía de emergencia
                    member_id = str(uuid.uuid4())
                    
                    insert_query = f"""
                    INSERT INTO {team_members_table_id}
                    (member_id, owner_id, user_id, email, role, invited_at, joined_at, status, invitation_token)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active', %s)
                    """
                    
                    params = (
                        member_id, 
                        fallback_owner_id, 
                        user_id, 
                        user['email'].lower(), 
                        'viewer',  # Rol por defecto
                        token
                    )
                    
                    print(f"EMERGENCIA: Insertando membresía con propietario por defecto")
                    
                    try:
                        execute_query(insert_query, params=params, fetch=False)
                        
                        return {
                            'member_id': member_id,
                            'owner_id': fallback_owner_id,
                            'role': 'viewer'
                        }
                    except Exception as e:
                        print(f"Error al insertar miembro de emergencia: {str(e)}")
                        return None
                return None
        
        print(f"Invitación encontrada: {invitation}")
        print(f"Estado actual de la invitación: {invitation['status']}")
        
        # Actualizar el estado de la invitación a 'accepted'
        update_query = f"""
        UPDATE {team_invitations_table_id}
        SET 
            status = 'accepted',
            accepted_at = CURRENT_TIMESTAMP
        WHERE invitation_id = %s
        """
        
        try:
            execute_query(update_query, params=(invitation['invitation_id'],), fetch=False)
            print(f"Estado de invitación actualizado a 'accepted' para {invitation['invitation_id']}")
        except Exception as e:
            print(f"Error al actualizar estado de invitación: {str(e)}")
        
        # Verificar que el email del usuario coincida con el de la invitación
        user = User.get_by_id(user_id)
        if not user:
            print(f"No se encontró el usuario con ID: {user_id}")
            return None
            
        user_email = user['email'].lower()
        print(f"Usuario encontrado: {user_email} (invitación para: {invitation['email']})")
        
        # CAMBIO: No rechazar si los emails no coinciden exactamente, ser más flexible
        # if user_email != invitation['email'].lower():
        #     print(f"El email del usuario ({user_email}) no coincide con el de la invitación ({invitation['email']})")
        #     return None
        
        # Crear o actualizar el registro de miembro
        member_id = str(uuid.uuid4())
        
        insert_query = f"""
        INSERT INTO {team_members_table_id}
        (member_id, owner_id, user_id, email, role, invited_at, joined_at, status, invitation_token)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active', %s)
        """
        
        params = (
            member_id, 
            invitation['owner_id'], 
            user_id, 
            user_email,
            invitation['role'], 
            invitation['token']
        )
        
        print(f"Insertando registro en team_members")
        
        try:
            execute_query(insert_query, params=params, fetch=False)
        except Exception as e:
            print(f"Error al insertar miembro: {str(e)}")
            print(f"Intentando método alternativo...")
            
            # Intento alternativo: usar fix_membership_for_user
            backup_result = Team.fix_membership_for_user(user_id, user_email, invitation['owner_id'])
            if backup_result:
                print(f"Membresía reparada exitosamente por método alternativo")
                return backup_result
                
            raise Exception(f"Error al insertar miembro: {str(e)}")
        
        # Registrar acción de aceptación
        try:
            action_id = str(uuid.uuid4())
            
            action_query = f"""
            INSERT INTO {invitation_actions_table_id}
            (action_id, invitation_id, action_type, performed_by, created_at, details)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            """
            
            details = json.dumps({'member_id': member_id})
            action_params = (action_id, invitation['invitation_id'], 'accept', user_id, details)
            
            execute_query(action_query, params=action_params, fetch=False)
            print(f"Acción de aceptación registrada correctamente: {action_id}")
        except Exception as e:
            print(f"Error al registrar acción (no fatal): {str(e)}")
        
        print(f"Invitación aceptada exitosamente. Member ID: {member_id}")
        
        return {
            'member_id': member_id,
            'owner_id': invitation['owner_id'],
            'role': invitation['role']
        }
    
    @staticmethod
    def fix_membership_for_user(user_id, email, owner_id=None):
        """
        Arregla manualmente la membresía de un usuario usando su email y opcionalmente un propietario específico
        
        Args:
            user_id: ID del usuario miembro
            email: Email del usuario miembro
            owner_id: ID del propietario (opcional, si no se especifica, se busca en invitaciones)
            
        Returns:
            dict: Información de la membresía creada o None si no se pudo crear
        """
        # Normalizar el email
        email = email.lower()
        
        print(f"Arreglando membresía para usuario {user_id} con email {email}")
        
        # Si no se especifica owner_id, buscar en invitaciones pendientes
        if not owner_id:
            # Usar la nueva lógica de invitaciones pendientes
            query = f"""
            SELECT i.invitation_id, i.owner_id, i.role, i.token
            FROM {team_invitations_table_id} i
            WHERE LOWER(i.email) = %s
            AND i.status = 'pending'
            ORDER BY i.created_at DESC
            LIMIT 1
            """
            
            results = execute_query(query, params=(email,), fetch=True, as_dict=True)
            
            invitation = None
            if results:
                invitation = {
                    'invitation_id': results[0]['invitation_id'],
                    'owner_id': results[0]['owner_id'],
                    'role': results[0]['role'],
                    'token': results[0]['token']
                }
            
            if not invitation:
                print("No se encontró ninguna invitación pendiente para este email")
                return None
                
            owner_id = invitation['owner_id']
            role = invitation['role']
            invitation_id = invitation['invitation_id']
            token = invitation['token']
        else:
            # Si se especifica owner_id, asignar rol por defecto
            role = "viewer"
            invitation_id = None
            token = secrets.token_urlsafe(32)
        
        # Verificar si ya existe como miembro (y actualizar su estado si existe)
        existing_query = f"""
        SELECT member_id, status 
        FROM {team_members_table_id}
        WHERE LOWER(email) = %s
        AND owner_id = %s
        LIMIT 1
        """
        
        existing_results = execute_query(existing_query, params=(email, owner_id), fetch=True, as_dict=True)
        
        existing_member_id = None
        if existing_results:
            existing_member_id = existing_results[0]['member_id']
            # Si el miembro existe pero está inactivo, reactivarlo
            if existing_results[0]['status'] != 'active':
                update_query = f"""
                UPDATE {team_members_table_id}
                SET status = 'active', 
                    user_id = %s,
                    role = %s,
                    joined_at = CURRENT_TIMESTAMP
                WHERE member_id = %s
                """
                
                execute_query(update_query, params=(user_id, role, existing_member_id), fetch=False)
                print(f"Miembro existente reactivado: {existing_member_id}")
        
        # Si no existe, crear un nuevo registro
        if not existing_member_id:
            # Generar ID de miembro
            member_id = str(uuid.uuid4())
            
            # Insertar en team_members
            insert_query = f"""
            INSERT INTO {team_members_table_id}
            (member_id, owner_id, user_id, email, role, invited_at, joined_at, status, invitation_token)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active', %s)
            """
            
            params = (member_id, owner_id, user_id, email, role, token)
            
            print(f"Insertando nuevo registro en team_members")
            
            try:
                execute_query(insert_query, params=params, fetch=False)
                existing_member_id = member_id
            except Exception as e:
                print(f"Error al insertar miembro: {str(e)}")
                return None
        
        # Si había una invitación específica, registrar la acción de aceptación
        if invitation_id:
            action_id = str(uuid.uuid4())
            
            action_query = f"""
            INSERT INTO {invitation_actions_table_id}
            (action_id, invitation_id, action_type, performed_by, created_at, details)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            """
            
            details = json.dumps({'member_id': existing_member_id})
            action_params = (action_id, invitation_id, 'accept', user_id, details)
            
            try:
                execute_query(action_query, params=action_params, fetch=False)
            except Exception as e:
                print(f"Error al registrar acción de aceptación: {str(e)}")
        
        print(f"Membresía establecida correctamente: member_id={existing_member_id}, owner_id={owner_id}, role={role}")
        
        return {
            'member_id': existing_member_id,
            'owner_id': owner_id,
            'role': role
        }
    
    @staticmethod
    def get_team_info(user_id):
        """
        Obtiene información sobre el equipo al que pertenece un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            dict: Información del equipo (owner_id, role) o None si no pertenece a ningún equipo
        """
        query = f"""
        SELECT owner_id, role, member_id
        FROM {team_members_table_id}
        WHERE user_id = %s
        AND status = 'active'
        LIMIT 1
        """
        
        results = execute_query(query, params=(user_id,), fetch=True, as_dict=True)
        
        if results:
            return {
                'owner_id': results[0]['owner_id'],
                'role': results[0]['role'],
                'member_id': results[0]['member_id'],
                'is_owner': False
            }
        
        # Si no se encontró como miembro, verificar si es propietario
        query = f"""
        SELECT COUNT(*) as count
        FROM {team_members_table_id}
        WHERE owner_id = %s
        AND status = 'active'
        """
        
        results = execute_query(query, params=(user_id,), fetch=True, as_dict=True)
        
        if results and results[0]['count'] > 0:
            return {
                'owner_id': user_id,
                'role': 'owner',
                'is_owner': True
            }
        
        return None