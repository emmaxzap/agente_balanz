# portfolio_manager.py - Motor principal con análisis financiero unificado
from datetime import date
import sys
from pathlib import Path

# Agregar rutas necesarias
sys.path.append(str(Path(__file__).parent))

from scraper.cartera_extractor import CarteraExtractor
from analysis.financial_analyzer import FinancialAnalyzer
from database.database_manager import SupabaseManager

class PortfolioManager:
    def __init__(self, page):
        self.page = page
        self.db = SupabaseManager()
        self.cartera_extractor = CarteraExtractor(page)
        self.financial_analyzer = FinancialAnalyzer(self.db)
        self.portfolio_data = None
    
    def run_complete_analysis(self):
        """
        Ejecuta análisis completo de la cartera:
        1. Extrae datos de la cartera
        2. Analiza posiciones existentes para venta (basado en rendimiento anualizado)
        3. Busca oportunidades de compra
        4. Genera recomendaciones
        5. Envía notificación por WhatsApp
        """
        try:
            print("\n🚀 INICIANDO ANÁLISIS COMPLETO DE CARTERA")
            print("="*60)
            
            # 1. Extraer datos de la cartera
            self.portfolio_data = self.cartera_extractor.extract_portfolio_data()
            
            if not self.portfolio_data:
                print("❌ No se pudieron extraer datos de la cartera")
                return False
            
            # 2. Análisis de posiciones existentes (decisiones de venta basadas en rendimiento anualizado)
            print(f"\n📊 ANÁLISIS FINANCIERO DE CARTERA")
            print("-" * 50)
            
            sell_recommendations = self.financial_analyzer.analyze_portfolio_for_sell_decisions(
                self.portfolio_data['activos']
            )
            
            # Mostrar resultados del análisis
            for asset in self.portfolio_data['activos']:
                ticker = asset['ticker']
                dias_tenencia = asset.get('dias_tenencia', 1)
                ganancia_perdida_pct = asset['ganancia_perdida_porcentaje']
                
                if dias_tenencia > 0:
                    rendimiento_anualizado = (ganancia_perdida_pct / dias_tenencia) * 365
                else:
                    rendimiento_anualizado = 0
                
                # Buscar si está en recomendaciones de venta
                sell_rec = next((rec for rec in sell_recommendations if rec['ticker'] == ticker), None)
                
                if sell_rec:
                    print(f"🔴 {ticker}: VENTA recomendada - {sell_rec['primary_reason']}")
                else:
                    print(f"🟢 {ticker}: MANTENER - Rendimiento {rendimiento_anualizado:.0f}% anualizado")
            
            # 3. Análisis de mercado (oportunidades de compra)
            owned_tickers = [asset['ticker'] for asset in self.portfolio_data['activos']]
            buy_opportunities = self.financial_analyzer.analyze_market_for_buy_opportunities(
                self.portfolio_data['dinero_disponible'],
                owned_tickers
            )
            
            # 4. Generar informe consolidado
            self._generate_recommendations_report(sell_recommendations, buy_opportunities)
            
            # 5. Guardar recomendaciones en BD
            self._save_recommendations_to_db(sell_recommendations, buy_opportunities)
            
            # 6. Enviar notificación por WhatsApp
            self._send_whatsapp_notification(sell_recommendations, buy_opportunities)
            
            print("\n✅ ANÁLISIS COMPLETO FINALIZADO")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en análisis completo: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_recommendations_report(self, sell_recs: list, buy_opps: list):
        """Genera reporte consolidado de recomendaciones"""
        
        print("\n" + "="*60)
        print("📋 REPORTE DE RECOMENDACIONES FINANCIERAS")
        print("="*60)
        
        # Resumen ejecutivo
        self._print_executive_summary(sell_recs, buy_opps)
        
        # Recomendaciones de venta
        if sell_recs:
            print("\n🔴 RECOMENDACIONES DE VENTA:")
            print("-" * 40)
            for rec in sell_recs:
                print(f"📊 {rec['ticker']} - Confianza: {rec['confidence']}%")
                print(f"    💰 Valor actual: ${rec['current_value']:,.2f}")
                print(f"    📈 G/P: {rec['gain_loss_pct']:+.1f}%")
                print(f"    ⏱️ Días tenencia: {rec['dias_tenencia']}")
                print(f"    📈 Rendimiento anualizado: {rec['rendimiento_anualizado']:+.0f}%")
                print(f"    💡 Razón: {rec['primary_reason']}")
                print()
        else:
            print("\n🟢 No hay recomendaciones de venta por el momento")
        
        # Oportunidades de compra
        if buy_opps:
            print("\n🟢 OPORTUNIDADES DE COMPRA:")
            print("-" * 40)
            for opp in buy_opps[:3]:  # Top 3
                print(f"📊 {opp['ticker']} - Confianza: {opp['confidence']}%")
                print(f"    💰 Precio actual: ${opp['current_price']:,.2f}")
                print(f"    🛒 Inversión sugerida: ${opp['suggested_investment']:,.0f}")
                print(f"    📊 Cantidad: {opp['suggested_quantity']} nominales")
                print(f"    💡 Razones: {', '.join(opp['reasons'][:2])}")
                print()
        else:
            print("\n⚠️ No se encontraron oportunidades de compra atractivas")
        
        # Resumen de acción
        self._print_action_summary(sell_recs, buy_opps)
    
    def _print_executive_summary(self, sell_recs: list, buy_opps: list):
        """Imprime resumen ejecutivo"""
        print("\n💼 RESUMEN EJECUTIVO:")
        print("-" * 30)
        
        total_sell_value = sum(rec['current_value'] for rec in sell_recs)
        total_buy_investment = sum(opp['suggested_investment'] for opp in buy_opps[:3])
        
        print(f"🔴 Activos a vender: {len(sell_recs)}")
        if total_sell_value > 0:
            print(f"    💰 Valor total a liberar: ${total_sell_value:,.2f}")
        
        print(f"🟢 Oportunidades encontradas: {len(buy_opps)}")
        if total_buy_investment > 0:
            print(f"    💰 Inversión sugerida: ${total_buy_investment:,.2f}")
        
        # Cash flow neto
        available_after_sales = self.portfolio_data['dinero_disponible'] + total_sell_value
        print(f"💰 Dinero disponible actual: ${self.portfolio_data['dinero_disponible']:,.2f}")
        if total_sell_value > 0:
            print(f"💰 Dinero después de ventas: ${available_after_sales:,.2f}")
        
        # Status general de la cartera
        total_gain_loss = self.portfolio_data['ganancia_perdida_total']
        total_invested = self.portfolio_data['total_invertido']
        
        if total_invested > 0:
            portfolio_return = (total_gain_loss / total_invested) * 100
            emoji = "📈" if portfolio_return > 0 else "📉"
            print(f"{emoji} Rendimiento cartera: {portfolio_return:+.2f}%")
    
    def _print_action_summary(self, sell_recs: list, buy_opps: list):
        """Imprime resumen de acciones recomendadas"""
        print("\n🎯 PLAN DE ACCIÓN RECOMENDADO:")
        print("-" * 40)
        
        if sell_recs or buy_opps:
            print("📋 Pasos sugeridos:")
            
            if sell_recs:
                print("1. 🔴 VENDER:")
                for i, rec in enumerate(sell_recs, 1):
                    print(f"   {i}. {rec['ticker']} - {rec['primary_reason']}")
            
            if buy_opps:
                start_num = len(sell_recs) + 1
                print(f"{start_num}. 🟢 COMPRAR:")
                for i, opp in enumerate(buy_opps[:3], 1):
                    print(f"   {i}. {opp['ticker']} - ${opp['suggested_investment']:,.0f} "
                          f"({opp['suggested_quantity']} nominales)")
            
            print(f"\n⚠️  CRITERIOS UTILIZADOS:")
            print(f"   • Rendimiento >500% anualizado = Venta inmediata")
            print(f"   • Rendimiento >200% anualizado = Toma de ganancias")
            print(f"   • Rendimiento >100% anualizado = Considerar venta")
            print(f"   • Rendimiento <-50% anualizado = Stop loss")
            print(f"   • Diversificación: máximo 20% por posición")
            
        else:
            print("✅ No se requieren acciones inmediatas")
            print("📊 Continúe monitoreando la cartera")
    
    def _save_recommendations_to_db(self, sell_recs: list, buy_opps: list):
        """Guarda las recomendaciones en la base de datos"""
        try:
            today = date.today()
            recommendations_data = []
            
            # Recomendaciones de venta
            for rec in sell_recs:
                rec_data = {
                    'fecha': today.isoformat(),
                    'ticker': rec['ticker'],
                    'tipo_recomendacion': 'VENTA',
                    'precio_actual': rec.get('current_price', 0),
                    'cantidad_sugerida': None,
                    'monto_sugerido': rec.get('current_value', 0),
                    'motivo': rec.get('primary_reason', ''),
                    'confianza_porcentaje': rec.get('confidence', 0)
                }
                recommendations_data.append(rec_data)
            
            # Oportunidades de compra
            for opp in buy_opps[:5]:  # Guardar top 5
                rec_data = {
                    'fecha': today.isoformat(),
                    'ticker': opp['ticker'],
                    'tipo_recomendacion': 'COMPRA',
                    'precio_actual': opp['current_price'],
                    'cantidad_sugerida': opp['suggested_quantity'],
                    'monto_sugerido': opp['suggested_investment'],
                    'motivo': ', '.join(opp['reasons'][:3]),
                    'confianza_porcentaje': opp['confidence']
                }
                recommendations_data.append(rec_data)
            
            # Insertar en BD
            if recommendations_data:
                result = self.db.supabase.table('recomendaciones').insert(recommendations_data).execute()
                print(f"✅ {len(recommendations_data)} recomendaciones guardadas en BD")
            
        except Exception as e:
            print(f"⚠️ Error guardando recomendaciones: {str(e)}")
    
    def _send_whatsapp_notification(self, sell_recs: list, buy_opps: list):
        """Envía notificación por WhatsApp"""
        try:
            from scraper.notifications.whatsapp_notifier import WhatsAppNotifier
            
            notifier = WhatsAppNotifier()
            if notifier.is_configured:
                success = notifier.send_portfolio_recommendations(
                    self.portfolio_data, sell_recs, buy_opps
                )
                if success:
                    print("✅ Mensaje enviado por WhatsApp exitosamente")
                else:
                    print("⚠️ Error enviando mensaje de WhatsApp")
            else:
                print("📱 WhatsApp no configurado - saltando notificación")
        
        except ImportError:
            print("📱 WhatsApp notifier no disponible - saltando notificación")
        except Exception as e:
            print(f"⚠️ Error enviando WhatsApp: {str(e)}")
    
    def get_portfolio_summary(self):
        """Devuelve resumen de la cartera para uso programático"""
        if not self.portfolio_data:
            return None
        
        return {
            'dinero_disponible': self.portfolio_data['dinero_disponible'],
            'valor_total': self.portfolio_data['valor_total_cartera'],
            'total_invertido': self.portfolio_data['total_invertido'],
            'ganancia_perdida': self.portfolio_data['ganancia_perdida_total'],
            'cantidad_activos': len(self.portfolio_data['activos']),
            'rendimiento_porcentaje': (self.portfolio_data['ganancia_perdida_total'] / self.portfolio_data['total_invertido'] * 100) if self.portfolio_data['total_invertido'] > 0 else 0
        }