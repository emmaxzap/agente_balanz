# analysis/technical_analyzer.py - Analizador técnico de precios
import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional

class TechnicalAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def analyze_asset_for_decision(self, ticker: str, current_price: float = None) -> Dict:
        """
        Analiza un activo para determinar si es momento de comprar, vender o mantener
        
        Args:
            ticker: Símbolo del activo
            current_price: Precio actual (opcional, se obtiene de BD si no se provee)
            
        Returns:
            Dict con recomendación y análisis
        """
        try:
            print(f"🔍 Analizando {ticker}...")
            
            # 1. Obtener datos históricos
            historical_data = self._get_historical_data(ticker, days=30)
            
            if historical_data.empty:
                return self._create_no_data_result(ticker)
            
            # 2. Obtener precio actual
            if not current_price:
                current_price = self._get_current_market_price(ticker)
            
            if not current_price:
                current_price = historical_data['precio_cierre'].iloc[-1]
            
            # 3. Calcular indicadores técnicos
            indicators = self._calculate_technical_indicators(historical_data, current_price)
            
            # 4. Determinar recomendación
            recommendation = self._generate_recommendation(ticker, indicators, historical_data, current_price)
            
            return recommendation
            
        except Exception as e:
            print(f"❌ Error analizando {ticker}: {str(e)}")
            return self._create_error_result(ticker, str(e))
    
    def _get_historical_data(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """Obtiene datos históricos del activo"""
        try:
            # Calcular fecha de inicio
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Consultar datos históricos
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
            print(f"❌ Error obteniendo datos históricos de {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def _get_current_market_price(self, ticker: str) -> Optional[float]:
        """Obtiene el precio actual del mercado"""
        try:
            # Obtener el precio más reciente
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
    
    def _calculate_technical_indicators(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Calcula indicadores técnicos básicos"""
        try:
            prices = df['precio_cierre'].values
            
            indicators = {
                'current_price': current_price,
                'data_points': len(prices)
            }
            
            if len(prices) < 5:
                return indicators
            
            # Media móvil simple (5, 10, 20 días)
            indicators['sma_5'] = np.mean(prices[-5:]) if len(prices) >= 5 else None
            indicators['sma_10'] = np.mean(prices[-10:]) if len(prices) >= 10 else None
            indicators['sma_20'] = np.mean(prices[-20:]) if len(prices) >= 20 else None
            
            # Precio máximo y mínimo reciente
            indicators['max_20'] = np.max(prices[-20:]) if len(prices) >= 20 else np.max(prices)
            indicators['min_20'] = np.min(prices[-20:]) if len(prices) >= 20 else np.min(prices)
            
            # Volatilidad (desviación estándar)
            indicators['volatility'] = np.std(prices[-10:]) if len(prices) >= 10 else np.std(prices)
            
            # Tendencia (pendiente de regresión lineal simple)
            if len(prices) >= 7:
                x = np.arange(len(prices[-7:]))
                y = prices[-7:]
                slope = np.polyfit(x, y, 1)[0]
                indicators['trend_slope'] = slope
                indicators['trend_direction'] = 'UP' if slope > 0 else 'DOWN' if slope < 0 else 'FLAT'
            
            # RSI simplificado (momentum)
            if len(prices) >= 14:
                gains = []
                losses = []
                
                for i in range(1, min(14, len(prices))):
                    change = prices[-(i+1)] - prices[-i]
                    if change > 0:
                        gains.append(change)
                    else:
                        losses.append(abs(change))
                
                avg_gain = np.mean(gains) if gains else 0
                avg_loss = np.mean(losses) if losses else 0
                
                if avg_loss != 0:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    indicators['rsi'] = rsi
            
            # Posición relativa en el rango
            if indicators['max_20'] != indicators['min_20']:
                indicators['position_in_range'] = (current_price - indicators['min_20']) / (indicators['max_20'] - indicators['min_20'])
            
            return indicators
            
        except Exception as e:
            print(f"❌ Error calculando indicadores: {str(e)}")
            return {'current_price': current_price, 'data_points': 0}
    
    def _generate_recommendation(self, ticker: str, indicators: Dict, historical_data: pd.DataFrame, current_price: float) -> Dict:
        """Genera recomendación basada en indicadores técnicos"""
        try:
            recommendation = {
                'ticker': ticker,
                'current_price': current_price,
                'recommendation': 'MANTENER',
                'confidence': 50,
                'reasons': [],
                'target_price': None,
                'stop_loss': None,
                'indicators': indicators
            }
            
            # Puntuación para la decisión
            buy_score = 0
            sell_score = 0
            reasons = []
            
            # 1. Análisis de tendencia
            if indicators.get('trend_direction') == 'UP':
                buy_score += 20
                reasons.append("📈 Tendencia alcista detectada")
            elif indicators.get('trend_direction') == 'DOWN':
                sell_score += 20
                reasons.append("📉 Tendencia bajista detectada")
            
            # 2. Análisis de medias móviles
            if indicators.get('sma_5') and indicators.get('sma_10'):
                if indicators['sma_5'] > indicators['sma_10']:
                    buy_score += 15
                    reasons.append("📊 Precio por encima de media móvil")
                else:
                    sell_score += 15
                    reasons.append("📊 Precio por debajo de media móvil")
            
            # 3. Análisis de posición en rango
            position = indicators.get('position_in_range', 0.5)
            if position < 0.2:  # Cerca del mínimo
                buy_score += 25
                reasons.append("💰 Precio cerca del mínimo reciente")
            elif position > 0.8:  # Cerca del máximo
                sell_score += 25
                reasons.append("⚠️ Precio cerca del máximo reciente")
            
            # 4. Análisis RSI
            rsi = indicators.get('rsi')
            if rsi:
                if rsi < 30:  # Sobreventa
                    buy_score += 20
                    reasons.append(f"📉 RSI sobreventa ({rsi:.1f})")
                elif rsi > 70:  # Sobrecompra
                    sell_score += 20
                    reasons.append(f"📈 RSI sobrecompra ({rsi:.1f})")
            
            # 5. Análisis de volatilidad
            volatility = indicators.get('volatility', 0)
            avg_price = indicators.get('sma_10', current_price)
            if avg_price > 0:
                volatility_pct = (volatility / avg_price) * 100
                if volatility_pct > 5:  # Alta volatilidad
                    sell_score += 10
                    reasons.append("⚡ Alta volatilidad detectada")
            
            # 6. Determinar recomendación final
            if buy_score > sell_score + 20:
                recommendation['recommendation'] = 'COMPRA'
                recommendation['confidence'] = min(90, 50 + buy_score - sell_score)
                recommendation['target_price'] = current_price * 1.1  # Target 10% arriba
                recommendation['stop_loss'] = current_price * 0.95   # Stop loss 5% abajo
            elif sell_score > buy_score + 20:
                recommendation['recommendation'] = 'VENTA'
                recommendation['confidence'] = min(90, 50 + sell_score - buy_score)
                recommendation['target_price'] = current_price * 0.9  # Target 10% abajo
                recommendation['stop_loss'] = current_price * 1.05   # Stop loss 5% arriba
            else:
                recommendation['recommendation'] = 'MANTENER'
                recommendation['confidence'] = 50
                reasons.append("📊 Señales mixtas - mantener posición")
            
            recommendation['reasons'] = reasons
            
            return recommendation
            
        except Exception as e:
            print(f"❌ Error generando recomendación: {str(e)}")
            return self._create_error_result(ticker, str(e))
    
    def analyze_portfolio_for_sell_decisions(self, portfolio_assets: List[Dict]) -> List[Dict]:
        """
        Analiza activos de la cartera para decisiones de venta
        
        Args:
            portfolio_assets: Lista de activos en cartera
            
        Returns:
            Lista de recomendaciones de venta
        """
        sell_recommendations = []
        
        print(f"\n📊 ANALIZANDO CARTERA PARA DECISIONES DE VENTA")
        print("-" * 50)
        
        for asset in portfolio_assets:
            ticker = asset['ticker']
            current_value = asset['valor_actual_total']
            initial_value = asset['valor_inicial_total']
            gain_loss_pct = asset['ganancia_perdida_porcentaje']
            
            # Análisis técnico del activo
            tech_analysis = self.analyze_asset_for_decision(ticker, asset['precio_actual_unitario'])
            
            # Decisión específica para activos en cartera
            sell_decision = self._evaluate_sell_decision(asset, tech_analysis)
            
            if sell_decision['recommendation'] == 'VENTA':
                sell_recommendations.append(sell_decision)
                print(f"🔴 {ticker}: VENTA recomendada - {sell_decision['primary_reason']}")
            else:
                print(f"🟢 {ticker}: MANTENER - {sell_decision['primary_reason']}")
        
        return sell_recommendations
    
    def analyze_market_for_buy_opportunities(self, available_money: float, owned_tickers: List[str] = None) -> List[Dict]:
        """
        Analiza el mercado buscando oportunidades de compra
        
        Args:
            available_money: Dinero disponible para invertir
            owned_tickers: Tickers que ya se poseen (para diversificación)
            
        Returns:
            Lista de oportunidades de compra ordenadas por atractivo
        """
        if owned_tickers is None:
            owned_tickers = []
        
        buy_opportunities = []
        
        print(f"\n🔍 BUSCANDO OPORTUNIDADES DE COMPRA")
        print(f"💰 Dinero disponible: ${available_money:,.2f}")
        print("-" * 50)
        
        try:
            # Obtener lista de activos disponibles con datos recientes
            result = self.db.supabase.table('precios_historico')\
                .select('ticker')\
                .gte('fecha', (date.today() - timedelta(days=3)).isoformat())\
                .execute()
            
            if not result.data:
                print("⚠️ No se encontraron activos para analizar")
                return []
            
            # Obtener tickers únicos
            available_tickers = list(set([row['ticker'] for row in result.data]))
            
            # Filtrar tickers que no se poseen (para diversificación)
            new_tickers = [t for t in available_tickers if t not in owned_tickers]
            
            # Analizar cada ticker
            for ticker in new_tickers[:20]:  # Limitar a 20 para no saturar
                try:
                    analysis = self.analyze_asset_for_decision(ticker)
                    
                    if analysis['recommendation'] == 'COMPRA':
                        # Calcular cantidad sugerida basada en dinero disponible
                        suggested_investment = min(available_money * 0.2, 50000)  # Máximo 20% del dinero o $50k
                        suggested_quantity = int(suggested_investment / analysis['current_price'])
                        
                        if suggested_quantity > 0:
                            opportunity = {
                                'ticker': ticker,
                                'recommendation': 'COMPRA',
                                'current_price': analysis['current_price'],
                                'confidence': analysis['confidence'],
                                'suggested_quantity': suggested_quantity,
                                'suggested_investment': suggested_quantity * analysis['current_price'],
                                'target_price': analysis.get('target_price'),
                                'reasons': analysis['reasons'],
                                'expected_return': ((analysis.get('target_price', 0) / analysis['current_price']) - 1) * 100 if analysis.get('target_price') else 0
                            }
                            
                            buy_opportunities.append(opportunity)
                            print(f"🟢 {ticker}: COMPRA - Confianza {analysis['confidence']}% - ${suggested_investment:,.0f}")
                    
                except Exception as e:
                    continue
            
            # Ordenar por confianza y retorno esperado
            buy_opportunities.sort(key=lambda x: (x['confidence'], x['expected_return']), reverse=True)
            
            return buy_opportunities[:5]  # Top 5 oportunidades
            
        except Exception as e:
            print(f"❌ Error buscando oportunidades: {str(e)}")
            return []
    
    def _evaluate_sell_decision(self, asset: Dict, tech_analysis: Dict) -> Dict:
        """Evalúa si un activo en cartera debe venderse"""
        try:
            gain_loss_pct = asset['ganancia_perdida_porcentaje']
            current_price = asset['precio_actual_unitario']
            
            sell_decision = {
                'ticker': asset['ticker'],
                'recommendation': 'MANTENER',
                'confidence': 50,
                'primary_reason': '',
                'current_value': asset['valor_actual_total'],
                'gain_loss_pct': gain_loss_pct,
                'tech_recommendation': tech_analysis['recommendation']
            }
            
            # Criterios de venta
            reasons_to_sell = []
            
            # 1. Ganancia objetivo alcanzada (>20%)
            if gain_loss_pct > 20:
                reasons_to_sell.append("🎯 Ganancia objetivo alcanzada (>20%)")
                sell_decision['confidence'] += 30
            
            # 2. Análisis técnico sugiere venta
            if tech_analysis['recommendation'] == 'VENTA':
                reasons_to_sell.append("📉 Análisis técnico sugiere venta")
                sell_decision['confidence'] += 20
            
            # 3. Pérdida significativa (-15%) + técnico negativo
            if gain_loss_pct < -15 and tech_analysis['recommendation'] in ['VENTA', 'MANTENER']:
                reasons_to_sell.append("🛑 Stop loss activado (-15%)")
                sell_decision['confidence'] += 25
            
            # 4. Sobrecompra extrema
            rsi = tech_analysis.get('indicators', {}).get('rsi')
            if rsi and rsi > 75:
                reasons_to_sell.append(f"📈 Sobrecompra extrema (RSI: {rsi:.1f})")
                sell_decision['confidence'] += 15
            
            # Decisión final
            if sell_decision['confidence'] >= 70 or len(reasons_to_sell) >= 2:
                sell_decision['recommendation'] = 'VENTA'
                sell_decision['primary_reason'] = reasons_to_sell[0] if reasons_to_sell else "Múltiples señales de venta"
            else:
                if gain_loss_pct > 0:
                    sell_decision['primary_reason'] = f"Ganancia {gain_loss_pct:.1f}% - mantener posición"
                else:
                    sell_decision['primary_reason'] = f"Pérdida {gain_loss_pct:.1f}% - evaluar recuperación"
            
            return sell_decision
            
        except Exception as e:
            return {
                'ticker': asset.get('ticker', 'UNKNOWN'),
                'recommendation': 'MANTENER',
                'confidence': 0,
                'primary_reason': f"Error en análisis: {str(e)}"
            }
    
    def _create_no_data_result(self, ticker: str) -> Dict:
        """Crea resultado cuando no hay datos suficientes"""
        return {
            'ticker': ticker,
            'recommendation': 'MANTENER',
            'confidence': 0,
            'reasons': ['❌ Datos históricos insuficientes'],
            'current_price': 0,
            'indicators': {}
        }
    
    def _create_error_result(self, ticker: str, error_msg: str) -> Dict:
        """Crea resultado cuando hay error en el análisis"""
        return {
            'ticker': ticker,
            'recommendation': 'MANTENER',
            'confidence': 0,
            'reasons': [f'❌ Error: {error_msg}'],
            'current_price': 0,
            'indicators': {}
        }