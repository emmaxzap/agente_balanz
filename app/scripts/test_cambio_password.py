import os
import sys

# Agregar la ruta del proyecto al path para poder importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.user import User
from app.utils.security import generate_password_hash, check_password_hash

def test_cambio_password(user_id, password_actual, password_nueva):
    """
    Prueba directa de cambio de contraseña sin pasar por el servicio
    """
    try:
        # 1. Verificar que el usuario existe
        user = User.get_by_id(user_id)
        if not user:
            print(f"Error: Usuario con ID {user_id} no encontrado")
            return False
        
        print(f"Usuario encontrado: {user['email']}")
        
        # 2. Verificar que la contraseña actual sea correcta
        if not check_password_hash(user['password_hash'], password_actual):
            print("Error: Contraseña actual incorrecta")
            return False
        
        print("Contraseña actual verificada correctamente")
        
        # 3. Generar hash de la nueva contraseña
        new_password_hash = generate_password_hash(password_nueva)
        
        # 4. Actualizar la contraseña
        success = User.update_password(user_id, new_password_hash)
        if not success:
            print(f"Error: No se pudo actualizar la contraseña para usuario {user_id}")
            return False
        
        print("Contraseña actualizada correctamente")
        return True
    
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return False

if __name__ == "__main__":
    # Ejemplo de uso
    user_id = input("Ingrese el ID de usuario: ")
    password_actual = input("Ingrese la contraseña actual: ")
    password_nueva = input("Ingrese la nueva contraseña: ")
    
    resultado = test_cambio_password(user_id, password_actual, password_nueva)
    print(f"Resultado de la prueba: {'Exitoso' if resultado else 'Fallido'}")