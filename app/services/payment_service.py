import uuid
from datetime import datetime, timedelta
import json
import os
from flask import session, request
from paypalrestsdk import Payment
import paypalrestsdk
from app.models.database_pg import execute_query, execute_transaction, transacciones_table_id, uso_creditos_table_id, usuarios_table_id
from app.models.user import User
from app.models.plan import Plan
from app.utils.logging import log_security_event, log_app_event
from app.models.team import Team

# Configurar PayPal
paypalrestsdk.configure({
    "mode": os.environ.get("PAYPAL_MODE", "sandbox"),
    "client_id": os.environ.get("PAYPAL_CLIENT_ID"),
    "client_secret": os.environ.get("PAYPAL_SECRET")
})

class PaymentService:
    # Variable para almacenar el último transaction_id
    _last_transaction_id = None
    
    @staticmethod
    def get_last_transaction_id():
        """Obtiene el último transaction_id generado"""
        return PaymentService._last_transaction_id
    
    @staticmethod
    def create_paypal_payment(cantidad, precio, return_url, cancel_url, tipo="creditos", plan_id=None):
        print(f"DEBUG: Entrando a create_paypal_payment - tipo={tipo}, plan_id={plan_id}, precio={precio}")
        # Verificar que PayPal está configurado
        if not os.environ.get('PAYPAL_CLIENT_ID') or not os.environ.get('PAYPAL_SECRET'):
            raise ValueError("PayPal no está configurado correctamente")
        
        # Formatear el precio con 2 decimales como máximo
        precio_formateado = "{:.2f}".format(round(precio, 2))
        print(f"DEBUG: Precio formateado para PayPal: {precio_formateado}")
        
        # Configuración del ítem según el tipo de pago
        if tipo == "plan" and plan_id:
            plan_details = Plan.get_plan_by_id(plan_id)
            if not plan_details:
                raise ValueError(f"Plan con ID {plan_id} no encontrado")
            
            item_name = f"Plan: {plan_details['plan_name']}"
            item_sku = f"plan_{plan_id}"
            item_description = f"Suscripción al plan {plan_details['plan_name']} por {plan_details['period_months']} mes(es)"
            cantidad = 1  # Siempre es 1 para planes
        else:
            item_name = f"{cantidad} Créditos"
            item_sku = "creditos"
            item_description = f"Compra de {cantidad} créditos"
        
        payment = Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": item_name,
                        "sku": item_sku,
                        "price": precio_formateado,  # Usar el precio formateado
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": precio_formateado,  # Usar el precio formateado
                    "currency": "USD"
                },
                "description": item_description
            }]
        })
        
        try:
            if payment.create():
                # Guardar ID de pago en la sesión
                session['paypal_payment_id'] = payment.id
                session['payment_type'] = tipo
                if tipo == "plan" and plan_id:
                    session['plan_id'] = plan_id
                
                # Registrar evento de creación de pago
                log_security_event(
                    user_id=session['user_id'],
                    event_type='payment_created',
                    details={
                        'payment_id': payment.id, 
                        'tipo': tipo,
                        'plan_id': plan_id if tipo == "plan" else None,
                        'creditos': cantidad if tipo == "creditos" else None,
                        'monto': precio
                    },
                    ip_address=request.remote_addr
                )
                
                # Retornar URL de aprobación
                for link in payment.links:
                    if link.rel == "approval_url":
                        print(f"DEBUG: URL de aprobación generada: {link.href}")
                        return link.href
                
                print("ERROR: No se encontró URL de aprobación en los enlaces del pago")
            else:
                print(f"ERROR: Falló la creación del pago en PayPal")
                if hasattr(payment, 'error'):
                    print(f"ERROR: Detalles del error de PayPal: {payment.error}")
        except Exception as e:
            print(f"ERROR en payment.create(): {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        return None
    
    @staticmethod
    def register_transaction(user_id, amount, credits, payment_method, status, transaction_id=None, details=None):
        """
        Registra una transacción en la base de datos
        
        Args:
            user_id: ID del usuario
            amount: Monto de la transacción
            credits: Cantidad de créditos
            payment_method: Método de pago
            status: Estado de la transacción
            transaction_id: ID de la transacción (opcional)
            details: Detalles adicionales (opcional)
        
        Returns:
            str: ID de la transacción
        """
        if transaction_id is None:
            transaction_id = str(uuid.uuid4())
            
        # Almacenar el último transaction_id generado
        PaymentService._last_transaction_id = transaction_id
            
        # Convertir details a JSON si no es string
        if details and not isinstance(details, str):
            details = json.dumps(details)
            
        query = f"""
        INSERT INTO {transacciones_table_id}
        (transaction_id, user_id, monto, creditos, metodo_pago, estado, fecha_transaccion, detalles)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            transaction_id,
            user_id,
            amount,
            credits,
            payment_method,
            status,
            datetime.now().isoformat(),
            details
        )
        
        execute_query(query, params=params, fetch=False)
        return transaction_id
    
    @staticmethod
    def execute_paypal_payment(payment_id, payer_id, user_id, cantidad=None):
        """
        Ejecuta un pago previamente creado en PayPal
        
        Args:
            payment_id: ID del pago en PayPal
            payer_id: ID del pagador en PayPal
            user_id: ID del usuario
            cantidad: Cantidad de créditos (si es pago de créditos)
            
        Returns:
            bool: True si el pago se ejecutó correctamente
        """
        payment = Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            transaction_id = str(uuid.uuid4())
            # Almacenar el último transaction_id generado
            PaymentService._last_transaction_id = transaction_id
            
            precio = float(payment.transactions[0].amount.total)
            
            # Determinar el tipo de pago según la sesión
            payment_type = session.get('payment_type', 'creditos')
            
            if payment_type == 'plan':
                plan_id = session.get('plan_id')
                if not plan_id:
                    log_security_event(
                        user_id=user_id,
                        event_type='payment_execution_error',
                        details={'payment_id': payment_id, 'error': 'Missing plan_id in session'},
                        ip_address=request.remote_addr
                    )
                    return False
                
                # Obtener detalles del plan
                plan_details = Plan.get_plan_by_id(plan_id)
                if not plan_details:
                    log_security_event(
                        user_id=user_id,
                        event_type='payment_execution_error',
                        details={'payment_id': payment_id, 'error': f'Plan {plan_id} not found'},
                        ip_address=request.remote_addr
                    )
                    return False
                
                # Registrar la suscripción al plan
                return PaymentService.register_plan_subscription(
                    user_id, 
                    plan_id, 
                    plan_details, 
                    payment_id, 
                    transaction_id, 
                    precio
                )
            else:
                # Es una recarga de créditos, verificar que tenga plan activo
                active_plan = Plan.get_user_active_plan(user_id)
                if not active_plan:
                    log_security_event(
                        user_id=user_id,
                        event_type='payment_execution_error',
                        details={'payment_id': payment_id, 'error': 'No active plan for credit recharge'},
                        ip_address=request.remote_addr
                    )
                    return False
                
                # Registrar la transacción
                detalles = json.dumps({
                    'paypal_payment_id': payment_id,
                    'plan_id': active_plan['plan_id']
                })
                
                PaymentService.register_transaction(
                    user_id=user_id,
                    amount=precio,
                    credits=cantidad,
                    payment_method='paypal',
                    status='completado',
                    transaction_id=transaction_id,
                    details=detalles
                )
                
                # Actualizar los créditos del usuario
                if not User.update_credits(user_id, cantidad):
                    log_security_event(
                        user_id=user_id,
                        event_type='credit_update_error',
                        details={'payment_id': payment_id, 'creditos': cantidad},
                        ip_address=request.remote_addr
                    )
                    return False
                
                # Registrar evento de pago exitoso
                log_security_event(
                    user_id=user_id,
                    event_type='payment_success',
                    details={
                        'payment_id': payment_id, 
                        'transaction_id': transaction_id, 
                        'creditos': cantidad, 
                        'monto': precio,
                        'tipo': 'recarga_creditos'
                    },
                    ip_address=request.remote_addr
                )
                
                return True
        else:
            # Registrar evento de error en pago
            log_security_event(
                user_id=user_id,
                event_type='payment_execution_failed',
                details={'payment_id': payment_id},
                ip_address=request.remote_addr
            )
            return False
    
    @staticmethod
    def register_plan_subscription(user_id, plan_id, plan_details, payment_id, transaction_id, precio):
        """
        Registra una suscripción a un plan
        """
        print(f"Registrando suscripción de plan para user_id={user_id}, plan_id={plan_id}")
        print(f"Detalles del plan: {plan_details}")
        
        # Tabla de suscripciones de usuario
        user_subscriptions_table = 'user_subscriptions'
        
        # Fecha de inicio (ahora)
        start_date = datetime.now()
        # Fecha de fin (según la duración del plan)
        end_date = start_date + timedelta(days=30 * plan_details['period_months'])
        
        # Subscription ID
        subscription_id = str(uuid.uuid4())
        
        try:
            # Asegurarse de que los créditos del plan estén definidos
            creditos = 0
            if 'credit_amount' in plan_details and plan_details['credit_amount'] is not None:
                creditos = plan_details['credit_amount']
            else:
                print(f"ADVERTENCIA: No se encontró 'credit_amount' en los detalles del plan o es None. Usando valor predeterminado 0.")
                
            print(f"Créditos a asignar según el plan: {creditos}")
            
            # PRIMERO - Registrar la transacción de pago
            detalles = json.dumps({
                'paypal_payment_id': payment_id,
                'plan_id': plan_id,
                'subscription_id': subscription_id,
                'tipo': 'compra_plan'
            })
            
            PaymentService.register_transaction(
                user_id=user_id,
                amount=precio,
                credits=creditos,  # Añadir los créditos iniciales del plan
                payment_method='paypal',
                status='completado',
                transaction_id=transaction_id,
                details=detalles
            )
            
            print(f"Transacción registrada exitosamente. ID: {transaction_id}")
            
            # SEGUNDO - Insertar la suscripción (ahora que la transacción existe)
            subscription_query = f"""
            INSERT INTO {user_subscriptions_table}
            (subscription_id, user_id, plan_id, start_date, end_date, is_active, payment_status, transaction_id, payment_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            subscription_params = (
                subscription_id,
                user_id,
                plan_id,
                start_date.isoformat(),
                end_date.isoformat(),
                True,
                'completed',
                transaction_id,
                json.dumps({'paypal_payment_id': payment_id})
            )
            
            execute_query(subscription_query, params=subscription_params, fetch=False)
            
            print(f"Suscripción registrada exitosamente. ID: {subscription_id}")
            
            # Verificar si es una actualización de plan
            from app.models.plan_upgrades import PlanUpgrade
            
            # Obtener todas las suscripciones anteriores para este usuario
            user_subs_query = f"""
            SELECT * FROM {user_subscriptions_table}
            WHERE user_id = %s AND subscription_id != %s
            ORDER BY start_date DESC
            LIMIT 1
            """
            
            previous_subs = execute_query(user_subs_query, params=(user_id, subscription_id), fetch=True, as_dict=True)
            
            # Si hay suscripciones anteriores, es un upgrade/cambio de plan
            is_plan_upgrade = len(previous_subs) > 0
            
            # Actualizar los créditos del usuario solo si NO es un upgrade
            if not is_plan_upgrade:
                print(f"Nueva suscripción (no es upgrade). Actualizando créditos del usuario: +{creditos}")
                
                # Verificar status de actualización de créditos
                update_result = User.update_credits(user_id, creditos)
                if not update_result:
                    print(f"ERROR: No se pudieron actualizar los créditos del usuario")
                    log_security_event(
                        user_id=user_id,
                        event_type='credit_update_error',
                        details={'payment_id': payment_id, 'creditos': creditos},
                        ip_address=request.remote_addr
                    )
                    return False
                
                print(f"Créditos del usuario actualizados correctamente")
            else:
                print(f"Es un upgrade de plan. Los créditos serán manejados por PlanUpgrade.register_plan_change()")
            
            # Registrar evento de suscripción exitosa
            log_security_event(
                user_id=user_id,
                event_type='subscription_success',
                details={
                    'payment_id': payment_id, 
                    'transaction_id': transaction_id,
                    'subscription_id': subscription_id,
                    'plan_id': plan_id,
                    'plan_name': plan_details['plan_name'],
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'monto': precio,
                    'creditos_iniciales': creditos
                },
                ip_address=request.remote_addr
            )
            
            return True
        except Exception as e:
            print(f"ERROR en register_plan_subscription: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
    
    @staticmethod
    def clear_payment_session_data():
        """
        Limpia los datos temporales de pago de la sesión pero mantiene información esencial
        """
        if 'temp_cantidad' in session:
            del session['temp_cantidad']
        if 'temp_precio' in session:
            del session['temp_precio']
        if 'paypal_payment_id' in session:
            del session['paypal_payment_id']
        if 'payment_type' in session:
            del session['payment_type']
    
    @staticmethod
    def use_credits(user_id, cantidad, servicio_id=None, descripcion=None, used_by=None):
        """
        Registra el uso de créditos
        
        Args:
            user_id: ID del usuario a quien se le descontarán los créditos
            cantidad: Cantidad de créditos a usar
            servicio_id: ID del servicio (opcional)
            descripcion: Descripción del uso (opcional)
            used_by: ID del usuario que realmente usó los créditos (si es diferente)
            
        Returns:
            bool: True si los créditos se usaron correctamente
        """
        # Si no se especifica quién usó los créditos, es el mismo usuario
        if not used_by:
            used_by = user_id
            
        # Verificar si es parte de un equipo
        is_team_usage = (user_id != used_by)
        
        # Verificar si el usuario tiene un plan activo
        active_plan = Plan.get_user_active_plan(user_id)
        if not active_plan:
            log_security_event(
                user_id=user_id,
                event_type='credits_usage_failed',
                details={
                    'creditos': cantidad, 
                    'servicio_id': servicio_id,
                    'used_by': used_by if is_team_usage else None,
                    'reason': 'no_active_plan'
                },
                ip_address=request.remote_addr
            )
            return False
        
        # Verificar si hay descripción
        if not descripcion:
            descripcion = f"Uso de {cantidad} créditos"
            if servicio_id:
                descripcion += f" en servicio {servicio_id}"
            if is_team_usage:
                user_data = User.get_by_id(used_by)
                user_email = user_data.get('email', 'desconocido') if user_data else 'desconocido'
                descripcion += f" (utilizado por miembro del equipo: {user_email})"
        
        # Actualizar los créditos del usuario propietario
        if not User.update_credits(user_id, -cantidad):
            log_security_event(
                user_id=user_id,
                event_type='credits_usage_failed',
                details={
                    'creditos': cantidad, 
                    'servicio_id': servicio_id,
                    'used_by': used_by if is_team_usage else None,
                    'reason': 'update_failed'
                },
                ip_address=request.remote_addr
            )
            return False
        
        # Registrar el uso de créditos en transacciones
        transaction_id = str(uuid.uuid4())
        transaction_details = {
            'servicio_id': servicio_id,
            'descripcion': descripcion,
            'plan_id': active_plan['plan_id']
        }
        
        # Si es uso por parte de un miembro del equipo, añadir esa información
        if is_team_usage:
            transaction_details['used_by'] = used_by
            transaction_details['is_team_usage'] = True
            
            # Obtener información del miembro
            member_info = Team.get_member_info(used_by)
            if member_info:
                transaction_details['member_role'] = member_info.get('role')
        
        # Registrar la transacción
        PaymentService.register_transaction(
            user_id=user_id,
            amount=0,  # No hay monto de dinero
            credits=-cantidad,  # Negativo para indicar uso
            payment_method='uso_servicio',
            status='completado',
            transaction_id=transaction_id,
            details=json.dumps(transaction_details)
        )
        
        # Registrar en la tabla de uso_creditos si existe
        if servicio_id:
            uso_id = str(uuid.uuid4())
            uso_query = f"""
            INSERT INTO {uso_creditos_table_id}
            (uso_id, user_id, servicio_id, creditos_usados, fecha_uso, descripcion, estado, used_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            uso_params = (
                uso_id,
                user_id,  # Propietario de los créditos
                servicio_id,
                cantidad,
                datetime.now().isoformat(),
                descripcion,
                'completado',
                used_by if is_team_usage else user_id  # Quién realmente lo usó
            )
            
            execute_query(uso_query, params=uso_params, fetch=False)
        
        # Registrar evento de uso de créditos
        log_app_event(
            user_id=used_by,  # El que realizó la acción
            module='credits',
            action='use_credits',
            details={
                'creditos': cantidad, 
                'servicio_id': servicio_id,
                'transaction_id': transaction_id,
                'plan_id': active_plan['plan_id'],
                'owner_id': user_id if is_team_usage else None,
                'is_team_usage': is_team_usage
            },
            ip_address=request.remote_addr
        )
        
        return True

    @staticmethod
    def transfer_credits(from_user_id, to_user_id, cantidad):
        """
        Transfiere créditos de un usuario a otro (específicamente de admin a miembro del equipo)
        
        Args:
            from_user_id: ID del usuario que transfiere los créditos (admin)
            to_user_id: ID del usuario que recibe los créditos (miembro)
            cantidad: Cantidad de créditos a transferir
            
        Returns:
            bool: True si la transferencia fue exitosa
            
        Raises:
            ValueError: Si alguna validación falla
        """
        # Validar cantidad
        if cantidad <= 0:
            raise ValueError("La cantidad de créditos a transferir debe ser mayor que cero")
        
        # Verificar relación de equipo (solo el admin puede transferir a miembros)
        member_info = Team.get_member_info(to_user_id)
        if not member_info or member_info['owner_id'] != from_user_id:
            raise ValueError("Solo puedes transferir créditos a miembros de tu equipo")
        
        # Verificar que el origen tenga suficientes créditos
        user_from = User.get_by_id(from_user_id)
        if not user_from or user_from.get('creditos', 0) < cantidad:
            raise ValueError("No tienes suficientes créditos para realizar esta transferencia")
        
        # Verificar que ambos usuarios tengan plan activo
        active_plan_from = Plan.get_user_active_plan(from_user_id)
        if not active_plan_from:
            raise ValueError("No tienes un plan activo")
        
        # Realizar la transferencia usando una transacción atómica real
        transaction_id = str(uuid.uuid4())
        
        try:
            # Crear todas las operaciones que deben ejecutarse en una sola transacción
            transaction_queries = [
                # 1. Descontar créditos del origen
                (
                    f"UPDATE {usuarios_table_id} SET creditos = creditos - %s WHERE user_id = %s",
                    [cantidad, from_user_id]
                ),
                # 2. Añadir créditos al destino
                (
                    f"UPDATE {usuarios_table_id} SET creditos = creditos + %s WHERE user_id = %s",
                    [cantidad, to_user_id]
                )
            ]
            
            # Ejecutar la transacción (automáticamente hace rollback si hay errores)
            execute_transaction(transaction_queries)
            
            # Obtener información para los registros
            user_to = User.get_by_id(to_user_id)
            to_email = user_to.get('email', 'Desconocido') if user_to else 'Desconocido'
            
            # 3. Registrar la transacción para el origen (salida)
            from_transaction = {
                'transaction_id': transaction_id + "_from",
                'user_id': from_user_id,
                'monto': 0,
                'creditos': -cantidad,
                'metodo_pago': 'transferencia_equipo',
                'estado': 'completado',
                'fecha_transaccion': datetime.now().isoformat(),
                'detalles': json.dumps({
                    'tipo': 'transferencia_salida',
                    'to_user_id': to_user_id,
                    'to_email': to_email,
                    'cantidad': cantidad,
                    'plan_id': active_plan_from['plan_id']
                })
            }
            
            # 4. Registrar la transacción para el destino (entrada)
            to_transaction = {
                'transaction_id': transaction_id + "_to",
                'user_id': to_user_id,
                'monto': 0,
                'creditos': cantidad,
                'metodo_pago': 'transferencia_equipo',
                'estado': 'completado',
                'fecha_transaccion': datetime.now().isoformat(),
                'detalles': json.dumps({
                    'tipo': 'transferencia_entrada',
                    'from_user_id': from_user_id,
                    'from_email': user_from.get('email', 'Admin'),
                    'cantidad': cantidad,
                    'plan_id': active_plan_from['plan_id']
                })
            }
            
            # Insertar los registros de transacción
            transaction_inserts = [
                (
                    f"INSERT INTO {transacciones_table_id} (transaction_id, user_id, monto, creditos, metodo_pago, estado, fecha_transaccion, detalles) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        from_transaction['transaction_id'],
                        from_transaction['user_id'],
                        from_transaction['monto'],
                        from_transaction['creditos'],
                        from_transaction['metodo_pago'],
                        from_transaction['estado'],
                        from_transaction['fecha_transaccion'],
                        from_transaction['detalles']
                    ]
                ),
                (
                    f"INSERT INTO {transacciones_table_id} (transaction_id, user_id, monto, creditos, metodo_pago, estado, fecha_transaccion, detalles) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        to_transaction['transaction_id'],
                        to_transaction['user_id'],
                        to_transaction['monto'],
                        to_transaction['creditos'],
                        to_transaction['metodo_pago'],
                        to_transaction['estado'],
                        to_transaction['fecha_transaccion'],
                        to_transaction['detalles']
                    ]
                )
            ]
            
            # Ejecutar inserciones en una segunda transacción
            execute_transaction(transaction_inserts)
            
            # Registrar evento de transferencia exitosa
            log_security_event(
                user_id=from_user_id,
                event_type='credit_transfer_success',
                details={
                    'to_user_id': to_user_id,
                    'cantidad': cantidad,
                    'transaction_id': transaction_id
                },
                ip_address=request.remote_addr
            )
            
            return True
            
        except Exception as e:
            print(f"Error al realizar la transferencia: {str(e)}")
            log_security_event(
                user_id=from_user_id,
                event_type='transfer_failed',
                details={
                    'to_user_id': to_user_id,
                    'cantidad': cantidad,
                    'error': str(e)
                },
                ip_address=request.remote_addr
            )
            return False