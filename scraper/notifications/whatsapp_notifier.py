# scraper/notifications/whatsapp_notifier.py - VERSIÓN MEJORADA SOLO ACCIONABLES
import os
from datetime import datetime
from typing import List, Dict
import requests

class WhatsAppNotifier:
    def __init__(self):
        # Configuración de Twilio WhatsApp
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        self.target_number = os.getenv('WHATSAPP_TARGET_NUMBER', 'whatsapp:+5491157658736')
        self.twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        # Verificar configuración
        self.is_configured = bool(self.account_sid and self.auth_token)
        
        if not self.is_configured:
            print("⚠️ WhatsApp no configurado")
    
    def send_message(self, message: str) -> bool:
        """Envía un mensaje por WhatsApp usando Twilio"""
        if not self.is_configured:
            print("❌ WhatsApp no configurado")
            return False
        
        try:
            # Dividir mensaje si es muy largo
            if len(message) > 1500:
                return self._send_long_message_in_parts(message)
            
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
            
            if response.status_code == 201:
                print("✅ WhatsApp enviado exitosamente")
                return True
            else:
                print(f"❌ Error WhatsApp: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error enviando WhatsApp: {str(e)}")
            return False
    
    def _send_long_message_in_parts(self, message: str) -> bool:
        """Divide mensajes largos en partes"""
        try:
            parts = []
            current_part = ""
            lines = message.split('\n')
            
            for line in lines:
                if len(current_part + line + '\n') > 1400:
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = ""
                current_part += line + '\n'
            
            if current_part:
                parts.append(current_part.strip())
            
            success_count = 0
            for i, part in enumerate(parts, 1):
                header = f"*PARTE {i}/{len(parts)}*\n\n" if len(parts) > 1 else ""
                full_part = header + part
                
                if self._send_single_message(full_part):
                    success_count += 1
                    if i < len(parts):
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
        """Envía mensaje MEJORADO de WhatsApp - Solo accionables claros"""
        try:
            # Extraer información real de la cartera
            portfolio_info = self._extract_portfolio_info_whatsapp(rules_analysis, expert_analysis)
            
            # Verificar si tenemos análisis real de Claude
            if self._has_real_claude_analysis(expert_analysis):
                message = self._create_actionable_whatsapp_message(portfolio_info, expert_analysis)
            else:
                message = self._create_basic_whatsapp_message(portfolio_info, rules_analysis)
            
            return self.send_message(message)
            
        except Exception as e:
            print(f"❌ Error preparando WhatsApp: {str(e)}")
            return False
    
    def _extract_portfolio_info_whatsapp(self, rules_analysis: Dict, expert_analysis: Dict) -> Dict:
        """Extrae información de cartera para WhatsApp"""
        portfolio_info = {
            'total_value': 0,
            'available_cash': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'positions': []
        }
        
        try:
            metrics = rules_analysis.get('portfolio_metrics', {})
            portfolio_info['total_value'] = metrics.get('total_value', 0)
            portfolio_info['total_pnl'] = metrics.get('total_pnl', 0)
            portfolio_info['total_pnl_pct'] = metrics.get('total_pnl_pct', 0)
            portfolio_info['available_cash'] = portfolio_info['total_value'] * metrics.get('cash_allocation', 0)
            
            # Posiciones actuales
            positions_analysis = rules_analysis.get('positions_analysis', [])
            for pos in positions_analysis:
                portfolio_info['positions'].append({
                    'ticker': pos.ticker,
                    'current_shares': pos.current_shares,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_pct': pos.unrealized_pnl_pct
                })
            
            return portfolio_info
            
        except Exception as e:
            print(f"⚠️ Error extrayendo info WhatsApp: {str(e)}")
            return portfolio_info
    
    def _has_real_claude_analysis(self, expert_analysis: Dict) -> bool:
        """Verifica si hay análisis real de Claude"""
        if not expert_analysis:
            return False
        
        analysis_source = expert_analysis.get('analysis_source', 'real')
        claude_available = expert_analysis.get('claude_api_available', True)
        
        if analysis_source in ['minimal_fallback', 'error_fallback'] or not claude_available:
            return False
        
        # Verificar análisis técnico real
        analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        return len(por_activo) > 0 and any(
            analysis.get('rsi_analysis', '') and 'no_calculado' not in analysis.get('rsi_analysis', '').lower()
            for analysis in por_activo.values()
        )
    
    def _create_actionable_whatsapp_message(self, portfolio_info: Dict, expert_analysis: Dict) -> str:
        """WhatsApp con acciones claras basadas en datos reales"""
        
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        
        message = f"*🎯 QUÉ HACER HOY*\n"
        message += f"📅 {timestamp}\n"
        message += "="*25 + "\n\n"
        
        # Situación actual
        pnl_emoji = "📈" if portfolio_info['total_pnl'] >= 0 else "📉"
        message += f"*💼 TU CARTERA*\n"
        message += f"💰 Total: ${portfolio_info['total_value']:,.0f}\n"
        message += f"{pnl_emoji} Resultado: ${portfolio_info['total_pnl']:,.0f} ({portfolio_info['total_pnl_pct']:+.1f}%)\n"
        message += f"💵 Disponible: ${portfolio_info['available_cash']:,.0f}\n\n"
        
        # Posiciones actuales (resumidas)
        if len(portfolio_info['positions']) <= 5:  # Solo si no son muchas
            message += f"*📋 TUS POSICIONES*\n"
            for pos in portfolio_info['positions']:
                pnl_emoji = "🟢" if pos['unrealized_pnl'] >= 0 else "🔴"
                message += f"{pnl_emoji} {pos['ticker']}: {pos['current_shares']} a ${pos['current_price']:.0f} ({pos['unrealized_pnl_pct']:+.1f}%)\n"
            message += "\n"
        
        # Acciones INMEDIATAS con datos específicos
        immediate_actions = expert_analysis.get('acciones_inmediatas', [])
        if immediate_actions:
            message += f"*🚨 HACER HOY*\n"
            message += "-"*15 + "\n"
            
            for i, action in enumerate(immediate_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '').upper()
                cantidad = action.get('cantidad', 0)
                precio_objetivo = action.get('precio_objetivo', 0)
                razon = action.get('razon', '')
                
                if 'COMPRAR' in accion:
                    inversion = cantidad * precio_objetivo
                    message += f"*{i}. COMPRAR {ticker}*\n"
                    message += f"📊 {cantidad} nominales máx ${precio_objetivo:.0f}\n"
                    message += f"💰 Invertir: ${inversion:,.0f}\n"
                    # Resumir razón para WhatsApp
                    razon_corta = razon[:60] + "..." if len(razon) > 60 else razon
                    message += f"💡 {razon_corta}\n\n"
                    
                elif 'VENDER' in accion:
                    # Encontrar posición actual
                    current_pos = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                    shares_text = f"{cantidad}"
                    if current_pos:
                        shares_text += f" de tus {current_pos['current_shares']}"
                    
                    message += f"*{i}. VENDER {ticker}*\n"
                    message += f"📊 {shares_text} nominales mín ${precio_objetivo:.0f}\n"
                    message += f"💰 Recibirás: ${cantidad * precio_objetivo:,.0f}\n"
                    razon_corta = razon[:60] + "..." if len(razon) > 60 else razon
                    message += f"💡 {razon_corta}\n\n"
        else:
            message += f"*✅ No hay acciones urgentes hoy*\n\n"
        
        # Stops importantes (solo los más críticos)
        stop_losses = expert_analysis.get('gestion_riesgo', {}).get('stop_loss_sugeridos', {})
        critical_stops = []
        for ticker, stop_price in stop_losses.items():
            current_pos = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
            if current_pos and current_pos['unrealized_pnl'] < 0:  # Solo stops para posiciones en pérdida
                try:
                    stop_float = float(stop_price)
                    critical_stops.append(f"• {ticker}: Vender TODAS si baja a ${stop_float:.0f}")
                except:
                    critical_stops.append(f"• {ticker}: Vender si baja a {stop_price}")
        
        if critical_stops:
            message += f"*🛡️ PROTECCIÓN*\n"
            for stop in critical_stops[:3]:  # Máximo 3 stops
                message += f"{stop}\n"
            message += "\n"
        
        # Próximas acciones (resumidas)
        short_term = expert_analysis.get('acciones_corto_plazo', [])
        if short_term and len(short_term) <= 2:  # Solo si son pocas
            message += f"*📅 PRÓXIMOS DÍAS*\n"
            for action in short_term:
                ticker = action.get('ticker', 'N/A')
                timeframe = action.get('timeframe', '')
                trigger = action.get('trigger_price')
                if trigger:
                    message += f"• {ticker}: Vigilar ${float(trigger):.0f} ({timeframe})\n"
                else:
                    message += f"• {ticker}: {timeframe}\n"
            message += "\n"
        
        # Footer conciso
        message += f"*⚠️ Verifica precios antes de operar*\n"
        message += f"🤖 _Análisis integral automático_"
        
        return message
    
    def _create_basic_whatsapp_message(self, portfolio_info: Dict, rules_analysis: Dict) -> str:
        """WhatsApp básico cuando no hay Claude"""
        
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        
        message = f"*📊 RECOMENDACIONES BÁSICAS*\n"
        message += f"📅 {timestamp}\n"
        message += "="*30 + "\n\n"
        
        # Situación actual
        pnl_emoji = "📈" if portfolio_info['total_pnl'] >= 0 else "📉"
        message += f"*💼 TU CARTERA*\n"
        message += f"💰 Total: ${portfolio_info['total_value']:,.0f}\n"
        message += f"{pnl_emoji} Resultado: ${portfolio_info['total_pnl']:,.0f} ({portfolio_info['total_pnl_pct']:+.1f}%)\n"
        message += f"💵 Disponible: ${portfolio_info['available_cash']:,.0f}\n\n"
        
        # Solo recomendaciones del sistema de reglas
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            message += f"*🎯 RECOMENDACIONES*\n"
            message += "-"*20 + "\n"
            
            for i, rec in enumerate(rules_recs[:3], 1):  # Máximo 3
                ticker = rec.ticker
                action_type = rec.action.value
                shares = rec.suggested_shares
                price = rec.target_price
                
                # Buscar posición actual
                current_pos = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                
                if 'stop_loss' in action_type:
                    shares_text = f"TODAS las {current_pos['current_shares']}" if current_pos else f"{shares}"
                    message += f"*{i}. PROTEGER {ticker}*\n"
                    message += f"🚨 Vender {shares_text} si baja a ${price:.0f}\n"
                    message += f"🔥 Confianza: {rec.confidence:.0f}%\n\n"
                    
                elif 'toma_ganancias' in action_type:
                    shares_text = f"{shares} de {current_pos['current_shares']}" if current_pos else f"{shares}"
                    message += f"*{i}. GANAR {ticker}*\n"
                    message += f"💰 Vender {shares_text} a ${price:.0f}+\n"
                    message += f"🔥 Confianza: {rec.confidence:.0f}%\n\n"
                    
                elif 'rebalanceo' in action_type:
                    shares_text = f"{shares} de {current_pos['current_shares']}" if current_pos else f"{shares}"
                    message += f"*{i}. BALANCEAR {ticker}*\n"
                    message += f"⚖️ Reducir {shares_text} nominales\n"
                    message += f"💰 Precio: ${price:.0f}\n\n"
        else:
            message += f"*✅ Cartera estable*\n"
            message += f"Sin recomendaciones urgentes\n\n"
        
        message += f"*⚠️ NOTA*\n"
        message += f"Análisis avanzado temporalmente no disponible\n\n"
        message += f"🤖 _Sistema automático_"
        
        return message
    
    def test_connection(self) -> bool:
        """Prueba la conexión"""
        if not self.is_configured:
            return False
        
        test_message = f"🧪 *TEST SISTEMA MEJORADO*\n"
        test_message += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        test_message += f"✅ WhatsApp funcionando\n"
        test_message += f"🎯 Recibirás recomendaciones accionables\n\n"
        test_message += f"Responde ✅ si lo ves"
        
        return self.send_message(test_message)