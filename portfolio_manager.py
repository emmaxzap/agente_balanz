# portfolio_manager.py - Sistema híbrido: Reglas + Agente Experto
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
            
            # 3. Análisis del agente experto
            print("🤖 EJECUTANDO ANÁLISIS DEL AGENTE EXPERTO")
            print("-" * 50)
            
            expert_analysis = self.expert_agent.analyze_portfolio_with_expert_agent(
                self.portfolio_data,
                self.portfolio_data['dinero_disponible']
            )
            
            # 4. Comparar y mostrar ambos análisis
            self._display_comparative_analysis(rules_analysis, expert_analysis)
            
            # 5. Generar recomendación combinada
            combined_recommendations = self._combine_analyses(rules_analysis, expert_analysis)
            
            # 6. Guardar análisis en BD
            self._save_comparative_analysis_to_db(rules_analysis, expert_analysis, combined_recommendations)
            
            # 7. Enviar notificación combinada
            self._send_comparative_whatsapp_notification(rules_analysis, expert_analysis, combined_recommendations)
            
            print("✅ ANÁLISIS HÍBRIDO COMPLETADO")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en análisis híbrido: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
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
                print(f"       Soporte: ${soporte} | Resistencia: ${resistencia}")
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
        
        # Razonamiento del experto
        reasoning = expert_analysis.get('reasoning', '')
        if reasoning:
            print(f"\n🧠 RAZONAMIENTO DEL EXPERTO:")
            print(f"    {reasoning[:200]}{'...' if len(reasoning) > 200 else ''}")
    
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
        expert_immediate = expert_analysis.get('immediate_actions', [])
        expert_short_term = expert_analysis.get('short_term_actions', [])
        
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
                            'expert_action': expert_action.get('action', 'unknown'),
                            'rules_confidence': rules_rec.confidence,
                            'expert_reasoning': expert_action.get('reason', 'No reason provided')
                        })
        
        return combined
    
    def _actions_conflict(self, rules_rec, expert_action) -> bool:
        """Determina si las recomendaciones de reglas y experto están en conflicto"""
        rules_action = rules_rec.action.value
        expert_action_type = expert_action.get('action', '')
        
        # Definir conflictos obvios
        conflicts = {
            'rebalanceo': ['hold_and_monitor', 'monitor_closely'],
            'toma_ganancias': ['hold_and_monitor'],
            'stop_loss': ['partial_profit_taking']
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
                'expert_immediate_count': len(expert_analysis.get('immediate_actions', [])),
                'expert_short_term_count': len(expert_analysis.get('short_term_actions', [])),
                'consensus_tickers': len(combined.get('consensus_actions', [])),
                'conflicting_opinions': len(combined.get('conflicting_opinions', [])),
                'expert_risk_level': expert_analysis.get('risk_assessment', {}).get('overall_risk_level', 0),
                'final_recommendation_source': combined.get('final_recommendation', ''),
                'expert_reasoning': expert_analysis.get('reasoning', '')[:500]  # Truncar a 500 chars
            }
            
            self.db.supabase.table('comparative_analysis').insert(comparative_data).execute()
            print("✅ Análisis comparativo guardado en BD")
            
        except Exception as e:
            print(f"⚠️ Error guardando análisis comparativo: {str(e)}")
    
    def _send_comparative_whatsapp_notification(self, rules_analysis: dict, expert_analysis: dict, combined: dict):
        """Envía notificación comparativa por WhatsApp"""
        try:
            from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
            
            notifier = WhatsAppNotifier()
            if notifier.is_configured:
                message = self._format_comparative_whatsapp_message(rules_analysis, expert_analysis, combined)
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
    
    def _format_comparative_whatsapp_message(self, rules_analysis: dict, expert_analysis: dict, combined: dict) -> str:
        """Formatea mensaje comparativo completo para WhatsApp"""
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
        
        # AGENTE EXPERTO - ACCIONES INMEDIATAS
        expert_immediate = expert_analysis.get('acciones_inmediatas', [])
        if expert_immediate:
            message += "*🚨 EXPERTO - URGENTE*\n"
            message += "-" * 20 + "\n"
            for action in expert_immediate:
                message += f"• *{action.get('ticker', 'N/A')}*: {action.get('accion', 'N/A')}\n"
                message += f"  ⚠️ {action.get('razon', 'N/A')[:80]}...\n\n"
        
        # AGENTE EXPERTO - ACCIONES DE CORTO PLAZO
        expert_short = expert_analysis.get('acciones_corto_plazo', [])
        if expert_short:
            message += "*📅 EXPERTO - PRÓXIMOS 2-3 DÍAS*\n"
            message += "-" * 25 + "\n"
            
            # Separar ventas, compras y monitoreos
            sells = []
            monitors = []
            
            for action in expert_short:
                action_type = action.get('accion', '').lower()
                if any(word in action_type for word in ['vender', 'reducir', 'toma_ganancias']):
                    sells.append(action)
                elif any(word in action_type for word in ['mantener', 'monitorear']):
                    monitors.append(action)
            
            if sells:
                message += "*VENDER/REDUCIR:*\n"
                for action in sells:
                    ticker = action.get('ticker', 'N/A')
                    shares = action.get('nominales_vender', 'N/A')
                    message += f"• *{ticker}*: {shares} nominales\n"
                    message += f"  💡 {action.get('razon', 'N/A')[:60]}...\n"
                message += "\n"
            
            if monitors:
                message += "*MANTENER/MONITOREAR:*\n"
                for action in monitors:
                    message += f"• *{action.get('ticker', 'N/A')}*: Mantener\n"
                message += "\n"
        
        # SISTEMA DE REGLAS - COMPARACIÓN
        rules_recs = rules_analysis.get('recommendations', [])
        if rules_recs:
            message += "*📊 SISTEMA REGLAS vs EXPERTO*\n"
            message += "-" * 25 + "\n"
            
            conflicts_found = False
            for rec in rules_recs:
                ticker = rec.ticker
                rules_action = rec.action.value
                
                # Buscar recomendación del experto para el mismo ticker
                expert_action_obj = next(
                    (a for a in expert_short if a.get('ticker') == ticker),
                    None
                )
                
                if expert_action_obj:
                    expert_action = expert_action_obj.get('accion', 'No especificada')
                    
                    # Mostrar comparación
                    message += f"*{ticker}*:\n"
                    message += f"📊 Reglas: {rules_action} {rec.suggested_shares} nominales\n"
                    message += f"🤖 Experto: {expert_action}\n"
                    
                    # Marcar si hay conflicto
                    if self._detect_conflict_spanish(rules_action, expert_action):
                        message += f"⚠️ *CONFLICTO DE OPINIÓN*\n"
                        conflicts_found = True
                    else:
                        message += f"✅ Recomendaciones similares\n"
                    message += "\n"
            
            if conflicts_found:
                message += "❗ *En caso de conflicto, priorizar EXPERTO*\n\n"
        
        # EVALUACIÓN DE RIESGO
        risk = expert_analysis.get('evaluacion_riesgo', {})
        if risk:
            message += f"*⚠️ EVALUACIÓN RIESGO*\n"
            message += f"Nivel: *{risk.get('nivel_riesgo_general', 'N/A')}/10*\n"
            key_risks = risk.get('riesgos_clave', [])
            if key_risks:
                message += f"Factor crítico:\n"
                message += f"• {key_risks[0][:70]}...\n\n"
        
        # RECOMENDACIONES ESTRATÉGICAS
        strategic = expert_analysis.get('recomendaciones_estrategicas', [])
        if strategic:
            message += "*🎯 ESTRATEGIA GENERAL*\n"
            for rec in strategic[:2]:  # Top 2
                message += f"• {rec[:80]}...\n"
            message += "\n"
        
        # PLAN DE ACCIÓN ESPECÍFICO
        message += "*📋 PLAN DE ACCIÓN*\n"
        message += "-" * 15 + "\n"
        
        if expert_immediate:
            message += "*HOY (urgente):*\n"
            for action in expert_immediate:
                message += f"• {action.get('ticker')}: {action.get('accion')}\n"
            message += "\n"
        
        if sells:
            message += "*2-3 DÍAS:*\n"
            for action in sells:
                shares = action.get('nominales_vender', 'N/A')
                message += f"• Vender {action.get('ticker')} {shares} nominales\n"
            message += "\n"
        
        if monitors:
            message += "*MONITOREAR:*\n"
            for action in monitors:
                message += f"• {action.get('ticker')}: Evaluar en 3-5 días\n"
            message += "\n"
        
        # Efectivo proyectado
        if sells:
            estimated_cash_from_sales = 0
            positions = rules_analysis['positions_analysis']
            for action in sells:
                ticker = action.get('ticker')
                shares_to_sell = action.get('nominales_vender', 0)
                position = next((p for p in positions if p.ticker == ticker), None)
                if position and isinstance(shares_to_sell, int):
                    estimated_cash_from_sales += shares_to_sell * position.current_price
            
            if estimated_cash_from_sales > 0:
                current_cash = metrics.get('cash_allocation', 0) * metrics['total_value']
                total_cash = current_cash + estimated_cash_from_sales
                message += f"💵 *EFECTIVO DESPUÉS DE VENTAS*\n"
                message += f"Disponible: ~${total_cash:,.0f}\n\n"
        
        message += "*🤖 Análisis híbrido: Reglas + IA*\n"
        message += "*⚠️ Confirmar precios antes de ejecutar*"
        
        return message
    
    def _detect_conflict_spanish(self, rules_action: str, expert_action: str) -> bool:
        """Detecta conflictos entre recomendaciones en español"""
        # Convertir a minúsculas para comparación
        rules_lower = rules_action.lower()
        expert_lower = expert_action.lower()
        
        # Conflictos obvios
        sell_actions = ['vender', 'reducir', 'toma_ganancias']
        hold_actions = ['mantener', 'monitorear']
        buy_actions = ['comprar', 'promedio']
        
        rules_is_sell = any(action in rules_lower for action in sell_actions)
        rules_is_hold = any(action in rules_lower for action in hold_actions)  
        rules_is_buy = any(action in rules_lower for action in buy_actions)
        
        expert_is_sell = any(action in expert_lower for action in sell_actions)
        expert_is_hold = any(action in expert_lower for action in hold_actions)
        expert_is_buy = any(action in expert_lower for action in buy_actions)
        
        # Detectar conflictos directos
        if (rules_is_sell and expert_is_buy) or (rules_is_buy and expert_is_sell):
            return True
        
        if rules_lower == 'rebalanceo' and expert_is_hold:
            return True
            
        return False            conflicts = combined.get('conflicting_opinions', [])
            if conflicts:
                message += "⚠️ OPINIONES DIVIDIDAS\n"
                message += "-" * 15 + "\n"
                for conflict in conflicts[:2]:
                    message += f"• {conflict['ticker']}: Sistema dice {conflict['rules_action']}, Experto dice {conflict['expert_action']}\n"
                message += "\n"
        
        # Evaluación de riesgo del experto
        risk = expert_analysis.get('evaluacion_riesgo', {})
        if risk:
            message += f"EVALUACIÓN RIESGO\n"
            message += f"Nivel: {risk.get('nivel_riesgo_general', 'N/A')}/10\n"
            key_risks = risk.get('riesgos_clave', [])
            if key_risks:
                message += f"Factor clave: {key_risks[0][:50]}...\n"
            message += "\n"
        
        # Recomendación final
        reasoning = expert_analysis.get('razonamiento', '')
        if reasoning:
            message += "CONCLUSIÓN EXPERTO\n"
            message += f"{reasoning[:100]}...\n\n"
        
        message += "🤖 Análisis híbrido: Reglas + IA\n"
        message += "⚠️ Verificar antes de ejecutar"
        
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