from datetime import datetime
import uuid

from app.models.database_pg import execute_query, usuarios_table_id, historial_passwords_table_id, transacciones_table_id
from app.utils.security import generate_password_hash

class User:
    @staticmethod
    def get_table_id():
        """
        Retorna el ID de la tabla de usuarios
        
        Returns:
            str: ID de la tabla de usuarios
        """
        return usuarios_table_id
        
    @staticmethod
    def get_by_id(user_id):
        """
        Obtiene un usuario por su ID
        
        Args:
            user_id: ID del usuario a buscar
            
        Returns:
            dict: Datos del usuario o None si no existe
        """
        query = f"""
        SELECT *
        FROM {usuarios_table_id}
        WHERE user_id = %s
        AND estado = 'activo'
        """
        
        results = execute_query(query, params=(user_id,), fetch=True, as_dict=True)
        
        return results[0] if results else None

    @staticmethod
    def get_by_email(email):
        """
        Obtiene un usuario por su email
        
        Args:
            email: Email del usuario a buscar
            
        Returns:
            dict: Datos del usuario o None si no existe
        """
        query = f"""
        SELECT *
        FROM {usuarios_table_id}
        WHERE email = %s
        AND estado = 'activo'
        """
        
        results = execute_query(query, params=(email,), fetch=True, as_dict=True)
        
        return results[0] if results else None
    
    @staticmethod
    def create(data):
        """
        Crea un nuevo usuario
        
        Args:
            data: Diccionario con los datos del usuario
            
        Returns:
            str: ID del usuario creado
            
        Raises:
            Exception: Si ocurre un error al insertar el usuario
        """
        # Verificar que el email no exista previamente
        query = f"""
        SELECT COUNT(*) as count
        FROM {usuarios_table_id}
        WHERE email = %s
        AND estado = 'activo'
        """
        
        results = execute_query(query, params=(data['email'],), fetch=True, as_dict=True)
        
        count = 0
        if results:
            count = results[0]['count']
        
        if count > 0:
            raise Exception(f"El email {data['email']} ya está registrado")
        
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(data['password'])
        
        # Preparar la consulta de inserción
        insert_query = f"""
        INSERT INTO {usuarios_table_id}
        (user_id, email, password_hash, nombre, apellido, telefono, pais, 
         fecha_registro, ultimo_login, estado, creditos, tipo_usuario, acepta_marketing, totp_secret)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Preparar los parámetros
        insert_params = (
            user_id,
            data['email'],
            password_hash,
            data['nombre'],
            data['apellido'],
            data.get('telefono'),
            data.get('pais'),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            'activo',
            0,
            'normal',
            data.get('acepta_marketing', False),
            None
        )
        
        # Ejecutar la inserción
        execute_query(insert_query, params=insert_params, fetch=False)
        
        return user_id
    
    @staticmethod
    def update_password(user_id, new_password_hash):
        """
        Actualiza la contraseña de un usuario
        
        Args:
            user_id: ID del usuario
            new_password_hash: Nuevo hash de contraseña
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        query = f"""
        UPDATE {usuarios_table_id}
        SET password_hash = %s
        WHERE user_id = %s
        """
        
        try:
            execute_query(query, params=(new_password_hash, user_id), fetch=False)
            return True
        except Exception as e:
            print(f"Error al actualizar contraseña: {str(e)}")
            return False
    
    @staticmethod
    def update_totp_secret(user_id, totp_secret):
        """
        Actualiza el secreto TOTP de un usuario
        
        Args:
            user_id: ID del usuario
            totp_secret: Nuevo secreto TOTP
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            query = f"""
            UPDATE {usuarios_table_id}
            SET totp_secret = %s
            WHERE user_id = %s
            """
            
            execute_query(query, params=(totp_secret, user_id), fetch=False)
            return True
        except Exception as e:
            print(f"Error al actualizar secreto TOTP: {str(e)}")
            return False
    
    @staticmethod
    def update_credits(user_id, cantidad, reset=False):
        """
        Actualiza la cantidad de créditos de un usuario
        
        Args:
            user_id: ID del usuario
            cantidad: Cantidad de créditos a añadir (positivo) o restar (negativo)
            reset: Si es True, establece la cantidad exacta de créditos en lugar de sumar/restar
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            print(f"Actualizando créditos para user_id={user_id}, cantidad={cantidad}, reset={reset}")
            
            # Primero verificar los créditos actuales del usuario
            query_check = f"""
            SELECT creditos, email
            FROM {usuarios_table_id}
            WHERE user_id = %s
            AND estado = 'activo'
            """
            
            results = execute_query(query_check, params=(user_id,), fetch=True, as_dict=True)
            
            if not results:
                print(f"ERROR: No se encontró un registro activo para el usuario {user_id}")
                return False
            
            creditos_actuales = results[0]['creditos']
            
            # Si es reset, simplemente establecer la cantidad, si no, sumar/restar
            if reset:
                nuevos_creditos = cantidad
            else:
                # Si la cantidad es negativa, verificar que el usuario tenga suficientes créditos
                if cantidad < 0 and creditos_actuales < abs(cantidad):
                    print(f"ERROR: Créditos insuficientes. Actual: {creditos_actuales}, Requerido: {abs(cantidad)}")
                    return False
                
                nuevos_creditos = creditos_actuales + cantidad
            
            # Actualizar directamente los créditos del usuario
            update_query = f"""
            UPDATE {usuarios_table_id}
            SET creditos = %s
            WHERE user_id = %s
            AND estado = 'activo'
            """
            
            execute_query(update_query, params=(nuevos_creditos, user_id), fetch=False)
            print(f"Créditos actualizados correctamente. Nuevos créditos: {nuevos_creditos}")
            
            return True
        except Exception as e:
            print(f"Error en update_credits: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
    
    @staticmethod
    def get_password_history(user_id, limit=3):
        """
        Obtiene el historial de contraseñas de un usuario
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de contraseñas a obtener
            
        Returns:
            list: Lista de hashes de contraseñas
        """
        query = f"""
        SELECT password_hash 
        FROM {historial_passwords_table_id} 
        WHERE user_id = %s
        ORDER BY fecha_creacion DESC
        LIMIT %s
        """
        
        results = execute_query(query, params=(user_id, limit), fetch=True, as_dict=True)
        
        password_hashes = []
        for row in results:
            password_hashes.append(row['password_hash'])
        
        return password_hashes
    
    @staticmethod
    def get_transactions(user_id, limit=10):
        """
        Obtiene el historial de transacciones de un usuario
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de transacciones a obtener
            
        Returns:
            list: Lista de transacciones
        """
        query = f"""
        SELECT transaction_id, monto, creditos, metodo_pago, estado, fecha_transaccion
        FROM {transacciones_table_id}
        WHERE user_id = %s
        ORDER BY fecha_transaccion DESC
        LIMIT %s
        """
        
        results = execute_query(query, params=(user_id, limit), fetch=True, as_dict=True)
        
        transactions = []
        for row in results:
            transactions.append({
                'transaction_id': row['transaction_id'],
                'monto': row['monto'],
                'creditos': row['creditos'],
                'metodo_pago': row['metodo_pago'],
                'estado': row['estado'],
                'fecha_transaccion': row['fecha_transaccion']
            })
        
        return transactions


    @staticmethod
    def transfer_credits(from_user_id, to_user_id, amount):
        """
        Transfiere créditos de un usuario a otro
        
        Args:
            from_user_id: ID del usuario que envía los créditos
            to_user_id: ID del usuario que recibe los créditos
            amount: Cantidad de créditos a transferir
            
        Returns:
            bool: True si la transferencia fue exitosa
        """
        try:
            # Verificar que el que envía tenga suficientes créditos
            from_user = User.get_by_id(from_user_id)
            if not from_user or 'creditos' not in from_user or from_user['creditos'] < amount:
                return False
            
            # Verificar que el destinatario exista
            to_user = User.get_by_id(to_user_id)
            if not to_user:
                return False
            
            # Iniciar transacción para asegurar que ambos cambios se realizan o ninguno
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Restar créditos al remitente
                update_sender = f"""
                UPDATE users
                SET creditos = creditos - %s
                WHERE user_id = %s
                """
                cursor.execute(update_sender, (amount, from_user_id))
                
                # Añadir créditos al destinatario
                update_receiver = f"""
                UPDATE users
                SET creditos = creditos + %s
                WHERE user_id = %s
                """
                cursor.execute(update_receiver, (amount, to_user_id))
                
                # Registrar la transacción en el log
                from app.models.creditos import CreditLog
                CreditLog.register_transfer(from_user_id, to_user_id, amount)
                
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"Error en transferencia de créditos: {str(e)}")
                return False
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"Error general en transferencia: {str(e)}")
            return False
        
    @staticmethod
    def add_password_to_history(user_id, password_hash):
        """
        Añade una contraseña al historial de contraseñas del usuario
        
        Args:
            user_id: ID del usuario
            password_hash: Hash de la contraseña a añadir
            
        Returns:
            bool: True si la inserción fue exitosa
        """
        try:
            history_id = str(uuid.uuid4())
            
            insert_query = f"""
            INSERT INTO {historial_passwords_table_id}
            (history_id, user_id, password_hash, fecha_creacion)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """
            
            execute_query(insert_query, params=(history_id, user_id, password_hash), fetch=False)
            
            return True
        except Exception as e:
            print(f"Error al añadir contraseña al historial: {str(e)}")
            return False