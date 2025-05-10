import os
from app import create_app
from flask import Flask
from dotenv import load_dotenv

load_dotenv() 
# Verificar que las variables se cargaron correctamente
print(f"DB_HOST cargado del .env: {os.environ.get('DB_HOST', 'No encontrado')}")
print(f"DB_PORT cargado del .env: {os.environ.get('DB_PORT', 'No encontrado')}")

# En lugar de intentar limpiar automáticamente, solo mostrar un mensaje de diagnóstico
try:
    print("Verificando si hay emails duplicados...")
    
    # Importaciones necesarias
    from google.cloud import bigquery
    from app.models.database_pg import client, usuarios_table_id
    
    # Identificar emails duplicados (activos)
    query_duplicados = """
    SELECT email, COUNT(*) as count
    FROM `{}` 
    WHERE estado = 'activo'
    GROUP BY email
    HAVING COUNT(*) > 1
    """.format(usuarios_table_id)
    
    duplicados_resultado = client.query(query_duplicados).result()
    
    emails_duplicados = []
    for row in duplicados_resultado:
        emails_duplicados.append((row.email, row.count))
    
    if emails_duplicados:
        print(f"¡ADVERTENCIA! Se encontraron emails duplicados:")
        for email, count in emails_duplicados:
            print(f"- Email: {email}, Cantidad: {count}")
        print("Ejecute el script de limpieza para corregir este problema.")
    else:
        print("No se encontraron emails duplicados.")
except Exception as e:
    print(f"Error al verificar duplicados: {str(e)}")

# Crear la aplicación
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Iniciar el servidor
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=port)