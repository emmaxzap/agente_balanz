# analysis/financial_analyzer.py - Analizador financiero basado en rendimiento anualizado
import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Dict, List, Optional

class FinancialAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        
        # Criterios de rendimiento anualizado para decisiones
        self.criterios = {
            'venta_inmediata': 500,      # >500% anualizado = venta inmediata
            'venta_fuerte': 200,         # >200% anualizado = venta fuerte
            'venta_moderada': 100,       # >100% anualizado = considerar venta
            'mantener_superior': 50,     # 50-100% anualizado = mantener (buen rendimiento)
            'mantener_moderado': 20,     # 20-50% anualizado = mantener
            'mantener_bajo': 0,          # 0-20% anualizado = mantener pero evaluar
            'stop_loss': -50             # <-50% anualizado = stop loss
        }
    
    def analyze_asset_for_decision(self, ticker: str, current_price: float = None) -> Dict:
        """Analiza un activo para determinar si es momento de comprar, vender o mantener"""
        try:
            # 1. Obtener datos históricos
            historical_data = self._get_historical_data(ticker, days=30)
            
            if historical_data.empty:
                return self._create_no_data_result(ticker)
            
            # 2. Obtener precio actual
            if not current_price:
                current_price = self._get_current_market_price(ticker)
            
            if not current_price:
                current_price = historical_data['precio_cierre'].iloc[-1]
            
            # 3. Calcular indicadores básicos de mercado
            market_indicators = self._calculate_market_indicators(historical_data, current_price)
            
            # 4. Generar recomendación de compra
            recommendation = self._generate_buy_recommendation(ticker, market_indicators, historical_data, current_price)
            
            return recommendation
            
        except Exception as e:
            return self._create_error_result(ticker, str(e))
    
    def analyze_portfolio_for_sell_decisions(self, portfolio_assets: List[Dict]) -> List[Dict]:
        """Analiza activos de la cartera para decisiones de venta basadas en rendimiento anualizado"""
        sell_recommendations = []
        
        for asset in portfolio_assets:
            ticker = asset['ticker']
            dias_tenencia = asset.get('dias_tenencia', 1)
            ganancia_perdida_pct = asset['ganancia_perdida_porcentaje']
            current_value = asset['valor_actual_total']
            
            # Calcular rendimiento anualizado
            if dias_tenencia > 0:
                rendimiento_anualizado = (ganancia_perdida_pct / dias_tenencia) * 365
            else:
                rendimiento_anualizado = 0
            
            # Evaluar decisión de venta
            sell_decision = self._evaluate_sell_decision_financial(
                asset, rendimiento_anualizado
            )
            
            if sell_decision['recommendation'] == 'VENTA':
                sell_recommendations.append(sell_decision)
        
        return sell_recommendations
    
    def analyze_market_for_buy_opportunities(self, available_money: float, owned_tickers: List[str] = None) -> List[Dict]:
        """Analiza el mercado buscando oportunidades de compra"""
        if owned_tickers is None:
            owned_tickers = []
        
        if available_money <= 0:
            return []
        
        buy_opportunities = []
        
        try:
            # Obtener lista de activos disponibles con datos recientes
            result = self.db.supabase.table('precios_historico')\
                .select('*')\
                .eq('activo_id', activo_id)\
                .gte('fecha', start_date.isoformat())\
                .execute()
            
            if not result.data:
                return []
            
            # Obtener tickers únicos
            available_tickers = list(set([row['ticker'] for row in result.data]))
            
            # Filtrar tickers que no se poseen (diversificación)
            new_tickers = [t for t in available_tickers if t not in owned_tickers]
            
            # Analizar cada ticker
            for ticker in new_tickers[:20]:  # Limitar a 20
                try:
                    analysis = self.analyze_asset_for_decision(ticker)
                    
                    if analysis['recommendation'] == 'COMPRA':
                        # Calcular cantidad sugerida
                        suggested_investment = min(available_money * 0.2, 50000)  # Máximo 20% o $50k
                        suggested_quantity = int(suggested_investment / analysis['current_price'])
                        
                        if suggested_quantity > 0:
                            opportunity = {
                                'ticker': ticker,
                                'recommendation': 'COMPRA',
                                'current_price': analysis['current_price'],
                                'confidence': analysis['confidence'],
                                'suggested_quantity': suggested_quantity,
                                'suggested_investment': suggested_quantity * analysis['current_price'],
                                'reasons': analysis['reasons']
                            }
                            
                            buy_opportunities.append(opportunity)
                
                except Exception as e:
                    continue
            
            # Ordenar por confianza
            buy_opportunities.sort(key=lambda x: x['confidence'], reverse=True)
            
            return buy_opportunities[:5]  # Top 5 oportunidades
            
        except Exception as e:
            return []
    
    def _evaluate_sell_decision_financial(self, asset: Dict, rendimiento_anualizado: float) -> Dict:
        """Evalúa si un activo debe venderse basado en criterios financieros reales"""
        try:
            ticker = asset['ticker']
            ganancia_perdida_pct = asset['ganancia_perdida_porcentaje']
            dias_tenencia = asset.get('dias_tenencia', 1)
            current_value = asset['valor_actual_total']
            
            sell_decision = {
                'ticker': ticker,
                'recommendation': 'MANTENER',
                'confidence': 50,
                'primary_reason': '',
                'current_value': current_value,
                'gain_loss_pct': ganancia_perdida_pct,
                'dias_tenencia': dias_tenencia,
                'rendimiento_anualizado': rendimiento_anualizado
            }
            
            # Criterios basados en rendimiento anualizado
            if rendimiento_anualizado >= self.criterios['venta_inmediata']:
                sell_decision.update({
                    'recommendation': 'VENTA',
                    'confidence': 95,
                    'primary_reason': f'Rendimiento excepcional {rendimiento_anualizado:.0f}% anualizado - venta inmediata'
                })
            
            elif rendimiento_anualizado >= self.criterios['venta_fuerte']:
                sell_decision.update({
                    'recommendation': 'VENTA',
                    'confidence': 85,
                    'primary_reason': f'Rendimiento alto {rendimiento_anualizado:.0f}% anualizado - toma de ganancias'
                })
            
            elif rendimiento_anualizado >= self.criterios['venta_moderada']:
                sell_decision.update({
                    'recommendation': 'VENTA',
                    'confidence': 70,
                    'primary_reason': f'Rendimiento bueno {rendimiento_anualizado:.0f}% anualizado - considerar venta'
                })
            
            elif rendimiento_anualizado <= self.criterios['stop_loss']:
                sell_decision.update({
                    'recommendation': 'VENTA',
                    'confidence': 90,
                    'primary_reason': f'Stop loss activado {rendimiento_anualizado:.0f}% anualizado'
                })
            
            else:
                # Mantener - determinar razón específica
                if rendimiento_anualizado >= self.criterios['mantener_superior']:
                    reason = f'Buen rendimiento {rendimiento_anualizado:.0f}% anualizado - mantener'
                elif rendimiento_anualizado >= self.criterios['mantener_moderado']:
                    reason = f'Rendimiento moderado {rendimiento_anualizado:.0f}% anualizado - mantener'
                elif rendimiento_anualizado >= self.criterios['mantener_bajo']:
                    reason = f'Rendimiento bajo {rendimiento_anualizado:.0f}% anualizado - evaluar'
                else:
                    reason = f'Rendimiento negativo {rendimiento_anualizado:.0f}% anualizado - evaluar recuperación'
                
                sell_decision['primary_reason'] = reason
            
            return sell_decision
            
        except Exception as e:
            return {
                'ticker': asset.get('ticker', 'UNKNOWN'),
                'recommendation': 'MANTENER',
                'confidence': 0,
                'primary_reason': f'Error en análisis: {str(e)}'
            }
    
    def _get_historical_data(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """Obtiene datos históricos del activo"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            result = self.db.supabase.table('precios_historico')\
                .select('*')\
                .eq('ticker', ticker)\
                .gte('fecha', start_date.isoformat())\
                .lte('fecha', end_date.isoformat())\
                .order('fecha')\
                .execute()
            
            if not result.data:
                return pd.DataFrame()
            
            df = pd.DataFrame(result.data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['precio_cierre'] = df['precio_cierre_anterior'].astype(float)
            
            return df.sort_values('fecha')
            
        except Exception as e:
            return pd.DataFrame()
    
    def _get_current_market_price(self, ticker: str) -> Optional[float]:
        """Obtiene el precio actual del mercado"""
        try:
            result = self.db.supabase.table('precios_historico')\
                .select('precio_actual')\
                .eq('ticker', ticker)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return float(result.data[0]['precio_actual'])
            
            return None
            
        except Exception as e:
            return None
    
    def _calculate_market_indicators(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Calcula indicadores básicos de mercado"""
        try:
            prices = df['precio_cierre'].values
            
            indicators = {
                'current_price': current_price,
                'data_points': len(prices)
            }
            
            if len(prices) < 5:
                return indicators
            
            # Indicadores básicos
            indicators['sma_5'] = np.mean(prices[-5:])
            indicators['sma_10'] = np.mean(prices[-10:]) if len(prices) >= 10 else indicators['sma_5']
            indicators['max_20'] = np.max(prices[-20:]) if len(prices) >= 20 else np.max(prices)
            indicators['min_20'] = np.min(prices[-20:]) if len(prices) >= 20 else np.min(prices)
            
            # Posición relativa en el rango
            if indicators['max_20'] != indicators['min_20']:
                indicators['position_in_range'] = (current_price - indicators['min_20']) / (indicators['max_20'] - indicators['min_20'])
            
            # Tendencia simple (últimos 7 días)
            if len(prices) >= 7:
                trend_slope = np.polyfit(range(7), prices[-7:], 1)[0]
                indicators['trend'] = 'UP' if trend_slope > 0 else 'DOWN' if trend_slope < 0 else 'FLAT'
            
            return indicators
            
        except Exception as e:
            return {'current_price': current_price, 'data_points': 0}
    
    def _generate_buy_recommendation(self, ticker: str, indicators: Dict, historical_data: pd.DataFrame, current_price: float) -> Dict:
        """Genera recomendación de compra basada en indicadores de mercado"""
        try:
            recommendation = {
                'ticker': ticker,
                'current_price': current_price,
                'recommendation': 'MANTENER',
                'confidence': 50,
                'reasons': [],
                'indicators': indicators
            }
            
            buy_score = 0
            reasons = []
            
            # 1. Precio cerca del mínimo (oportunidad)
            position = indicators.get('position_in_range', 0.5)
            if position < 0.3:  # Cerca del mínimo
                buy_score += 30
                reasons.append(f"Precio cerca del mínimo reciente (posición {position:.1%})")
            
            # 2. Tendencia alcista
            if indicators.get('trend') == 'UP':
                buy_score += 20
                reasons.append("Tendencia alcista detectada")
            
            # 3. Precio por encima de media móvil (momentum positivo)
            if indicators.get('sma_5') and current_price > indicators['sma_5']:
                buy_score += 15
                reasons.append("Precio por encima de media móvil")
            
            # Determinar recomendación final
            if buy_score >= 40:
                recommendation.update({
                    'recommendation': 'COMPRA',
                    'confidence': min(90, 50 + buy_score),
                    'reasons': reasons
                })
            else:
                recommendation['reasons'] = ['Señales de compra insuficientes']
            
            return recommendation
            
        except Exception as e:
            return self._create_error_result(ticker, str(e))
    
    def _create_no_data_result(self, ticker: str) -> Dict:
        """Crea resultado cuando no hay datos suficientes"""
        return {
            'ticker': ticker,
            'recommendation': 'MANTENER',
            'confidence': 0,
            'reasons': ['Datos históricos insuficientes'],
            'current_price': 0,
            'indicators': {}
        }
    
    def _create_error_result(self, ticker: str, error_msg: str) -> Dict:
        """Crea resultado cuando hay error en el análisis"""
        return {
            'ticker': ticker,
            'recommendation': 'MANTENER',
            'confidence': 0,
            'reasons': [f'Error: {error_msg}'],
            'current_price': 0,
            'indicators': {}
        }