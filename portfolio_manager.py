# portfolio_manager.py - Integración con sistema avanzado corregido
from datetime import date, datetime
import sys
from pathlib import Path

# Agregar rutas necesarias
sys.path.append(str(Path(__file__).parent))

from scraper.cartera_extractor import CarteraExtractor
from analysis.financial_analyzer import FinancialAnalyzer
from advanced_portfolio_manager import AdvancedPortfolioManager, ActionType
from database.database_manager import SupabaseManager

class PortfolioManager:
    def __init__(self, page):
        self.page = page
        self.db = SupabaseManager()
        self.cartera_extractor = CarteraExtractor(page)
        self.financial_analyzer = FinancialAnalyzer(self.db)
        self.advanced_manager = AdvancedPortfolioManager(self.db, self.financial_analyzer)
        self.portfolio_data = None
    
    def run_complete_analysis(self):
        """Ejecuta análisis completo con sistema avanzado de gestión"""
        try:
            print("\n🚀 INICIANDO ANÁLISIS AVANZADO DE CARTERA")
            print("="*60)
            
            # 1. Extraer datos de la cartera
            self.portfolio_data = self.cartera_extractor.extract_portfolio_data()
            
            if not self.portfolio_data:
                print("❌ No se pudieron extraer datos de la cartera")
                return False
            
            # 2. Análisis avanzado completo
            print(f"\n📊 EJECUTANDO ANÁLISIS PROFESIONAL DE CARTERA")
            print("-" * 50)
            
            advanced_analysis = self.advanced_manager.analyze_complete_portfolio(
                self.portfolio_data,
                self.portfolio_data['dinero_disponible']
            )
            
            # 3. Mostrar resultados detallados
            self._display_advanced_results(advanced_analysis)
            
            # 4. Guardar análisis en BD
            self._save_advanced_analysis_to_db(advanced_analysis)
            
            # 5. Enviar notificación avanzada
            self._send_advanced_whatsapp_notification(advanced_analysis)
            
            print("\n✅ ANÁLISIS AVANZADO COMPLETADO")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en análisis avanzado: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _display_advanced_results(self, analysis: dict):
        """Muestra resultados del análisis avanzado"""
        
        positions = analysis['positions_analysis']
        metrics = analysis['portfolio_metrics']
        recommendations = analysis['recommendations']
        risk_assessment = analysis['risk_assessment']
        execution_plan = analysis['execution_plan']
        
        print(f"\n📊 MÉTRICAS AVANZADAS DE CARTERA")
        print("="*50)
        
        # Métricas generales
        print(f"💰 Valor total: ${metrics['total_value']:,.2f}")
        print(f"📈 P&L total: ${metrics['total_pnl']:,.2f} ({metrics['total_pnl_pct']:+.1f}%)")
        print(f"💵 Efectivo: {metrics['cash_allocation']:.1%}")
        print(f"🏛️ Posiciones: {metrics['number_of_positions']}")
        print(f"📊 Sharpe ratio: {metrics['risk_metrics']['sharpe_ratio']:.2f}")
        print(f"⚠️ Riesgo concentración: {metrics['risk_metrics']['concentration_risk']:.2f}")
        
        # Diversificación por sector
        print(f"\n🏢 DIVERSIFICACIÓN SECTORIAL:")
        print("-" * 30)
        for sector, allocation in metrics['sector_allocation'].items():
            print(f"   {sector.title()}: {allocation:.1%}")
        
        # Evaluación de riesgo
        print(f"\n⚠️ EVALUACIÓN DE RIESGO:")
        print("-" * 30)
        print(f"🎯 Nivel de riesgo: {risk_assessment['overall_risk'].upper()}")
        print(f"📊 Score de riesgo: {risk_assessment['risk_score']}/10")
        
        if risk_assessment['risk_factors']:
            print(f"\n🚨 Factores de riesgo identificados:")
            for factor in risk_assessment['risk_factors']:
                print(f"   • {factor}")
        
        # Recomendaciones por estrategia
        print(f"\n📋 RECOMENDACIONES ESTRATÉGICAS")
        print("="*50)
        
        if not recommendations:
            print("✅ No hay recomendaciones en este momento")
            return
        
        # Agrupar por tipo de acción
        actions_by_type = {}
        for rec in recommendations:
            action_type = rec.action.value
            if action_type not in actions_by_type:
                actions_by_type[action_type] = []
            actions_by_type[action_type].append(rec)
        
        # Mostrar por categoría
        action_emojis = {
            'stop_loss': '🚨',
            'trailing_stop': '📉',
            'toma_ganancias': '💰',
            'promedio_a_la_baja': '📊',
            'rebalanceo': '⚖️',
            'compra_inicial': '🟢',
            'compra_momentum': '⚡',
            'reducir_posicion': '⚠️'
        }
        
        for action_type, recs in actions_by_type.items():
            emoji = action_emojis.get(action_type, '📈')
            print(f"\n{emoji} {action_type.replace('_', ' ').upper()} ({len(recs)} recomendaciones):")
            print("-" * 40)
            
            for rec in recs:
                investment = rec.suggested_shares * rec.target_price
                print(f"📊 {rec.ticker} - Confianza: {rec.confidence:.0f}%")
                print(f"   💰 Acción: {rec.suggested_shares} nominales a ${rec.target_price:,.2f}")
                print(f"   💵 Inversión: ${investment:,.0f}")
                print(f"   💡 Razón: {rec.reasons[0] if rec.reasons else 'N/A'}")
                
                if rec.stop_loss_price:
                    print(f"   🚨 Stop loss: ${rec.stop_loss_price:,.2f}")
                if rec.take_profit_price:
                    print(f"   🎯 Take profit: ${rec.take_profit_price:,.2f}")
                
                print(f"   ⚠️ Riesgo: {rec.risk_assessment}")
                print()
        
        # Plan de ejecución
        print(f"\n🎯 PLAN DE EJECUCIÓN")
        print("="*50)
        
        if execution_plan['immediate_actions']:
            print(f"🚨 ACCIONES INMEDIATAS (24 horas):")
            for action in execution_plan['immediate_actions']:
                print(f"   • {action['ticker']}: {action['action']} {action['shares']} nominales")
        
        if execution_plan['planned_actions']:
            print(f"\n📅 ACCIONES PLANIFICADAS (esta semana):")
            for action in execution_plan['planned_actions']:
                print(f"   • {action['ticker']}: {action['action']} {action['shares']} nominales")
        
        if execution_plan['monitoring_alerts']:
            print(f"\n👁️ MONITOREAR (ejecutar si condiciones persisten):")
            for action in execution_plan['monitoring_alerts']:
                print(f"   • {action['ticker']}: {action['action']} {action['shares']} nominales")
    
    def _save_advanced_analysis_to_db(self, analysis: dict):
        """Guarda análisis avanzado en la base de datos"""
        try:
            today = date.today()
            
            # Guardar métricas de cartera
            portfolio_metrics = {
                'fecha': today.isoformat(),
                'valor_total': analysis['portfolio_metrics']['total_value'],
                'pnl_total': analysis['portfolio_metrics']['total_pnl'],
                'pnl_porcentaje': analysis['portfolio_metrics']['total_pnl_pct'],
                'cash_allocation': analysis['portfolio_metrics']['cash_allocation'],
                'num_posiciones': analysis['portfolio_metrics']['number_of_positions'],
                'sharpe_ratio': analysis['portfolio_metrics']['risk_metrics']['sharpe_ratio'],
                'concentration_risk': analysis['portfolio_metrics']['risk_metrics']['concentration_risk'],
                'risk_level': analysis['risk_assessment']['overall_risk'],
                'risk_score': analysis['risk_assessment']['risk_score']
            }
            
            self.db.supabase.table('portfolio_metrics_advanced').upsert(portfolio_metrics).execute()
            
            # Guardar recomendaciones avanzadas
            recommendations_data = []
            for rec in analysis['recommendations']:
                rec_data = {
                    'fecha': today.isoformat(),
                    'ticker': rec.ticker,
                    'action_type': rec.action.value,
                    'suggested_shares': rec.suggested_shares,
                    'target_price': rec.target_price,
                    'confidence': int(rec.confidence),
                    'primary_reason': rec.reasons[0] if rec.reasons else '',
                    'risk_assessment': rec.risk_assessment,
                    'stop_loss_price': rec.stop_loss_price,
                    'take_profit_price': rec.take_profit_price
                }
                recommendations_data.append(rec_data)
            
            if recommendations_data:
                self.db.supabase.table('advanced_recommendations').insert(recommendations_data).execute()
                print(f"✅ {len(recommendations_data)} recomendaciones avanzadas guardadas en BD")
            
        except Exception as e:
            print(f"⚠️ Error guardando análisis avanzado: {str(e)}")
    
    def _send_advanced_whatsapp_notification(self, analysis: dict):
        """Envía notificación avanzada por WhatsApp"""
        try:
            from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
            
            notifier = WhatsAppNotifier()
            if notifier.is_configured:
                message = self._format_advanced_whatsapp_message(analysis)
                success = notifier.send_message(message)
                if success:
                    print("✅ Notificación avanzada enviada por WhatsApp")
                else:
                    print("⚠️ Error enviando notificación avanzada")
            else:
                print("📱 WhatsApp no configurado - saltando notificación")
        
        except ImportError:
            print("📱 WhatsApp notifier no disponible")
        except Exception as e:
            print(f"⚠️ Error enviando WhatsApp avanzado: {str(e)}")
    
    def _format_advanced_whatsapp_message(self, analysis: dict) -> str:
        """Formatea mensaje avanzado para WhatsApp con acciones específicas"""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        metrics = analysis['portfolio_metrics']
        risk = analysis['risk_assessment']
        recommendations = analysis['recommendations']
        execution_plan = analysis['execution_plan']
        
        message = f"📊 *ANÁLISIS BALANZ* - {timestamp}\n"
        message += "="*30 + "\n\n"
        
        # Resumen ejecutivo compacto
        message += f"💼 *RESUMEN*\n"
        message += f"💰 Valor: ${metrics['total_value']:,.0f}\n"
        message += f"📈 P&L: ${metrics['total_pnl']:,.0f} ({metrics['total_pnl_pct']:+.1f}%)\n"
        message += f"⚠️ Riesgo: {risk['overall_risk'].upper()}\n\n"
        
        # ACCIONES INMEDIATAS (más críticas)
        immediate_actions = execution_plan.get('immediate_actions', [])
        if immediate_actions:
            message += f"🚨 *URGENTE - HACER HOY*\n"
            message += "-"*20 + "\n"
            for action in immediate_actions:
                if 'stop_loss' in action['action'] or 'trailing_stop' in action['action']:
                    message += f"🔴 VENDER {action['ticker']}: {action['shares']} nominales\n"
                    message += f"   💰 A ${action['price_target']:,.0f} c/u\n"
                else:
                    message += f"• {action['ticker']}: {action['action']} {action['shares']} nominales\n"
            message += "\n"
        
        # ACCIONES PLANIFICADAS (esta semana)
        planned_actions = execution_plan.get('planned_actions', [])
        if planned_actions:
            message += f"📅 *HACER ESTA SEMANA*\n"
            message += "-"*20 + "\n"
            
            # Separar ventas y compras para mayor claridad
            sales = [a for a in planned_actions if 'rebalanceo' in a['action'] or 'reducir' in a['action']]
            buys = [a for a in planned_actions if 'compra' in a['action']]
            
            if sales:
                message += f"🔴 *VENDER:*\n"
                for action in sales:
                    message += f"• {action['ticker']}: {action['shares']} nominales\n"
                    message += f"  💰 ~${action['shares'] * action['price_target']:,.0f}\n"
            
            if buys:
                message += f"🟢 *COMPRAR:*\n"
                for action in buys:
                    message += f"• {action['ticker']}: {action['shares']} nominales\n"
                    message += f"  💰 ~${action['shares'] * action['price_target']:,.0f}\n"
            
            message += "\n"
        
        # OPORTUNIDADES DE MONITOREO (menos críticas)
        monitoring_alerts = execution_plan.get('monitoring_alerts', [])
        if monitoring_alerts:
            message += f"👁️ *MONITOREAR*\n"
            message += "-"*15 + "\n"
            for action in monitoring_alerts[:3]:  # Solo top 3
                if 'compra' in action['action']:
                    message += f"📊 {action['ticker']}: Comprar {action['shares']} si persiste oportunidad\n"
            message += "\n"
        
        # Resumen de efectivo después de operaciones
        cash_after_sales = metrics.get('cash_allocation', 0) * metrics['total_value']
        planned_sales_value = sum(a['shares'] * a['price_target'] for a in planned_actions if 'rebalanceo' in a['action'] or 'reducir' in a['action'])
        
        if planned_sales_value > 0:
            total_cash_after = cash_after_sales + planned_sales_value
            message += f"💵 *EFECTIVO DESPUÉS DE VENTAS*\n"
            message += f"Disponible: ~${total_cash_after:,.0f}\n\n"
        
        # Factores de riesgo críticos
        if risk['risk_factors']:
            message += f"⚠️ *ALERTAS*\n"
            message += "-"*10 + "\n"
            for factor in risk['risk_factors'][:2]:  # Solo top 2
                if 'posición' in factor.lower():
                    message += f"• {factor}\n"
                elif 'concentración' in factor.lower():
                    message += f"• Diversificar más\n"
            message += "\n"
        
        message += f"🤖 _Sistema automatizado_\n"
        message += f"📞 _Confirmar antes de ejecutar_"
        
        return message
    
    def get_portfolio_summary(self):
        """Devuelve resumen avanzado de la cartera"""
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
            'advanced_available': True,
            'last_analysis': datetime.now().isoformat()
        }