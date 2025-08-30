# notifications/whatsapp_notifier.py - Notificaciones mejoradas por WhatsApp
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
            # Dividir mensaje si es muy largo (WhatsApp tiene límite de ~1600 caracteres)
            if len(message) > 1500:
                return self._send_long_message_in_parts(message)
            
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
    
    def _send_long_message_in_parts(self, message: str) -> bool:
        """Divide mensajes largos en partes"""
        try:
            # Dividir por secciones naturales
            parts = []
            current_part = ""
            
            lines = message.split('\n')
            
            for line in lines:
                if len(current_part + line + '\n') > 1400:  # Margen de seguridad
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = ""
                
                current_part += line + '\n'
            
            if current_part:
                parts.append(current_part.strip())
            
            # Enviar cada parte
            success_count = 0
            for i, part in enumerate(parts, 1):
                header = f"*PARTE {i}/{len(parts)}*\n\n" if len(parts) > 1 else ""
                full_part = header + part
                
                if self._send_single_message(full_part):
                    success_count += 1
                    if i < len(parts):  # Pausa entre mensajes
                        import time
                        time.sleep(2)
            
            return success_count == len(parts)
            
        except Exception as e:
            print(f"❌ Error enviando mensaje largo: {str(e)}")
            return False
    
    def _send_single_message(self, message: str) -> bool:
        """Envía un mensaje individual"""
        try:
            data = {
                'From': self.twilio_whatsapp_number,
                'To': self.target_number,
                'Body': message
            }
            
            response = requests.post(
                self.twilio_url,
                data=data,
                auth=(self.account_sid, self.auth_token)
            )
            
            return response.status_code == 201
            
        except Exception as e:
            return False
    
    def send_portfolio_analysis_message(self, rules_analysis: Dict, expert_analysis: Dict, combined: Dict) -> bool:
        """Envía análisis completo con recomendaciones específicas por WhatsApp"""
        try:
            # Verificar si tenemos análisis real de Claude
            has_real_analysis = self._has_real_claude_analysis(expert_analysis)
            
            if not has_real_analysis:
                print("⚠️ Enviando solo recomendaciones básicas por WhatsApp")
                message = self._format_basic_whatsapp_message(rules_analysis)
            else:
                message = self._format_actionable_whatsapp_message(rules_analysis, expert_analysis)
            
            return self.send_message(message)
            
        except Exception as e:
            print(f"❌ Error preparando mensaje de análisis: {str(e)}")
            return False
    
    def _has_real_claude_analysis(self, expert_analysis: Dict) -> bool:
        """Verifica si tenemos análisis real de Claude"""
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        
        # Verificar que no sea análisis genérico
        generic_indicators = [
            'análisis de respaldo',
            'técnico mejorado no disponible',
            'posiciones muy recientes (1 día promedio)',
            'pérdidas actuales son normales'
        ]
        
        is_generic = any(indicator in razonamiento.lower() for indicator in generic_indicators)
        
        # Verificar análisis técnico real
        analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        has_real_rsi = False
        if por_activo:
            for ticker, analysis in por_activo.items():
                rsi = analysis.get('rsi_analysis', '')
                if rsi and 'no_calculado' not in rsi and '(' in rsi:  # Buscar valores específicos
                    has_real_rsi = True
                    break
        
        return not is_generic and has_real_rsi and len(razonamiento) > 100
    
    def _format_actionable_whatsapp_message(self, rules_analysis: Dict, expert_analysis: Dict) -> str:
        """Formatea mensaje ACCIONABLE con recomendaciones específicas"""
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        metrics = rules_analysis.get('portfolio_metrics', {})
        
        message = f"*🎯 QUÉ HACER CON TUS INVERSIONES*\n"
        message += f"📅 {timestamp}\n"
        message += "=" * 30 + "\n\n"
        
        # Situación actual
        total_value = metrics.get('total_value', 0)
        total_pnl = metrics.get('total_pnl', 0)
        total_pnl_pct = metrics.get('total_pnl_pct', 0)
        cash_available = total_value * metrics.get('cash_allocation', 0)
        
        message += f"*💼 TU SITUACIÓN*\n"
        message += f"💰 Total: ${total_value:,.0f}\n"
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        message += f"{pnl_emoji} Resultado: ${total_pnl:,.0f} ({total_pnl_pct:+.1f}%)\n"
        message += f"💵 Disponible: ${cash_available:,.0f}\n\n"
        
        # ACCIONES INMEDIATAS - ESPECÍFICAS
        immediate_actions = expert_analysis.get('acciones_inmediatas', [])
        if immediate_actions:
            message += f"*🚨 HACER HOY*\n"
            message += "-" * 15 + "\n"
            
            for i, action in enumerate(immediate_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '')
                cantidad = action.get('cantidad', 0)
                precio = action.get('precio_objetivo', 0)
                razon = action.get('razon', '')
                inversion_total = action.get('inversion_total', 0)
                
                if 'comprar' in accion.lower():
                    message += f"*{i}. COMPRAR {ticker}*\n"
                    message += f"📊 Cantidad: {cantidad} acciones\n"
                    message += f"💰 Precio máx: ${precio:.0f}\n"
                    message += f"💵 Invertir: ${inversion_total:,.0f}\n"
                    message += f"❓ Por qué: {razon}\n\n"
                    
                elif 'vender' in accion.lower():
                    message += f"*{i}. VENDER {ticker}*\n"
                    message += f"📊 Cantidad: {cantidad} acciones\n"
                    message += f"💰 Precio mín: ${precio:.0f}\n"
                    message += f"❓ Por qué: {razon}\n\n"
        else:
            message += f"*✅ No hay acciones urgentes hoy*\n\n"
        
        # ACCIONES PARA PRÓXIMOS DÍAS
        short_term_actions = expert_analysis.get('acciones_corto_plazo', [])
        if short_term_actions:
            message += f"*📅 PRÓXIMOS DÍAS*\n"
            message += "-" * 15 + "\n"
            
            for i, action in enumerate(short_term_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '').replace('_', ' ')
                timeframe = action.get('timeframe', '')
                condiciones = action.get('condiciones', '')
                explicacion = action.get('explicacion_simple', condiciones)
                
                message += f"*{i}. {ticker}* - {accion}\n"
                message += f"⏰ Cuándo: {timeframe}\n"
                message += f"📋 Qué vigilar: {explicacion}\n\n"
        
        # NIVELES DE PROTECCIÓN
        stop_losses = expert_analysis.get('gestion_riesgo', {}).get('stop_loss_sugeridos', {})
        if stop_losses:
            message += f"*🛡️ PROTECCIÓN AUTOMÁTICA*\n"
            message += "-" * 20 + "\n"
            message += f"Vende automáticamente si llegan a:\n"
            
            for ticker, stop_price in stop_losses.items():
                try:
                    precio_stop = float(stop_price)
                    message += f"• *{ticker}*: ${precio_stop:.0f}\n"
                except:
                    message += f"• *{ticker}*: {stop_price}\n"
            
            message += "\n"
        
        # ANÁLISIS TÉCNICO SIMPLIFICADO
        analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        if por_activo and len(por_activo) <= 5:  # Solo si no son muchas posiciones
            message += f"*📈 ESTADO DE TUS ACCIONES*\n"
            message += "-" * 20 + "\n"
            
            for ticker, analysis in por_activo.items():
                momentum = analysis.get('momentum', 'neutral')
                rsi_analysis = analysis.get('rsi_analysis', '')
                
                # Emoji según momentum
                emoji = "📈" if momentum == 'alcista' else "📉" if momentum == 'bajista' else "➡️"
                
                # Simplificar RSI para WhatsApp
                if 'sobrecomprado' in rsi_analysis:
                    estado = "Muy caro"
                elif 'sobrevendido' in rsi_analysis:
                    estado = "Oportunidad?"
                else:
                    estado = "Normal"
                
                message += f"{emoji} *{ticker}*: {estado}\n"
            
            message += "\n"
        
        # CONCLUSIÓN DEL EXPERTO (SOLO SI ES REAL)
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento and self._has_real_claude_analysis(expert_analysis):
            # Tomar solo la parte más importante
            conclusion = razonamiento[:150] + "..." if len(razonamiento) > 150 else razonamiento
            message += f"*🧠 CONCLUSIÓN*\n"
            message += f"{conclusion}\n\n"
        
        # ADVERTENCIAS
        message += f"*⚠️ IMPORTANTE*\n"
        message += f"• Son sugerencias, no consejos financieros\n"
        message += f"• Verifica precios antes de operar\n"
        message += f"• No arriesgues más de lo que puedes perder\n\n"
        
        message += f"🤖 _Sistema automático de análisis_"
        
        return message
    
    def _format_basic_whatsapp_message(self, rules_analysis: Dict) -> str:
        """Mensaje básico cuando no hay análisis de Claude"""
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        metrics = rules_analysis.get('portfolio_metrics', {})
        
        message = f"*📊 RECOMENDACIONES BÁSICAS*\n"
        message += f"📅 {timestamp}\n"
        message += "=" * 25 + "\n\n"
        
        # Situación actual
        total_value = metrics.get('total_value', 0)
        total_pnl = metrics.get('total_pnl', 0)
        total_pnl_pct = metrics.get('total_pnl_pct', 0)
        
        message += f"*💼 TU SITUACIÓN*\n"
        message += f"💰 Total: ${total_value:,.0f}\n"
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        message += f"{pnl_emoji} Resultado: ${total_pnl:,.0f} ({total_pnl_pct:+.1f}%)\n\n"
        
        # Solo recomendaciones del sistema de reglas
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            message += f"*🎯 RECOMENDACIONES AUTOMÁTICAS*\n"
            message += "-" * 25 + "\n"
            
            for i, rec in enumerate(rules_recs, 1):
                ticker = rec.ticker
                action_type = rec.action.value
                shares = rec.suggested_shares
                price = rec.target_price
                
                if 'stop_loss' in action_type:
                    message += f"*{i}. PROTEGER:* Vender {ticker}\n"
                    message += f"📊 Todas las {shares} acciones\n"
                    message += f"💰 Si baja a ${price:.0f}\n"
                    message += f"❓ Para evitar más pérdidas\n\n"
                    
                elif 'rebalanceo' in action_type:
                    message += f"*{i}. BALANCEAR:* Reducir {ticker}\n"
                    message += f"📊 Vender {shares} acciones\n"
                    message += f"💰 Precio actual ${price:.0f}\n"
                    message += f"❓ Tienes demasiado en esta acción\n\n"
                    
                elif 'toma_ganancias' in action_type:
                    message += f"*{i}. GANAR:* Vender {ticker}\n"
                    message += f"📊 Vender {shares} acciones\n"
                    message += f"💰 Si sube a ${price:.0f}\n"
                    message += f"❓ Para asegurar ganancias\n\n"
        else:
            message += f"*✅ Tu cartera está estable*\n"
            message += f"No hay recomendaciones urgentes\n\n"
        
        message += f"*⚠️ NOTA*\n"
        message += f"El análisis avanzado no está disponible.\n"
        message += f"Estas son recomendaciones básicas.\n\n"
        
        message += f"🤖 _Sistema automático_"
        
        return message
    
    def send_immediate_alert(self, ticker: str, action: str, price: float, reason: str) -> bool:
        """Envía alerta inmediata específica"""
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        
        message = f"🚨 *ALERTA INMEDIATA*\n"
        message += f"⏰ {timestamp}\n\n"
        
        message += f"*{ticker}*\n"
        message += f"🎯 Acción: {action}\n"
        message += f"💰 Precio: ${price:.0f}\n"
        message += f"❓ Motivo: {reason}\n\n"
        
        message += f"⚠️ *Verificar precio antes de operar*"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """Prueba la conexión enviando un mensaje de test"""
        if not self.is_configured:
            return False
        
        test_message = f"🧪 *TEST SISTEMA*\n"
        test_message += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        test_message += f"✅ WhatsApp funcionando\n"
        test_message += f"📱 Recibirás recomendaciones aquí\n\n"
        test_message += f"Responde con ✅ si lo ves"
        
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
    
    def send_portfolio_analysis_message(self, rules_analysis: Dict, expert_analysis: Dict, combined: Dict) -> bool:
        """Envía análisis usando WhatsApp Web"""
        # Usar formato simplificado para WhatsApp Web
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        metrics = rules_analysis.get('portfolio_metrics', {})
        
        message = f"📊 RECOMENDACIONES - {timestamp}\n\n"
        
        # Resumen básico
        total_value = metrics.get('total_value', 0)
        total_pnl = metrics.get('total_pnl', 0)
        
        message += f"💰 Total: ${total_value:,.0f}\n"
        message += f"📈 P&L: ${total_pnl:,.0f}\n\n"
        
        # Recomendaciones básicas
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            for rec in rules_recs[:3]:  # Top 3
                ticker = rec.ticker
                action_type = rec.action.value
                shares = rec.suggested_shares
                
                if 'stop_loss' in action_type:
                    message += f"🔴 VENDER {ticker}: {shares} acciones\n"
                elif 'rebalanceo' in action_type:
                    message += f"⚖️ REDUCIR {ticker}: {shares} acciones\n"
                elif 'toma_ganancias' in action_type:
                    message += f"💰 GANAR {ticker}: {shares} acciones\n"
        else:
            message += "✅ Cartera estable\n"
        
        return self.send_message_instant(message)