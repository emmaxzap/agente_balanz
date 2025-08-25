# notifications/whatsapp_notifier.py - Notificaciones por WhatsApp
import os
from datetime import datetime
from typing import List, Dict
import requests
import json

class WhatsAppNotifier:
    def __init__(self):
        # Configuración de Twilio WhatsApp
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        
        # Tu número de WhatsApp
        self.target_number = os.getenv('WHATSAPP_TARGET_NUMBER', 'whatsapp:+5491157658736')
        
        # URL de la API de Twilio
        self.twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        # Verificar configuración
        self.is_configured = bool(self.account_sid and self.auth_token)
        
        if not self.is_configured:
            print("⚠️ WhatsApp no configurado. Agrega las variables de entorno:")
            print("   TWILIO_ACCOUNT_SID=tu_account_sid")
            print("   TWILIO_AUTH_TOKEN=tu_auth_token") 
            print("   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886")
            print("   WHATSAPP_TARGET_NUMBER=whatsapp:+5491157658736")
    
    def send_message(self, message: str) -> bool:
        """Envía un mensaje por WhatsApp usando Twilio"""
        if not self.is_configured:
            print("❌ WhatsApp no configurado - no se puede enviar mensaje")
            return False
        
        try:
            # Datos para la API de Twilio
            data = {
                'From': self.twilio_whatsapp_number,
                'To': self.target_number,
                'Body': message
            }
            
            # Enviar mensaje
            response = requests.post(
                self.twilio_url,
                data=data,
                auth=(self.account_sid, self.auth_token)
            )
            
            if response.status_code == 201:
                print("✅ Mensaje enviado por WhatsApp exitosamente")
                return True
            else:
                print(f"❌ Error enviando WhatsApp: {response.status_code}")
                print(f"   Respuesta: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error enviando mensaje WhatsApp: {str(e)}")
            return False
    
    def send_portfolio_recommendations(self, portfolio_data: Dict, sell_recs: List[Dict], buy_opps: List[Dict]) -> bool:
        """Envía recomendaciones de cartera por WhatsApp"""
        try:
            # Crear mensaje formateado
            message = self._format_recommendations_message(portfolio_data, sell_recs, buy_opps)
            
            # Enviar mensaje
            return self.send_message(message)
            
        except Exception as e:
            print(f"❌ Error preparando mensaje de recomendaciones: {str(e)}")
            return False
    
    def _format_recommendations_message(self, portfolio_data: Dict, sell_recs: List[Dict], buy_opps: List[Dict]) -> str:
        """Formatea el mensaje de recomendaciones para WhatsApp"""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        message = f"📊 *REPORTE BALANZ* - {timestamp}\n"
        message += "="*30 + "\n\n"
        
        # Resumen de cartera
        if portfolio_data:
            dinero = portfolio_data.get('dinero_disponible', 0)
            valor_total = portfolio_data.get('valor_total_cartera', 0)
            ganancia = portfolio_data.get('ganancia_perdida_total', 0)
            total_invertido = portfolio_data.get('total_invertido', 0)
            
            rendimiento = (ganancia / total_invertido * 100) if total_invertido > 0 else 0
            
            message += f"💼 *RESUMEN CARTERA*\n"
            message += f"💰 Disponible: ${dinero:,.0f}\n"
            message += f"📈 Valor total: ${valor_total:,.0f}\n"
            message += f"📊 Rendimiento: {rendimiento:+.1f}%\n\n"
        
        # Recomendaciones de venta
        if sell_recs:
            message += f"🔴 *RECOMENDACIONES DE VENTA* ({len(sell_recs)})\n"
            message += "-"*25 + "\n"
            
            for rec in sell_recs[:3]:  # Top 3
                ticker = rec.get('ticker', 'N/A')
                valor = rec.get('current_value', 0)
                ganancia_pct = rec.get('gain_loss_pct', 0)
                razon = rec.get('primary_reason', 'No especificada')
                confianza = rec.get('confidence', 0)
                
                emoji = "🟢" if ganancia_pct > 0 else "🔴"
                message += f"{emoji} *{ticker}* - {confianza}% confianza\n"
                message += f"   💰 Valor: ${valor:,.0f}\n"
                message += f"   📊 G/P: {ganancia_pct:+.1f}%\n"
                message += f"   💡 Razón: {razon}\n\n"
        else:
            message += "🟢 *No hay recomendaciones de venta*\n\n"
        
        # Oportunidades de compra
        if buy_opps:
            message += f"🟢 *OPORTUNIDADES DE COMPRA* ({len(buy_opps)})\n"
            message += "-"*25 + "\n"
            
            for opp in buy_opps[:3]:  # Top 3
                ticker = opp.get('ticker', 'N/A')
                precio = opp.get('current_price', 0)
                inversion = opp.get('suggested_investment', 0)
                cantidad = opp.get('suggested_quantity', 0)
                confianza = opp.get('confidence', 0)
                retorno = opp.get('expected_return', 0)
                
                message += f"📈 *{ticker}* - {confianza}% confianza\n"
                message += f"   💰 Precio: ${precio:,.0f}\n"
                message += f"   🛒 Invertir: ${inversion:,.0f}\n"
                message += f"   📊 Cantidad: {cantidad} nominales\n"
                message += f"   🎯 Retorno esp.: +{retorno:.1f}%\n\n"
        else:
            message += "⚠️ *No hay oportunidades de compra*\n\n"
        
        # Mensaje final
        message += "⚠️ *IMPORTANTE*\n"
        message += "• Sugerencias basadas en análisis técnico\n"
        message += "• Considerar factores fundamentales\n"
        message += "• No arriesgar >5-10% por posición\n\n"
        
        message += "🤖 _Generado automáticamente por Balanz Scraper_"
        
        return message
    
    def send_simple_alert(self, title: str, message: str) -> bool:
        """Envía una alerta simple por WhatsApp"""
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        
        formatted_message = f"🚨 *{title}*\n"
        formatted_message += f"⏰ {timestamp}\n\n"
        formatted_message += message
        
        return self.send_message(formatted_message)
    
    def test_connection(self) -> bool:
        """Prueba la conexión enviando un mensaje de test"""
        if not self.is_configured:
            return False
        
        test_message = f"🧪 *TEST BALANZ SCRAPER*\n"
        test_message += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        test_message += f"✅ WhatsApp configurado correctamente\n"
        test_message += f"📱 Recibirás notificaciones aquí"
        
        return self.send_message(test_message)


# Alternativa gratuita usando pywhatkit (si no quieres usar Twilio)
class WhatsAppNotifierFree:
    def __init__(self, target_number: str = "+5491157658736"):
        self.target_number = target_number
        try:
            import pywhatkit
            self.pywhatkit = pywhatkit
            self.is_available = True
            print("✅ pywhatkit disponible para WhatsApp gratuito")
        except ImportError:
            self.is_available = False
            print("❌ pywhatkit no instalado. Instalar con: pip install pywhatkit")
    
    def send_message_instant(self, message: str) -> bool:
        """Envía mensaje instantáneo por WhatsApp Web"""
        if not self.is_available:
            return False
        
        try:
            # Envía mensaje instantáneo (requiere WhatsApp Web abierto)
            self.pywhatkit.sendwhatmsg_instantly(
                phone_no=self.target_number,
                message=message,
                wait_time=10,  # Esperar 10 segundos
                tab_close=True  # Cerrar tab después
            )
            
            print("✅ Mensaje enviado por WhatsApp Web")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando mensaje WhatsApp Web: {str(e)}")
            return False
    
    def send_portfolio_recommendations(self, portfolio_data: Dict, sell_recs: List[Dict], buy_opps: List[Dict]) -> bool:
        """Envía recomendaciones usando WhatsApp Web"""
        # Usar el mismo formato que Twilio pero simplificado
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        
        message = f"📊 BALANZ REPORT - {timestamp}\n"
        
        # Resumen básico
        if portfolio_data:
            dinero = portfolio_data.get('dinero_disponible', 0)
            message += f"💰 Disponible: ${dinero:,.0f}\n"
        
        # Ventas
        if sell_recs:
            message += f"🔴 VENDER ({len(sell_recs)}):\n"
            for rec in sell_recs[:2]:
                ticker = rec.get('ticker', 'N/A')
                ganancia_pct = rec.get('gain_loss_pct', 0)
                message += f"• {ticker} ({ganancia_pct:+.1f}%)\n"
        
        # Compras
        if buy_opps:
            message += f"🟢 COMPRAR ({len(buy_opps)}):\n"
            for opp in buy_opps[:2]:
                ticker = opp.get('ticker', 'N/A')
                inversion = opp.get('suggested_investment', 0)
                message += f"• {ticker} (${inversion:,.0f})\n"
        
        return self.send_message_instant(message)