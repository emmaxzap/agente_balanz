from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.user import User
from app.forms.payment_forms import CompraForm, CompraPlanForm, RecargaCreditosForm
from app.utils.decorators import login_required
from app.utils.logging import log_security_event, log_app_event
from app.services.payment_service import PaymentService
from app.models.plan import Plan
from app.models.database_pg import execute_query, planes_creditos_table_id, transacciones_table_id
import json

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/planes', methods=['GET', 'POST'])
@login_required
def planes():
    """
    Página de compra de planes de suscripción
    """
    # Verificar si el usuario ya tiene un plan activo
    active_plan = Plan.get_user_active_plan(session['user_id'])
    
    form = CompraPlanForm()
    
    # Cargar planes disponibles para el selector del formulario
    available_plans = Plan.get_available_plans()
    form.plan_id.choices = [(plan['plan_id'], plan['plan_name']) for plan in available_plans]
    
    if form.validate_on_submit():
        plan_id = form.plan_id.data
        
        # Obtener detalles del plan seleccionado
        selected_plan = next((plan for plan in available_plans if plan['plan_id'] == plan_id), None)
        if not selected_plan:
            flash('Plan no válido. Por favor selecciona un plan disponible.', 'danger')
            return redirect(url_for('payments.planes'))
        
        # Guardar datos temporales en la sesión
        session['temp_plan_id'] = plan_id
        session['temp_precio'] = selected_plan['price_amount']
        
        # Registrar intento de compra
        log_security_event(
            user_id=session['user_id'],
            event_type='subscription_attempt',
            details={'plan_id': plan_id, 'plan_name': selected_plan['plan_name'], 'monto': selected_plan['price_amount']},
            ip_address=request.remote_addr
        )
        
        # Proceder con PayPal
        return redirect(url_for('payments.procesar_plan_paypal'))
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='payments',
        action='view_plans',
        details={},
        ip_address=request.remote_addr
    )
    
    return render_template('planes.html', 
                          form=form, 
                          planes=available_plans, 
                          active_plan=active_plan)

@payments_bp.route('/recargar_creditos', methods=['GET', 'POST'])
@login_required
def recargar_creditos():
    """
    Página de recarga de créditos
    """
    # Verificar que el usuario tenga un plan activo
    active_plan = Plan.get_user_active_plan(session['user_id'])
    if not active_plan:
        flash('Necesitas tener un plan activo para recargar créditos. Por favor, adquiere un plan primero.', 'warning')
        return redirect(url_for('payments.planes'))
    
    form = RecargaCreditosForm()
    if form.validate_on_submit():
        cantidad = form.cantidad.data
        # Calcular precio (por ejemplo, $1 por crédito)
        precio = cantidad * 1.0
        
        session['temp_cantidad'] = cantidad
        session['temp_precio'] = precio
        
        # Registrar intento de recarga
        log_security_event(
            user_id=session['user_id'],
            event_type='credit_recharge_attempt',
            details={'creditos': cantidad, 'monto': precio, 'plan_id': active_plan['plan_id']},
            ip_address=request.remote_addr
        )
        
        # Proceder con PayPal
        return redirect(url_for('payments.procesar_paypal'))
    
    # Cargar planes de créditos disponibles - Adaptado para PostgreSQL
    query = f"""
    SELECT plan_id, nombre, descripcion, cantidad_creditos, precio, descuento, precio_final
    FROM {planes_creditos_table_id}
    WHERE activo = TRUE
    ORDER BY cantidad_creditos
    """
    
    results = execute_query(query, fetch=True, as_dict=True)
    
    planes_creditos = []
    for row in results:
        planes_creditos.append({
            'plan_id': row['plan_id'],
            'nombre': row['nombre'],
            'descripcion': row['descripcion'],
            'cantidad_creditos': row['cantidad_creditos'],
            'precio': row['precio'],
            'descuento': row['descuento'],
            'precio_final': row['precio_final']
        })
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='payments',
        action='view_recharge',
        details={},
        ip_address=request.remote_addr
    )
    
    return render_template('recargar_creditos.html', 
                          form=form, 
                          planes_creditos=planes_creditos, 
                          active_plan=active_plan)

@payments_bp.route('/procesar_paypal')
@login_required
def procesar_paypal():
    """
    Procesa el pago de recarga de créditos a través de PayPal
    """
    # Verificar que el usuario tenga un plan activo
    active_plan = Plan.get_user_active_plan(session['user_id'])
    if not active_plan:
        flash('Necesitas tener un plan activo para recargar créditos.', 'warning')
        return redirect(url_for('payments.planes'))
    
    cantidad = session.get('temp_cantidad', 0)
    precio = session.get('temp_precio', 0)
    
    if cantidad <= 0 or precio <= 0:
        flash('Cantidad o precio inválido. Por favor intente nuevamente.', 'danger')
        return redirect(url_for('payments.recargar_creditos'))
    
    try:
        # Crear el pago en PayPal para recarga de créditos
        payment_url = PaymentService.create_paypal_payment(
            cantidad, 
            precio,
            url_for('payments.confirmar_pago', _external=True),
            url_for('payments.cancelar_pago', _external=True),
            tipo="creditos"
        )
        
        if payment_url:
            # Registrar evento
            log_app_event(
                user_id=session['user_id'],
                module='payments',
                action='redirect_to_paypal',
                details={'tipo': 'creditos', 'cantidad': cantidad, 'precio': precio},
                ip_address=request.remote_addr
            )
            
            return redirect(payment_url)
        else:
            flash('Error al procesar el pago con PayPal. Intente nuevamente.', 'danger')
            
    except Exception as e:
        flash(f'Error al procesar el pago: {str(e)}', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_error',
            details={'tipo': 'creditos', 'creditos': cantidad, 'monto': precio, 'error': str(e)},
            ip_address=request.remote_addr
        )
    
    return redirect(url_for('payments.recargar_creditos'))

@payments_bp.route('/procesar_plan_paypal')
@login_required
def procesar_plan_paypal():
    """
    Procesa el pago de un plan a través de PayPal
    """
    plan_id = session.get('temp_plan_id', 0)
    precio = session.get('temp_precio', 0)
    
    if not plan_id or precio <= 0:
        flash('Plan o precio inválido. Por favor intente nuevamente.', 'danger')
        return redirect(url_for('payments.planes'))
    
    try:
        # Obtener detalles del plan
        plan_details = Plan.get_plan_by_id(plan_id)
        if not plan_details:
            flash('El plan seleccionado no está disponible. Por favor seleccione otro plan.', 'danger')
            return redirect(url_for('payments.planes'))
        
        # Crear el pago en PayPal para plan
        payment_url = PaymentService.create_paypal_payment(
            1,  # Cantidad siempre es 1 para planes
            precio,
            url_for('payments.confirmar_pago', _external=True),
            url_for('payments.cancelar_pago', _external=True),
            tipo="plan",
            plan_id=plan_id
        )
        
        if payment_url:
            # Registrar evento
            log_app_event(
                user_id=session['user_id'],
                module='payments',
                action='redirect_to_paypal',
                details={'tipo': 'plan', 'plan_id': plan_id, 'precio': precio},
                ip_address=request.remote_addr
            )
            
            return redirect(payment_url)
        else:
            flash('Error al procesar el pago con PayPal. Intente nuevamente.', 'danger')
            
    except Exception as e:
        flash(f'Error al procesar el pago: {str(e)}', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_error',
            details={'tipo': 'plan', 'plan_id': plan_id, 'monto': precio, 'error': str(e)},
            ip_address=request.remote_addr
        )
    
    return redirect(url_for('payments.planes'))

@payments_bp.route('/confirmar_pago')
@login_required
def confirmar_pago():
    """
    Confirma el pago luego de que el usuario completa la transacción en PayPal
    """
    # Parámetros recibidos de PayPal
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    
    # También intenta recuperar de la sesión
    session_payment_id = session.get('paypal_payment_id', '')
    
    # Usar el payment_id de la URL si no está en la sesión
    if not session_payment_id and payment_id:
        print(f"No se encontró payment_id en la sesión, usando el de la URL: {payment_id}")
        session['paypal_payment_id'] = payment_id
    else:
        payment_id = session_payment_id
    
    # Verificar si hay un plan_id en la sesión
    plan_id = session.get('plan_id')
    payment_type = session.get('payment_type', 'plan')
    
    print(f"Confirmando pago: payment_id={payment_id}, payer_id={payer_id}")
    print(f"Datos de sesión: user_id={session.get('user_id')}, plan_id={plan_id}, payment_type={payment_type}")
    
    if not payment_id or not payer_id:
        flash('No se pudo verificar el pago. Por favor intente nuevamente.', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_verification_failed',
            details={'reason': 'missing_params'},
            ip_address=request.remote_addr
        )
        return redirect(url_for('payments.planes'))
    
    try:
        # Si no hay plan_id en la sesión pero estamos procesando un pago de plan,
        # intentar recuperarlo del historial de sesión o establecer un valor predeterminado
        if payment_type == 'plan' and not plan_id:
            print("ERROR: No hay plan_id en la sesión para un pago de plan")
            plan_id = session.get('temp_plan_id')
            if plan_id:
                session['plan_id'] = plan_id
                print(f"Recuperado plan_id de temp_plan_id: {plan_id}")
            else:
                # Si aún no hay plan_id, esto es un error grave
                flash('Error: No se pudo determinar el plan seleccionado.', 'danger')
                return redirect(url_for('payments.planes'))
        
        # CRITICAL: Asegurarse que el usuario sea reconocido como admin, no como miembro de equipo
        user_id = session['user_id']
        session['is_team_member'] = False  # Por defecto, un usuario que compra un plan es admin
        
        # Es un pago de plan
        if payment_type == 'plan':
            # Ejecutar el pago y registrar la suscripción
            success = PaymentService.execute_paypal_payment(
                payment_id, 
                payer_id,
                user_id
            )
            
            if success:
                print(f"Pago exitoso para plan_id={plan_id}")
                
                # Obtener detalles del plan
                plan_details = Plan.get_plan_by_id(plan_id)
                
                if plan_details:
                    # CRITICAL: Actualizar créditos en la sesión explícitamente
                    creditos = plan_details.get('credit_amount', 0)
                    session['creditos'] = creditos
                    print(f"Créditos actualizados en sesión desde plan_details: {creditos}")
                    
                    # Forzar una recarga del usuario para verificar créditos actualizados
                    user = User.get_by_id(user_id)
                    if user:
                        # CRITICAL: Actualizar sesión con créditos reales del usuario
                        session['creditos'] = user.get('creditos', 0)
                        print(f"Créditos reales del usuario: {session['creditos']}")
                        
                        # Si los créditos no coinciden, intentar actualizar manualmente
                        if session['creditos'] != creditos:
                            print(f"ADVERTENCIA: Discrepancia en créditos. Sesión: {session['creditos']}, Plan: {creditos}")
                            # Intentar actualizar créditos manualmente
                            User.update_credits(user_id, creditos)
                            # Recargar usuario después de la actualización manual
                            user = User.get_by_id(user_id)
                            if user:
                                session['creditos'] = user.get('creditos', 0)
                                print(f"Créditos después de actualización manual: {session['creditos']}")
                
                # Limpiar datos temporales de pago (exceptuando plan_id para que persista)
                if 'temp_cantidad' in session:
                    del session['temp_cantidad']
                if 'temp_precio' in session:
                    del session['temp_precio']
                if 'paypal_payment_id' in session:
                    del session['paypal_payment_id']
                if 'payment_type' in session:
                    del session['payment_type']
                
                flash('¡Plan adquirido con éxito! Ya puedes disfrutar de los beneficios de tu nuevo plan.', 'success')
            else:
                print("ERROR: El pago no se ejecutó correctamente en PayPal")
                flash('Hubo un error al procesar el pago del plan. Por favor intente nuevamente.', 'danger')
        else:
            # Es una recarga de créditos
            success = PaymentService.execute_paypal_payment(
                payment_id, 
                payer_id,
                user_id,
                session.get('temp_cantidad', 0)
            )
            
            if success:
                # Actualizar la sesión con los nuevos créditos
                user = User.get_by_id(user_id)
                if user:
                    session['creditos'] = user.get('creditos', 0)
                    print(f"Recarga de créditos exitosa. Nuevos créditos: {session['creditos']}")
                
                # Limpiar datos temporales
                PaymentService.clear_payment_session_data()
                
                flash(f'¡Pago exitoso! Se han añadido {session.get("temp_cantidad", 0)} créditos a tu cuenta.', 'success')
            else:
                print("ERROR: La recarga de créditos falló")
                flash('Hubo un error al procesar el pago. Por favor intente nuevamente.', 'danger')
            
    except Exception as e:
        print(f"ERROR CRÍTICO en confirmar_pago: {str(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        
        flash(f'Error al confirmar el pago: {str(e)}', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='payment_execution_failed',
            details={'payment_id': payment_id, 'error': str(e), 'traceback': traceback_str},
            ip_address=request.remote_addr
        )
    
    return redirect(url_for('dashboard.index'))

@payments_bp.route('/cancelar_pago')
@login_required
def cancelar_pago():
    """
    Maneja la cancelación del pago por parte del usuario
    """
    # Registrar evento de cancelación de pago
    payment_id = session.get('paypal_payment_id', '')
    payment_type = session.get('payment_type', 'creditos')
    
    log_security_event(
        user_id=session['user_id'],
        event_type='payment_canceled',
        details={'payment_id': payment_id, 'tipo': payment_type},
        ip_address=request.remote_addr
    )
    
    # Limpiar datos temporales
    PaymentService.clear_payment_session_data()
    
    flash('Has cancelado el proceso de pago.', 'info')
    
    if payment_type == 'plan':
        return redirect(url_for('payments.planes'))
    else:
        return redirect(url_for('payments.recargar_creditos'))

@payments_bp.route('/historial_pagos')
@login_required
def historial_pagos():
    """
    Muestra el historial detallado de pagos del usuario
    """
    # Parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    # Obtener transacciones de pago (solo compras)
    from app.utils.sanitization import sanitize_output
    
    # Contar total de transacciones de pago - Adaptado para PostgreSQL
    count_query = f"""
    SELECT COUNT(*) as total
    FROM {transacciones_table_id}
    WHERE user_id = %s
    AND (creditos > 0 OR (detalles->>'tipo') = 'compra_plan')
    """
    
    count_results = execute_query(count_query, params=(session['user_id'],), fetch=True, as_dict=True)
    total = 0
    if count_results:
        total = count_results[0]['total']
    
    # Calcular total de páginas
    total_pages = (total + per_page - 1) // per_page
    
    # Obtener pagos paginados - Adaptado para PostgreSQL
    query = f"""
    SELECT transaction_id, monto, creditos, metodo_pago, estado, fecha_transaccion, detalles
    FROM {transacciones_table_id}
    WHERE user_id = %s
    AND (creditos > 0 OR (detalles->>'tipo') = 'compra_plan')
    ORDER BY fecha_transaccion DESC
    LIMIT %s
    OFFSET %s
    """
    
    params = (session['user_id'], per_page, offset)
    results = execute_query(query, params=params, fetch=True, as_dict=True)
    
    pagos = []
    for row in results:
        # Analizar detalles para determinar si es compra de plan
        detalles = {}
        try:
            if row['detalles']:
                if isinstance(row['detalles'], str):
                    detalles = json.loads(row['detalles'])
                else:
                    detalles = row['detalles']
        except:
            detalles = {}
        
        es_plan = detalles.get('tipo') == 'compra_plan'
        
        pagos.append({
            'transaction_id': row['transaction_id'],
            'monto': row['monto'],
            'creditos': row['creditos'],
            'metodo_pago': sanitize_output(row['metodo_pago']),
            'estado': sanitize_output(row['estado']),
            'fecha_transaccion': row['fecha_transaccion'],
            'detalles': row['detalles'],
            'es_plan': es_plan,
            'plan_id': detalles.get('plan_id')
        })
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='payments',
        action='view_payment_history',
        details={'page': page},
        ip_address=request.remote_addr
    )
    
    # Cargar plan activo del usuario
    active_plan = Plan.get_user_active_plan(session['user_id'])
    
    return render_template('historial_pagos.html', 
                          pagos=pagos,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          active_plan=active_plan)