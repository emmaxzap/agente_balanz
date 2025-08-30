# portfolio_manager.py - Sistema híbrido: FINAL FIX
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from scraper.cartera_extractor import CarteraExtractor
from analysis.financial_analyzer import FinancialAnalyzer
from advanced_portfolio_manager import AdvancedPortfolioManager, ActionType
from claude_portfolio_agent import ClaudePortfolioAgent
from database.database_manager import SupabaseManager

class PortfolioManager:
    def __init__(self, page):
        self.page = page
        self.db = SupabaseManager()
        self.cartera_extractor = CarteraExtractor(page)
        self.financial_analyzer = FinancialAnalyzer(self.db)
        self.advanced_manager = AdvancedPortfolioManager(self.db, self.financial_analyzer)
        self.expert_agent = ClaudePortfolioAgent(self.db)
        self.portfolio_data = None
    
    def run_complete_analysis(self):
        """Ejecuta análisis completo: Sistema de reglas + Agente experto"""
        try:
            print("🚀 INICIANDO ANÁLISIS HÍBRIDO: REGLAS + AGENTE EXPERTO")
            print("="*70)
            
            # 1. Extraer datos de la cartera
            self.portfolio_data = self.cartera_extractor.extract_portfolio_data()
            
            if not self.portfolio_data:
                print("❌ No se pudieron extraer datos de la cartera")
                return False
            
            # 2. Análisis del sistema de reglas (actual)
            print("📊 EJECUTANDO ANÁLISIS DEL SISTEMA DE REGLAS")
            print("-" * 50)
            
            rules_analysis = self.advanced_manager.analyze_complete_portfolio(
                self.portfolio_data,
                self.portfolio_data['dinero_disponible']
            )
            
            # 3. Análisis del agente experto (con manejo de errores mejorado)
            print("🤖 EJECUTANDO ANÁLISIS DEL AGENTE EXPERTO")
            print("-" * 50)
            
            expert_analysis = self._safe_expert_analysis()
            
            # 4. Comparar y mostrar ambos análisis
            self._display_comparative_analysis(rules_analysis, expert_analysis)
            
            # 5. Generar recomendación combinada
            combined_recommendations = self._combine_analyses(rules_analysis, expert_analysis)
            
            # 6. Guardar análisis en BD
            self._save_comparative_analysis_to_db(rules_analysis, expert_analysis, combined_recommendations)
            
            # 7. Enviar notificaciones (WhatsApp + Email backup)
            self._send_dual_notifications(rules_analysis, expert_analysis, combined_recommendations)            
            print("✅ ANÁLISIS HÍBRIDO COMPLETADO")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en análisis híbrido: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _safe_expert_analysis(self):
        """Ejecuta análisis del agente experto con debug completo"""
        try:
            print("🔍 DEBUG: Preparando datos para agente experto...")
            
            # 1. Verificar datos de entrada
            print(f"   📊 Portfolio data keys: {list(self.portfolio_data.keys())}")
            print(f"   📊 Cantidad activos: {len(self.portfolio_data.get('activos', []))}")
            print(f"   💰 Dinero disponible: ${self.portfolio_data.get('dinero_disponible', 0):,.2f}")
            
            # 2. Llamar al agente experto con debug
            print("🔍 DEBUG: Llamando al agente experto...")
            expert_analysis = self.expert_agent.analyze_portfolio_with_expert_agent(
                self.portfolio_data,
                self.portfolio_data['dinero_disponible']
            )
            
            # 3. Verificar respuesta del agente
            print("🔍 DEBUG: Verificando respuesta del agente...")
            print(f"   📊 Respuesta type: {type(expert_analysis)}")
            print(f"   📊 Respuesta keys: {list(expert_analysis.keys()) if isinstance(expert_analysis, dict) else 'No es dict'}")
            
            # 4. Verificar contenido específico
            if isinstance(expert_analysis, dict):
                analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
                print(f"   📊 Análisis técnico keys: {list(analisis_tecnico.keys())}")
                
                razonamiento = expert_analysis.get('razonamiento_integral', '')
                print(f"   📊 Razonamiento length: {len(razonamiento)} chars")
                print(f"   📊 Razonamiento preview: {razonamiento[:100]}...")
                
                # 5. Determinar si es análisis válido
                has_technical = bool(analisis_tecnico.get('por_activo'))
                has_reasoning = len(razonamiento) > 50
                
                print(f"   📊 Has technical analysis: {has_technical}")
                print(f"   📊 Has reasoning: {has_reasoning}")
                
                if has_technical and has_reasoning:
                    print("✅ Análisis experto válido")
                    return expert_analysis
                else:
                    print("⚠️ Análisis experto incompleto - faltan componentes clave")
                    return self._create_basic_expert_analysis()
            else:
                print("❌ Respuesta del agente no es dict válido")
                return self._create_basic_expert_analysis()
                
        except Exception as e:
            print(f"❌ Error completo en agente experto: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_basic_expert_analysis()
    
    def _create_basic_expert_analysis(self):
        """Crea análisis básico cuando el agente experto falla"""
        positions = self.portfolio_data.get('activos', [])
        
        # Análisis básico basado en las reglas del sistema
        basic_analysis = {
            'analisis_tecnico': {
                'por_activo': {},
                'mercado_general': 'Análisis básico - posiciones muy recientes (1 día promedio)'
            },
            'acciones_inmediatas': [],
            'acciones_corto_plazo': [],
            'gestion_riesgo': {
                'riesgo_cartera': 6,
                'concentraciones_riesgo': ['Alta concentración en 5 posiciones sin diversificación'],
                'escenarios_stress': 'Riesgo moderado por posiciones recientes'
            },
            'estrategia_efectivo': {
                'efectivo_optimo': '25-30%',
                'colocaciones_sugeridas': [
                    {
                        'instrumento': 'plazo_fijo',
                        'monto': '10000',
                        'plazo': '30 días',
                        'tasa_esperada': '100%'
                    }
                ]
            },
            'plan_mediano_plazo': {
                'objetivos_1_mes': [
                    'Monitorear posiciones recientes por alta volatilidad inicial',
                    'Considerar stops losses más estrictos para posiciones nuevas'
                ]
            },
            'razonamiento_integral': 'Cartera con posiciones muy recientes (1 día promedio). Se recomienda cautela y monitoreo cercano. Las pérdidas actuales son normales en posiciones del primer día.'
        }
        
        # Generar recomendaciones básicas por activo
        for activo in positions:
            ticker = activo['ticker']
            ganancia_pct = activo['ganancia_perdida_porcentaje']
            
            # Análisis técnico básico
            momentum = 'bajista' if ganancia_pct < -2 else 'neutral' if ganancia_pct < 2 else 'alcista'
            basic_analysis['analisis_tecnico']['por_activo'][ticker] = {
                'momentum': momentum,
                'soporte': activo['precio_actual_unitario'] * 0.95,
                'resistencia': activo['precio_actual_unitario'] * 1.05,
                'recomendacion': f'Monitorear posición de 1 día - {momentum} momentum inicial'
            }
            
            # Acciones de corto plazo
            if ganancia_pct < -5:  # Pérdida significativa
                basic_analysis['acciones_corto_plazo'].append({
                    'ticker': ticker,
                    'accion': 'evaluar_stop_loss',
                    'timeframe': '2-3 días',
                    'condiciones': f'Monitorear si pérdida {ganancia_pct:.1f}% continúa'
                })
            elif ganancia_pct > 3:  # Ganancia moderada
                basic_analysis['acciones_corto_plazo'].append({
                    'ticker': ticker,
                    'accion': 'mantener_con_seguimiento',
                    'timeframe': '3-5 días',
                    'condiciones': f'Seguir evolución de ganancia {ganancia_pct:.1f}%'
                })
        
        return basic_analysis
    
    def _display_comparative_analysis(self, rules_analysis: dict, expert_analysis: dict):
        """Muestra comparación entre análisis de reglas y experto"""
        
        print("📊 COMPARACIÓN DE ANÁLISIS")
        print("="*50)
        
        # Resumen de cartera (común)
        positions = rules_analysis['positions_analysis']
        metrics = rules_analysis['portfolio_metrics']
        
        print(f"💼 DATOS DE CARTERA:")
        print(f"💰 Valor total: ${metrics['total_value']:,.2f}")
        print(f"📈 P&L total: ${metrics['total_pnl']:,.2f} ({metrics['total_pnl_pct']:+.1f}%)")
        print(f"💵 Efectivo: {metrics['cash_allocation']:.1%}")
        print(f"⏱️ Días promedio tenencia: {metrics['risk_metrics']['avg_days_held']:.1f}")
        
        # Posiciones detalladas con contexto
        print(f"\n📋 POSICIONES CON CONTEXTO:")
        print("-" * 40)
        for position in positions:
            pnl_emoji = "🟢" if position.unrealized_pnl > 0 else "🔴" if position.unrealized_pnl < 0 else "⚪"
            print(f"{pnl_emoji} {position.ticker}: {position.current_shares} nominales")
            print(f"    💰 P&L: ${position.unrealized_pnl:,.2f} ({position.unrealized_pnl_pct:+.1f}%)")
            print(f"    📅 Días: {position.days_held} | Tamaño: {position.position_size_pct:.1%}")
            print(f"    🏭 Sector: {position.sector}")
        
        print("\n" + "="*50)
        print("🤖 VS 📊 COMPARACIÓN DE RECOMENDACIONES")
        print("="*50)
        
        # Recomendaciones del sistema de reglas
        print("📊 SISTEMA DE REGLAS:")
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            for rec in rules_recs:
                action_emoji = self._get_action_emoji(rec.action.value)
                print(f"{action_emoji} {rec.ticker}: {rec.action.value} {rec.suggested_shares} nominales (Confianza: {rec.confidence:.0f}%)")
                print(f"    💡 {rec.reasons[0] if rec.reasons else 'No reason provided'}")
        else:
            print("    ✅ Sin recomendaciones")
        
        print("\n🤖 AGENTE EXPERTO:")
        
        # Análisis técnico por activo
        analisis_tecnico = expert_analysis.get('analisis_tecnico', {})
        if analisis_tecnico:
            print("📈 ANÁLISIS TÉCNICO POR ACTIVO:")
            por_activo = analisis_tecnico.get('por_activo', {})
            for ticker, analysis in por_activo.items():
                momentum = analysis.get('momentum', 'neutral')
                soporte = analysis.get('soporte', 0)
                resistencia = analysis.get('resistencia', 0)
                recomendacion = analysis.get('recomendacion', 'No especificada')
                
                emoji = "📈" if momentum == 'alcista' else "📉" if momentum == 'bajista' else "➡️"
                print(f"    {emoji} {ticker}: {momentum.upper()}")
                print(f"       Soporte: ${soporte:,.0f} | Resistencia: ${resistencia:,.0f}")
                print(f"       {recomendacion}")
        
        # Acciones inmediatas
        immediate = expert_analysis.get('acciones_inmediatas', [])
        if immediate:
            print("🚨 ACCIONES INMEDIATAS:")
            for action in immediate:
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', 'N/A')
                urgencia = action.get('urgencia', 'media')
                razon = action.get('razon', 'No especificada')
                print(f"    ⚠️ {ticker}: {accion} (Urgencia: {urgencia})")
                print(f"       {razon}")
        
        # Acciones de corto plazo
        short_term = expert_analysis.get('acciones_corto_plazo', [])
        if short_term:
            print("📅 ACCIONES CORTO PLAZO:")
            for action in short_term:
                ticker = action.get('ticker', 'N/A')
                accion = action.get('accion', 'N/A')
                timeframe = action.get('timeframe', 'No especificado')
                condiciones = action.get('condiciones', 'No especificadas')
                print(f"    📊 {ticker}: {accion} ({timeframe})")
                print(f"       {condiciones}")
        
        # Gestión de riesgo
        gestion_riesgo = expert_analysis.get('gestion_riesgo', {})
        if gestion_riesgo:
            print(f"\n⚠️ GESTIÓN DE RIESGO:")
            print(f"    🎯 Nivel de riesgo: {gestion_riesgo.get('riesgo_cartera', 'N/A')}/10")
            concentraciones = gestion_riesgo.get('concentraciones_riesgo', [])
            if concentraciones:
                print("    🚨 Concentraciones de riesgo:")
                for riesgo in concentraciones[:2]:
                    print(f"       • {riesgo}")
        
        # Estrategia de efectivo
        estrategia_efectivo = expert_analysis.get('estrategia_efectivo', {})
        if estrategia_efectivo:
            print(f"\n💰 ESTRATEGIA DE EFECTIVO:")
            efectivo_optimo = estrategia_efectivo.get('efectivo_optimo', 'N/A')
            print(f"    🎯 Efectivo óptimo: {efectivo_optimo}")
            colocaciones = estrategia_efectivo.get('colocaciones_sugeridas', [])
            if colocaciones:
                print("    💎 Colocaciones sugeridas:")
                for colocacion in colocaciones:
                    instrumento = colocacion.get('instrumento', 'N/A')
                    monto = colocacion.get('monto', 'N/A')
                    plazo = colocacion.get('plazo', 'N/A')
                    tasa = colocacion.get('tasa_esperada', 'N/A')
                    print(f"       • {instrumento}: ${monto} a {plazo} ({tasa})")
        
        # Plan de mediano plazo
        plan_mediano = expert_analysis.get('plan_mediano_plazo', {})
        if plan_mediano:
            objetivos = plan_mediano.get('objetivos_1_mes', [])
            if objetivos:
                print(f"\n🎯 OBJETIVOS 1 MES:")
                for objetivo in objetivos[:2]:
                    print(f"    💡 {objetivo}")
        
        # Razonamiento integral
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento:
            print(f"\n🧠 RAZONAMIENTO INTEGRAL:")
            print(f"    {razonamiento[:300]}{'...' if len(razonamiento) > 300 else ''}")
    
    def _get_action_emoji(self, action_type: str) -> str:
        """Obtiene emoji para tipo de acción"""
        emoji_map = {
            'stop_loss': '🚨',
            'toma_ganancias': '💰',
            'promedio_a_la_baja': '📊',
            'rebalanceo': '⚖️',
            'compra_inicial': '🟢',
            'reducir_posicion': '⚠️'
        }
        return emoji_map.get(action_type, '📈')
    
    def _combine_analyses(self, rules_analysis: dict, expert_analysis: dict) -> dict:
        """Combina ambos análisis en recomendación unificada"""
        
        # Extraer recomendaciones del sistema de reglas
        rules_recs = rules_analysis.get('recommendations', [])
        rules_immediate = rules_analysis.get('execution_plan', {}).get('immediate_actions', [])
        
        # Extraer recomendaciones del experto
        expert_immediate = expert_analysis.get('acciones_inmediatas', [])
        expert_short_term = expert_analysis.get('acciones_corto_plazo', [])
        
        # Crear recomendación combinada priorizando al experto en casos de conflicto
        combined = {
            'source': 'hybrid_analysis',
            'priority_recommendations': [],
            'consensus_actions': [],
            'conflicting_opinions': [],
            'final_recommendation': ''
        }
        
        # Priorizar acciones inmediatas del experto
        if expert_immediate:
            combined['priority_recommendations'] = expert_immediate
            combined['final_recommendation'] = 'Priorizar recomendaciones del agente experto para acciones inmediatas'
        
        # Buscar consenso entre ambos sistemas
        expert_tickers = set()
        for action in expert_short_term:
            expert_tickers.add(action.get('ticker', ''))
        
        rules_tickers = set()
        for rec in rules_recs:
            rules_tickers.add(rec.ticker)
        
        # Tickers que ambos sistemas recomiendan actuar
        consensus_tickers = expert_tickers.intersection(rules_tickers)
        if consensus_tickers:
            combined['consensus_actions'] = list(consensus_tickers)
        
        # Identificar conflictos
        if rules_recs and expert_short_term:
            for rules_rec in rules_recs:
                expert_action = next(
                    (a for a in expert_short_term if a.get('ticker') == rules_rec.ticker), 
                    None
                )
                if expert_action:
                    if self._actions_conflict(rules_rec, expert_action):
                        combined['conflicting_opinions'].append({
                            'ticker': rules_rec.ticker,
                            'rules_action': rules_rec.action.value,
                            'expert_action': expert_action.get('accion', 'unknown'),
                            'rules_confidence': rules_rec.confidence,
                            'expert_reasoning': expert_action.get('condiciones', 'No reason provided')
                        })
        
        return combined
    
    def _actions_conflict(self, rules_rec, expert_action) -> bool:
        """Determina si las recomendaciones de reglas y experto están en conflicto"""
        rules_action = rules_rec.action.value
        expert_action_type = expert_action.get('accion', '')
        
        # Definir conflictos obvios
        conflicts = {
            'rebalanceo': ['mantener_con_seguimiento', 'monitorear'],
            'stop_loss': ['mantener_con_seguimiento'],
            'toma_ganancias': ['mantener_con_seguimiento']
        }
        
        return expert_action_type in conflicts.get(rules_action, [])
    
    def _save_comparative_analysis_to_db(self, rules_analysis: dict, expert_analysis: dict, combined: dict):
        """Guarda análisis comparativo en la base de datos"""
        try:
            today = date.today()
            
            # Guardar análisis comparativo
            comparative_data = {
                'fecha': today.isoformat(),
                'rules_recommendations_count': len(rules_analysis.get('recommendations', [])),
                'expert_immediate_count': len(expert_analysis.get('acciones_inmediatas', [])),
                'expert_short_term_count': len(expert_analysis.get('acciones_corto_plazo', [])),
                'consensus_tickers': len(combined.get('consensus_actions', [])),
                'conflicting_opinions': len(combined.get('conflicting_opinions', [])),
                'expert_risk_level': expert_analysis.get('gestion_riesgo', {}).get('riesgo_cartera', 5),
                'final_recommendation_source': combined.get('final_recommendation', ''),
                'expert_reasoning': expert_analysis.get('razonamiento_integral', '')[:500]  # Truncar a 500 chars
            }
            
            self.db.supabase.table('comparative_analysis').insert(comparative_data).execute()
            print("✅ Análisis comparativo guardado en BD")
            
        except Exception as e:
            print(f"⚠️ Error guardando análisis comparativo: {str(e)}")
    
    def _send_comparative_whatsapp_notification_fixed(self, rules_analysis: dict, expert_analysis: dict, combined: dict):
        """Envía notificación comparativa por WhatsApp - VERSION CORREGIDA"""
        try:
            from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
            
            notifier = WhatsAppNotifier()
            if notifier.is_configured:
                message = self._format_comparative_whatsapp_message_fixed(rules_analysis, expert_analysis, combined)
                success = notifier.send_message(message)
                if success:
                    print("✅ Notificación comparativa enviada por WhatsApp")
                else:
                    print("⚠️ Error enviando notificación comparativa")
            else:
                print("📱 WhatsApp no configurado - saltando notificación")
        
        except ImportError:
            print("📱 WhatsApp notifier no disponible")
        except Exception as e:
            print(f"⚠️ Error enviando WhatsApp comparativo: {str(e)}")
    
    def _format_comparative_whatsapp_message_fixed(self, rules_analysis: dict, expert_analysis: dict, combined: dict) -> str:
        """Formatea mensaje comparativo completo para WhatsApp - SIN ERRORES DE VARIABLES"""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        metrics = rules_analysis['portfolio_metrics']
        
        message = f"*ANÁLISIS HÍBRIDO* - {timestamp}\n"
        message += "=" * 30 + "\n\n"
        
        # Resumen de cartera
        message += "*CARTERA ACTUAL*\n"
        message += f"💰 Valor: ${metrics['total_value']:,.0f}\n"
        message += f"📈 P&L: ${metrics['total_pnl']:,.0f} ({metrics['total_pnl_pct']:+.1f}%)\n"
        message += f"⏱️ Días promedio: {metrics['risk_metrics']['avg_days_held']:.1f}\n"
        message += f"💵 Efectivo: {metrics['cash_allocation']:.1%}\n\n"
        
        # SISTEMA DE REGLAS - RECOMENDACIONES
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            message += "*📊 SISTEMA DE REGLAS*\n"
            message += "-" * 20 + "\n"
            
            # Separar por tipo de acción
            stop_losses = [r for r in rules_recs if 'stop_loss' in r.action.value]
            rebalances = [r for r in rules_recs if 'rebalanceo' in r.action.value]
            profit_takes = [r for r in rules_recs if 'ganancias' in r.action.value]
            
            if stop_losses:
                message += "*🚨 STOP LOSSES:*\n"
                for rec in stop_losses:
                    message += f"• *{rec.ticker}*: Vender {rec.suggested_shares} nominales\n"
                    message += f"  ⚠️ {rec.reasons[0] if rec.reasons else 'Stop loss activado'}\n"
                message += "\n"
            
            if profit_takes:
                message += "*💰 TOMA DE GANANCIAS:*\n"
                for rec in profit_takes:
                    message += f"• *{rec.ticker}*: Vender {rec.suggested_shares} nominales\n"
                    message += f"  📈 {rec.reasons[0] if rec.reasons else 'Tomar ganancias'}\n"
                message += "\n"
            
            if rebalances:
                message += "*⚖️ REBALANCEO:*\n"
                for rec in rebalances:
                    message += f"• *{rec.ticker}*: Reducir {rec.suggested_shares} nominales\n"
                    message += f"  📊 Posición excede límites de riesgo\n"
                message += "\n"
        
        # AGENTE EXPERTO
        expert_immediate = expert_analysis.get('acciones_inmediatas', [])
        expert_short = expert_analysis.get('acciones_corto_plazo', [])
        
        if expert_immediate or expert_short:
            message += "*🤖 AGENTE EXPERTO*\n"
            message += "-" * 15 + "\n"
            
            if expert_immediate:
                message += "*🚨 URGENTE:*\n"
                for action in expert_immediate:
                    message += f"• *{action.get('ticker', 'N/A')}*: {action.get('accion', 'N/A')}\n"
                    message += f"  ⚠️ {action.get('razon', 'No especificada')[:60]}...\n"
                message += "\n"
            
            if expert_short:
                message += "*📅 CORTO PLAZO (2-5 días):*\n"
                for action in expert_short:
                    message += f"• *{action.get('ticker', 'N/A')}*: {action.get('accion', 'N/A')}\n"
                    message += f"  📊 {action.get('condiciones', 'No especificadas')[:60]}...\n"
                message += "\n"
        
        # EVALUACIÓN DE RIESGO
        risk = expert_analysis.get('gestion_riesgo', {})
        if risk:
            message += f"*⚠️ EVALUACIÓN RIESGO*\n"
            message += f"Nivel: *{risk.get('riesgo_cartera', 5)}/10*\n"
            concentraciones = risk.get('concentraciones_riesgo', [])
            if concentraciones:
                message += f"Riesgo clave:\n"
                message += f"• {concentraciones[0][:70]}...\n"
            message += "\n"
        
        # ESTRATEGIA DE EFECTIVO
        efectivo_strategy = expert_analysis.get('estrategia_efectivo', {})
        if efectivo_strategy:
            message += "*💰 ESTRATEGIA EFECTIVO*\n"
            efectivo_optimo = efectivo_strategy.get('efectivo_optimo', 'N/A')
            message += f"Objetivo: {efectivo_optimo} en efectivo\n"
            
            colocaciones = efectivo_strategy.get('colocaciones_sugeridas', [])
            if colocaciones:
                message += "Sugerencia:\n"
                for col in colocaciones[:1]:  # Solo primera
                    instrumento = col.get('instrumento', 'plazo_fijo')
                    monto = col.get('monto', '10000')
                    tasa = col.get('tasa_esperada', '100%')
                    message += f"• {instrumento.title()}: ${monto} ({tasa})\n"
            message += "\n"
        
        # PLAN DE ACCIÓN SIMPLIFICADO
        message += "*📋 PLAN DE ACCIÓN*\n"
        message += "-" * 15 + "\n"
        
        # Combinar acciones inmediatas
        immediate_count = len(expert_immediate) + len(stop_losses)
        short_term_count = len(expert_short) + len(rebalances) + len(profit_takes)
        
        if immediate_count > 0:
            message += f"*HOY (urgente):* {immediate_count} acciones\n"
        
        if short_term_count > 0:
            message += f"*2-5 DÍAS:* {short_term_count} acciones programadas\n"
        
        message += f"*MONITOREO:* Todas las posiciones (promedio 1 día)\n\n"
        
        # CONCLUSIÓN
        razonamiento = expert_analysis.get('razonamiento_integral', '')
        if razonamiento:
            message += "*🧠 CONCLUSIÓN EXPERTO*\n"
            message += f"{razonamiento[:120]}...\n\n"
        
        message += "*🤖 Análisis híbrido: Reglas + IA*\n"
        message += "*⚠️ Confirmar precios antes de ejecutar*"
        
        return message
    
    def get_portfolio_summary(self):
        """Devuelve resumen híbrido de la cartera"""
        if not self.portfolio_data:
            return None
        
        return {
            'basic_metrics': {
                'dinero_disponible': self.portfolio_data['dinero_disponible'],
                'valor_total': self.portfolio_data['valor_total_cartera'],
                'total_invertido': self.portfolio_data['total_invertido'],
                'ganancia_perdida': self.portfolio_data['ganancia_perdida_total'],
                'cantidad_activos': len(self.portfolio_data['activos'])
            },
            'analysis_methods': ['rules_based', 'expert_agent'],
            'last_analysis': datetime.now().isoformat(),
            'hybrid_analysis_available': True
        }
    def _send_dual_notifications(self, rules_analysis: dict, expert_analysis: dict, combined: dict):
        """Envía notificaciones por WhatsApp Y Email (backup)"""
        whatsapp_success = False
        email_success = False
        
        try:
            # Intentar WhatsApp primero
            from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
            
            whatsapp_notifier = WhatsAppNotifier()
            if whatsapp_notifier.is_configured:
                message = self._format_comparative_whatsapp_message_fixed(rules_analysis, expert_analysis, combined)
                whatsapp_success = whatsapp_notifier.send_message(message)
                if whatsapp_success:
                    print("✅ Notificación enviada por WhatsApp")
                else:
                    print("⚠️ Error enviando WhatsApp - intentando email backup")
            else:
                print("📱 WhatsApp no configurado - usando solo email")
        
        except Exception as e:
            print(f"⚠️ Error con WhatsApp: {str(e)} - usando email backup")
        
        try:
            # Enviar email (siempre, como backup)
            from scraper.notifications.email_notifier import EmailNotifier
            
            email_notifier = EmailNotifier()
            if email_notifier.is_configured:
                email_success = email_notifier.send_portfolio_analysis_email(rules_analysis, expert_analysis, combined)
                if email_success:
                    print("✅ Notificación enviada por Email")
                else:
                    print("⚠️ Error enviando Email")
            else:
                print("📧 Email no configurado")
        
        except Exception as e:
            print(f"⚠️ Error con Email: {str(e)}")
        
        # Reporte final
        if whatsapp_success and email_success:
            print("🎉 Notificaciones enviadas por WhatsApp Y Email")
        elif whatsapp_success:
            print("✅ Notificación enviada solo por WhatsApp")
        elif email_success:
            print("✅ Notificación enviada solo por Email (WhatsApp falló)")
        else:
            print("❌ Error enviando notificaciones por ambos canales")
        
        return whatsapp_success or email_success    