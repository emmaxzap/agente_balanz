from datetime import datetime
import uuid

from app.models.database_pg import execute_query

class Plan:
    @staticmethod
    def get_available_plans():
        """
        Obtiene todos los planes disponibles para compra
        
        Returns:
            list: Lista de planes disponibles
        """
        # Referencia a las tablas que usaremos
        subscription_plans_table = 'subscription_plans'
        service_categories_table = 'service_categories'
        subscription_levels_table = 'subscription_levels'
        credit_packages_table = 'credit_packages'
        pricing_tiers_table = 'pricing_tiers'
        
        # Consulta para obtener planes con toda su información
        query = f"""
        SELECT 
            p.plan_id, 
            p.plan_name, 
            p.is_featured,
            p.period_months,
            p.subscription_level_id,  -- Aseguramos que se seleccione este campo
            sc.category_name,
            sc.category_description,
            sl.level_name,
            sl.description AS level_description,
            sl.features_included,
            sl.max_users,
            cp.credit_amount,
            cp.description AS credit_description,
            pt.price_amount,
            pt.currency,
            pt.description AS price_description
        FROM {subscription_plans_table} p
        JOIN {service_categories_table} sc ON p.category_id = sc.category_id
        JOIN {subscription_levels_table} sl ON p.subscription_level_id = sl.subscription_level_id
        JOIN {credit_packages_table} cp ON p.credit_package_id = cp.credit_package_id
        JOIN {pricing_tiers_table} pt ON p.pricing_tier_id = pt.pricing_tier_id
        ORDER BY p.is_featured DESC, sc.category_name, sl.subscription_level_id
        """
        
        results = execute_query(query, fetch=True, as_dict=True)
        
        plans = []
        for row in results:
            plans.append({
                'plan_id': row['plan_id'],
                'plan_name': row['plan_name'],
                'is_featured': row['is_featured'],
                'period_months': row['period_months'],
                'subscription_level_id': row['subscription_level_id'],  # Incluimos este campo
                'category_name': row['category_name'],
                'category_description': row['category_description'],
                'level_name': row['level_name'],
                'level_description': row['level_description'],
                'features_included': row['features_included'],
                'max_users': row['max_users'],
                'credit_amount': row['credit_amount'],
                'credit_description': row['credit_description'],
                'price_amount': float(row['price_amount']),
                'currency': row['currency'],
                'price_description': row['price_description']
            })
        
        return plans
    
    @staticmethod
    def get_plan_by_id(plan_id):
        """
        Obtiene un plan específico por su ID
        
        Args:
            plan_id: ID del plan
            
        Returns:
            dict: Datos del plan o None si no existe
        """
        # Referencia a las tablas que usaremos
        subscription_plans_table = 'subscription_plans'
        service_categories_table = 'service_categories'
        subscription_levels_table = 'subscription_levels'
        credit_packages_table = 'credit_packages'
        pricing_tiers_table = 'pricing_tiers'
        
        # Consulta para obtener un plan específico
        query = f"""
        SELECT 
            p.plan_id, 
            p.plan_name, 
            p.is_featured,
            p.period_months,
            p.subscription_level_id,  
            sc.category_name,
            sc.category_description,
            sl.level_name,
            sl.description AS level_description,
            sl.features_included,
            sl.max_users,
            cp.credit_amount,
            cp.description AS credit_description,
            pt.price_amount,
            pt.currency,
            pt.description AS price_description
        FROM {subscription_plans_table} p
        JOIN {service_categories_table} sc ON p.category_id = sc.category_id
        JOIN {subscription_levels_table} sl ON p.subscription_level_id = sl.subscription_level_id
        JOIN {credit_packages_table} cp ON p.credit_package_id = cp.credit_package_id
        JOIN {pricing_tiers_table} pt ON p.pricing_tier_id = pt.pricing_tier_id
        WHERE p.plan_id = %s
        """
        
        results = execute_query(query, params=(plan_id,), fetch=True, as_dict=True)
        
        if results:
            row = results[0]
            return {
                'plan_id': row['plan_id'],
                'plan_name': row['plan_name'],
                'is_featured': row['is_featured'],
                'period_months': row['period_months'],
                'category_name': row['category_name'],
                'category_description': row['category_description'],
                'level_name': row['level_name'],
                'level_description': row['level_description'],
                'features_included': row['features_included'],
                'max_users': row['max_users'],
                'credit_amount': row['credit_amount'],
                'credit_description': row['credit_description'],
                'price_amount': float(row['price_amount']),
                'currency': row['currency'],
                'price_description': row['price_description'],
                # Añadir siempre el subscription_level_id
                'subscription_level_id': row['subscription_level_id']
            }
            
        return None
    
    @staticmethod
    def get_user_active_plan(user_id):
        """
        Obtiene el plan activo de un usuario
        
        Args:
            user_id: ID del usuario
                
        Returns:
            dict: Datos del plan activo o None si no tiene
        """
        from app.models.database_pg import user_subscriptions_table_id, subscription_plans_table_id, subscription_levels_table_id
        
        # Consulta adaptada a la estructura real de las tablas
        query = f"""
        SELECT 
            us.subscription_id, us.user_id, us.plan_id, us.start_date, us.end_date, 
            us.is_active, us.payment_status, us.transaction_id, us.payment_details,
            p.plan_name, p.subscription_level_id, p.credit_package_id, p.pricing_tier_id, 
            p.is_featured, p.period_months,
            sl.level_name, sl.description as level_description, sl.features_included, sl.max_users
        FROM {user_subscriptions_table_id} us
        LEFT JOIN {subscription_plans_table_id} p ON us.plan_id = p.plan_id
        LEFT JOIN {subscription_levels_table_id} sl ON p.subscription_level_id = sl.subscription_level_id
        WHERE us.user_id = %s
        AND us.is_active = TRUE
        ORDER BY us.start_date DESC
        LIMIT 1
        """
        
        try:
            results = execute_query(query, params=(user_id,), fetch=True, as_dict=True)
            
            # Si encontramos una suscripción activa
            if results:
                row = results[0]
                subscription = {
                    'subscription_id': row['subscription_id'],
                    'user_id': row['user_id'],
                    'plan_id': row['plan_id'],
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'is_active': row['is_active'],
                    'payment_status': row['payment_status'],
                    'transaction_id': row.get('transaction_id'),
                    'payment_details': row.get('payment_details'),
                    
                    # Datos del plan
                    'plan_name': row.get('plan_name', "Plan Desconocido"),
                    'subscription_level_id': row.get('subscription_level_id', 0),
                    'credit_package_id': row.get('credit_package_id', 0),
                    'pricing_tier_id': row.get('pricing_tier_id', 0),
                    'is_featured': row.get('is_featured', False),
                    'period_months': row.get('period_months', 1),
                    
                    # Datos del nivel de suscripción
                    'level_name': row.get('level_name', "Nivel Básico"),
                    'level_description': row.get('level_description', ""),
                    'features_included': row.get('features_included', ""),
                    'max_users': row.get('max_users', 1),
                    
                    # Añadimos estos campos para compatibilidad con el código existente
                    'price_amount': 0.0,  # Este campo no existe en tus tablas, pero se usa en el código
                    'credit_amount': 0    # Este campo no existe en tus tablas, pero se usa en el código
                }
                
                return subscription
            
            return None
            
        except Exception as e:
            print(f"Error al obtener el plan activo: {str(e)}")
            # En caso de error, devolver None para que el sistema maneje la falta de plan
            return None
            
    @staticmethod
    def deactivate_subscription(subscription_id):
        """
        Desactiva una suscripción
        
        Args:
            subscription_id: ID de la suscripción a desactivar
            
        Returns:
            bool: True si se desactivó correctamente
        """
        from app.models.database_pg import user_subscriptions_table_id
        
        query = f"""
        UPDATE {user_subscriptions_table_id}
        SET is_active = FALSE
        WHERE subscription_id = %s
        """
        
        try:
            execute_query(query, params=(subscription_id,), fetch=False)
            return True
        except Exception as e:
            print(f"Error al desactivar suscripción: {str(e)}")
            return False