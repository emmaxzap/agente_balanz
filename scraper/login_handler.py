# scraper/login_handler.py - Manejo especializado del login
import time
from utils.helpers import find_element_by_selectors
from utils.constants import SELECTORS, LOG_MESSAGES

class LoginHandler:
    def __init__(self, page):
        self.page = page
    
    def perform_login(self, url, username, password):
        """
        Realiza login en Balanz con flujo de dos pasos
        """
        try:
            print(f"🌐 Navegando a: {url}")
            self.page.goto(url, wait_until='networkidle')
            time.sleep(3)
            
            # PASO 1: Ingresar usuario
            if not self._login_step1(username):
                return False
            
            # PASO 2: Ingresar contraseña
            if not self._login_step2(password):
                return False
            
            # Verificar éxito del login
            return self._verify_login_success(url)
            
        except Exception as e:
            print(f"❌ Error durante el login: {str(e)}")
            return False
    
    def _login_step1(self, username):
        """Paso 1: Ingresar usuario y hacer click en Continuar"""
        print(f"\n{LOG_MESSAGES['login_step1']}")
        
        # Buscar campo de usuario
        username_element, selector = find_element_by_selectors(
            self.page, SELECTORS['username_fields'], "campo usuario"
        )
        
        if not username_element:
            return False
        
        # Completar campo usuario
        print("📝 Ingresando usuario...")
        username_element.fill(username)
        time.sleep(1)
        
        # Buscar y hacer click en "Continuar"
        continue_element, _ = find_element_by_selectors(
            self.page, SELECTORS['submit_buttons'][:1], "botón Continuar"
        )
        
        if continue_element:
            print("🖱️ Haciendo click en Continuar...")
            continue_element.click()
        else:
            print("⚠️ Intentando Enter...")
            self.page.keyboard.press('Enter')
        
        time.sleep(3)
        return True
    
    def _login_step2(self, password):
        """Paso 2: Ingresar contraseña y hacer click en Ingresar"""
        print(f"\n{LOG_MESSAGES['login_step2']}")
        
        # Buscar campo de contraseña con reintentos
        password_element = None
        for attempt in range(10):
            password_element, _ = find_element_by_selectors(
                self.page, SELECTORS['password_fields'], "campo contraseña"
            )
            
            if password_element:
                break
            
            print(f"⏳ Intento {attempt + 1}/10 - Esperando campo contraseña...")
            time.sleep(1)
        
        if not password_element:
            print("❌ No se encontró campo de contraseña")
            return False
        
        # Completar contraseña
        print("📝 Ingresando contraseña...")
        password_element.fill(password)
        time.sleep(1)
        
        # Buscar y hacer click en "Ingresar"
        login_element, _ = find_element_by_selectors(
            self.page, SELECTORS['submit_buttons'][1:], "botón Ingresar"
        )
        
        if login_element:
            print("🖱️ Haciendo click en Ingresar...")
            login_element.click()
        else:
            print("⚠️ Intentando Enter...")
            self.page.keyboard.press('Enter')
        
        return True
    
    def _verify_login_success(self, original_url):
        """Verifica si el login fue exitoso"""
        print("⏳ Verificando login...")
        
        success_indicators = ['/app/', '/dashboard', '/home', '/main', '/portfolio']
        success_elements = ['a[href*="/app/"]', 'nav', '.user-menu']
        
        for attempt in range(15):
            time.sleep(1)
            current_url = self.page.url
            
            # Verificar URL
            url_success = any(indicator in current_url.lower() for indicator in success_indicators)
            
            # Verificar elementos
            element_success = any(
                self.page.locator(selector).count() > 0 
                for selector in success_elements
            )
            
            if url_success or element_success:
                print(f"✅ Login exitoso! URL: {current_url}")
                return True
            
            # Verificar errores
            if self._check_login_errors():
                return False
            
            print(f"⏳ Verificando... {attempt + 1}/15")
        
        # Verificar si salió de la página de login
        final_url = self.page.url
        if '/login' not in final_url.lower() and '/auth' not in final_url.lower():
            print(f"✅ Login exitoso (salió de login): {final_url}")
            return True
        
        print(f"❌ Login falló: {final_url}")
        return False
    
    def _check_login_errors(self):
        """Verifica si hay errores de login en la página"""
        error_selectors = [
            '.alert-danger', 
            '.alert-error',
            ':has-text("Usuario o contraseña incorrectos")',
            ':has-text("Error de autenticación")'
        ]
        
        for selector in error_selectors:
            elements = self.page.locator(selector)
            if elements.count() > 0:
                error_text = elements.first.text_content().strip()
                if error_text and len(error_text) < 200:
                    print(f"❌ Error de login: {error_text}")
                    return True
        
        return False