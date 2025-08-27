# test_whatsapp.py - Script para probar configuración de WhatsApp
import os
import requests
from dotenv import load_dotenv

def test_whatsapp_config():
    load_dotenv()
    
    # Obtener credenciales
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
    to_number = os.getenv('WHATSAPP_TARGET_NUMBER')
    
    print("CONFIGURACION WHATSAPP:")
    print(f"Account SID: {account_sid}")
    print(f"Auth Token: {auth_token[:8]}...")
    print(f"From: {from_number}")
    print(f"To: {to_number}")
    print()
    
    if not all([account_sid, auth_token, from_number, to_number]):
        print("❌ Faltan credenciales")
        return False
    
    # Probar envío
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        data = {
            'From': from_number,
            'To': to_number,
            'Body': '🧪 TEST BALANZ SCRAPER\n✅ WhatsApp funcionando correctamente!'
        }
        
        response = requests.post(
            url,
            data=data,
            auth=(account_sid, auth_token)
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Mensaje enviado exitosamente!")
            return True
        else:
            print("❌ Error enviando mensaje")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_whatsapp_config()