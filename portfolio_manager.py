# portfolio_manager.py - Sistema híbrido integrado sin hardcodeo

from datetime import date, datetime
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Asegura import relativo al paquete actual
sys.path.append(str(Path(__file__).parent))

from scraper.cartera_extractor import CarteraExtractor
from analysis.financial_analyzer import FinancialAnalyzer
from advanced_portfolio_manager import AdvancedPortfolioManager, ActionType
from claude_portfolio_agent import ClaudePortfolioAgent
from database.database_manager import SupabaseManager


class PortfolioManager:
    """
    Orquestador de análisis híbrido (reglas + agente experto con datos reales).
    MEJORADO: Sin respuestas hardcodeadas, recomendaciones específicas y accionables.
    """

    def __init__(self, page: Any):
        self.page = page
        self.db = SupabaseManager()
        self.cartera_extractor = CarteraExtractor(page)
        self.financial_analyzer = FinancialAnalyzer(self.db)
        self.advanced_manager = AdvancedPortfolioManager(self.db, self.financial_analyzer)
        # Pasar página al agente para scraping fundamental/técnico
        self.expert_agent = ClaudePortfolioAgent(self.db, page)
        self.portfolio_data: Optional[Dict[str, Any]] = None

    def run_complete_analysis(self) -> bool:
        """Ejecuta análisis completo: Sistema de reglas + Agente experto con datos reales."""
        try:
            print("🚀 INICIANDO ANÁLISIS HÍBRIDO: REGLAS + AGENTE EXPERTO")
            print("=" * 70)

            # 1) Extraer datos de la cartera
            self.portfolio_data = self.cartera_extractor.extract_portfolio_data()
            if not self.portfolio_data:
                print("❌ No se pudieron extraer datos de la cartera")
                return False

            # 2) Análisis del sistema de reglas
            print("📊 EJECUTANDO ANÁLISIS DEL SISTEMA DE REGLAS")
            print("-" * 50)
            rules_analysis = self.advanced_manager.analyze_complete_portfolio(
                self.portfolio_data,
                self.portfolio_data.get("dinero_disponible", 0.0)
            )

            # 3) Análisis del agente experto mejorado con datos reales
            print("🤖 EJECUTANDO ANÁLISIS DEL AGENTE EXPERTO MEJORADO")
            print("-" * 50)
            expert_analysis = self._safe_expert_analysis_improved()

            # 4) Comparar y mostrar ambos análisis
            self._display_comparative_analysis_improved(rules_analysis, expert_analysis)

            # 5) Generar recomendación combinada
            combined_recommendations = self._combine_analyses(rules_analysis, expert_analysis)

            # 6) Guardar análisis en BD
            self._save_comparative_analysis_to_db(rules_analysis, expert_analysis, combined_recommendations)

            # 7) Enviar notificaciones mejoradas (WhatsApp + Email backup)
            self._send_improved_notifications(rules_analysis, expert_analysis, combined_recommendations)

            print("✅ ANÁLISIS HÍBRIDO COMPLETADO")
            return True

        except Exception as e:
            print(f"❌ Error en análisis híbrido: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _safe_expert_analysis_improved(self) -> Dict[str, Any]:
        """Ejecuta análisis del agente experto con validación estricta."""
        try:
            print("🔍 DEBUG: Preparando datos mejorados para agente experto...")

            if not self.portfolio_data:
                raise ValueError("No hay portfolio_data disponible.")

            print(f"   📊 Portfolio data keys: {list(self.portfolio_data.keys())}")
            print(f"   📊 Cantidad activos: {len(self.portfolio_data.get('activos', []))}")
            print(f"   💰 Dinero disponible: ${self.portfolio_data.get('dinero_disponible', 0):,.2f}")

            print("🔍 DEBUG: Llamando al agente experto con datos reales...")
            expert_analysis = self.expert_agent.analyze_portfolio_with_expert_agent(
                self.portfolio_data,
                self.portfolio_data.get("dinero_disponible", 0.0)
            )

            print("🔍 DEBUG: Verificando respuesta del agente...")
            print(f"   📊 Respuesta type: {type(expert_analysis)}")
            if isinstance(expert_analysis, dict):
                print(f"   📊 Respuesta keys: {list(expert_analysis.keys())}")
                
                # Verificar si es análisis real o fallback
                analysis_source = expert_analysis.get('analysis_source', 'real_analysis')
                claude_available = expert_analysis.get('claude_api_available', True)
                
                if analysis_source == 'minimal_fallback' or not claude_available:
                    print("⚠️ Se recibió análisis minimal/fallback - no es análisis real de Claude")
                    return expert_analysis  # Lo devolvemos pero será manejado apropiadamente
                
                analisis_tecnico = expert_analysis.get("analisis_tecnico", {})
                print(f"   📊 Análisis técnico keys: {list(analisis_tecnico.keys()) if isinstance(analisis_tecnico, dict) else 'n/a'}")

                por_activo = analisis_tecnico.get("por_activo", {}) if isinstance(analisis_tecnico, dict) else {}
                print(f"   📊 Activos con análisis técnico: {len(por_activo)}")

                for ticker, analysis in por_activo.items():
                    rsi_analysis = analysis.get("rsi_analysis", "")
                    macd_signal = analysis.get("macd_signal", "")
                    if rsi_analysis and macd_signal:
                        print(f"   ✅ {ticker}: RSI={rsi_analysis}, MACD={macd_signal}")

                razonamiento = expert_analysis.get("razonamiento_integral", "") or ""
                print(f"   📊 Razonamiento length: {len(razonamiento)} chars")

                has_technical = bool(por_activo)
                has_reasoning = len(razonamiento) > 50
                has_real_data = ("datos reales" in razonamiento.lower()) or ("indicadores calculados" in razonamiento.lower())

                print(f"   📊 Has technical analysis: {has_technical}")
                print(f"   📊 Has reasoning: {has_reasoning}")
                print(f"   📊 Based on real data: {has_real_data}")

                if has_technical and has_reasoning and has_real_data:
                    print("✅ Análisis experto real y válido")
                    return expert_analysis
                else:
                    print("⚠️ Análisis experto incompleto o genérico")
                    return expert_analysis
            else:
                print("❌ Respuesta del agente no es dict válido")
                return expert_analysis

        except Exception as e:
            print(f"❌ Error completo en agente experto mejorado: {str(e)}")
            import traceback
            traceback.print_exc()
            # Retornar análisis mínimo en lugar de hardcodeado
            return {
                "analisis_tecnico": {"por_activo": {}, "mercado_general": "Error en análisis"},
                "acciones_inmediatas": [],
                "acciones_corto_plazo": [],
                "gestion_riesgo": {"riesgo_cartera": 5},
                "razonamiento_integral": "Error obteniendo análisis técnico avanzado",
                "analysis_source": "error_fallback",
                "claude_api_available": False
            }

    def _display_comparative_analysis_improved(self, rules_analysis: Dict[str, Any], expert_analysis: Dict[str, Any]) -> None:
        """Muestra comparación mejorada entre análisis."""
        print("📊 COMPARACIÓN DE ANÁLISIS MEJORADA")
        print("=" * 50)

        positions = rules_analysis.get("positions_analysis", [])
        metrics = rules_analysis.get("portfolio_metrics", {})

        print("💼 DATOS DE CARTERA:")
        print(f"💰 Valor total: ${metrics.get('total_value', 0.0):,.2f}")
        print(f"📈 P&L total: ${metrics.get('total_pnl', 0.0):,.2f} ({metrics.get('total_pnl_pct', 0.0):+.1f}%)")
        print(f"💵 Efectivo: {metrics.get('cash_allocation', 0.0):.1%}")
        risk_metrics = metrics.get("risk_metrics", {})
        print(f"⏱️ Días promedio tenencia: {risk_metrics.get('avg_days_held', 0.0):.1f}")

        print("\n📋 POSICIONES CON CONTEXTO:")
        print("-" * 40)
        for position in positions:
            pnl_emoji = "🟢" if getattr(position, "unrealized_pnl", 0) > 0 else "🔴" if getattr(position, "unrealized_pnl", 0) < 0 else "⚪"
            print(f"{pnl_emoji} {position.ticker}: {position.current_shares} nominales")
            print(f"    💰 P&L: ${position.unrealized_pnl:,.2f} ({position.unrealized_pnl_pct:+.1f}%)")
            print(f"    📅 Días: {position.days_held} | Tamaño: {position.position_size_pct:.1%}")
            print(f"    🏭 Sector: {position.sector}")

        print("\n" + "=" * 50)
        print("🤖 VS 📊 COMPARACIÓN DE RECOMENDACIONES")
        print("=" * 50)

        # Recomendaciones del sistema de reglas
        print("📊 SISTEMA DE REGLAS:")
        rules_recs = rules_analysis.get("recommendations", [])
        if rules_recs:
            for rec in rules_recs:
                action_value = rec.action.value if hasattr(rec.action, "value") else str(rec.action)
                action_emoji = self._get_action_emoji(action_value)
                print(f"{action_emoji} {rec.ticker}: {action_value} {rec.suggested_shares} nominales (Confianza: {rec.confidence:.0f}%)")
                first_reason = rec.reasons[0] if getattr(rec, "reasons", []) else "No reason provided"
                print(f"    💡 {first_reason}")
        else:
            print("    ✅ Sin recomendaciones")

        # Verificar si el análisis experto es real o fallback
        analysis_source = expert_analysis.get('analysis_source', 'real_analysis')
        claude_available = expert_analysis.get('claude_api_available', True)
        
        if analysis_source in ['minimal_fallback', 'error_fallback'] or not claude_available:
            print("\n🤖 AGENTE EXPERTO:")
            print("⚠️ Análisis técnico avanzado no disponible")
            print("📊 Usando solo sistema de reglas automáticas")
        else:
            print("\n🤖 AGENTE EXPERTO MEJORADO:")
            analisis_tecnico = expert_analysis.get("analisis_tecnico", {})
            if isinstance(analisis_tecnico, dict):
                print("📈 ANÁLISIS TÉCNICO CON INDICADORES CALCULADOS:")
                por_activo = analisis_tecnico.get("por_activo", {})
                for ticker, analysis in por_activo.items():
                    momentum = analysis.get("momentum", "neutral")
                    rsi_analysis = analysis.get("rsi_analysis", "N/A")
                    macd_signal = analysis.get("macd_signal", "N/A")
                    volatility = analysis.get("volatility_assessment", "N/A")
                    recomendacion = analysis.get("recomendacion", "No especificada")

                    emoji = "📈" if momentum == "alcista" else "📉" if momentum == "bajista" else "➡️"
                    print(f"    {emoji} {ticker}: {momentum.upper()}")
                    print(f"       RSI: {rsi_analysis} | MACD: {macd_signal}")
                    print(f"       Volatilidad: {volatility}")
                    print(f"       {recomendacion}")

            # Acciones inmediatas
            immediate = expert_analysis.get("acciones_inmediatas", [])
            if immediate:
                print("🚨 ACCIONES INMEDIATAS:")
                for action in immediate:
                    ticker = action.get("ticker", "N/A")
                    accion = action.get("accion", "N/A")
                    urgencia = action.get("urgencia", "media")
                    razon = action.get("razon", "No especificada")
                    stop_loss = action.get("stop_loss")
                    take_profit = action.get("take_profit")

                    print(f"    ⚠️ {ticker}: {accion} (Urgencia: {urgencia})")
                    print(f"       {razon}")
                    if stop_loss is not None:
                        print(f"       Stop Loss: ${float(stop_loss):.2f}")
                    if take_profit is not None:
                        print(f"       Take Profit: ${float(take_profit):.2f}")

            # Acciones de corto plazo
            short_term = expert_analysis.get("acciones_corto_plazo", [])
            if short_term:
                print("📅 ACCIONES CORTO PLAZO CON TRIGGERS TÉCNICOS:")
                for action in short_term:
                    ticker = action.get("ticker", "N/A")
                    accion = action.get("accion", "N/A")
                    timeframe = action.get("timeframe", "No especificado")
                    condiciones = action.get("condiciones", "No especificadas")
                    trigger_price = action.get("trigger_price")

                    print(f"    📊 {ticker}: {accion} ({timeframe})")
                    print(f"       Condiciones: {condiciones}")
                    if trigger_price is not None:
                        print(f"       Precio Trigger: ${float(trigger_price):.2f}")

            # Gestión de riesgo
            gestion_riesgo = expert_analysis.get("gestion_riesgo", {})
            if isinstance(gestion_riesgo, dict) and gestion_riesgo:
                print("\n⚠️ GESTIÓN DE RIESGO CON VOLATILIDAD REAL:")
                print(f"    🎯 Nivel de riesgo: {gestion_riesgo.get('riesgo_cartera', 'N/A')}/10")

                volatilidad_obs = gestion_riesgo.get("volatilidad_observada", "")
                if volatilidad_obs:
                    print(f"    📊 Volatilidad observada: {volatilidad_obs}")

                stop_losses = gestion_riesgo.get("stop_loss_sugeridos", {})
                if stop_losses:
                    print("    🚨 Stop Loss Técnicos Sugeridos:")
                    for ticker, stop_price in stop_losses.items():
                        try:
                            print(f"       • {ticker}: ${float(stop_price):.2f}")
                        except Exception:
                            print(f"       • {ticker}: {stop_price}")

                recomendaciones_sizing = gestion_riesgo.get("recomendaciones_sizing", [])
                if recomendaciones_sizing:
                    print("    📊 Sizing Recomendado:")
                    for rec in recomendaciones_sizing[:2]:
                        print(f"       • {rec}")

            razonamiento = expert_analysis.get("razonamiento_integral", "")
            if razonamiento:
                print("\n🧠 RAZONAMIENTO INTEGRAL:")
                print(f"    {razonamiento}")

    def _get_action_emoji(self, action_type: str) -> str:
        """Obtiene emoji para tipo de acción."""
        emoji_map = {
            "stop_loss": "🚨",
            "toma_ganancias": "💰",
            "promedio_a_la_baja": "📊",
            "rebalanceo": "⚖️",
            "compra_inicial": "🟢",
            "reducir_posicion": "⚠️",
        }
        return emoji_map.get(action_type, "📈")

    def _combine_analyses(self, rules_analysis: Dict[str, Any], expert_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Combina ambos análisis en recomendación unificada."""
        rules_recs = rules_analysis.get("recommendations", []) or []
        expert_immediate = expert_analysis.get("acciones_inmediatas", []) or []
        expert_short_term = expert_analysis.get("acciones_corto_plazo", []) or []

        combined: Dict[str, Any] = {
            "source": "hybrid_analysis_with_real_data",
            "priority_recommendations": [],
            "consensus_actions": [],
            "technical_insights": [],
            "final_recommendation": "",
            "has_claude_analysis": expert_analysis.get('claude_api_available', True)
        }

        # Priorizar acciones del experto si existen y son reales
        if expert_immediate and expert_analysis.get('claude_api_available', True):
            combined["priority_recommendations"] = expert_immediate
            combined["final_recommendation"] = "Priorizar recomendaciones basadas en indicadores técnicos calculados"
        else:
            combined["final_recommendation"] = "Usar recomendaciones del sistema de reglas automáticas"

        # Extraer insights técnicos del análisis experto (solo si es real)
        if expert_analysis.get('claude_api_available', True):
            analisis_tecnico = expert_analysis.get("analisis_tecnico", {})
            por_activo = analisis_tecnico.get("por_activo", {}) if isinstance(analisis_tecnico, dict) else {}

            for ticker, analysis in por_activo.items():
                rsi_analysis = analysis.get("rsi_analysis", "")
                macd_signal = analysis.get("macd_signal", "")
                if "sobrecomprado" in rsi_analysis or "sobrevendido" in rsi_analysis:
                    combined["technical_insights"].append({
                        "ticker": ticker,
                        "insight": f"RSI {rsi_analysis}, MACD {macd_signal}",
                        "actionable": True,
                    })

        return combined

    def _save_comparative_analysis_to_db(
        self,
        rules_analysis: Dict[str, Any],
        expert_analysis: Dict[str, Any],
        combined: Dict[str, Any],
    ) -> None:
        """Guarda análisis comparativo mejorado en la base de datos."""
        try:
            today = date.today()

            analisis_tecnico = expert_analysis.get("analisis_tecnico", {})
            technical_count = len(analisis_tecnico.get("por_activo", {})) if isinstance(analisis_tecnico, dict) else 0

            razonamiento = expert_analysis.get("razonamiento_integral", "") or ""
            has_real_data = ("datos reales" in razonamiento.lower()) or ("indicadores calculados" in razonamiento.lower())
            
            # Verificar si es análisis real de Claude
            claude_available = expert_analysis.get('claude_api_available', True)
            analysis_source = expert_analysis.get('analysis_source', 'real_analysis')

            comparative_data = {
                "fecha": today.isoformat(),
                "rules_recommendations_count": len(rules_analysis.get("recommendations", [])),
                "expert_immediate_count": len(expert_analysis.get("acciones_inmediatas", [])),
                "expert_short_term_count": len(expert_analysis.get("acciones_corto_plazo", [])),
                "technical_analysis_count": technical_count,
                "has_real_indicators": has_real_data,
                "technical_insights_count": len(combined.get("technical_insights", [])),
                "expert_risk_level": expert_analysis.get("gestion_riesgo", {}).get("riesgo_cartera", 5),
                "claude_api_available": claude_available,
                "analysis_source": analysis_source,
                "expert_reasoning": razonamiento[:500],
            }

            self.db.supabase.table("comparative_analysis").insert(comparative_data).execute()
            print("✅ Análisis comparativo mejorado guardado en BD")

        except Exception as e:
            print(f"⚠️ Error guardando análisis comparativo: {str(e)}")

    def _send_improved_notifications(
        self,
        rules_analysis: Dict[str, Any],
        expert_analysis: Dict[str, Any],
        combined: Dict[str, Any],
    ) -> bool:
        """Envía notificaciones mejoradas SIN hardcodeo por WhatsApp y Email."""
        whatsapp_success = False
        email_success = False

        # WHATSAPP MEJORADO
        try:
            from scraper.notifications.whatsapp_notifier import WhatsAppNotifier

            whatsapp_notifier = WhatsAppNotifier()
            if getattr(whatsapp_notifier, "is_configured", False):
                # Usar método específico para análisis de portfolio
                whatsapp_success = whatsapp_notifier.send_portfolio_analysis_message(
                    rules_analysis, expert_analysis, combined
                )
                if whatsapp_success:
                    print("✅ Mensaje enviado por WhatsApp exitosamente")
                else:
                    print("⚠️ Error enviando WhatsApp - intentando email backup")
            else:
                print("📱 WhatsApp no configurado - usando solo email")

        except Exception as e:
            print(f"⚠️ Error con WhatsApp: {str(e)} - usando email backup")

        # EMAIL MEJORADO
        try:
            from scraper.notifications.email_notifier import EmailNotifier

            email_notifier = EmailNotifier()
            if getattr(email_notifier, "is_configured", False):
                email_success = email_notifier.send_portfolio_analysis_email(
                    rules_analysis, expert_analysis, combined
                )
                if email_success:
                    print("✅ Email enviado exitosamente")
                else:
                    print("⚠️ Error enviando Email")
            else:
                print("📧 Email no configurado")

        except Exception as e:
            print(f"⚠️ Error con Email: {str(e)}")

        # Resultados
        if whatsapp_success and email_success:
            print("🎉 Notificaciones enviadas por WhatsApp Y Email")
        elif whatsapp_success:
            print("✅ Notificación enviada solo por WhatsApp")
        elif email_success:
            print("✅ Notificación enviada solo por Email (WhatsApp falló)")
        else:
            print("❌ Error enviando notificaciones por ambos canales")

        return whatsapp_success or email_success

    def get_portfolio_summary_improved(self) -> Optional[Dict[str, Any]]:
        """Devuelve resumen híbrido mejorado de la cartera."""
        if not self.portfolio_data:
            return None

        return {
            "basic_metrics": {
                "dinero_disponible": self.portfolio_data.get("dinero_disponible", 0.0),
                "valor_total": self.portfolio_data.get("valor_total_cartera", 0.0),
                "total_invertido": self.portfolio_data.get("total_invertido", 0.0),
                "ganancia_perdida": self.portfolio_data.get("ganancia_perdida_total", 0.0),
                "cantidad_activos": len(self.portfolio_data.get("activos", [])),
            },
            "analysis_methods": ["rules_based", "expert_agent_with_real_data"],
            "data_enhancements": [
                "historical_30day_series",
                "calculated_technical_indicators",
                "real_fundamental_data_scraping",
            ],
            "technical_indicators_available": [
                "RSI_14",
                "MACD",
                "SMA_20_10_5",
                "Bollinger_Bands",
                "Volatility_Real",
                "Momentum_5d_10d",
            ],
            "last_analysis": datetime.now().isoformat(),
            "hybrid_analysis_available": True,
            "data_quality": "enhanced_with_real_indicators",
        }