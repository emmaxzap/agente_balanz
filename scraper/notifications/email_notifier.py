# scraper/notifications/email_notifier.py - Notificaciones por Email
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
        """Envía análisis completo de cartera por email"""
        try:
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            subject = f"📊 ANÁLISIS BALANZ - {timestamp}"
            
            # Generar contenido texto y HTML
            body_text = self._format_text_email(rules_analysis, expert_analysis, combined, timestamp)
            body_html = self._format_html_email(rules_analysis, expert_analysis, combined, timestamp)
            
            return self.send_email(subject, body_text, body_html)
            
        except Exception as e:
            print(f"❌ Error preparando email de análisis: {str(e)}")
            return False
    
    def _format_text_email(self, rules_analysis: Dict, expert_analysis: Dict, combined: Dict, timestamp: str) -> str:
        """Formatea email en texto plano"""
        metrics = rules_analysis['portfolio_metrics']
        positions = rules_analysis['positions_analysis']
        
        email = f"""ANÁLISIS HÍBRIDO BALANZ - {timestamp}
{'='*50}

RESUMEN DE CARTERA
{'='*20}
💰 Valor Total: ${metrics['total_value']:,.2f}
📈 P&L Total: ${metrics['total_pnl']:,.2f} ({metrics['total_pnl_pct']:+.1f}%)
💵 Efectivo: {metrics['cash_allocation']:.1%}
⏱️ Días Promedio Tenencia: {metrics['risk_metrics']['avg_days_held']:.1f}
📊 Cantidad Activos: {len(positions)}

DETALLE DE POSICIONES
{'='*25}"""

        for position in positions:
            pnl_symbol = "+" if position.unrealized_pnl >= 0 else ""
            email += f"""
- {position.ticker}: {position.current_shares} nominales
  Valor: ${position.current_value:,.2f}
  P&L: ${pnl_symbol}{position.unrealized_pnl:,.2f} ({position.unrealized_pnl_pct:+.1f}%)
  Días: {position.days_held} | Tamaño: {position.position_size_pct:.1%}
  Sector: {position.sector.title()}"""

        # Sistema de reglas
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            email += f"\n\nSISTEMA DE REGLAS - RECOMENDACIONES\n{'='*35}\n"
            
            for rec in rules_recs:
                action_name = rec.action.value.replace('_', ' ').title()
                email += f"• {rec.ticker}: {action_name} {rec.suggested_shares} nominales\n"
                email += f"  Confianza: {rec.confidence:.0f}%\n"
                email += f"  Razón: {rec.reasons[0] if rec.reasons else 'No especificada'}\n\n"
        
        # Agente experto
        expert_immediate = expert_analysis.get('acciones_inmediatas', [])
        expert_short = expert_analysis.get('acciones_corto_plazo', [])
        
        if expert_immediate or expert_short:
            email += f"AGENTE EXPERTO - RECOMENDACIONES\n{'='*30}\n"
            
            if expert_immediate:
                email += "🚨 ACCIONES INMEDIATAS:\n"
                for action in expert_immediate:
                    email += f"• {action.get('ticker', 'N/A')}: {action.get('accion', 'N/A')}\n"
                    email += f"  Urgencia: {action.get('urgencia', 'media')}\n"
                    email += f"  Razón: {action.get('razon', 'No especificada')}\n\n"
            
            if expert_short:
                email += "📅 ACCIONES CORTO PLAZO:\n"
                for action in expert_short:
                    email += f"• {action.get('ticker', 'N/A')}: {action.get('accion', 'N/A')}\n"
                    email += f"  Timeframe: {action.get('timeframe', 'No especificado')}\n"
                    email += f"  Condiciones: {action.get('condiciones', 'No especificadas')}\n\n"
        
        # Evaluación de riesgo
        risk = expert_analysis.get('gestion_riesgo', {})
        if risk:
            email += f"EVALUACIÓN DE RIESGO\n{'='*20}\n"
            email += f"Nivel de Riesgo: {risk.get('riesgo_cartera', 'N/A')}/10\n"
            concentraciones = risk.get('concentraciones_riesgo', [])
            if concentraciones:
                email += "Factores de Riesgo:\n"
                for riesgo in concentraciones[:3]:
                    email += f"• {riesgo}\n"
        
        # Razonamiento
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento:
            email += f"\nCONCLUSIÓN DEL EXPERTO\n{'='*25}\n"
            email += f"{razonamiento}\n"
        
        email += f"\n{'='*50}\n"
        email += "🤖 Generado automáticamente por Balanz Scraper\n"
        email += "⚠️ Verificar precios antes de ejecutar operaciones"
        
        return email
    
    def _format_html_email(self, rules_analysis: Dict, expert_analysis: Dict, combined: Dict, timestamp: str) -> str:
        """Formatea email en HTML con estilos"""
        metrics = rules_analysis['portfolio_metrics']
        positions = rules_analysis['positions_analysis']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .header {{ background-color: #2c3e50; color: white; padding: 15px; border-radius: 5px; text-align: center; }}
                .section {{ margin: 20px 0; }}
                .section h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #ecf0f1; border-radius: 5px; }}
                .positive {{ color: #27ae60; font-weight: bold; }}
                .negative {{ color: #e74c3c; font-weight: bold; }}
                .neutral {{ color: #7f8c8d; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #3498db; color: white; }}
                .recommendation {{ background-color: #fff3cd; border: 1px solid #ffeeba; padding: 10px; margin: 5px 0; border-radius: 5px; }}
                .urgent {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
                .footer {{ text-align: center; margin-top: 20px; color: #7f8c8d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 ANÁLISIS HÍBRIDO BALANZ</h1>
                    <p>{timestamp}</p>
                </div>
                
                <div class="section">
                    <h2>💼 Resumen de Cartera</h2>
                    <div class="metric">💰 Valor Total: <strong>${metrics['total_value']:,.2f}</strong></div>
                    <div class="metric">📈 P&L: <span class="{'positive' if metrics['total_pnl'] >= 0 else 'negative'}">${metrics['total_pnl']:,.2f} ({metrics['total_pnl_pct']:+.1f}%)</span></div>
                    <div class="metric">💵 Efectivo: <strong>{metrics['cash_allocation']:.1%}</strong></div>
                    <div class="metric">⏱️ Días Promedio: <strong>{metrics['risk_metrics']['avg_days_held']:.1f}</strong></div>
                </div>
                
                <div class="section">
                    <h2>📋 Detalle de Posiciones</h2>
                    <table>
                        <tr>
                            <th>Ticker</th>
                            <th>Nominales</th>
                            <th>Valor Actual</th>
                            <th>P&L</th>
                            <th>%</th>
                            <th>Días</th>
                            <th>Sector</th>
                        </tr>"""
        
        for position in positions:
            pnl_class = "positive" if position.unrealized_pnl >= 0 else "negative"
            html += f"""
                        <tr>
                            <td><strong>{position.ticker}</strong></td>
                            <td>{position.current_shares:,}</td>
                            <td>${position.current_value:,.2f}</td>
                            <td class="{pnl_class}">${position.unrealized_pnl:,.2f}</td>
                            <td class="{pnl_class}">{position.unrealized_pnl_pct:+.1f}%</td>
                            <td>{position.days_held}</td>
                            <td>{position.sector.title()}</td>
                        </tr>"""
        
        html += """
                    </table>
                </div>"""
        
        # Sistema de reglas
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            html += """
                <div class="section">
                    <h2>📊 Sistema de Reglas - Recomendaciones</h2>"""
            
            for rec in rules_recs:
                action_name = rec.action.value.replace('_', ' ').title()
                urgency_class = "urgent" if "stop" in rec.action.value.lower() else "recommendation"
                html += f"""
                    <div class="{urgency_class}">
                        <strong>{rec.ticker}</strong>: {action_name} {rec.suggested_shares} nominales<br>
                        <small>Confianza: {rec.confidence:.0f}% | {rec.reasons[0] if rec.reasons else 'No especificada'}</small>
                    </div>"""
            
            html += "</div>"
        
        # Agente experto
        expert_immediate = expert_analysis.get('acciones_inmediatas', [])
        expert_short = expert_analysis.get('acciones_corto_plazo', [])
        
        if expert_immediate or expert_short:
            html += """
                <div class="section">
                    <h2>🤖 Agente Experto - Recomendaciones</h2>"""
            
            if expert_immediate:
                html += "<h3>🚨 Acciones Inmediatas</h3>"
                for action in expert_immediate:
                    html += f"""
                    <div class="urgent">
                        <strong>{action.get('ticker', 'N/A')}</strong>: {action.get('accion', 'N/A')}<br>
                        <small>Urgencia: {action.get('urgencia', 'media')} | {action.get('razon', 'No especificada')}</small>
                    </div>"""
            
            if expert_short:
                html += "<h3>📅 Acciones Corto Plazo</h3>"
                for action in expert_short:
                    html += f"""
                    <div class="recommendation">
                        <strong>{action.get('ticker', 'N/A')}</strong>: {action.get('accion', 'N/A')}<br>
                        <small>{action.get('timeframe', 'No especificado')} | {action.get('condiciones', 'No especificadas')}</small>
                    </div>"""
            
            html += "</div>"
        
        # Evaluación de riesgo
        risk = expert_analysis.get('gestion_riesgo', {})
        if risk:
            risk_level = risk.get('riesgo_cartera', 5)
            risk_color = "negative" if risk_level >= 7 else "positive" if risk_level <= 3 else "neutral"
            
            html += f"""
                <div class="section">
                    <h2>⚠️ Evaluación de Riesgo</h2>
                    <div class="metric">
                        Nivel de Riesgo: <span class="{risk_color}"><strong>{risk_level}/10</strong></span>
                    </div>"""
            
            concentraciones = risk.get('concentraciones_riesgo', [])
            if concentraciones:
                html += "<h3>Factores de Riesgo:</h3><ul>"
                for riesgo in concentraciones[:3]:
                    html += f"<li>{riesgo}</li>"
                html += "</ul>"
            
            html += "</div>"
        
        # Conclusión
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento:
            html += f"""
                <div class="section">
                    <h2>🧠 Conclusión del Experto</h2>
                    <p style="background-color: #e8f4fd; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db;">
                        {razonamiento}
                    </p>
                </div>"""
        
        html += """
                <div class="footer">
                    <p>🤖 <strong>Generado automáticamente por Balanz Scraper</strong></p>
                    <p>⚠️ <em>Verificar precios antes de ejecutar operaciones</em></p>
                </div>
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