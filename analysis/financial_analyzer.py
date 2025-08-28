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
            # 1. Obtener datos históricos con período más largo
            historical_data = self._get_historical_data(ticker, days=60)
            
            if historical_data.empty:
                return self._create_no_data_result(ticker)
            
            # 2. Obtener precio actual
            if not current_price:
                current_price = self._get_current_market_price(ticker)
            
            if not current_price:
                current_price = historical_data['precio_cierre'].iloc[-1]
            
            # 3. Calcular indicadores básicos de mercado
            market_indicators = self._calculate_market_indicators(historical_data, current_price)
            
            # 4. Generar recomendación de compra con rigor estadístico
            recommendation = self._generate_buy_recommendation_rigorous(ticker, market_indicators, historical_data, current_price)
            
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
        """Analiza el mercado buscando oportunidades de compra con criterios rigurosos"""
        if owned_tickers is None:
            owned_tickers = []
        
        if available_money <= 0:
            return []
        
        buy_opportunities = []
        
        try:
            # Obtener tickers con datos recientes
            end_date = date.today()
            start_date = end_date - timedelta(days=10)
            
            result = self.db.supabase.table('precios_historico')\
                .select('ticker')\
                .gte('fecha', start_date.isoformat())\
                .execute()
            
            if not result.data:
                return []
            
            # Obtener tickers únicos
            available_tickers = list(set([row['ticker'] for row in result.data]))
            
            # Filtrar tickers que no se poseen
            new_tickers = [t for t in available_tickers if t not in owned_tickers]
            
            print(f"Analizando {len(new_tickers)} tickers para oportunidades de compra...")
            
            valid_analyses = 0
            insufficient_data = 0
            
            # Analizar cada ticker
            for i, ticker in enumerate(new_tickers[:25]):
                try:
                    if i % 5 == 0:
                        print(f"   Progreso: {i+1}/{min(25, len(new_tickers))}")
                    
                    analysis = self.analyze_asset_for_decision(ticker)
                    
                    # Verificar si el análisis es válido
                    if 'insufficient_data' in str(analysis.get('reasons', [])):
                        insufficient_data += 1
                        continue
                    
                    valid_analyses += 1
                    
                    if analysis['recommendation'] == 'COMPRA':
                        # Calcular cantidad sugerida
                        suggested_investment = min(available_money * 0.15, 40000)
                        suggested_quantity = int(suggested_investment / analysis['current_price'])
                        
                        if suggested_quantity > 0:
                            opportunity = {
                                'ticker': ticker,
                                'recommendation': 'COMPRA',
                                'current_price': analysis['current_price'],
                                'confidence': analysis['confidence'],
                                'suggested_quantity': suggested_quantity,
                                'suggested_investment': suggested_quantity * analysis['current_price'],
                                'reasons': analysis['reasons'],
                                'score_details': analysis.get('score_details', {}),
                                'data_quality': analysis.get('indicators', {}).get('data_points', 0)
                            }
                            
                            buy_opportunities.append(opportunity)
                
                except Exception as e:
                    continue
            
            # Ordenar por confianza y calidad de datos
            buy_opportunities.sort(key=lambda x: (x['confidence'], x['data_quality']), reverse=True)
            
            print(f"Análisis completado:")
            print(f"   Análisis válidos: {valid_analyses}")
            print(f"   Datos insuficientes: {insufficient_data}")
            print(f"   Oportunidades encontradas: {len(buy_opportunities)}")
            
            return buy_opportunities[:8]
            
        except Exception as e:
            print(f"Error buscando oportunidades: {str(e)}")
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
    
    def _get_historical_data(self, ticker: str, days: int = 60) -> pd.DataFrame:
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
            df['precio_cierre'] = pd.to_numeric(df['precio_cierre'], errors='coerce')
            
            # Limpiar datos nulos
            df = df.dropna(subset=['precio_cierre'])
            
            return df.sort_values('fecha')
            
        except Exception as e:
            return pd.DataFrame()
    
    def _get_current_market_price(self, ticker: str) -> Optional[float]:
        """Obtiene el precio actual del mercado"""
        try:
            result = self.db.supabase.table('precios_historico')\
                .select('precio_cierre')\
                .eq('ticker', ticker)\
                .order('fecha', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and result.data[0]['precio_cierre']:
                return float(result.data[0]['precio_cierre'])
            
            return None
            
        except Exception as e:
            return None
    
    def _calculate_market_indicators(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Calcula indicadores básicos de mercado con criterios estadísticamente válidos"""
        try:
            prices = df['precio_cierre'].values
            
            indicators = {
                'current_price': current_price,
                'data_points': len(prices),
                'data_quality': self._assess_data_quality(len(prices))
            }
            
            # Mínimo estadísticamente válido para análisis básico
            if len(prices) < 7:
                indicators['insufficient_data'] = True
                return indicators
            
            # SMA 5 (requiere mínimo 5 puntos)
            if len(prices) >= 5:
                indicators['sma_5'] = np.mean(prices[-5:])
            
            # SMA 10 (requiere mínimo 10 puntos)
            if len(prices) >= 10:
                indicators['sma_10'] = np.mean(prices[-10:])
            else:
                indicators['sma_10'] = indicators.get('sma_5', current_price)
            
            # Max/Min range - requiere mínimo 14 puntos para ser confiable
            if len(prices) >= 14:
                max_min_period = min(30, len(prices))
                indicators['max_range'] = np.max(prices[-max_min_period:])
                indicators['min_range'] = np.min(prices[-max_min_period:])
                indicators['range_reliability'] = 'high'
            else:
                # Para pocos datos, usar todo el período disponible pero marcarlo como menos confiable
                indicators['max_range'] = np.max(prices)
                indicators['min_range'] = np.min(prices)
                indicators['range_reliability'] = 'low'
            
            # Posición relativa en el rango
            if indicators['max_range'] != indicators['min_range']:
                indicators['position_in_range'] = (current_price - indicators['min_range']) / (indicators['max_range'] - indicators['min_range'])
            else:
                indicators['position_in_range'] = 0.5
            
            # Tendencia - requiere mínimo 7 puntos para regresión confiable
            trend_period = min(10, len(prices))
            trend_slope = np.polyfit(range(trend_period), prices[-trend_period:], 1)[0]
            indicators['trend'] = 'UP' if trend_slope > 0 else 'DOWN' if trend_slope < 0 else 'FLAT'
            indicators['trend_slope'] = trend_slope
            
            # Volatilidad - requiere mínimo 10 puntos para desviación estándar meaningful
            if len(prices) >= 10:
                recent_std = np.std(prices[-10:])
                avg_price = np.mean(prices[-10:])
                indicators['volatility'] = (recent_std / avg_price) * 100 if avg_price > 0 else 0
            
            return indicators
            
        except Exception as e:
            return {'current_price': current_price, 'data_points': 0, 'insufficient_data': True}
    
    def _assess_data_quality(self, data_points: int) -> str:
        """Evalúa la calidad de los datos basado en cantidad de puntos"""
        if data_points >= 30:
            return 'excellent'
        elif data_points >= 14:
            return 'good'
        elif data_points >= 7:
            return 'adequate'
        else:
            return 'insufficient'
    
    def _generate_buy_recommendation_rigorous(self, ticker: str, indicators: Dict, historical_data: pd.DataFrame, current_price: float) -> Dict:
        """Genera recomendación de compra con criterios rigurosos basados en calidad de datos"""
        try:
            recommendation = {
                'ticker': ticker,
                'current_price': current_price,
                'recommendation': 'MANTENER',
                'confidence': 50,
                'reasons': [],
                'indicators': indicators,
                'score_details': {}
            }
            
            # Verificar si hay datos suficientes
            if indicators.get('insufficient_data'):
                recommendation['reasons'] = ['Datos históricos insuficientes para análisis riguroso (mínimo 7 días)']
                return recommendation
            
            buy_score = 0
            reasons = []
            score_details = {}
            data_points = indicators.get('data_points', 0)
            data_quality = indicators.get('data_quality', 'insufficient')
            
            # CRITERIO 1: Posición en rango (ajustado por calidad de datos)
            position = indicators.get('position_in_range', 0.5)
            range_reliability = indicators.get('range_reliability', 'low')
            
            if position <= 0.2:  # Muy cerca del mínimo
                points = 35 if range_reliability == 'high' else 25
                reason = f"Precio muy cerca del mínimo ({position:.1%})"
            elif position <= 0.4:  # Cerca del mínimo
                points = 25 if range_reliability == 'high' else 20
                reason = f"Precio cerca del mínimo ({position:.1%})"
            elif position <= 0.6:  # Posición media-baja
                points = 15
                reason = f"Precio en posición favorable ({position:.1%})"
            elif position <= 0.8:  # Posición media-alta
                points = 5
                reason = f"Precio en posición media ({position:.1%})"
            else:  # Cerca del máximo
                points = 0
                reason = f"Precio cerca del máximo ({position:.1%})"
            
            if range_reliability == 'low':
                reason += " (confianza limitada por pocos datos)"
            
            buy_score += points
            if points > 0:
                reasons.append(reason)
            
            score_details['position'] = {
                'value': position,
                'points': points,
                'reason': reason
            }
            
            # CRITERIO 2: Tendencia
            trend = indicators.get('trend', 'FLAT')
            trend_slope = indicators.get('trend_slope', 0)
            
            if trend == 'UP':
                if abs(trend_slope) > 100:  # Tendencia fuerte
                    points = 30
                    reason = "Tendencia alcista fuerte"
                else:  # Tendencia moderada
                    points = 20
                    reason = "Tendencia alcista moderada"
            elif trend == 'FLAT':
                points = 10
                reason = "Tendencia lateral (estable)"
            else:  # DOWN
                if abs(trend_slope) > 100:  # Caída fuerte (oportunidad?)
                    points = 5
                    reason = "Tendencia bajista (posible rebote)"
                else:
                    points = 0
                    reason = "Tendencia bajista moderada"
            
            buy_score += points
            if points > 0:
                reasons.append(reason)
            
            score_details['trend'] = {
                'value': trend,
                'slope': trend_slope,
                'points': points,
                'reason': reason
            }
            
            # CRITERIO 3: Precio vs SMA - MÁS FLEXIBLE
            sma_5 = indicators.get('sma_5')
            if sma_5:
                sma_ratio = current_price / sma_5
                
                if sma_ratio >= 1.05:  # 5% por encima
                    points = 20
                    reason = f"Precio fuertemente por encima de SMA ({sma_ratio:.2%})"
                elif sma_ratio >= 1.02:  # 2% por encima
                    points = 15
                    reason = f"Precio por encima de SMA ({sma_ratio:.2%})"
                elif sma_ratio >= 0.98:  # Cerca de SMA
                    points = 10
                    reason = f"Precio cerca de SMA ({sma_ratio:.2%})"
                else:  # Por debajo
                    points = 5
                    reason = f"Precio por debajo de SMA ({sma_ratio:.2%}) - posible oportunidad"
                
                buy_score += points
                reasons.append(reason)
                
                score_details['sma'] = {
                    'current_vs_sma': sma_ratio,
                    'points': points,
                    'reason': reason
                }
            
            # CRITERIO 4: Volatilidad (solo con datos suficientes)
            volatility = indicators.get('volatility', 0)
            if volatility > 0 and data_points >= 10:
                if 2 <= volatility <= 8:  # Volatilidad saludable
                    points = 10
                    reason = f"Volatilidad saludable ({volatility:.1f}%)"
                    buy_score += points
                    reasons.append(reason)
                
                score_details['volatility'] = {
                    'value': volatility,
                    'points': points if 2 <= volatility <= 8 else 0,
                    'reason': reason if 2 <= volatility <= 8 else f"Volatilidad {volatility:.1f}% fuera del rango óptimo"
                }
            
            # CRITERIO 5: Calidad de datos
            if data_quality == 'excellent':
                points = 10
                reason = f"Análisis con datos excelentes ({data_points} días)"
            elif data_quality == 'good':
                points = 5
                reason = f"Análisis con datos buenos ({data_points} días)"
            elif data_quality == 'adequate':
                points = 2
                reason = f"Análisis con datos adecuados ({data_points} días)"
            else:
                points = 0
                reason = f"Datos limitados ({data_points} días)"
            
            if points > 0:
                buy_score += points
                reasons.append(reason)
            
            score_details['data_quality'] = {
                'days': data_points,
                'quality': data_quality,
                'points': points,
                'reason': reason
            }
            
            # UMBRALES RIGUROSOS basados en calidad de datos
            if data_quality == 'excellent':
                threshold = 45  # Más estricto con datos excelentes
            elif data_quality == 'good':
                threshold = 35  # Moderadamente estricto
            elif data_quality == 'adequate':
                threshold = 25  # Más permisivo con datos limitados
            else:
                threshold = 50  # Muy estricto si datos insuficientes
            
            # Determinar recomendación final
            if buy_score >= threshold:
                confidence = min(95, 40 + buy_score)
                recommendation.update({
                    'recommendation': 'COMPRA',
                    'confidence': confidence,
                    'reasons': reasons
                })
            else:
                recommendation['reasons'] = [f'Score insuficiente: {buy_score}/{threshold} puntos (calidad datos: {data_quality})']
            
            recommendation['score_details'] = {
                'total_score': buy_score,
                'threshold': threshold,
                'data_quality': data_quality,
                'breakdown': score_details
            }
            
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
            'indicators': {},
            'score_details': {'total_score': 0, 'threshold': 0, 'breakdown': {}}
        }
    
    def _create_error_result(self, ticker: str, error_msg: str) -> Dict:
        """Crea resultado cuando hay error en el análisis"""
        return {
            'ticker': ticker,
            'recommendation': 'MANTENER',
            'confidence': 0,
            'reasons': [f'Error: {error_msg}'],
            'current_price': 0,
            'indicators': {},
            'score_details': {'total_score': 0, 'threshold': 0, 'breakdown': {}}
        }