# scraper/notifications/email_notifier.py - VERSIÓN MEJORADA SOLO ACCIONABLES
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
            print("   EMAIL_FROM=tu_email@gmail.com")
            print("   EMAIL_PASSWORD=tu_app_password")
    
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
        """Envía análisis MEJORADO - Solo accionables claros"""
        try:
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Extraer información real de la cartera
            portfolio_info = self._extract_portfolio_info(rules_analysis, expert_analysis)
            
            # Determinar tipo de email según disponibilidad de análisis
            if self._has_real_claude_analysis(expert_analysis):
                subject = f"🎯 QUÉ HACER HOY - {timestamp}"
                body_text = self._create_actionable_text_email(portfolio_info, expert_analysis, timestamp)
                body_html = self._create_actionable_html_email(portfolio_info, expert_analysis, timestamp)
            else:
                subject = f"📊 RECOMENDACIONES BÁSICAS - {timestamp}"
                body_text = self._create_basic_text_email(portfolio_info, rules_analysis, timestamp)
                body_html = self._create_basic_html_email(portfolio_info, rules_analysis, timestamp)
            
            return self.send_email(subject, body_text, body_html)
            
        except Exception as e:
            print(f"❌ Error preparando email mejorado: {str(e)}")
            return False
    
    def _extract_portfolio_info(self, rules_analysis: Dict, expert_analysis: Dict) -> Dict:
        """Extrae información real de la cartera de los análisis"""
        portfolio_info = {
            'total_value': 0,
            'available_cash': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'positions': [],
            'market_context': {},
            'fundamental_data': {}
        }
        
        try:
            # Métricas generales del portfolio
            metrics = rules_analysis.get('portfolio_metrics', {})
            portfolio_info['total_value'] = metrics.get('total_value', 0)
            portfolio_info['total_pnl'] = metrics.get('total_pnl', 0)
            portfolio_info['total_pnl_pct'] = metrics.get('total_pnl_pct', 0)
            portfolio_info['available_cash'] = portfolio_info['total_value'] * metrics.get('cash_allocation', 0)
            
            # Información de posiciones actuales
            positions_analysis = rules_analysis.get('positions_analysis', [])
            for pos in positions_analysis:
                position_info = {
                    'ticker': pos.ticker,
                    'current_shares': pos.current_shares,
                    'current_price': pos.current_price,
                    'current_value': pos.current_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                    'days_held': pos.days_held
                }
                portfolio_info['positions'].append(position_info)
            
            # Contexto de mercado si está disponible
            # Esto vendría del análisis integral
            market_report = getattr(expert_analysis, 'market_report', {})
            if market_report:
                portfolio_insights = market_report.get('portfolio_insights', {})
                portfolio_info['market_context'] = {
                    'sentiment': portfolio_insights.get('sentiment_general', 'neutral'),
                    'mentioned_assets': portfolio_insights.get('tickers_mencionados', {}),
                    'market_drivers': portfolio_insights.get('market_drivers', [])
                }
            
            return portfolio_info
            
        except Exception as e:
            print(f"⚠️ Error extrayendo info de cartera: {str(e)}")
            return portfolio_info
    
    def _has_real_claude_analysis(self, expert_analysis: Dict) -> bool:
        """Verifica si tenemos análisis real de Claude"""
        if not expert_analysis:
            return False
        
        # Verificar indicadores de análisis real
        analysis_source = expert_analysis.get('analysis_source', 'real')
        claude_available = expert_analysis.get('claude_api_available', True)
        
        if analysis_source in ['minimal_fallback', 'error_fallback'] or not claude_available:
            return False
        
        # Verificar que hay análisis técnico real
        analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        real_analysis_count = 0
        for ticker, analysis in por_activo.items():
            rsi = analysis.get('rsi_analysis', '')
            if rsi and 'no_calculado' not in rsi.lower():
                real_analysis_count += 1
        
        return real_analysis_count > 0
    
    def _create_actionable_text_email(self, portfolio_info: Dict, expert_analysis: Dict, timestamp: str) -> str:
        """Email de texto con acciones claras basadas en datos reales"""
        
        email = f"""🎯 QUÉ HACER CON TUS INVERSIONES - {timestamp}
{'='*55}

💼 TU CARTERA ACTUAL:
💰 Total: ${portfolio_info['total_value']:,.0f}
📊 Resultado: ${portfolio_info['total_pnl']:,.0f} ({portfolio_info['total_pnl_pct']:+.1f}%)
💵 Disponible: ${portfolio_info['available_cash']:,.0f}

📋 TUS POSICIONES ACTUALES:"""
        
        # Mostrar posiciones actuales reales
        for pos in portfolio_info['positions']:
            pnl_emoji = "🟢" if pos['unrealized_pnl'] >= 0 else "🔴"
            email += f"""
{pnl_emoji} {pos['ticker']}: {pos['current_shares']} nominales a ${pos['current_price']:.0f}
   💰 Valor: ${pos['current_value']:,.0f}
   📊 Resultado: ${pos['unrealized_pnl']:,.0f} ({pos['unrealized_pnl_pct']:+.1f}%)
   📅 Días tenencia: {pos['days_held']}"""
        
        email += f"\n\n🚨 ACCIONES PARA HOY:\n"
        email += "="*30 + "\n"
        
        # Acciones inmediatas del análisis real
        immediate_actions = expert_analysis.get('acciones_inmediatas', [])
        if immediate_actions:
            for i, action in enumerate(immediate_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '').upper()
                cantidad = action.get('cantidad', 0)
                precio_objetivo = action.get('precio_objetivo', 0)
                razon = action.get('razon', '')
                
                if 'COMPRAR' in accion:
                    email += f"""
{i}. COMPRAR {ticker}
   📊 Cantidad: {cantidad} nominales
   💰 Precio máximo: ${precio_objetivo:.0f} por acción
   💵 Inversión total: ${cantidad * precio_objetivo:,.0f}
   💡 Por qué: {razon}"""
                    
                elif 'VENDER' in accion:
                    # Buscar cuántos nominales tienes actualmente
                    current_position = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                    if current_position:
                        email += f"""
{i}. VENDER {ticker}
   📊 Vender: {cantidad} de tus {current_position['current_shares']} nominales
   💰 Precio mínimo: ${precio_objetivo:.0f} por acción
   💵 Recibirás: ${cantidad * precio_objetivo:,.0f} aprox
   💡 Por qué: {razon}"""
                    else:
                        email += f"""
{i}. VENDER {ticker}
   📊 Cantidad: {cantidad} nominales
   💰 Precio: ${precio_objetivo:.0f}
   💡 Por qué: {razon}"""
        
        # Acciones de corto plazo con triggers específicos
        short_term_actions = expert_analysis.get('acciones_corto_plazo', [])
        if short_term_actions:
            email += f"\n\n📅 VIGILAR PRÓXIMOS DÍAS:\n"
            email += "-"*30 + "\n"
            
            for action in short_term_actions:
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '')
                timeframe = action.get('timeframe', '')
                condiciones = action.get('condiciones', '')
                trigger_price = action.get('trigger_price')
                
                email += f"""
• {ticker} - {accion.replace('_', ' ').title()}
  ⏰ Cuándo: {timeframe}
  📋 Condición: {condiciones}"""
                
                if trigger_price:
                    email += f"""
  🎯 Precio gatillo: ${float(trigger_price):.0f}"""
                
                email += "\n"
        
        # Stops sugeridos con precios específicos
        stop_losses = expert_analysis.get('gestion_riesgo', {}).get('stop_loss_sugeridos', {})
        if stop_losses:
            email += f"\n🛡️ PROTECCIÓN (Stop Loss):\n"
            email += "-"*30 + "\n"
            
            for ticker, stop_price in stop_losses.items():
                current_position = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                if current_position:
                    try:
                        stop_price_float = float(stop_price)
                        email += f"• {ticker}: Vender TODAS las {current_position['current_shares']} si baja a ${stop_price_float:.0f}\n"
                    except:
                        email += f"• {ticker}: Vender si baja a {stop_price}\n"
        
        # Contexto de mercado si está disponible
        market_context = portfolio_info.get('market_context', {})
        if market_context and market_context.get('mentioned_assets'):
            email += f"\n📰 CONTEXTO DE MERCADO:\n"
            email += f"📊 Sentiment general: {market_context['sentiment'].title()}\n"
            
            mentioned = market_context['mentioned_assets']
            tus_activos_mencionados = []
            for ticker, info in mentioned.items():
                if info.get('mencionado') and ticker in [p['ticker'] for p in portfolio_info['positions']]:
                    performance = info.get('performance_reportada', 'mencionado')
                    tus_activos_mencionados.append(f"{ticker}: {performance}")
            
            if tus_activos_mencionados:
                email += f"🎯 Tus activos en las noticias:\n"
                for mention in tus_activos_mencionados:
                    email += f"   • {mention}\n"
        
        # Análisis del experto (resumen)
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento and len(razonamiento) > 50:
            # Tomar las primeras 2 oraciones del razonamiento
            sentences = razonamiento.split('. ')
            summary = '. '.join(sentences[:2])
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            email += f"\n🧠 ANÁLISIS DEL EXPERTO:\n{summary}\n"
        
        # Footer
        email += f"""
{'='*55}
⚠️ IMPORTANTE:
• Estas son recomendaciones basadas en análisis técnico y fundamental
• Siempre verifica precios antes de operar
• No inviertas más de lo que puedes permitirte perder

🤖 Generado por tu Sistema Integral de Análisis v3.0
   Datos reales • Análisis técnico • Ratios fundamentales"""
        
        return email
    
    def _create_actionable_html_email(self, portfolio_info: Dict, expert_analysis: Dict, timestamp: str) -> str:
        """Email HTML mejorado con acciones claras"""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background-color: #f5f7fa; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: white; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .section {{ padding: 25px; border-bottom: 1px solid #e1e5e9; }}
        .portfolio-summary {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 20px; margin: 20px 0; }}
        .position {{ background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin: 10px 0; }}
        .position.profit {{ border-left: 4px solid #28a745; }}
        .position.loss {{ border-left: 4px solid #dc3545; }}
        .action-card {{ border-radius: 10px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .action-buy {{ background-color: #d4edda; border-left: 5px solid #28a745; }}
        .action-sell {{ background-color: #f8d7da; border-left: 5px solid #dc3545; }}
        .action-watch {{ background-color: #fff3cd; border-left: 5px solid #ffc107; }}
        .price {{ font-weight: bold; color: #007bff; font-size: 16px; }}
        .positive {{ color: #28a745; font-weight: bold; }}
        .negative {{ color: #dc3545; font-weight: bold; }}
        .market-context {{ background-color: #e7f3ff; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .footer {{ background-color: #6c757d; color: white; padding: 20px; text-align: center; }}
        h2 {{ color: #495057; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 QUÉ HACER CON TUS INVERSIONES</h1>
            <p style="font-size: 18px; margin: 10px 0;">{timestamp}</p>
        </div>
        
        <div class="section">
            <div class="portfolio-summary">
                <h2>💼 Tu Cartera Actual</h2>
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                    <div style="text-align: center; margin: 10px;">
                        <div style="font-size: 24px; font-weight: bold;">${portfolio_info['total_value']:,.0f}</div>
                        <div style="color: #6c757d;">Total</div>
                    </div>
                    <div style="text-align: center; margin: 10px;">
                        <div style="font-size: 24px; font-weight: bold;" class="{'positive' if portfolio_info['total_pnl'] >= 0 else 'negative'}">
                            ${portfolio_info['total_pnl']:,.0f}
                        </div>
                        <div style="color: #6c757d;">Resultado ({portfolio_info['total_pnl_pct']:+.1f}%)</div>
                    </div>
                    <div style="text-align: center; margin: 10px;">
                        <div style="font-size: 24px; font-weight: bold;">${portfolio_info['available_cash']:,.0f}</div>
                        <div style="color: #6c757d;">Disponible</div>
                    </div>
                </div>
            </div>
            
            <h3>📋 Tus Posiciones Actuales</h3>"""
        
        # Mostrar posiciones actuales
        for pos in portfolio_info['positions']:
            profit_class = 'profit' if pos['unrealized_pnl'] >= 0 else 'loss'
            pnl_class = 'positive' if pos['unrealized_pnl'] >= 0 else 'negative'
            
            html += f"""
            <div class="position {profit_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 18px;">{pos['ticker']}</strong>
                        <div>{pos['current_shares']} nominales a <span class="price">${pos['current_price']:.0f}</span></div>
                        <div style="color: #6c757d;">Valor: ${pos['current_value']:,.0f} | {pos['days_held']} días</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="{pnl_class}" style="font-size: 16px;">${pos['unrealized_pnl']:,.0f}</div>
                        <div class="{pnl_class}">({pos['unrealized_pnl_pct']:+.1f}%)</div>
                    </div>
                </div>
            </div>"""
        
        html += "</div>"
        
        # Acciones inmediatas
        immediate_actions = expert_analysis.get('acciones_inmediatas', [])
        if immediate_actions:
            html += """
            <div class="section">
                <h2>🚨 Acciones para Hoy</h2>"""
            
            for i, action in enumerate(immediate_actions, 1):
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '').upper()
                cantidad = action.get('cantidad', 0)
                precio_objetivo = action.get('precio_objetivo', 0)
                razon = action.get('razon', '')
                
                if 'COMPRAR' in accion:
                    inversion_total = cantidad * precio_objetivo
                    html += f"""
                    <div class="action-card action-buy">
                        <h3>{i}. COMPRAR {ticker}</h3>
                        <div style="font-size: 16px; margin: 10px 0;">
                            <strong>📊 Cantidad:</strong> {cantidad} nominales<br>
                            <strong>💰 Precio máximo:</strong> <span class="price">${precio_objetivo:.0f}</span> por acción<br>
                            <strong>💵 Inversión total:</strong> <span class="price">${inversion_total:,.0f}</span><br>
                            <strong>💡 Por qué:</strong> {razon}
                        </div>
                    </div>"""
                    
                elif 'VENDER' in accion:
                    current_position = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                    recibo_aprox = cantidad * precio_objetivo
                    
                    shares_info = f"{cantidad}"
                    if current_position:
                        shares_info += f" de tus {current_position['current_shares']}"
                    
                    html += f"""
                    <div class="action-card action-sell">
                        <h3>{i}. VENDER {ticker}</h3>
                        <div style="font-size: 16px; margin: 10px 0;">
                            <strong>📊 Cantidad:</strong> {shares_info} nominales<br>
                            <strong>💰 Precio mínimo:</strong> <span class="price">${precio_objetivo:.0f}</span> por acción<br>
                            <strong>💵 Recibirás aprox:</strong> <span class="price">${recibo_aprox:,.0f}</span><br>
                            <strong>💡 Por qué:</strong> {razon}
                        </div>
                    </div>"""
            
            html += "</div>"
        
        # Acciones de corto plazo
        short_term_actions = expert_analysis.get('acciones_corto_plazo', [])
        if short_term_actions:
            html += """
            <div class="section">
                <h2>📅 Vigilar Próximos Días</h2>"""
            
            for action in short_term_actions:
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', '').replace('_', ' ').title()
                timeframe = action.get('timeframe', '')
                condiciones = action.get('condiciones', '')
                trigger_price = action.get('trigger_price')
                
                html += f"""
                <div class="action-card action-watch">
                    <h4>{ticker} - {accion}</h4>
                    <div>
                        <strong>⏰ Cuándo:</strong> {timeframe}<br>
                        <strong>📋 Condición:</strong> {condiciones}"""
                
                if trigger_price:
                    html += f"<br><strong>🎯 Precio gatillo:</strong> <span class='price'>${float(trigger_price):,.0f}</span>"
                
                html += "</div></div>"
            
            html += "</div>"
        
        # Stop losses
        stop_losses = expert_analysis.get('gestion_riesgo', {}).get('stop_loss_sugeridos', {})
        if stop_losses:
            html += """
            <div class="section">
                <h2>🛡️ Protección (Stop Loss)</h2>
                <p style="color: #6c757d;">Vende automáticamente para proteger tu capital:</p>"""
            
            for ticker, stop_price in stop_losses.items():
                current_position = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                
                try:
                    stop_price_float = float(stop_price)
                    shares_text = f"TODAS las {current_position['current_shares']} nominales" if current_position else "tus nominales"
                    
                    html += f"""
                    <div style="background-color: #fff5f5; border: 1px solid #f5c6cb; padding: 15px; margin: 10px 0; border-radius: 5px;">
                        <strong>{ticker}:</strong> Vender {shares_text} si baja a <span class="price">${stop_price_float:.0f}</span>
                    </div>"""
                except:
                    html += f"""
                    <div style="background-color: #fff5f5; border: 1px solid #f5c6cb; padding: 15px; margin: 10px 0; border-radius: 5px;">
                        <strong>{ticker}:</strong> Vender si baja a {stop_price}
                    </div>"""
            
            html += "</div>"
        
        # Contexto de mercado
        market_context = portfolio_info.get('market_context', {})
        if market_context and market_context.get('sentiment'):
            html += f"""
            <div class="section">
                <div class="market-context">
                    <h3>📰 Contexto de Mercado Hoy</h3>
                    <div><strong>Sentiment general:</strong> {market_context['sentiment'].title()}</div>"""
            
            mentioned = market_context.get('mentioned_assets', {})
            if mentioned:
                your_assets_mentioned = []
                for ticker, info in mentioned.items():
                    if info.get('mencionado') and ticker in [p['ticker'] for p in portfolio_info['positions']]:
                        performance = info.get('performance_reportada', 'mencionado')
                        your_assets_mentioned.append(f"{ticker}: {performance}")
                
                if your_assets_mentioned:
                    html += "<div style='margin-top: 10px;'><strong>🎯 Tus activos en las noticias:</strong><ul>"
                    for mention in your_assets_mentioned:
                        html += f"<li>{mention}</li>"
                    html += "</ul></div>"
            
            html += "</div></div>"
        
        # Footer
        html += f"""
        <div class="footer">
            <h4>⚠️ Importante</h4>
            <p>Estas son recomendaciones basadas en análisis técnico y fundamental automatizado.</p>
            <p>Siempre verifica precios y condiciones antes de operar. No inviertas más de lo que puedes perder.</p>
            <hr style="border: 1px solid #5a6268; margin: 20px 0;">
            <p><strong>🤖 Sistema Integral de Análisis de Cartera v3.0</strong></p>
            <p><em>Datos reales • Análisis técnico • Ratios fundamentales</em></p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _create_basic_text_email(self, portfolio_info: Dict, rules_analysis: Dict, timestamp: str) -> str:
        """Email básico cuando no hay análisis de Claude"""
        
        email = f"""📊 RECOMENDACIONES BÁSICAS - {timestamp}
{'='*45}

💼 TU CARTERA:
💰 Total: ${portfolio_info['total_value']:,.0f}
📊 Resultado: ${portfolio_info['total_pnl']:,.0f} ({portfolio_info['total_pnl_pct']:+.1f}%)
💵 Disponible: ${portfolio_info['available_cash']:,.0f}

⚠️ El análisis avanzado no está disponible temporalmente.
Estas son recomendaciones del sistema automático:

"""
        
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            email += "🎯 RECOMENDACIONES:\n"
            email += "-"*20 + "\n"
            
            for i, rec in enumerate(rules_recs, 1):
                ticker = rec.ticker
                action_type = rec.action.value
                shares = rec.suggested_shares
                price = rec.target_price
                
                # Buscar posición actual
                current_position = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                
                if 'stop_loss' in action_type:
                    shares_text = f"TODAS las {current_position['current_shares']}" if current_position else f"{shares}"
                    email += f"""
{i}. PROTEGER {ticker}:
   📊 Vender {shares_text} nominales
   💰 Si baja a ${price:.0f}
   💡 Para evitar más pérdidas
   🔥 Confianza: {rec.confidence:.0f}%"""
                    
                elif 'toma_ganancias' in action_type:
                    shares_text = f"{shares} de tus {current_position['current_shares']}" if current_position else f"{shares}"
                    email += f"""
{i}. ASEGURAR GANANCIAS {ticker}:
   📊 Vender {shares_text} nominales
   💰 A ${price:.0f} o más
   💡 Para tomar ganancias
   🔥 Confianza: {rec.confidence:.0f}%"""
                    
                elif 'rebalanceo' in action_type:
                    shares_text = f"{shares} de tus {current_position['current_shares']}" if current_position else f"{shares}"
                    email += f"""
{i}. BALANCEAR CARTERA {ticker}:
   📊 Reducir {shares_text} nominales
   💰 Precio actual ${price:.0f}
   💡 Tienes demasiado en esta acción
   🔥 Confianza: {rec.confidence:.0f}%"""
                
                email += "\n"
        else:
            email += "✅ Tu cartera está estable por ahora.\n"
            email += "No hay recomendaciones urgentes del sistema automático.\n"
        
        email += f"""
{'='*45}
⚠️ NOTA: El análisis técnico avanzado estará disponible pronto.
🤖 Sistema automático de reglas"""
        
        return email
    
    def _create_basic_html_email(self, portfolio_info: Dict, rules_analysis: Dict, timestamp: str) -> str:
        """Email HTML básico cuando no hay análisis de Claude"""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #fff3cd; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; }}
        .warning-header {{ background-color: #ffc107; color: #212529; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }}
        .portfolio-summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .recommendation {{ border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="warning-header">
            <h2>📊 RECOMENDACIONES BÁSICAS</h2>
            <p>{timestamp}</p>
        </div>
        
        <div class="portfolio-summary">
            <h3>💼 Tu Cartera</h3>
            <p><strong>Total:</strong> ${portfolio_info['total_value']:,.0f}</p>
            <p><strong>Resultado:</strong> ${portfolio_info['total_pnl']:,.0f} ({portfolio_info['total_pnl_pct']:+.1f}%)</p>
            <p><strong>Disponible:</strong> ${portfolio_info['available_cash']:,.0f}</p>
        </div>
        
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h4>⚠️ El análisis avanzado no está disponible temporalmente</h4>
            <p>Estas son recomendaciones del sistema automático:</p>
        </div>"""
        
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            html += "<h3>🎯 Recomendaciones:</h3>"
            
            for i, rec in enumerate(rules_recs, 1):
                ticker = rec.ticker
                action_type = rec.action.value
                shares = rec.suggested_shares
                price = rec.target_price
                confidence = rec.confidence
                
                current_position = next((p for p in portfolio_info['positions'] if p['ticker'] == ticker), None)
                
                if 'stop_loss' in action_type:
                    shares_text = f"TODAS las {current_position['current_shares']}" if current_position else f"{shares}"
                    action_desc = f"PROTEGER {ticker}"
                    details = f"Vender {shares_text} nominales si baja a ${price:.0f}"
                    reason = "Para evitar más pérdidas"
                    
                elif 'toma_ganancias' in action_type:
                    shares_text = f"{shares} de tus {current_position['current_shares']}" if current_position else f"{shares}"
                    action_desc = f"ASEGURAR GANANCIAS {ticker}"
                    details = f"Vender {shares_text} nominales a ${price:.0f} o más"
                    reason = "Para tomar ganancias"
                    
                elif 'rebalanceo' in action_type:
                    shares_text = f"{shares} de tus {current_position['current_shares']}" if current_position else f"{shares}"
                    action_desc = f"BALANCEAR {ticker}"
                    details = f"Reducir {shares_text} nominales (precio actual ${price:.0f})"
                    reason = "Tienes demasiado en esta acción"
                
                else:
                    action_desc = f"{action_type.replace('_', ' ').title()} {ticker}"
                    details = f"{shares} nominales a ${price:.0f}"
                    reason = "Recomendación del sistema"
                
                html += f"""
                <div class="recommendation">
                    <h4>{i}. {action_desc}</h4>
                    <p><strong>📊 Acción:</strong> {details}</p>
                    <p><strong>💡 Por qué:</strong> {reason}</p>
                    <p><strong>🔥 Confianza:</strong> {confidence:.0f}%</p>
                </div>"""
        else:
            html += """
            <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; text-align: center;">
                <h3 style="color: #155724;">✅ Tu cartera está estable</h3>
                <p style="color: #155724;">No hay recomendaciones urgentes por ahora</p>
            </div>"""
        
        html += """
        <div style="background-color: #e9ecef; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: center;">
            <p><strong>⚠️ NOTA:</strong> El análisis técnico avanzado estará disponible pronto</p>
            <p><em>🤖 Sistema automático de reglas</em></p>
        </div>
    </div>
</body>
</html>"""
        
        return html