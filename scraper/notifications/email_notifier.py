# scraper/notifications/email_notifier.py - Notificaciones mejoradas con análisis real
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List

class EmailNotifier:
    def __init__(self):
        # Configuración Gmail SMTP
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.from_email = os.getenv('EMAIL_FROM')
        self.from_password = os.getenv('EMAIL_PASSWORD')
        self.to_email = os.getenv('EMAIL_TO', 'mhv220@gmail.com')
        
        # Verificar configuración
        self.is_configured = bool(self.from_email and self.from_password)
        
        if not self.is_configured:
            print("⚠️ Email no configurado. Agrega las variables de entorno:")
            print("   EMAIL_SMTP_SERVER=smtp.gmail.com")
            print("   EMAIL_SMTP_PORT=587")
            print("   EMAIL_FROM=tu_email@gmail.com")
            print("   EMAIL_PASSWORD=tu_app_password")
            print("   EMAIL_TO=mhv220@gmail.com")
    
    def send_email(self, subject: str, body_text: str, body_html: str = None) -> bool:
        """Envía un email con contenido texto y HTML"""
        if not self.is_configured:
            print("❌ Email no configurado - no se puede enviar")
            return False
        
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            
            # Agregar contenido texto
            part_text = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(part_text)
            
            # Agregar contenido HTML si existe
            if body_html:
                part_html = MIMEText(body_html, 'html', 'utf-8')
                msg.attach(part_html)
            
            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.from_password)
                text = msg.as_string()
                server.sendmail(self.from_email, self.to_email, text)
            
            print("✅ Email enviado exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email: {str(e)}")
            return False
    
    def send_portfolio_analysis_email(self, rules_analysis: Dict, expert_analysis: Dict, combined: Dict) -> bool:
        """Envía análisis completo de cartera por email - MEJORADO"""
        try:
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            subject = f"📊 RECOMENDACIONES DE INVERSIÓN - {timestamp}"
            
            # Verificar si tenemos análisis real de Claude
            has_real_analysis = self._has_real_claude_analysis(expert_analysis)
            
            if not has_real_analysis:
                print("⚠️ No hay análisis real de Claude - enviando solo sistema de reglas")
                return self._send_rules_only_email(rules_analysis, timestamp)
            
            # Generar contenido con análisis real
            body_text = self._format_actionable_text_email(rules_analysis, expert_analysis, timestamp)
            body_html = self._format_actionable_html_email(rules_analysis, expert_analysis, timestamp)
            
            return self.send_email(subject, body_text, body_html)
            
        except Exception as e:
            print(f"❌ Error preparando email de análisis: {str(e)}")
            return False
    
    def _has_real_claude_analysis(self, expert_analysis: Dict) -> bool:
        """Verifica si tenemos análisis real de Claude (no fallback)"""
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        
        # Señales de que es análisis real:
        real_indicators = [
            'datos reales' in razonamiento.lower(),
            'indicadores calculados' in razonamiento.lower(),
            'rsi' in razonamiento.lower(),
            'macd' in razonamiento.lower(),
            len(razonamiento) > 100  # Análisis real es más detallado
        ]
        
        # También verificar si tiene análisis técnico por activo
        analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        has_technical_details = False
        if por_activo:
            for ticker, analysis in por_activo.items():
                rsi = analysis.get('rsi_analysis', '')
                if 'no_calculado' not in rsi and rsi != 'N/A':
                    has_technical_details = True
                    break
        
        return any(real_indicators) and has_technical_details
    
    def _send_rules_only_email(self, rules_analysis: Dict, timestamp: str) -> bool:
        """Envía email solo con análisis de reglas cuando Claude no responde"""
        subject = f"📊 RECOMENDACIONES BÁSICAS - {timestamp}"
        
        body_text = self._format_rules_only_text(rules_analysis, timestamp)
        body_html = self._format_rules_only_html(rules_analysis, timestamp)
        
        return self.send_email(subject, body_text, body_html)
    
    def _format_actionable_text_email(self, rules_analysis: Dict, expert_analysis: Dict, timestamp: str) -> str:
        """Formatea email ACCIONABLE en lenguaje simple"""
        metrics = rules_analysis['portfolio_metrics']
        
        email = f"""QUÉ HACER CON TUS INVERSIONES - {timestamp}
{'='*50}

TU SITUACIÓN ACTUAL
{'='*20}
💰 Total invertido: ${metrics['total_value']:,.0f}
📈 Ganancia/Pérdida: ${metrics['total_pnl']:,.0f} ({metrics['total_pnl_pct']:+.1f}%)
💵 Dinero disponible: ${metrics['total_value'] * metrics['cash_allocation']:,.0f}

"""

        # ACCIONES INMEDIATAS - EN LENGUAJE SIMPLE
        immediate_actions = expert_analysis.get('acciones_inmediatas', [])
        if immediate_actions:
            email += "🚨 HACER HOY (URGENTE)\n"
            email += "="*25 + "\n"
            
            for i, action in enumerate(immediate_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '')
                cantidad = action.get('cantidad', 0)
                precio = action.get('precio_objetivo', 0)
                razon = action.get('razon', '')
                
                if 'comprar' in accion.lower():
                    email += f"{i}. COMPRAR {ticker}\n"
                    email += f"   • Cantidad: {cantidad} acciones\n"
                    email += f"   • Precio máximo: ${precio:.0f} por acción\n"
                    email += f"   • Inversión total: ${cantidad * precio:,.0f}\n"
                    email += f"   • Por qué: {razon}\n\n"
                    
                elif 'vender' in accion.lower():
                    email += f"{i}. VENDER {ticker}\n"
                    email += f"   • Cantidad: {cantidad} acciones\n"
                    email += f"   • Precio mínimo: ${precio:.0f} por acción\n"
                    email += f"   • Por qué: {razon}\n\n"
        else:
            email += "✅ NO HAY ACCIONES URGENTES HOY\n\n"

        # ACCIONES PARA LOS PRÓXIMOS DÍAS
        short_term_actions = expert_analysis.get('acciones_corto_plazo', [])
        if short_term_actions:
            email += "📅 HACER EN LOS PRÓXIMOS DÍAS\n"
            email += "="*35 + "\n"
            
            for i, action in enumerate(short_term_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '')
                timeframe = action.get('timeframe', '')
                condiciones = action.get('condiciones', '')
                trigger_price = action.get('trigger_price')
                
                email += f"{i}. {ticker} - {accion.replace('_', ' ').title()}\n"
                email += f"   • Cuándo: {timeframe}\n"
                email += f"   • Condición: {condiciones}\n"
                if trigger_price:
                    email += f"   • Precio gatillo: ${float(trigger_price):,.0f}\n"
                email += "\n"

        # RECOMENDACIONES DE SISTEMA DE REGLAS (SIMPLIFICADAS)
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            email += "🎯 OTRAS RECOMENDACIONES\n"
            email += "="*25 + "\n"
            
            for i, rec in enumerate(rules_recs, 1):
                action_type = rec.action.value
                ticker = rec.ticker
                shares = rec.suggested_shares
                price = rec.target_price
                
                if 'stop_loss' in action_type:
                    email += f"{i}. PROTEGER PÉRDIDAS: Vender {ticker}\n"
                    email += f"   • Vender todas las {shares} acciones\n"
                    email += f"   • Precio: ${price:.0f} o menos\n"
                    email += f"   • Motivo: Evitar más pérdidas\n\n"
                    
                elif 'rebalanceo' in action_type:
                    email += f"{i}. BALANCEAR CARTERA: Reducir {ticker}\n"
                    email += f"   • Vender {shares} acciones\n"
                    email += f"   • Precio: ${price:.0f}\n"
                    email += f"   • Motivo: Tienes demasiado en esta acción\n\n"
                    
                elif 'toma_ganancias' in action_type:
                    email += f"{i}. TOMAR GANANCIAS: Vender {ticker}\n"
                    email += f"   • Vender {shares} acciones\n"
                    email += f"   • Precio: ${price:.0f} o más\n"
                    email += f"   • Motivo: Asegurar ganancias\n\n"

        # CONCLUSIÓN DEL EXPERTO (SOLO SI ES REAL)
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento and self._has_real_claude_analysis(expert_analysis):
            email += "🧠 ANÁLISIS DEL EXPERTO\n"
            email += "="*25 + "\n"
            email += f"{razonamiento}\n\n"

        # NIVELES DE STOP LOSS ESPECÍFICOS
        stop_losses = expert_analysis.get('gestion_riesgo', {}).get('stop_loss_sugeridos', {})
        if stop_losses:
            email += "🛡️ PROTECCIÓN AUTOMÁTICA\n"
            email += "="*25 + "\n"
            email += "Vende automáticamente si llegan a estos precios:\n\n"
            
            for ticker, stop_price in stop_losses.items():
                try:
                    precio_stop = float(stop_price)
                    email += f"• {ticker}: Vender si baja a ${precio_stop:.0f}\n"
                except:
                    email += f"• {ticker}: Vender si baja a {stop_price}\n"

        email += f"\n{'='*50}\n"
        email += "⚠️ IMPORTANTE:\n"
        email += "• Estas son sugerencias, no consejos financieros\n"
        email += "• Siempre verifica los precios antes de operar\n"
        email += "• No inviertas más de lo que puedes permitirte perder\n"
        email += "• Consulta con un asesor si tienes dudas\n\n"
        email += "🤖 Generado automáticamente por tu sistema de análisis"
        
        return email
    
    def _format_actionable_html_email(self, rules_analysis: Dict, expert_analysis: Dict, timestamp: str) -> str:
        """Formatea email HTML ACCIONABLE y simple"""
        metrics = rules_analysis['portfolio_metrics']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; line-height: 1.6; }}
                .container {{ background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 800px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
                .section {{ margin: 25px 0; }}
                .section h2 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; font-size: 20px; }}
                .action-card {{ background-color: #fff; border: 2px solid #e74c3c; padding: 20px; margin: 15px 0; border-radius: 10px; }}
                .buy-card {{ border-color: #27ae60; background-color: #f8fff8; }}
                .sell-card {{ border-color: #e74c3c; background-color: #fff8f8; }}
                .watch-card {{ border-color: #f39c12; background-color: #fffbf0; }}
                .metric {{ display: inline-block; margin: 15px; padding: 15px; background: linear-gradient(135deg, #74b9ff, #0984e3); color: white; border-radius: 10px; text-align: center; min-width: 140px; }}
                .positive {{ color: #27ae60; font-weight: bold; }}
                .negative {{ color: #e74c3c; font-weight: bold; }}
                .action-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
                .action-details {{ font-size: 14px; }}
                .price {{ font-size: 16px; font-weight: bold; color: #2c3e50; }}
                .warning {{ background-color: #fff3cd; border: 2px solid #ffeaa7; padding: 20px; border-radius: 10px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #636e72; font-size: 14px; }}
                .urgency-high {{ border-left: 6px solid #e74c3c; }}
                .urgency-medium {{ border-left: 6px solid #f39c12; }}
                .urgency-low {{ border-left: 6px solid #27ae60; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 TUS RECOMENDACIONES DE INVERSIÓN</h1>
                    <p style="font-size: 18px; margin: 0;">{timestamp}</p>
                </div>
                
                <div class="section">
                    <h2>💼 Tu Situación Actual</h2>
                    <div style="text-align: center;">
                        <div class="metric">
                            <strong>TOTAL</strong><br>
                            ${metrics['total_value']:,.0f}
                        </div>
                        <div class="metric">
                            <strong>GANANCIA/PÉRDIDA</strong><br>
                            <span class="{'positive' if metrics['total_pnl'] >= 0 else 'negative'}">${metrics['total_pnl']:,.0f}</span><br>
                            <small>({metrics['total_pnl_pct']:+.1f}%)</small>
                        </div>
                        <div class="metric">
                            <strong>DISPONIBLE</strong><br>
                            ${metrics['total_value'] * metrics['cash_allocation']:,.0f}
                        </div>
                    </div>
                </div>"""

        # ACCIONES INMEDIATAS CON LENGUAJE SIMPLE
        immediate_actions = expert_analysis.get('acciones_inmediatas', [])
        if immediate_actions:
            html += """
                <div class="section">
                    <h2>🚨 QUÉ HACER HOY (Urgente)</h2>"""
            
            for i, action in enumerate(immediate_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '')
                cantidad = action.get('cantidad', 0)
                precio = action.get('precio_objetivo', 0)
                razon = action.get('razon', '')
                urgencia = action.get('urgencia', 'media')
                
                urgency_class = f"urgency-{urgencia}"
                
                if 'comprar' in accion.lower():
                    card_class = "action-card buy-card"
                    action_text = f"COMPRAR {ticker}"
                    details = f"""
                        <div class="action-details">
                            <strong>Cantidad:</strong> {cantidad} acciones<br>
                            <strong>Precio máximo:</strong> <span class="price">${precio:.0f}</span> por acción<br>
                            <strong>Inversión total:</strong> <span class="price">${cantidad * precio:,.0f}</span><br>
                            <strong>Por qué:</strong> {razon}
                        </div>"""
                        
                elif 'vender' in accion.lower():
                    card_class = "action-card sell-card"
                    action_text = f"VENDER {ticker}"
                    details = f"""
                        <div class="action-details">
                            <strong>Cantidad:</strong> {cantidad} acciones<br>
                            <strong>Precio mínimo:</strong> <span class="price">${precio:.0f}</span> por acción<br>
                            <strong>Por qué:</strong> {razon}
                        </div>"""
                else:
                    card_class = "action-card watch-card"
                    action_text = f"MONITOREAR {ticker}"
                    details = f"""
                        <div class="action-details">
                            <strong>Acción:</strong> {accion}<br>
                            <strong>Por qué:</strong> {razon}
                        </div>"""
                
                html += f"""
                    <div class="{card_class} {urgency_class}">
                        <div class="action-title">{i}. {action_text}</div>
                        {details}
                    </div>"""
            
            html += "</div>"
        else:
            html += """
                <div class="section">
                    <div style="text-align: center; padding: 20px; background-color: #d4edda; border-radius: 10px;">
                        <h3 style="color: #155724; margin: 0;">✅ No hay acciones urgentes hoy</h3>
                        <p style="color: #155724; margin: 10px 0 0 0;">Tu cartera está estable por ahora</p>
                    </div>
                </div>"""

        # ACCIONES PARA PRÓXIMOS DÍAS
        short_term_actions = expert_analysis.get('acciones_corto_plazo', [])
        if short_term_actions:
            html += """
                <div class="section">
                    <h2>📅 Para los Próximos Días</h2>"""
            
            for i, action in enumerate(short_term_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '').replace('_', ' ').title()
                timeframe = action.get('timeframe', '')
                condiciones = action.get('condiciones', '')
                trigger_price = action.get('trigger_price')
                
                html += f"""
                    <div class="action-card watch-card">
                        <div class="action-title">{i}. {ticker} - {accion}</div>
                        <div class="action-details">
                            <strong>Cuándo:</strong> {timeframe}<br>
                            <strong>Condición:</strong> {condiciones}<br>"""
                
                if trigger_price:
                    html += f"<strong>Precio gatillo:</strong> <span class='price'>${float(trigger_price):,.0f}</span><br>"
                
                html += "</div></div>"
            
            html += "</div>"

        # NIVELES DE PROTECCIÓN
        stop_losses = expert_analysis.get('gestion_riesgo', {}).get('stop_loss_sugeridos', {})
        if stop_losses:
            html += """
                <div class="section">
                    <h2>🛡️ Niveles de Protección</h2>
                    <p style="color: #636e72;">Vende automáticamente si tus acciones bajan a estos precios para proteger tu dinero:</p>"""
            
            for ticker, stop_price in stop_losses.items():
                try:
                    precio_stop = float(stop_price)
                    html += f"""
                        <div style="background-color: #fff5f5; border: 1px solid #feb2b2; padding: 15px; margin: 10px 0; border-radius: 8px;">
                            <strong>{ticker}:</strong> Vender si baja a <span class="price">${precio_stop:.0f}</span>
                        </div>"""
                except:
                    html += f"""
                        <div style="background-color: #fff5f5; border: 1px solid #feb2b2; padding: 15px; margin: 10px 0; border-radius: 8px;">
                            <strong>{ticker}:</strong> Vender si baja a {stop_price}
                        </div>"""
            
            html += "</div>"

        # ANÁLISIS DEL EXPERTO (SOLO SI ES REAL)
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento and self._has_real_claude_analysis(expert_analysis):
            html += f"""
                <div class="section">
                    <h2>🧠 Lo que Dice el Experto</h2>
                    <div style="background-color: #e8f4fd; padding: 20px; border-radius: 10px; border-left: 6px solid #3498db;">
                        <p style="margin: 0; font-size: 16px; color: #2c3e50;">{razonamiento}</p>
                    </div>
                </div>"""

        # INDICADORES TÉCNICOS EN LENGUAJE SIMPLE
        analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        if por_activo:
            html += """
                <div class="section">
                    <h2>📈 Estado Técnico de tus Acciones</h2>
                    <div style="font-size: 14px; color: #636e72; margin-bottom: 15px;">
                        Basado en análisis técnico profesional (RSI, MACD, etc.)
                    </div>"""
            
            for ticker, analysis in por_activo.items():
                momentum = analysis.get('momentum', 'neutral')
                rsi_analysis = analysis.get('rsi_analysis', '')
                recomendacion = analysis.get('recomendacion', '')
                
                # Simplificar el momentum para lenguaje común
                if momentum == 'alcista':
                    momentum_text = "📈 Subiendo"
                    momentum_color = "#27ae60"
                elif momentum == 'bajista':
                    momentum_text = "📉 Bajando" 
                    momentum_color = "#e74c3c"
                else:
                    momentum_text = "➡️ Estable"
                    momentum_color = "#636e72"
                
                # Simplificar RSI
                rsi_simple = ""
                if 'sobrecomprado' in rsi_analysis:
                    rsi_simple = "Muy caro ahora"
                elif 'sobrevendido' in rsi_analysis:
                    rsi_simple = "Posible oportunidad de compra"
                else:
                    rsi_simple = "Precio normal"
                
                html += f"""
                    <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; background-color: #fafafa;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="font-size: 16px;">{ticker}</strong>
                            <span style="color: {momentum_color}; font-weight: bold;">{momentum_text}</span>
                        </div>
                        <div style="margin-top: 10px; font-size: 14px; color: #636e72;">
                            <strong>Análisis:</strong> {rsi_simple}<br>
                            <strong>Recomendación:</strong> {recomendacion}
                        </div>
                    </div>"""
            
            html += "</div>"

        # ADVERTENCIAS IMPORTANTES
        html += """
                <div class="warning">
                    <h3 style="margin-top: 0; color: #856404;">⚠️ Importante Leer</h3>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>Estas son sugerencias</strong>, no consejos financieros profesionales</li>
                        <li><strong>Siempre verifica los precios</strong> antes de hacer cualquier operación</li>
                        <li><strong>No inviertas más</strong> de lo que puedes permitirte perder</li>
                        <li><strong>Si tienes dudas</strong>, consulta con un asesor financiero</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p><strong>🤖 Generado automáticamente por tu sistema de análisis</strong></p>
                    <p><em>Sistema híbrido: Reglas automatizadas + Análisis de inteligencia artificial</em></p>
                </div>
            </div>
        </body>
        </html>"""
        
        return html
    
    def _format_rules_only_text(self, rules_analysis: Dict, timestamp: str) -> str:
        """Email solo con reglas cuando Claude no funciona"""
        metrics = rules_analysis['portfolio_metrics']
        
        email = f"""RECOMENDACIONES BÁSICAS - {timestamp}
{'='*40}

TU SITUACIÓN ACTUAL
{'='*20}
💰 Total: ${metrics['total_value']:,.0f}
📈 Ganancia/Pérdida: ${metrics['total_pnl']:,.0f} ({metrics['total_pnl_pct']:+.1f}%)

⚠️ NOTA: El análisis avanzado no está disponible temporalmente.
Estas son recomendaciones básicas del sistema de reglas:

"""
        
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            for i, rec in enumerate(rules_recs, 1):
                ticker = rec.ticker
                action_type = rec.action.value
                shares = rec.suggested_shares
                
                if 'stop_loss' in action_type:
                    email += f"{i}. VENDER {ticker} - Proteger de más pérdidas\n"
                elif 'rebalanceo' in action_type:
                    email += f"{i}. REDUCIR {ticker} - Balancear cartera\n"
                elif 'toma_ganancias' in action_type:
                    email += f"{i}. VENDER {ticker} - Asegurar ganancias\n"
                
                email += f"   • Cantidad: {shares} acciones\n"
                email += f"   • Confianza: {rec.confidence:.0f}%\n\n"
        else:
            email += "✅ No hay recomendaciones urgentes por ahora\n"
        
        email += "\n🤖 Sistema básico - El análisis completo estará disponible pronto"
        return email
    
    def _format_rules_only_html(self, rules_analysis: Dict, timestamp: str) -> str:
        """HTML solo con reglas cuando Claude no funciona"""
        metrics = rules_analysis['portfolio_metrics']
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background-color: #fff3cd; border: 2px solid #ffeaa7; padding: 20px; border-radius: 10px;">
                <h2 style="color: #856404;">📊 RECOMENDACIONES BÁSICAS - {timestamp}</h2>
                <p><strong>💰 Total:</strong> ${metrics['total_value']:,.0f}</p>
                <p><strong>📈 P&L:</strong> ${metrics['total_pnl']:,.0f} ({metrics['total_pnl_pct']:+.1f}%)</p>
                
                <h3>⚠️ Análisis avanzado temporalmente no disponible</h3>
                <p>Recomendaciones básicas del sistema de reglas:</p>"""
        
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            for i, rec in enumerate(rules_recs, 1):
                ticker = rec.ticker
                action_type = rec.action.value
                shares = rec.suggested_shares
                
                if 'stop_loss' in action_type:
                    action_text = f"VENDER {ticker} - Proteger de más pérdidas"
                elif 'rebalanceo' in action_type:
                    action_text = f"REDUCIR {ticker} - Balancear cartera"
                elif 'toma_ganancias' in action_type:
                    action_text = f"VENDER {ticker} - Asegurar ganancias"
                else:
                    action_text = f"{action_type.replace('_', ' ').title()} {ticker}"
                
                html += f"""
                <div style="border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <strong>{i}. {action_text}</strong><br>
                    <small>Cantidad: {shares} acciones | Confianza: {rec.confidence:.0f}%</small>
                </div>"""
        else:
            html += "<p>✅ No hay recomendaciones urgentes por ahora</p>"
        
        html += """
                <hr>
                <p style="text-align: center; color: #636e72;">
                    🤖 El análisis completo estará disponible pronto
                </p>
            </div>
        </body>
        </html>"""
        
        return html
    
    def test_connection(self) -> bool:
        """Prueba la conexión enviando un email de test"""
        if not self.is_configured:
            return False
        
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        subject = "🧪 TEST BALANZ SCRAPER"
        
        body_text = f"""TEST BALANZ SCRAPER - {timestamp}
{'='*30}

✅ Email configurado correctamente
📧 Recibirás notificaciones de análisis aquí
🔧 Sistema funcionando normalmente

Este es un mensaje de prueba para verificar que el sistema de email funciona correctamente."""
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background-color: #e8f5e8; border: 2px solid #4caf50; padding: 20px; border-radius: 10px;">
                <h2 style="color: #2e7d32;">🧪 TEST BALANZ SCRAPER</h2>
                <p><strong>Fecha:</strong> {timestamp}</p>
                <p>✅ <strong>Email configurado correctamente</strong></p>
                <p>📧 Recibirás notificaciones de análisis aquí</p>
                <p>🔧 Sistema funcionando normalmente</p>
                <hr>
                <p><em>Este es un mensaje de prueba para verificar que el sistema de email funciona correctamente.</em></p>
            </div>
        </body>
        </html>"""
        
        return self.send_email(subject, body_text, body_html)