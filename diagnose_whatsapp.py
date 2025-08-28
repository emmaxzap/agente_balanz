# debug_messages.py - Investigar qué pasó con los mensajes de hoy
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz

def debug_todays_messages():
    """Investiga el status de los mensajes enviados hoy"""
    load_dotenv()
    
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    print("🔍 INVESTIGANDO MENSAJES DE HOY")
    print("=" * 50)
    
    try:
        # Obtener mensajes de las últimas 24 horas
        messages_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        # Fecha de hace 24 horas
        yesterday = datetime.now() - timedelta(days=1)
        date_filter = yesterday.strftime('%Y-%m-%d')
        
        response = requests.get(
            messages_url + f"?PageSize=50&DateSent>={date_filter}",
            auth=(account_sid, auth_token)
        )
        
        if response.status_code == 200:
            messages = response.json().get('messages', [])
            
            print(f"📊 MENSAJES DE LAS ÚLTIMAS 24 HORAS: {len(messages)}")
            print("-" * 50)
            
            if not messages:
                print("❌ No se encontraron mensajes en las últimas 24 horas")
                return
            
            # Analizar cada mensaje
            for i, msg in enumerate(messages, 1):
                date_sent = msg.get('date_sent', '')
                date_updated = msg.get('date_updated', '')
                status = msg.get('status', 'unknown')
                error_code = msg.get('error_code', None)
                error_msg = msg.get('error_message', None)
                to_number = msg.get('to', 'unknown')
                from_number = msg.get('from', 'unknown')
                sid = msg.get('sid', 'N/A')
                body = msg.get('body', '')
                price = msg.get('price', 'N/A')
                
                # Emojis por status
                status_emoji = {
                    'delivered': '✅',
                    'sent': '📤', 
                    'queued': '⏳',
                    'failed': '❌',
                    'undelivered': '⚠️',
                    'accepted': '🔄',
                    'receiving': '📥',
                    'received': '✅'
                }.get(status, '❓')
                
                print(f"\n{i}. {status_emoji} MENSAJE {sid}")
                print(f"   📅 Enviado: {date_sent}")
                print(f"   📅 Actualizado: {date_updated}")
                print(f"   📊 Status: {status}")
                print(f"   📱 Para: {to_number}")
                print(f"   📱 Desde: {from_number}")
                print(f"   💰 Precio: {price}")
                print(f"   📝 Contenido: {body[:100]}..." if len(body) > 100 else f"   📝 Contenido: {body}")
                
                if error_code:
                    print(f"   ❌ ERROR CODE: {error_code}")
                    print(f"   ❌ ERROR MSG: {error_msg}")
                    
                    # Explicar errores específicos
                    explain_error_detailed(error_code, error_msg)
                
                # Analizar status específicos
                if status == 'queued':
                    print(f"   💭 El mensaje está en cola, debería procesarse pronto")
                elif status == 'failed':
                    print(f"   💭 El mensaje falló definitivamente")
                elif status == 'undelivered':
                    print(f"   💭 No se pudo entregar (problema del destinatario)")
                elif status == 'sent':
                    print(f"   💭 Enviado pero no confirmado como entregado")
                elif status == 'delivered':
                    print(f"   💭 ¡Entregado exitosamente!")
        
        # Estadísticas resumidas
        print(f"\n📈 RESUMEN:")
        print("-" * 20)
        status_counts = {}
        failed_count = 0
        
        for msg in messages:
            status = msg.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if msg.get('error_code'):
                failed_count += 1
        
        for status, count in status_counts.items():
            emoji = {
                'delivered': '✅',
                'sent': '📤', 
                'queued': '⏳',
                'failed': '❌',
                'undelivered': '⚠️'
            }.get(status, '❓')
            print(f"{emoji} {status}: {count}")
        
        if failed_count > 0:
            print(f"❌ Total con errores: {failed_count}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error investigando mensajes: {str(e)}")
        return False

def explain_error_detailed(error_code, error_msg):
    """Explica errores específicos con más detalle"""
    explanations = {
        63016: {
            'title': 'Número no está en WhatsApp Sandbox',
            'solution': 'Aunque ya te registraste antes, puede que el sandbox haya expirado. Intenta registrarte de nuevo.'
        },
        63017: {
            'title': 'Mensaje rechazado por WhatsApp',
            'solution': 'WhatsApp bloqueó el mensaje. Puede ser por contenido o frecuencia.'
        },
        21211: {
            'title': 'Formato de número inválido',
            'solution': 'Verifica que el número tenga formato: whatsapp:+5491157658736'
        },
        21612: {
            'title': 'No puede recibir mensajes',
            'solution': 'El número no puede recibir WhatsApp en este momento'
        },
        30007: {
            'title': 'Mensaje muy largo',
            'solution': 'Reduce el tamaño del mensaje a menos de 1600 caracteres'
        },
        30008: {
            'title': 'Contenido no permitido',
            'solution': 'WhatsApp rechazó el contenido del mensaje'
        }
    }
    
    if error_code in explanations:
        exp = explanations[error_code]
        print(f"   💡 Problema: {exp['title']}")
        print(f"   🔧 Solución: {exp['solution']}")
    else:
        print(f"   💡 Error desconocido. Consulta: https://www.twilio.com/docs/api/errors/{error_code}")

def check_sandbox_expiry():
    """Verifica si el sandbox puede haber expirado"""
    print(f"\n🕐 VERIFICANDO POSIBLE EXPIRACIÓN DEL SANDBOX:")
    print("-" * 50)
    print("• Los sandbox de Twilio trial a veces se resetean")
    print("• Esto puede pasar después de períodos de inactividad")
    print("• Si ayer funcionó pero hoy no, puede que necesites re-registrarte")
    
    print(f"\n🔄 PARA RE-REGISTRARTE (por si acaso):")
    print("1. Ve a: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn")
    print("2. Encuentra tu palabra clave actual")
    print("3. Desde WhatsApp envía: 'join <palabra>' a +1-415-523-8886")
    print("4. Espera confirmación")

def send_test_message_now():
    """Envía un mensaje de prueba ahora mismo"""
    load_dotenv()
    
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
    to_number = os.getenv('WHATSAPP_TARGET_NUMBER', 'whatsapp:+5491157658736')
    
    print(f"\n📤 ENVIANDO MENSAJE DE PRUEBA AHORA:")
    print("-" * 40)
    
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        message_body = f"""🧪 TEST DE DEBUGGING
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

🔍 Investigando por qué no llegan mensajes
✅ Si ves esto, WhatsApp funciona
❌ Si no lo ves, hay un problema

Responde con cualquier emoji para confirmar."""
        
        data = {
            'From': from_number,
            'To': to_number,
            'Body': message_body
        }
        
        response = requests.post(
            url,
            data=data,
            auth=(account_sid, auth_token)
        )
        
        if response.status_code == 201:
            response_data = response.json()
            print(f"✅ Mensaje enviado exitosamente")
            print(f"   📋 SID: {response_data.get('sid', 'N/A')}")
            print(f"   📊 Status inicial: {response_data.get('status', 'N/A')}")
            print(f"   💰 Precio: {response_data.get('price', 'N/A')}")
            
            # Esperar un poco y verificar status
            print(f"\n⏳ Esperando 30 segundos para verificar entrega...")
            import time
            time.sleep(30)
            
            # Verificar status del mensaje
            msg_sid = response_data.get('sid')
            if msg_sid:
                check_specific_message_status(msg_sid, account_sid, auth_token)
            
            return True
        else:
            print(f"❌ Error enviando: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def check_specific_message_status(msg_sid, account_sid, auth_token):
    """Verifica el status de un mensaje específico"""
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{msg_sid}.json"
        
        response = requests.get(url, auth=(account_sid, auth_token))
        
        if response.status_code == 200:
            msg_data = response.json()
            status = msg_data.get('status', 'unknown')
            error_code = msg_data.get('error_code', None)
            error_msg = msg_data.get('error_message', None)
            
            print(f"📊 Status actual del mensaje:")
            print(f"   📋 SID: {msg_sid}")
            print(f"   📊 Status: {status}")
            
            if error_code:
                print(f"   ❌ Error: {error_code} - {error_msg}")
                explain_error_detailed(error_code, error_msg)
            else:
                if status == 'delivered':
                    print(f"   ✅ ¡Mensaje entregado! Debería estar en tu WhatsApp")
                elif status == 'sent':
                    print(f"   📤 Enviado pero no confirmado como entregado")
                elif status == 'queued':
                    print(f"   ⏳ Aún en cola de procesamiento")
                elif status == 'failed':
                    print(f"   ❌ Falló sin código de error específico")
                    
    except Exception as e:
        print(f"❌ Error verificando mensaje específico: {str(e)}")

if __name__ == "__main__":
    print("🚀 DEBUGGING DE MENSAJES DE WHATSAPP\n")
    
    # 1. Investigar mensajes recientes
    debug_todays_messages()
    
    # 2. Verificar posible expiración
    check_sandbox_expiry()
    
    # 3. Enviar mensaje de prueba
    print("\n" + "="*60)
    send_test_message_now()
    
    print(f"\n📋 CONCLUSIONES:")
    print("• Si el mensaje de prueba llega = problema solucionado")
    print("• Si no llega = necesitas re-registrar el sandbox")
    print("• Si hay errores específicos = revisar código de error")