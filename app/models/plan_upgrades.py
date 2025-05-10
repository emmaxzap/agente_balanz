from datetime import datetime, timedelta
import uuid
import json
from app.models.database_pg import execute_query, user_subscriptions_table_id, plan_changes_table_id
from app.models.plan import Plan


class PlanUpgrade:
    """
    Clase para gestionar la actualización de planes
    """
    
    @staticmethod
    def calculate_prorated_value(current_subscription):
        """
        Calcula el valor prorrateado del plan actual
        
        Args:
            current_subscription: Suscripción actual del usuario
            
        Returns:
            dict: Datos del prorrateo
        """
        # Obtener detalles del plan actual
        current_plan = Plan.get_plan_by_id(current_subscription['plan_id'])
        if not current_plan:
            return {
                'days_remaining': 0,
                'total_days': 0,
                'value_per_day': 0,
                'prorated_value': 0
            }
        
        # Fecha actual
        now = datetime.now()
        
        # Fecha de fin de la suscripción
        end_date = current_subscription['end_date']
        
        # Asegurarnos de que end_date es un objeto datetime
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Eliminar información de zona horaria si existe
        if hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        
        # Tiempo restante
        time_remaining = end_date - now
        days_remaining = max(0, time_remaining.days)  # Evitar valores negativos
        
        # Duración total del plan en días (considerando que period_months está en meses)
        total_days = current_plan['period_months'] * 30  # Aproximación de días por mes
        
        # Valor por día
        total_price = current_plan['price_amount']
        value_per_day = total_price / total_days if total_days > 0 else 0
        
        # Valor prorrateado
        prorated_value = value_per_day * days_remaining
        
        return {
            'days_remaining': days_remaining,
            'total_days': total_days,
            'value_per_day': value_per_day,
            'prorated_value': prorated_value
        }
    
    @staticmethod
    def calculate_upgrade_cost(current_subscription, new_plan_id):
        """
        Calcula el costo de actualización a un nuevo plan, ajustando los créditos
        
        Args:
            current_subscription: Suscripción actual del usuario
            new_plan_id: ID del nuevo plan
            
        Returns:
            dict: Datos del costo de actualización incluyendo ajuste de créditos
        """
        from app.models.user import User
        
        # Obtener detalles del nuevo plan
        new_plan = Plan.get_plan_by_id(new_plan_id)
        if not new_plan:
            return None
        
        # Obtener valor prorrateado de la suscripción actual
        prorated_data = PlanUpgrade.calculate_prorated_value(current_subscription)
        
        # Obtener créditos actuales y consumidos del usuario
        user_id = current_subscription.get('user_id')
        user = User.get_by_id(user_id)
        current_credits = user.get('creditos', 0)
        
        # Créditos iniciales del plan actual
        initial_credits = current_subscription.get('credit_amount', 0)
        
        # Créditos consumidos = iniciales - actuales
        consumed_credits = max(0, initial_credits - current_credits)
        
        # Créditos del nuevo plan
        new_plan_credits = new_plan.get('credit_amount', 0)
        
        # Ajuste de créditos para el nuevo plan
        # Si ya consumió créditos, se le deben restar al nuevo plan
        adjusted_new_credits = max(0, new_plan_credits - consumed_credits)
        
        # Costo final (precio del nuevo plan menos el valor prorrateado)
        upgrade_cost = max(0, new_plan.get('price_amount', 0) - prorated_data.get('prorated_value', 0))
        
        # Información completa
        return {
            'current_plan_id': current_subscription.get('plan_id'),
            'current_plan_name': current_subscription.get('plan_name', 'Plan Actual'),
            'new_plan_id': new_plan_id,
            'new_plan_name': new_plan.get('plan_name', 'Nuevo Plan'),
            'prorated_discount': prorated_data.get('prorated_value', 0),
            'days_remaining': prorated_data.get('days_remaining', 0),
            'upgrade_cost': upgrade_cost,
            'current_credits': current_credits,
            'consumed_credits': consumed_credits,
            'new_plan_credits': new_plan_credits,
            'adjusted_new_credits': adjusted_new_credits  # Este es el valor importante
        }
    
    @staticmethod
    def get_available_upgrades(user_id):
        """
        Obtiene los planes disponibles para actualización
        
        Args:
            user_id: ID del usuario
            
        Returns:
            list: Lista de planes disponibles para actualización con costos
        """
        # Obtener plan actual del usuario
        current_subscription = Plan.get_user_active_plan(user_id)
        if not current_subscription:
            print("DEBUG: No hay suscripción actual para el usuario")
            return []
        
        # Logs para depuración
        print(f"DEBUG: Plan actual encontrado - ID: {current_subscription.get('plan_id')}, Level ID: {current_subscription.get('subscription_level_id')}")
        
        # Verificar si subscription_level_id existe en la suscripción
        if 'subscription_level_id' not in current_subscription:
            print("ADVERTENCIA: El plan actual no tiene 'subscription_level_id', asignando valor por defecto 1")
            current_subscription['subscription_level_id'] = 1
        
        # Obtener todos los planes disponibles
        all_plans = Plan.get_available_plans()
        print(f"DEBUG: Total de planes disponibles: {len(all_plans)}")
        
        # Filtrar planes que son de actualización (mayor nivel o mismo nivel pero distinto plan)
        available_upgrades = []
        for plan in all_plans:
            # Depuración para cada plan
            print(f"DEBUG: Evaluando plan {plan.get('plan_id')}, nivel: {plan.get('subscription_level_id', 0)}")
            
            # Asegurarnos de que las claves existan antes de comparar
            current_level_id = current_subscription.get('subscription_level_id', 0)
            plan_level_id = plan.get('subscription_level_id', 0)
            
            print(f"DEBUG: Comparando - actual: {current_level_id}, plan: {plan_level_id}, plan_id actual: {current_subscription.get('plan_id')}, plan_id evaluado: {plan.get('plan_id')}")
            
            # Si el plan es el mismo que el actual, lo saltamos
            if plan.get('plan_id') == current_subscription.get('plan_id'):
                print(f"DEBUG: Plan {plan.get('plan_id')} es el plan actual, saltando")
                continue
            
            # Si el nivel es mayor, es una actualización válida
            if plan_level_id > current_level_id:
                print(f"DEBUG: Plan {plan.get('plan_id')} es una actualización posible (nivel superior)")
                upgrade_info = PlanUpgrade.calculate_upgrade_cost(current_subscription, plan.get('plan_id'))
                if upgrade_info:
                    available_upgrades.append({
                        **plan,
                        'upgrade_info': upgrade_info
                    })
                    print(f"DEBUG: Plan {plan.get('plan_id')} añadido a la lista de actualizaciones")
                else:
                    print(f"DEBUG: No se pudo calcular costo de actualización para plan {plan.get('plan_id')}")
            # Si es del mismo nivel pero diferente plan/categoría, también es válido
            elif plan_level_id == current_level_id and plan.get('category_id') != current_subscription.get('category_id', 0):
                print(f"DEBUG: Plan {plan.get('plan_id')} es una actualización posible (mismo nivel, diferente categoría)")
                upgrade_info = PlanUpgrade.calculate_upgrade_cost(current_subscription, plan.get('plan_id'))
                if upgrade_info:
                    available_upgrades.append({
                        **plan,
                        'upgrade_info': upgrade_info
                    })
                    print(f"DEBUG: Plan {plan.get('plan_id')} añadido a la lista de actualizaciones")
                else:
                    print(f"DEBUG: No se pudo calcular costo de actualización para plan {plan.get('plan_id')}")
            else:
                print(f"DEBUG: Plan {plan.get('plan_id')} NO es actualización porque level_id actual: {current_level_id}, level_id plan: {plan_level_id}")
        
        # Logs finales
        print(f"DEBUG: Total de planes para actualización encontrados: {len(available_upgrades)}")
        
        # Ordenar por nivel y luego por otros criterios
        available_upgrades.sort(key=lambda x: (x.get('subscription_level_id', 0), x.get('plan_id', 0)))
        
        return available_upgrades
    
    @staticmethod
    def register_plan_change(user_id, current_subscription, new_plan_id, transaction_id, additional_details=None):
        """
        Registra el cambio de plan y ajusta los créditos
        
        Args:
            user_id: ID del usuario
            current_subscription: Suscripción actual
            new_plan_id: ID del nuevo plan
            transaction_id: ID de la transacción
            additional_details: Detalles adicionales
                
        Returns:
            dict: Datos de la nueva suscripción
        """
        from app.models.user import User
        from app.models.database_pg import execute_query, user_subscriptions_table_id, transacciones_table_id
        import uuid
        from datetime import datetime, timedelta
        
        # Obtener cálculo de costo y créditos ajustados
        upgrade_info = PlanUpgrade.calculate_upgrade_cost(current_subscription, new_plan_id)
        if not upgrade_info:
            raise ValueError("No se pudo calcular información del upgrade")
        
        # Desactivar plan anterior
        Plan.deactivate_subscription(current_subscription.get('subscription_id'))
        
        # Crear nueva suscripción
        subscription_id = str(uuid.uuid4())
        new_plan = Plan.get_plan_by_id(new_plan_id)
        
        # Calcular fecha de fin basado en period_months del nuevo plan
        start_date = datetime.now()
        period_months = new_plan.get('period_months', 1)
        end_date = start_date + timedelta(days=30 * period_months)
        
        # Datos para la nueva suscripción
        payment_details = json.dumps({
            'upgrade_from': current_subscription.get('plan_id'),
            'prorated_discount': upgrade_info.get('prorated_discount', 0),
            'adjusted_credits': upgrade_info.get('adjusted_new_credits', 0),
            **(additional_details or {})
        })
        
        # Insertar nueva suscripción
        insert_query = f"""
        INSERT INTO {user_subscriptions_table_id}
        (subscription_id, user_id, plan_id, start_date, end_date, is_active, payment_status, transaction_id, payment_details)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        insert_params = (
            subscription_id,
            user_id,
            new_plan_id,
            start_date.isoformat(),
            end_date.isoformat(),
            True,
            'completed',
            transaction_id,
            payment_details
        )
        
        execute_query(insert_query, params=insert_params, fetch=False)
        
        # Actualizar créditos del usuario
        adjusted_credits = upgrade_info.get('adjusted_new_credits', 0)
        print(f"Actualizando créditos del usuario a: {adjusted_credits} (reset=True)")
        User.update_credits(user_id, adjusted_credits, reset=True)  # reset=True para establecer, no sumar
        print(f"Créditos actualizados correctamente a {adjusted_credits}")
        
        # Registrar el cambio de plan en la tabla plan_changes
        PlanUpgrade.register_plan_change_history(
            user_id,
            current_subscription.get('plan_id'),
            new_plan_id,
            transaction_id,
            current_subscription.get('subscription_id'),
            subscription_id,
            upgrade_info.get('prorated_discount', 0),
            adjusted_credits
        )
        
        return {
            'subscription_id': subscription_id,
            'plan_id': new_plan_id,
            'adjusted_credits': adjusted_credits
        }



    @staticmethod
    def register_plan_change_history(user_id, old_plan_id, new_plan_id, transaction_id, 
                                   old_subscription_id, new_subscription_id, prorated_amount, credits_transferred):
        """
        Registra el cambio de plan en la tabla plan_changes
        
        Args:
            user_id: ID del usuario
            old_plan_id: ID del plan anterior
            new_plan_id: ID del nuevo plan
            transaction_id: ID de la transacción
            old_subscription_id: ID de la suscripción anterior
            new_subscription_id: ID de la nueva suscripción
            prorated_amount: Monto prorrateado
            credits_transferred: Créditos transferidos
        """
        change_id = str(uuid.uuid4())
        
        insert_query = f"""
        INSERT INTO {plan_changes_table_id}
        (change_id, user_id, old_plan_id, new_plan_id, transaction_id, old_subscription_id, 
         new_subscription_id, prorated_amount, credits_transferred, change_date, status, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
        """
        
        details = json.dumps({
            'source': 'user_upgrade',
            'timestamp': datetime.now().isoformat()
        })
        
        insert_params = (
            change_id,
            user_id,
            old_plan_id,
            new_plan_id,
            transaction_id,
            old_subscription_id,
            new_subscription_id,
            prorated_amount,
            credits_transferred,
            'completed',
            details
        )
        
        try:
            execute_query(insert_query, params=insert_params, fetch=False)
            return True
        except Exception as e:
            print(f"Error al registrar historial de cambio de plan: {str(e)}")
            return False
    
    @staticmethod
    def create_plan_changes_table_if_not_exists():
        """
        Crea la tabla plan_changes si no existe
        """
        # En PostgreSQL esta función tendría que ser reescrita para usar CREATE TABLE IF NOT EXISTS
        # Esta implementación depende de una migración adecuada de las tablas en PostgreSQL
        
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {plan_changes_table_id} (
            change_id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            old_plan_id INTEGER NOT NULL,
            new_plan_id INTEGER NOT NULL,
            transaction_id VARCHAR(255) NOT NULL,
            old_subscription_id VARCHAR(36) NOT NULL,
            new_subscription_id VARCHAR(36) NOT NULL,
            prorated_amount NUMERIC(10, 2) NOT NULL,
            credits_transferred INTEGER,
            change_date TIMESTAMP NOT NULL,
            status VARCHAR(50) NOT NULL,
            details TEXT
        )
        """
        
        try:
            execute_query(create_table_query, fetch=False)
            return True
        except Exception as e:
            print(f"Error al crear tabla plan_changes: {str(e)}")
            return False