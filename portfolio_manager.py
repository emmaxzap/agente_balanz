# portfolio_manager.py - Motor principal del administrador de cartera
from datetime import date
import sys
from pathlib import Path

# Agregar rutas necesarias
sys.path.append(str(Path(__file__).parent))

from scraper.cartera_extractor import CarteraExtractor
from analysis.technical_analyzer import TechnicalAnalyzer
from database.database_manager import SupabaseManager

class PortfolioManager:
    def __init__(self, page):
        self.page = page
        self.db = SupabaseManager()
        self.cartera_extractor = CarteraExtractor(page)
        self.analyzer = TechnicalAnalyzer(self.db)
        self.portfolio_data = None
    
    def run_complete_analysis(self):
        """
        Ejecuta análisis completo de la cartera:
        1. Extrae datos de la cartera
        2. Analiza posiciones existentes para venta
        3. Busca oportunidades de compra
        4. Genera recomendaciones
        5. Guarda resultados
        6. Envía notificación por WhatsApp
        """
        try:
            print("\n🚀 INICIANDO ANÁLISIS COMPLETO DE CARTERA")
            print("="*60)
            
            # 1. Extraer datos de la cartera
            self.portfolio_data = self.cartera_extractor.extract_portfolio_data()
            
            if not self.portfolio_data:
                print("❌ No se pudieron extraer datos de la cartera")
                return False
            
            # 2. Guardar snapshot de la cartera en BD
            self.cartera_extractor.save_portfolio_to_db(self.portfolio_data, self.db)
            
            # 3. Análisis de posiciones existentes (decisiones de venta)
            sell_recommendations = self.analyzer.analyze_portfolio_for_sell_decisions(
                self.portfolio_data['activos']
            )
            
            # 4. Análisis de mercado (oportunidades de compra)
            owned_tickers = [asset['ticker'] for asset in self.portfolio_data['activos']]
            buy_opportunities = self.analyzer.analyze_market_for_buy_opportunities(
                self.portfolio_data['dinero_disponible'],
                owned_tickers
            )
            
            # 5. Generar informe consolidado
            self._generate_recommendations_report(sell_recommendations, buy_opportunities)
            
            # 6. Guardar recomendaciones en BD
            self._save_recommendations_to_db(sell_recommendations, buy_opportunities)
            
            # 7. Enviar notificación por WhatsApp
            self._send_whatsapp_notification(sell_recommendations, buy_opportunities)
            
            print("\n✅ ANÁLISIS COMPLETO FINALIZADO")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en análisis completo: {str(e)}")
            return False
    
    def _generate_recommendations_report(self, sell_recs: list, buy_opps: list):
        """Genera reporte consolidado de recomendaciones"""
        
        print("\n" + "="*60)
        print("📋 REPORTE DE RECOMENDACIONES")
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
                print(f"    🎯 Retorno esperado: {opp['expected_return']:+.1f}%")
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
        
        # Cálculo de cash flow neto
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
            
            print(f"\n⚠️  IMPORTANTE:")
            print(f"   • Estas son sugerencias basadas en análisis técnico")
            print(f"   • Considere factores fundamentales y noticias")
            print(f"   • No arriesgue más del 5-10% en una sola posición")
            print(f"   • Use stop-loss para limitar pérdidas")
            
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
                    'precio_objetivo': None,
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
                    'precio_objetivo': opp.get('target_price'),
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