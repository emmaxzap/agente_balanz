# app/scripts/limpieza_manual.py
from app.models.database_pg import client, usuarios_table_id
from google.cloud import bigquery
import time

def limpiar_duplicados_manualmente():
    """
    Script especial para limpiar duplicados de manera segura
    Usa un enfoque de exportación/eliminación/importación para evitar problemas de buffer
    """
    # 1. Obtener todos los emails duplicados
    query_duplicados = f"""
    SELECT email, COUNT(*) as count
    FROM `{usuarios_table_id}`
    WHERE estado = 'activo'
    GROUP BY email
    HAVING COUNT(*) > 1
    """
    
    duplicados_resultado = client.query(query_duplicados).result()
    
    emails_duplicados = []
    for row in duplicados_resultado:
        emails_duplicados.append(row.email)
    
    if not emails_duplicados:
        print("No hay duplicados para limpiar.")
        return
    
    print(f"Se encontraron {len(emails_duplicados)} emails duplicados.")
    
    # 2. Para cada email duplicado, encontrar el mejor registro
    for email in emails_duplicados:
        print(f"\nProcesando email: {email}")
        
        query_mejores = f"""
        SELECT *
        FROM `{usuarios_table_id}`
        WHERE email = @email
        AND estado = 'activo'
        ORDER BY creditos DESC, fecha_registro DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email),
            ]
        )
        
        mejor_resultado = client.query(query_mejores, job_config).result()
        mejor_registro = None
        
        for row in mejor_resultado:
            mejor_registro = {key: row[key] for key in row.keys()}
            break
        
        if not mejor_registro:
            print(f"No se encontró registro para {email}. Continuando...")
            continue
        
        print(f"Mejor registro: user_id={mejor_registro['user_id']}, creditos={mejor_registro['creditos']}")
        
        # 3. Crear una copia limpia
        mejor_user_id = mejor_registro['user_id']
        
        # 4. Intentar desactivar TODOS los registros de este email (incluyendo el mejor)
        try:
            print("Desactivando todos los registros antiguos...")
            query_desactivar = f"""
            UPDATE `{usuarios_table_id}`
            SET estado = 'inactivo'
            WHERE email = @email
            AND estado = 'activo'
            """
            
            desactivar_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("email", "STRING", email),
                ]
            )
            
            client.query(query_desactivar, desactivar_config).result()
            print("Registros desactivados correctamente. Esperando a que se complete...")
            
            # Esperar un momento para que se complete la operación
            time.sleep(3)
            
            # 5. Crear un nuevo registro limpio
            from datetime import datetime
            import copy
            
            # Crear una copia limpia
            nuevo_registro = copy.deepcopy(mejor_registro)
            nuevo_registro['estado'] = 'activo'
            nuevo_registro['fecha_registro'] = datetime.now().isoformat()
            nuevo_registro['ultimo_login'] = datetime.now().isoformat()
            
            # Convertir todos los campos datetime a string
            for key, value in nuevo_registro.items():
                if isinstance(value, datetime):
                    nuevo_registro[key] = value.isoformat()
            
            print("Insertando nuevo registro limpio...")
            errors = client.insert_rows_json(usuarios_table_id, [nuevo_registro])
            
            if errors:
                print(f"ERROR al insertar: {errors}")
            else:
                print(f"Registro limpio creado correctamente para {email}")
                
        except Exception as e:
            print(f"Error al limpiar {email}: {str(e)}")
    
    print("\nProceso de limpieza completado.")
    
if __name__ == "__main__":
    print("Iniciando limpieza manual de registros duplicados...")
    limpiar_duplicados_manualmente()
    print("Proceso finalizado.")