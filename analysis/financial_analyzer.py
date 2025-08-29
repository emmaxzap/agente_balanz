# analysis/financial_analyzer.py - Analizador financiero profesional para corto plazo
import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Dict, List, Optional

class FinancialAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        
        # Criterios profesionales ajustados por marco temporal
        self.criterios_corto_plazo = {
            # Posiciones 0-3 días
            'new_stop_loss': -8,               # Stop loss más estricto
            'new_profit_taking': 15,           # Tomar ganancias más rápido
            'new_volatility_limit': 12,        # Límite de volatilidad diaria
            
            # Posiciones 4-30 días  
            'established_stop_loss': -12,      # Stop loss moderado
            'established_profit_taking': 25,   # Tomar ganancias moderado
            'established_volatility_limit': 8, # Volatilidad moderada
            
            # Posiciones 30+ días
            'mature_stop_loss': -20,           # Stop loss flexible
            'mature_profit_taking': 40,        # Tomar ganancias conservador
            'mature_volatility_limit': 15,     # Mayor tolerancia volatilidad
            
            # Criterios generales
            'momentum_threshold': 3,           # Días para confirmar momentum
            'technical_weight': 0.8,           # 80% peso análisis técnico vs fundamental
        }
    
    def analyze_asset_for_decision(self, ticker: str, current_price: float = None) -> Dict:
        """Análisis de activo optimizado para decisiones de corto plazo"""
        try:
            # 1. Obtener datos históricos con enfoque en corto plazo
            historical_data = self._get_historical_data(ticker, days=30)  # Reducido a 30 días
            
            if historical_data.empty:
                return self._create_no_data_result(ticker)
            
            # 2. Obtener precio actual
            if not current_price:
                current_price = self._get_current_market_price(ticker)
            
            if not current_price:
                current_price = historical_data['precio_cierre'].iloc[-1]
            
            # 3. Calcular indicadores técnicos específicos para corto plazo
            technical_indicators = self._calculate_short_term_indicators(historical_data, current_price)
            
            # 4. Generar recomendación con peso en análisis técnico
            recommendation = self._generate_short_term_recommendation(ticker, technical_indicators, historical_data, current_price)
            
            return recommendation
            
        except Exception as e:
            return self._create_error_result(ticker, str(e))
    
    def analyze_portfolio_for_sell_decisions(self, portfolio_assets: List[Dict]) -> List[Dict]:
        """Análisis profesional de decisiones de venta según marco temporal"""
        sell_recommendations = []
        
        for asset in portfolio_assets:
            ticker = asset['ticker']
            dias_tenencia = max(asset.get('dias_tenencia', 0), 0)
            ganancia_perdida_pct = asset['ganancia_perdida_porcentaje']
            current_value = asset['valor_actual_total']
            
            # Evaluar decisión de venta con criterios específicos por plazo
            sell_decision = self._evaluate_sell_decision_by_timeframe(
                asset, dias_tenencia, ganancia_perdida_pct, current_value, ticker
            )
            
            if sell_decision['recommendation'] == 'VENTA':
                sell_recommendations.append(sell_decision)
        
        return sell_recommendations
    
    def analyze_market_for_buy_opportunities(self, available_money: float, owned_tickers: List[str] = None) -> List[Dict]:
        """Análisis de oportunidades de compra con criterios técnicos intensivos"""
        if owned_tickers is None:
            owned_tickers = []
        
        if available_money <= 0:
            return []
        
        buy_opportunities = []
        
        try:
            # Obtener tickers con datos recientes
            end_date = date.today()
            start_date = end_date - timedelta(days=7)  # Solo últimos 7 días
            
            result = self.db.supabase.table('precios_historico')\
                .select('ticker')\
                .gte('fecha', start_date.isoformat())\
                .execute()
            
            if not result.data:
                return []
            
            available_tickers = list(set([row['ticker'] for row in result.data]))
            new_tickers = [t for t in available_tickers if t not in owned_tickers]
            
            print(f"Analizando {len(new_tickers)} tickers para oportunidades técnicas...")
            
            valid_analyses = 0
            
            # Analizar con enfoque técnico intensivo
            for i, ticker in enumerate(new_tickers[:20]):  # Top 20
                try:
                    if i % 5 == 0:
                        print(f"   Progreso: {i+1}/{min(20, len(new_tickers))}")
                    
                    analysis = self.analyze_asset_for_decision(ticker)
                    
                    if analysis['recommendation'] == 'COMPRA' and analysis['confidence'] >= 85:
                        valid_analyses += 1
                        
                        # Tamaño de posición conservador para nuevas posiciones
                        max_investment = min(available_money * 0.12, 15000)  # 12% o $15k máximo
                        suggested_quantity = max(1, int(max_investment / analysis['current_price']))
                        
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
                                'technical_strength': analysis.get('indicators', {}).get('trend_strength', 0)
                            }
                            
                            buy_opportunities.append(opportunity)
                
                except Exception as e:
                    continue
            
            # Ordenar por strength técnica y confianza
            buy_opportunities.sort(
                key=lambda x: (x['technical_strength'], x['confidence']), 
                reverse=True
            )
            
            print(f"Análisis técnico completado:")
            print(f"   Análisis válidos: {valid_analyses}")
            print(f"   Oportunidades técnicas: {len(buy_opportunities)}")
            
            return buy_opportunities[:8]  # Top 8 oportunidades técnicas
            
        except Exception as e:
            print(f"Error buscando oportunidades técnicas: {str(e)}")
            return []
    
    def _evaluate_sell_decision_by_timeframe(self, asset: Dict, dias_tenencia: int, ganancia_perdida_pct: float, current_value: float, ticker: str) -> Dict:
        """Evalúa venta según marco temporal específico"""
        try:
            sell_decision = {
                'ticker': ticker,
                'recommendation': 'MANTENER',
                'confidence': 50,
                'primary_reason': '',
                'current_value': current_value,
                'gain_loss_pct': ganancia_perdida_pct,
                'dias_tenencia': dias_tenencia,
                'timeframe_category': self._get_timeframe_category(dias_tenencia)
            }
            
            # Determinar criterios según plazo
            if dias_tenencia <= 3:
                # Posiciones nuevas - Criterios más estrictos
                stop_threshold = self.criterios_corto_plazo['new_stop_loss']
                profit_threshold = self.criterios_corto_plazo['new_profit_taking']
                category = "nueva"
            elif dias_tenencia <= 30:
                # Posiciones establecidas - Criterios moderados
                stop_threshold = self.criterios_corto_plazo['established_stop_loss']
                profit_threshold = self.criterios_corto_plazo['established_profit_taking']
                category = "establecida"
            else:
                # Posiciones maduras - Criterios flexibles
                stop_threshold = self.criterios_corto_plazo['mature_stop_loss']
                profit_threshold = self.criterios_corto_plazo['mature_profit_taking']
                category = "madura"
            
            # Obtener análisis técnico para contexto
            technical_analysis = self.analyze_asset_for_decision(ticker)
            momentum = technical_analysis.get('indicators', {}).get('trend', 'FLAT')
            
            # Evaluar según criterios específicos
            if ganancia_perdida_pct <= stop_threshold:
                # Stop loss activado
                sell_decision.update({
                    'recommendation': 'VENTA',
                    'confidence': 95,
                    'primary_reason': f'Stop loss activado - pérdida {ganancia_perdida_pct:.1f}% en posición {category} ({dias_tenencia} días)'
                })
            
            elif ganancia_perdida_pct >= profit_threshold:
                # Tomar ganancias - ajustar por momentum
                if momentum == 'UP' and dias_tenencia <= 7:
                    # Momentum positivo en posición reciente - tomar solo parcial
                    confidence = 70
                    reason = f'Toma ganancias parcial - {ganancia_perdida_pct:.1f}% en posición {category} con momentum positivo'
                else:
                    # Sin momentum fuerte - tomar ganancias completas
                    confidence = 85
                    reason = f'Toma ganancias - {ganancia_perdida_pct:.1f}% en posición {category}'
                
                sell_decision.update({
                    'recommendation': 'VENTA',
                    'confidence': confidence,
                    'primary_reason': reason
                })
            
            elif dias_tenencia == 0 and ganancia_perdida_pct <= -5:
                # Stop loss rápido para posiciones del mismo día
                sell_decision.update({
                    'recommendation': 'VENTA',
                    'confidence': 90,
                    'primary_reason': f'Stop loss rápido - pérdida {ganancia_perdida_pct:.1f}% en posición del mismo día'
                })
            
            else:
                # Mantener - dar razón específica
                if momentum == 'DOWN' and ganancia_perdida_pct < 0:
                    reason = f'Mantener con precaución - pérdida {ganancia_perdida_pct:.1f}% y momentum negativo'
                    sell_decision['confidence'] = 30  # Baja confianza en mantener
                elif momentum == 'UP' and ganancia_perdida_pct > 0:
                    reason = f'Mantener - ganancia {ganancia_perdida_pct:.1f}% con momentum positivo'
                    sell_decision['confidence'] = 80  # Alta confianza en mantener
                else:
                    reason = f'Mantener posición {category} - {ganancia_perdida_pct:+.1f}% en {dias_tenencia} días'
                
                sell_decision['primary_reason'] = reason
            
            return sell_decision
            
        except Exception as e:
            return {
                'ticker': ticker,
                'recommendation': 'MANTENER',
                'confidence': 0,
                'primary_reason': f'Error en análisis: {str(e)}'
            }
    
    def _get_timeframe_category(self, dias_tenencia: int) -> str:
        """Determina categoría de marco temporal"""
        if dias_tenencia <= 3:
            return "nueva"
        elif dias_tenencia <= 30:
            return "establecida"
        else:
            return "madura"
    
    def _calculate_short_term_indicators(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Calcula indicadores técnicos optimizados para corto plazo"""
        try:
            prices = df['precio_cierre'].values
            
            indicators = {
                'current_price': current_price,
                'data_points': len(prices),
                'timeframe': 'short_term'
            }
            
            if len(prices) < 3:
                indicators['insufficient_data'] = True
                return indicators
            
            # SMA más cortas para análisis de corto plazo
            if len(prices) >= 3:
                indicators['sma_3'] = np.mean(prices[-3:])
            
            if len(prices) >= 5:
                indicators['sma_5'] = np.mean(prices[-5:])
            
            if len(prices) >= 7:
                indicators['sma_7'] = np.mean(prices[-7:])
            
            # Rango de precios reciente
            recent_period = min(10, len(prices))
            indicators['max_recent'] = np.max(prices[-recent_period:])
            indicators['min_recent'] = np.min(prices[-recent_period:])
            
            # Posición en rango
            if indicators['max_recent'] != indicators['min_recent']:
                indicators['position_in_range'] = (current_price - indicators['min_recent']) / (indicators['max_recent'] - indicators['min_recent'])
            else:
                indicators['position_in_range'] = 0.5
            
            # Tendencia de corto plazo
            trend_period = min(5, len(prices))
            if trend_period >= 3:
                trend_slope = np.polyfit(range(trend_period), prices[-trend_period:], 1)[0]
                indicators['trend_slope'] = trend_slope
                
                # Clasificar tendencia con mayor sensibilidad para corto plazo
                if trend_slope > 10:  # Más sensible para detectar cambios rápidos
                    indicators['trend'] = 'UP'
                elif trend_slope < -10:
                    indicators['trend'] = 'DOWN'
                else:
                    indicators['trend'] = 'FLAT'
            
            # Volatilidad reciente
            if len(prices) >= 5:
                recent_returns = np.diff(prices[-5:]) / prices[-6:-1] * 100
                indicators['recent_volatility'] = np.std(recent_returns)
            
            # Momentum de corto plazo (últimos 3 vs 3 anteriores)
            if len(prices) >= 6:
                recent_avg = np.mean(prices[-3:])
                previous_avg = np.mean(prices[-6:-3])
                indicators['short_momentum'] = (recent_avg - previous_avg) / previous_avg * 100
            
            return indicators
            
        except Exception as e:
            return {'current_price': current_price, 'data_points': 0, 'insufficient_data': True}
    
    def _generate_short_term_recommendation(self, ticker: str, indicators: Dict, historical_data: pd.DataFrame, current_price: float) -> Dict:
        """Genera recomendación optimizada para trading de corto plazo"""
        try:
            recommendation = {
                'ticker': ticker,
                'current_price': current_price,
                'recommendation': 'MANTENER',
                'confidence': 50,
                'reasons': [],
                'indicators': indicators
            }
            
            if indicators.get('insufficient_data'):
                recommendation['reasons'] = ['Datos insuficientes para análisis técnico de corto plazo']
                return recommendation
            
            buy_score = 0
            reasons = []
            
            # 1. Posición en rango (mayor peso para corto plazo)
            position = indicators.get('position_in_range', 0.5)
            if position <= 0.15:  # Muy cerca del mínimo
                buy_score += 40
                reasons.append(f"Precio muy cerca del mínimo reciente ({position:.1%})")
            elif position <= 0.35:  # Cerca del mínimo
                buy_score += 30
                reasons.append(f"Precio cerca del mínimo reciente ({position:.1%})")
            elif position >= 0.85:  # Cerca del máximo
                buy_score -= 20
                reasons.append(f"Precio cerca del máximo reciente ({position:.1%})")
            
            # 2. Tendencia de corto plazo (peso crítico)
            trend = indicators.get('trend', 'FLAT')
            trend_slope = indicators.get('trend_slope', 0)
            
            if trend == 'UP':
                if abs(trend_slope) > 50:  # Tendencia fuerte
                    buy_score += 35
                    reasons.append("Tendencia alcista fuerte de corto plazo")
                else:
                    buy_score += 25
                    reasons.append("Tendencia alcista moderada")
            elif trend == 'DOWN':
                buy_score -= 25
                reasons.append("Tendencia bajista de corto plazo")
            
            # 3. Momentum de corto plazo
            short_momentum = indicators.get('short_momentum', 0)
            if short_momentum > 3:  # Momentum positivo fuerte
                buy_score += 20
                reasons.append(f"Momentum positivo (+{short_momentum:.1f}%)")
            elif short_momentum < -3:  # Momentum negativo
                buy_score -= 15
                reasons.append(f"Momentum negativo ({short_momentum:.1f}%)")
            
            # 4. Volatilidad (controlar riesgo)
            volatility = indicators.get('recent_volatility', 0)
            if 2 <= volatility <= 6:  # Volatilidad saludable
                buy_score += 10
                reasons.append(f"Volatilidad saludable ({volatility:.1f}%)")
            elif volatility > 10:  # Muy volátil
                buy_score -= 10
                reasons.append(f"Alta volatilidad ({volatility:.1f}%)")
            
            # 5. Relación con medias móviles
            sma_3 = indicators.get('sma_3')
            sma_5 = indicators.get('sma_5')
            
            if sma_3 and sma_5 and current_price > sma_3 > sma_5:
                buy_score += 15
                reasons.append("Precio por encima de medias móviles ascendentes")
            elif sma_3 and current_price > sma_3:
                buy_score += 10
                reasons.append("Precio por encima de SMA corta")
            
            # Determinar recomendación final (umbrales ajustados para corto plazo)
            data_quality = indicators.get('data_points', 0)
            if data_quality >= 10:
                threshold = 60  # Umbral alto con datos suficientes
            elif data_quality >= 5:
                threshold = 50  # Umbral moderado
            else:
                threshold = 70  # Umbral alto si pocos datos
            
            if buy_score >= threshold:
                confidence = min(95, 50 + buy_score)
                recommendation.update({
                    'recommendation': 'COMPRA',
                    'confidence': confidence,
                    'reasons': reasons
                })
            else:
                recommendation['reasons'] = [f'Señales técnicas insuficientes: {buy_score}/{threshold} puntos']
            
            recommendation['score_details'] = {
                'total_score': buy_score,
                'threshold': threshold,
                'data_quality': data_quality,
                'timeframe': 'short_term'
            }
            
            return recommendation
            
        except Exception as e:
            return self._create_error_result(ticker, str(e))
    
    def _get_historical_data(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """Obtiene datos históricos optimizados para corto plazo"""
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
    
    def _create_no_data_result(self, ticker: str) -> Dict:
        """Crea resultado cuando no hay datos suficientes"""
        return {
            'ticker': ticker,
            'recommendation': 'MANTENER',
            'confidence': 0,
            'reasons': ['Datos históricos insuficientes para análisis de corto plazo'],
            'current_price': 0,
            'indicators': {},
            'score_details': {'total_score': 0, 'threshold': 0, 'timeframe': 'short_term'}
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
            'score_details': {'total_score': 0, 'threshold': 0, 'timeframe': 'short_term'}
        }