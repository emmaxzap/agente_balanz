import html
import re

def sanitize_output(text):
    """
    Sanitiza texto para prevenir XSS
    
    Args:
        text: Texto a sanitizar
        
    Returns:
        str: Texto sanitizado
    """
    if text is None:
        return ""
    return html.escape(str(text))

def sanitize_input(text):
    """
    Sanitiza la entrada de texto para prevenir inyecciones
    
    Args:
        text: Texto a sanitizar
        
    Returns:
        str: Texto sanitizado
    """
    if text is None:
        return ""
    
    # Eliminar caracteres peligrosos
    sanitized = str(text)
    # Eliminar etiquetas HTML
    sanitized = re.sub(r'<[^>]*>', '', sanitized)
    # Eliminar secuencias de escape JavaScript
    sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
    return sanitized.strip()

def sanitize_filename(filename):
    """
    Sanitiza un nombre de archivo para evitar path traversal
    
    Args:
        filename: Nombre de archivo a sanitizar
        
    Returns:
        str: Nombre de archivo sanitizado
    """
    if filename is None:
        return ""
    
    # Eliminar path absoluto
    sanitized = os.path.basename(str(filename))
    # Eliminar cualquier caracter no alfanumérico, guión bajo o punto
    sanitized = re.sub(r'[^\w\-\.]', '_', sanitized)
    return sanitized

def sanitize_email(email):
    """
    Sanitiza una dirección de correo electrónico
    
    Args:
        email: Email a sanitizar
        
    Returns:
        str: Email sanitizado o cadena vacía si no es válido
    """
    if email is None:
        return ""
    
    # Patrón básico de correo electrónico
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if re.match(pattern, email):
        return email.lower()
    return ""

def sanitize_html(html_content, allowed_tags=None):
    """
    Sanitiza contenido HTML, permitiendo solo ciertas etiquetas
    
    Args:
        html_content: Contenido HTML a sanitizar
        allowed_tags: Lista de etiquetas permitidas
        
    Returns:
        str: HTML sanitizado
    """
    if html_content is None:
        return ""
        
    if allowed_tags is None:
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    # Implementación básica, para una solución más robusta se recomienda usar bibliotecas como bleach
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Eliminar todas las etiquetas no permitidas
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()
    
    # Eliminar todos los atributos excepto href en enlaces
    for tag in soup.find_all(True):
        if tag.name == 'a':
            # Conservar solo href, y sanitizarlo
            href = tag.get('href', '')
            tag.attrs = {}
            if href.startswith(('http://', 'https://', '/', '#', 'mailto:')):
                tag['href'] = href
        else:
            # Eliminar todos los atributos de otras etiquetas
            tag.attrs = {}
    
    return str(soup)