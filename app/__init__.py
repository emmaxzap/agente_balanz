import os
import atexit
import secrets
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.logging import log_security_event
from dotenv import load_dotenv
import traceback
from app.controllers.upgrade import upgrade_bp

# Cargar variables de entorno desde .env
load_dotenv()

# Verificar y establecer credenciales de PayPal si no están disponibles
if not os.environ.get('PAYPAL_CLIENT_ID') or not os.environ.get('PAYPAL_SECRET'):
    print("⚠️ ADVERTENCIA: Variables de entorno PAYPAL_CLIENT_ID o PAYPAL_SECRET no encontradas")
    print("Usando credenciales de PayPal establecidas manualmente...")
    os.environ['PAYPAL_CLIENT_ID'] = "AZ8zTKyriOFD5SqIyPSHftR8ZsD2NAiozvCcI7Fs6UN4TOBmX-2UA_-kvIdMc8q7RQv1Smo147ffuyf7"
    os.environ['PAYPAL_SECRET'] = "EALl3-tOo9lruuWlyJHd3AFTxf5caqgsfjqRQlDOZmgiS5b6wkc5TOdghpmRxuJLTc1H2R9F-cy6zivm"

# Crear extensiones
csrf = CSRFProtect()
limiter = Limiter(
    get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
scheduler = BackgroundScheduler()

def rotate_session_key(app):
    """Rota la clave de sesión periódicamente"""
    new_key = secrets.token_hex(32)
    app.config['SECRET_KEY'] = new_key
    
    try:
        log_security_event(
            user_id=None,
            event_type='key_rotation',
            details={'tipo': 'session_key'},
            ip_address='internal'
        )
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo registrar evento de rotación de clave: {str(e)}")
    
    print("Clave de sesión rotada exitosamente")

# Función para inicializar tablas de base de datos
def init_app_tables():
    try:
        # Verificar si hay emails duplicados
        print("Verificando si hay emails duplicados...")
        
        # En PostgreSQL, verificamos si hay duplicados pero no necesitamos limpiarlos como en BigQuery
        try:
            from app.models.database_pg import execute_query
            
            query = """
            SELECT email, COUNT(*) as count 
            FROM usuarios 
            WHERE estado = 'activo' 
            GROUP BY email 
            HAVING COUNT(*) > 1
            """
            
            results = execute_query(query, fetch=True, as_dict=True)
            if results:
                print(f"ADVERTENCIA: Se encontraron {len(results)} emails duplicados en la base de datos.")
                print("En PostgreSQL puedes manejar esto manualmente o añadir restricciones UNIQUE.")
            else:
                print("No se encontraron emails duplicados.")
        except Exception as e:
            print(f"Error al verificar emails duplicados: {str(e)}")
        
        # Crear tabla para cambios de plan si no existe
        try:
            from app.models.plan_upgrades import PlanUpgrade
            PlanUpgrade.create_plan_changes_table_if_not_exists()
        except Exception as e:
            print(f"Error al crear tabla de cambios de plan: {str(e)}")
    
    except Exception as e:
        print(f"Error al inicializar tablas: {str(e)}")
        print(traceback.format_exc())

def create_app(config_name=None):
    """
    Crea y configura la aplicación Flask
    
    Args:
        config_name: Nombre de la configuración a usar
        
    Returns:
        Flask: La aplicación configurada
    """
    app = Flask(__name__)
    
    # Configuración por entorno
    if config_name == 'production' or os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # Inicializar extensiones
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Configuración de seguridad con Talisman
    csp = {
        'default-src': "'self'",
        'script-src': ["'self'", "https://cdn.jsdelivr.net", "https://www.paypal.com"],
        'style-src': ["'self'", "https://cdn.jsdelivr.net"],
        'img-src': ["'self'", "data:"],
        'font-src': ["'self'", "https://cdn.jsdelivr.net"],
        'frame-src': ["'self'", "https://www.paypal.com"],
    }
    
    force_https = app.config.get('ENV') == 'production'
    talisman = Talisman(
        app,
        content_security_policy=csp,
        force_https=force_https,
        strict_transport_security=True,
        session_cookie_secure=app.config.get('SESSION_COOKIE_SECURE', True),
        session_cookie_http_only=True,
        feature_policy={
            'geolocation': "'none'",
            'microphone': "'none'",
            'camera': "'none'"
        }
    )
    
    if app.config.get('ENV') == 'development':
        talisman.content_security_policy_report_only = True
    
    # Configurar rotación de claves
    scheduler.add_job(
        lambda: rotate_session_key(app), 
        'interval', 
        hours=24
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    
    # Configurar Jinja2 para escapar automáticamente
    app.jinja_env.autoescape = True
    
    # Registrar blueprints
    from app.controllers.auth import auth_bp
    from app.controllers.dashboard import dashboard_bp
    from app.controllers.payments import payments_bp
    from app.controllers.team import team_bp
    # Nuevo blueprint para actualizaciones de planes
    from app.controllers.upgrade import upgrade_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(team_bp, url_prefix='/team')
    # Registrar el nuevo blueprint
    app.register_blueprint(upgrade_bp, url_prefix='/upgrade')
    
    # Añadir rutas principales
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard_redirect():
        from flask import redirect, url_for
        return redirect(url_for('dashboard.index'))
    
    # Registrar manejadores de errores
    from app.controllers.errors import register_error_handlers
    register_error_handlers(app)
    
    # Inicializar tablas - llamando a la función directamente en lugar de usar el decorador eliminado
    # Esta es la alternativa a @app.before_first_request en Flask 2.0+
    with app.app_context():
        init_app_tables()
    
    # Registrar evento de inicio de aplicación
    try:
        log_security_event(
            user_id=None,
            event_type='application_start',
            details={'environment': app.config.get('ENV', 'development')},
            ip_address='internal'
        )
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo registrar evento de inicio de aplicación: {str(e)}")
    
    return app