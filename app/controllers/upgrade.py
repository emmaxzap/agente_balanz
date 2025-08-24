from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify
from app.utils.decorators import login_required
from app.utils.sanitization import sanitize_output
from app.models.user import User
from app.models.plan import Plan
from app.models.plan_upgrades import PlanUpgrade
from app.utils.logging import log_app_event, log_security_event
from app.services.payment_service import PaymentService
import uuid

upgrade_bp = Blueprint('upgrade', __name__)

@upgrade_bp.route('/')
@login_required
def index():
    """
    Página principal para actualizar plan
    Muestra los planes disponibles para actualización
    """
    # Obtener plan actual del usuario
    current_plan = Plan.get_user_active_plan(session['user_id'])
    
    if not current_plan:
        flash('Necesitas tener un plan activo para actualizar.', 'warning')
        return redirect(url_for('payments.planes'))
    
    # Añadir logs para depuración
    print(f"DEBUG: Plan actual del usuario: {current_plan.get('plan_id')}, nivel: {current_plan.get('subscription_level_id')}")
    
    # Obtener planes disponibles para actualización
    available_upgrades = PlanUpgrade.get_available_upgrades(session['user_id'])
    
    # Más logs para depuración
    print(f"DEBUG: Planes disponibles para actualización: {len(available_upgrades)}")
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='upgrade',
        action='view_upgrades',
        details={'current_plan_id': current_plan['plan_id']},
        ip_address=request.remote_addr
    )
    
    return render_template('upgrade_plans.html', 
                          current_plan=current_plan,
                          available_upgrades=available_upgrades)

# Cambiamos la ruta para que coincida con la que se usa en la plantilla
@upgrade_bp.route('/plan/<int:plan_id>')
@login_required
def plan_details(plan_id):
    """
    Página de detalles y confirmación para actualizar a un plan específico
    """
    # Obtener plan actual del usuario
    current_plan = Plan.get_user_active_plan(session['user_id'])
    
    if not current_plan:
        flash('Necesitas tener un plan activo para actualizar.', 'warning')
        return redirect(url_for('payments.planes'))
    
    # Obtener detalles del nuevo plan
    new_plan = Plan.get_plan_by_id(plan_id)
    if not new_plan:
        flash('El plan seleccionado no existe.', 'danger')
        return redirect(url_for('upgrade.index'))
    
    # Calcular costos de actualización
    upgrade_info = PlanUpgrade.calculate_upgrade_cost(current_plan, plan_id)
    
    if not upgrade_info:
        flash('No se pudo calcular el costo de actualización. Por favor, inténtalo de nuevo.', 'danger')
        return redirect(url_for('upgrade.index'))
    
    # Registrar evento
    log_app_event(
        user_id=session['user_id'],
        module='upgrade',
        action='view_upgrade_details',
        details={
            'current_plan_id': current_plan['plan_id'],
            'new_plan_id': plan_id,
            'upgrade_cost': upgrade_info['upgrade_cost']
        },
        ip_address=request.remote_addr
    )
    
    return render_template('upgrade_details.html',
                          current_plan=current_plan,
                          new_plan=new_plan,
                          upgrade_info=upgrade_info)

# Mantener la ruta anterior para compatibilidad
@upgrade_bp.route('/details/<int:plan_id>')
@login_required
def details_redirect(plan_id):
    """
    Redirige a la nueva ruta de detalles
    """
    return redirect(url_for('upgrade.plan_details', plan_id=plan_id))

@upgrade_bp.route('/process/<int:plan_id>', methods=['POST'])
@login_required
def process_upgrade(plan_id):
    """
    Procesa la solicitud de actualización de plan y redirecciona al pago
    """
    # Obtener plan actual del usuario
    current_plan = Plan.get_user_active_plan(session['user_id'])
    
    if not current_plan:
        flash('Necesitas tener un plan activo para actualizar.', 'warning')
        return redirect(url_for('payments.planes'))
    
    # Calcular costos de actualización
    upgrade_info = PlanUpgrade.calculate_upgrade_cost(current_plan, plan_id)
    
    if not upgrade_info:
        flash('No se pudo calcular el costo de actualización. Por favor, inténtalo de nuevo.', 'danger')
        return redirect(url_for('upgrade.index'))
    
    # Guardar información en la sesión para el proceso de pago
    session['upgrade_from_plan_id'] = current_plan['plan_id']
    session['upgrade_to_plan_id'] = plan_id
    session['upgrade_cost'] = upgrade_info['upgrade_cost']
    session['prorated_discount'] = upgrade_info['prorated_discount']
    
    # Registrar evento
    log_security_event(
        user_id=session['user_id'],
        event_type='upgrade_initiated',
        details={
            'current_plan_id': current_plan['plan_id'],
            'new_plan_id': plan_id,
            'upgrade_cost': upgrade_info['upgrade_cost'],
            'prorated_discount': upgrade_info['prorated_discount']
        },
        ip_address=request.remote_addr
    )
    
    # Redireccionar al procesamiento de pago
    return redirect(url_for('upgrade.process_payment', plan_id=plan_id))

@upgrade_bp.route('/process_payment/<int:plan_id>')
@login_required
def process_payment(plan_id):
    """
    Procesa el pago de la actualización de plan
    """
    # Verificar que tenemos la información necesaria en la sesión
    if ('upgrade_from_plan_id' not in session or 
        'upgrade_to_plan_id' not in session or 
        'upgrade_cost' not in session):
        flash('Información de actualización no disponible. Por favor, inicia el proceso nuevamente.', 'danger')
        return redirect(url_for('upgrade.index'))
    
    # Verificar que el plan_id coincide con el almacenado en la sesión
    if int(session['upgrade_to_plan_id']) != plan_id:
        flash('Inconsistencia en los datos de actualización. Por favor, inicia el proceso nuevamente.', 'danger')
        return redirect(url_for('upgrade.index'))
    
    # Obtener detalles de los planes
    current_plan = Plan.get_user_active_plan(session['user_id'])
    new_plan = Plan.get_plan_by_id(plan_id)
    
    if not current_plan or not new_plan:
        flash('Error al obtener información de los planes. Por favor, inténtalo de nuevo.', 'danger')
        return redirect(url_for('upgrade.index'))
    
    # Si el costo de actualización es 0, procesar directamente
    if session['upgrade_cost'] <= 0:
        # Crear un ID de transacción para mantener consistencia
        transaction_id = f"upgrade-free-{str(uuid.uuid4())}"
        
        try:
            # Registrar el cambio de plan
            new_subscription = PlanUpgrade.register_plan_change(
                session['user_id'],
                current_plan,
                plan_id,
                transaction_id,
                {
                    'upgrade_type': 'free_upgrade',
                    'prorated_discount': session['prorated_discount']
                }
            )
            
            # Limpiar datos de sesión
            session.pop('upgrade_from_plan_id', None)
            session.pop('upgrade_to_plan_id', None)
            session.pop('upgrade_cost', None)
            session.pop('prorated_discount', None)
            
            # Registrar evento
            log_security_event(
                user_id=session['user_id'],
                event_type='plan_upgraded',
                details={
                    'old_plan_id': current_plan['plan_id'],
                    'new_plan_id': plan_id,
                    'transaction_id': transaction_id,
                    'upgrade_cost': 0,
                    'prorated_discount': session.get('prorated_discount', 0)
                },
                ip_address=request.remote_addr
            )
            
            flash('¡Tu plan ha sido actualizado con éxito! No se aplicaron cargos adicionales gracias al descuento prorrateado.', 'success')
            return redirect(url_for('dashboard.index'))
            
        except Exception as e:
            flash(f'Error al procesar la actualización: {str(e)}', 'danger')
            return redirect(url_for('upgrade.index'))
    
    # Crear pago en PayPal para la diferencia
    try:
        print(f"DEBUG: Creando pago PayPal para upgrade - plan_id: {plan_id}, costo: {session['upgrade_cost']}")
        payment_url = PaymentService.create_paypal_payment(
            1,  # Cantidad siempre es 1 para actualizaciones de plan
            session['upgrade_cost'],
            url_for('upgrade.confirm_payment', _external=True),
            url_for('upgrade.cancel_payment', _external=True),
            tipo="plan",
            plan_id=plan_id
        )
        print(f"DEBUG: URL de pago generada: {payment_url}")

        if payment_url:
            # Registrar evento
            log_app_event(
                user_id=session['user_id'],
                module='upgrade',
                action='redirect_to_paypal',
                details={
                    'current_plan_id': current_plan['plan_id'],
                    'new_plan_id': plan_id,
                    'upgrade_cost': session['upgrade_cost']
                },
                ip_address=request.remote_addr
            )
            
            return redirect(payment_url)
        else:
            print("ERROR: PaymentService.create_paypal_payment retornó None")
            flash('Error al procesar el pago con PayPal. Intente nuevamente.', 'danger')
            
    except Exception as e:
        print(f"ERROR en process_payment: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash(f'Error al procesar el pago: {str(e)}', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='upgrade_payment_error',
            details={
                'current_plan_id': current_plan['plan_id'],
                'new_plan_id': plan_id,
                'upgrade_cost': session['upgrade_cost'],
                'error': str(e)
            },
            ip_address=request.remote_addr
        )
    
    return redirect(url_for('upgrade.index'))

@upgrade_bp.route('/confirm_payment')
@login_required
def confirm_payment():
    """
    Confirma el pago de la actualización de plan
    """
    payment_id = session.get('paypal_payment_id', '')
    payer_id = request.args.get('PayerID')
    
    if not payment_id or not payer_id:
        flash('No se pudo verificar el pago. Por favor intente nuevamente.', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='upgrade_payment_verification_failed',
            details={'reason': 'missing_params'},
            ip_address=request.remote_addr
        )
        return redirect(url_for('upgrade.index'))
    
    # Verificar que tenemos la información necesaria en la sesión
    if ('upgrade_from_plan_id' not in session or 
        'upgrade_to_plan_id' not in session):
        flash('Información de actualización no disponible. Por favor, inicia el proceso nuevamente.', 'danger')
        return redirect(url_for('upgrade.index'))
    
    # Obtener plan actual
    current_plan = Plan.get_user_active_plan(session['user_id'])
    
    if not current_plan:
        flash('No se encontró información de tu plan actual. Por favor, contacta a soporte.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # ID del nuevo plan
    plan_id = int(session['upgrade_to_plan_id'])
    
    try:
        # Ejecutar el pago
        paypal_result = PaymentService.execute_paypal_payment(
            payment_id, 
            payer_id,
            session['user_id']
        )
        
        if paypal_result:
            # Obtener el ID de transacción generado por el servicio de pago
            transaction_id = PaymentService.get_last_transaction_id()
            if not transaction_id:
                transaction_id = f"upgrade-{payment_id}"
            
            # Registrar el cambio de plan
            new_subscription = PlanUpgrade.register_plan_change(
                session['user_id'],
                current_plan,
                plan_id,
                transaction_id,
                {
                    'payment_id': payment_id,
                    'payer_id': payer_id,
                    'upgrade_cost': session.get('upgrade_cost', 0),
                    'prorated_discount': session.get('prorated_discount', 0)
                }
            )
            
            # Limpiar datos de sesión
            session.pop('upgrade_from_plan_id', None)
            session.pop('upgrade_to_plan_id', None)
            session.pop('upgrade_cost', None)
            session.pop('prorated_discount', None)
            PaymentService.clear_payment_session_data()
            
            # Registrar evento
            log_security_event(
                user_id=session['user_id'],
                event_type='plan_upgraded',
                details={
                    'old_plan_id': current_plan['plan_id'],
                    'new_plan_id': plan_id,
                    'transaction_id': transaction_id,
                    'payment_id': payment_id
                },
                ip_address=request.remote_addr
            )
            
            flash('¡Tu plan ha sido actualizado con éxito! Ya puedes disfrutar de los beneficios de tu nuevo plan.', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Hubo un error al procesar el pago de la actualización. Por favor intente nuevamente.', 'danger')
    
    except Exception as e:
        flash(f'Error al confirmar el pago: {str(e)}', 'danger')
        log_security_event(
            user_id=session['user_id'],
            event_type='upgrade_payment_execution_failed',
            details={'payment_id': payment_id, 'error': str(e)},
            ip_address=request.remote_addr
        )
    
    return redirect(url_for('upgrade.index'))

@upgrade_bp.route('/cancel_payment')
@login_required
def cancel_payment():
    """
    Maneja la cancelación del pago por parte del usuario
    """
    # Registrar evento de cancelación de pago
    payment_id = session.get('paypal_payment_id', '')
    
    log_security_event(
        user_id=session['user_id'],
        event_type='upgrade_payment_canceled',
        details={
            'payment_id': payment_id, 
            'from_plan_id': session.get('upgrade_from_plan_id'),
            'to_plan_id': session.get('upgrade_to_plan_id')
        },
        ip_address=request.remote_addr
    )
    
    # Limpiar datos temporales
    session.pop('upgrade_from_plan_id', None)
    session.pop('upgrade_to_plan_id', None)
    session.pop('upgrade_cost', None)
    session.pop('prorated_discount', None)
    PaymentService.clear_payment_session_data()
    
    flash('Has cancelado el proceso de actualización de plan.', 'info')
    return redirect(url_for('upgrade.index'))