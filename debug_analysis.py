# debug_analysis_fixed.py - Debugger corregido con los problemas identificados
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from database.database_manager import SupabaseManager
from analysis.financial_analyzer import FinancialAnalyzer
import pandas as pd
from datetime import date, timedelta
import numpy as np

class AnalysisDebugger:
    def __init__(self):
        self.db = SupabaseManager()
        self.analyzer = FinancialAnalyzer(self.db)
        
    def debug_full_analysis_pipeline(self, sample_tickers=None):
        """Debug completo del pipeline de análisis"""
        print("🔍 DEBUGGING COMPLETO DEL ANÁLISIS FINANCIERO")
        print("=" * 60)
        
        # 1. Verificar qué activos hay disponibles
        available_tickers = self._get_available_tickers()
        print(f"\n📊 ACTIVOS DISPONIBLES EN BD: {len(available_tickers)}")
        print("-" * 40)
        
        if not available_tickers:
            print("❌ No hay activos en la base de datos")
            return
        
        # Usar muestra o todos
        test_tickers = sample_tickers or available_tickers[:5]  # Primeros 5 para debug
        
        print(f"🎯 ANALIZANDO: {test_tickers}")
        
        # 2. Debug de cada ticker individualmente
        for ticker in test_tickers:
            print(f"\n{'='*50}")
            print(f"🔍 DEBUGGING: {ticker}")
            print(f"{'='*50}")
            
            self._debug_single_ticker(ticker)
        
        # 3. Debug del método de oportunidades de compra
        print(f"\n{'='*60}")
        print("🔍 DEBUGGING MÉTODO analyze_market_for_buy_opportunities")
        print(f"{'='*60}")
        
        self._debug_buy_opportunities_method(available_money=100000, owned_tickers=[])
    
    def _get_available_tickers(self):
        """Obtiene tickers con datos recientes"""
        try:
            # Buscar tickers con datos de los últimos 7 días
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            
            result = self.db.supabase.table('precios_historico')\
                .select('ticker')\
                .gte('fecha', start_date.isoformat())\
                .execute()
            
            if result.data:
                tickers = list(set([row['ticker'] for row in result.data]))
                print(f"Tickers con datos recientes: {tickers[:10]}...")
                return sorted(tickers)
            
            return []
            
        except Exception as e:
            print(f"❌ Error obteniendo tickers: {str(e)}")
            return []
    
    def _debug_single_ticker(self, ticker):
        """Debug detallado de un ticker específico"""
        
        # 1. Verificar datos históricos
        print(f"\n1️⃣ DATOS HISTÓRICOS DE {ticker}:")
        print("-" * 30)
        
        historical_data = self._get_detailed_historical_data(ticker)
        
        if historical_data.empty:
            print(f"❌ No hay datos históricos para {ticker}")
            return
        
        print(f"✅ {len(historical_data)} registros encontrados")
        print(f"📅 Rango de fechas: {historical_data['fecha'].min()} a {historical_data['fecha'].max()}")
        
        # Mostrar muestra de datos
        print(f"\n📋 MUESTRA DE DATOS:")
        print(historical_data[['fecha', 'precio_cierre']].tail(10))
        
        # 2. Verificar precio actual
        print(f"\n2️⃣ PRECIO ACTUAL DE {ticker}:")
        print("-" * 30)
        
        current_price = self._get_detailed_current_price(ticker, historical_data)
        print(f"💰 Precio actual: ${current_price:,.2f}" if current_price else "❌ No se encontró precio actual")
        
        if not current_price:
            print("⚠️ Saltando análisis - sin precio actual")
            return
        
        # 3. Calcular indicadores paso a paso
        print(f"\n3️⃣ INDICADORES TÉCNICOS DE {ticker}:")
        print("-" * 30)
        
        indicators = self._calculate_detailed_indicators(historical_data, current_price)
        
        for key, value in indicators.items():
            if key != 'error':
                print(f"📊 {key}: {value}")
        
        # 4. Generar recomendación paso a paso
        print(f"\n4️⃣ ANÁLISIS DE RECOMENDACIÓN DE {ticker}:")
        print("-" * 30)
        
        recommendation = self._debug_recommendation_logic(ticker, indicators, historical_data, current_price)
        
        print(f"📋 RESULTADO FINAL:")
        print(f"   🎯 Recomendación: {recommendation['recommendation']}")
        print(f"   🔥 Confianza: {recommendation['confidence']}%")
        print(f"   💡 Razones: {recommendation['reasons']}")
    
    def _get_detailed_historical_data(self, ticker, days=30):
        """Obtiene datos históricos con debug"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # VERIFICAR QUERY EXACTA
            print(f"🔍 Query: ticker='{ticker}', fecha >= '{start_date}', fecha <= '{end_date}'")
            
            result = self.db.supabase.table('precios_historico')\
                .select('*')\
                .eq('ticker', ticker)\
                .gte('fecha', start_date.isoformat())\
                .lte('fecha', end_date.isoformat())\
                .order('fecha')\
                .execute()
            
            print(f"📊 Registros encontrados: {len(result.data)}")
            
            if not result.data:
                # Intentar sin filtro de fecha
                print("🔍 Intentando sin filtro de fecha...")
                result_all = self.db.supabase.table('precios_historico')\
                    .select('*')\
                    .eq('ticker', ticker)\
                    .order('fecha')\
                    .execute()
                
                print(f"📊 Total registros históricos para {ticker}: {len(result_all.data)}")
                
                if result_all.data:
                    print("📅 Fechas disponibles:")
                    for row in result_all.data[-5:]:  # Últimos 5
                        precio = row.get('precio_cierre') or row.get('precio_cierre_anterior', 'N/A')
                        print(f"   {row['fecha']}: ${precio}")
                
                return pd.DataFrame()
            
            df = pd.DataFrame(result.data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            # VERIFICAR COLUMNAS DISPONIBLES
            print(f"📊 Columnas disponibles: {list(df.columns)}")
            
            # PROBLEMA 1: No existe columna precio_actual, usar precio_cierre
            if 'precio_cierre' in df.columns:
                df['precio_cierre'] = pd.to_numeric(df['precio_cierre'], errors='coerce')
                print("✅ Usando columna 'precio_cierre'")
            elif 'precio_cierre_anterior' in df.columns:
                df['precio_cierre'] = pd.to_numeric(df['precio_cierre_anterior'], errors='coerce')
                print("⚠️ Usando 'precio_cierre_anterior' como precio_cierre")
            else:
                print("❌ No se encontró columna de precios válida")
                return pd.DataFrame()
            
            # Limpiar datos nulos
            df = df.dropna(subset=['precio_cierre'])
            df = df.sort_values('fecha')
            
            print(f"✅ {len(df)} registros válidos después de limpieza")
            
            # PROBLEMA 2: Pocos datos para análisis técnico
            if len(df) < 5:
                print(f"⚠️ Solo {len(df)} registros - insuficientes para análisis (mín: 5)")
            
            return df
            
        except Exception as e:
            print(f"❌ Error obteniendo datos históricos: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def _get_detailed_current_price(self, ticker, historical_df=None):
        """Obtiene precio actual con debug - CORREGIDO"""
        try:
            # PROBLEMA IDENTIFICADO: precio_actual no existe
            # Usar el último precio_cierre disponible
            
            if historical_df is not None and not historical_df.empty:
                latest_price = historical_df['precio_cierre'].iloc[-1]
                latest_date = historical_df['fecha'].iloc[-1]
                print(f"💰 Usando último precio histórico: ${latest_price:,.2f} ({latest_date.date()})")
                return float(latest_price)
            
            # Fallback: último registro en BD
            result = self.db.supabase.table('precios_historico')\
                .select('precio_cierre, fecha')\
                .eq('ticker', ticker)\
                .order('fecha', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                row = result.data[0]
                if row.get('precio_cierre'):
                    precio = float(row['precio_cierre'])
                    print(f"💰 Último precio en BD: ${precio:,.2f} ({row['fecha']})")
                    return precio
            
            print("⚠️ No se encontró precio actual")
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo precio actual: {str(e)}")
            return None
    
    def _calculate_detailed_indicators(self, df, current_price):
        """Calcula indicadores con debug detallado - CORREGIDO"""
        try:
            if df.empty:
                print("⚠️ DataFrame vacío")
                return {'error': 'empty_dataframe'}
                
            # PROBLEMA 3: Criterio muy estricto (mínimo 5 registros)
            min_data_points = 3  # Reducido de 5 a 3
            
            if len(df) < min_data_points:
                print(f"⚠️ Solo {len(df)} registros - insuficientes para análisis (mín: {min_data_points})")
                return {'error': f'insufficient_data: {len(df)}<{min_data_points}'}
            
            prices = df['precio_cierre'].values
            indicators = {'current_price': current_price, 'data_points': len(prices)}
            
            print(f"📊 Precios para análisis: {prices}")
            
            # SMA 5 (o menos si no hay suficientes datos)
            sma_period = min(5, len(prices))
            indicators['sma_5'] = np.mean(prices[-sma_period:])
            print(f"📈 SMA {sma_period}: ${indicators['sma_5']:,.2f}")
            
            # SMA 10
            sma_10_period = min(10, len(prices))
            indicators['sma_10'] = np.mean(prices[-sma_10_period:])
            print(f"📈 SMA {sma_10_period}: ${indicators['sma_10']:,.2f}")
            
            # Max/Min en período disponible
            lookback = min(20, len(prices))
            indicators['max_20'] = np.max(prices[-lookback:])
            indicators['min_20'] = np.min(prices[-lookback:])
            
            print(f"📈 Máximo {lookback}d: ${indicators['max_20']:,.2f}")
            print(f"📉 Mínimo {lookback}d: ${indicators['min_20']:,.2f}")
            
            # Posición en rango
            if indicators['max_20'] != indicators['min_20']:
                indicators['position_in_range'] = (current_price - indicators['min_20']) / (indicators['max_20'] - indicators['min_20'])
                print(f"📊 Posición en rango: {indicators['position_in_range']:.1%}")
            else:
                indicators['position_in_range'] = 0.5
                print(f"📊 Posición en rango: 50% (precio estable)")
            
            # Tendencia (usando datos disponibles)
            trend_period = min(7, len(prices))
            if trend_period >= 2:  # Mínimo 2 puntos para tendencia
                trend_slope = np.polyfit(range(trend_period), prices[-trend_period:], 1)[0]
                indicators['trend'] = 'UP' if trend_slope > 0 else 'DOWN' if trend_slope < 0 else 'FLAT'
                indicators['trend_slope'] = trend_slope
                print(f"📊 Tendencia ({trend_period}d): {indicators['trend']} (slope: {trend_slope:.2f})")
            else:
                indicators['trend'] = 'UNKNOWN'
                print(f"📊 Tendencia: Datos insuficientes")
            
            return indicators
            
        except Exception as e:
            print(f"❌ Error calculando indicadores: {str(e)}")
            return {'error': str(e)}
    
    def _debug_recommendation_logic(self, ticker, indicators, historical_data, current_price):
        """Debug paso a paso de la lógica de recomendación - CORREGIDO"""
        
        recommendation = {
            'ticker': ticker,
            'current_price': current_price,
            'recommendation': 'MANTENER',
            'confidence': 50,
            'reasons': [],
            'debug_scores': {},
            'indicators': indicators
        }
        
        if 'error' in indicators:
            recommendation['reasons'] = [f"Error en indicadores: {indicators['error']}"]
            return recommendation
        
        buy_score = 0
        reasons = []
        
        print(f"\n🧮 CALCULANDO SCORE DE COMPRA:")
        
        # Criterio 1: Precio cerca del mínimo - CRITERIO RELAJADO
        position = indicators.get('position_in_range', 0.5)
        # CAMBIO: De 0.3 a 0.5 (más permisivo)
        threshold = 0.5
        if position < threshold:
            points = 30
            buy_score += points
            reason = f"Precio cerca del mínimo reciente (posición {position:.1%})"
            reasons.append(reason)
            print(f"✅ +{points} puntos: {reason}")
        else:
            print(f"❌ +0 puntos: Precio no cerca del mínimo (posición {position:.1%} >= {threshold:.1%})")
        
        recommendation['debug_scores']['position_score'] = position
        recommendation['debug_scores']['position_threshold'] = threshold
        
        # Criterio 2: Tendencia alcista - CRITERIO RELAJADO
        trend = indicators.get('trend', 'UNKNOWN')
        # CAMBIO: Aceptar también FLAT
        if trend in ['UP', 'FLAT']:
            points = 20 if trend == 'UP' else 10  # Menos puntos para FLAT
            buy_score += points
            reason = f"Tendencia {'alcista' if trend == 'UP' else 'neutral'} detectada"
            reasons.append(reason)
            print(f"✅ +{points} puntos: {reason}")
        else:
            print(f"❌ +0 puntos: Tendencia no favorable ({trend})")
        
        recommendation['debug_scores']['trend'] = trend
        
        # Criterio 3: Precio por encima de SMA - CORREGIDO manejo de None
        sma_5 = indicators.get('sma_5')
        if sma_5 is not None and current_price > sma_5:
            points = 15
            buy_score += points
            reason = f"Precio por encima de media móvil (${current_price:,.2f} > ${sma_5:,.2f})"
            reasons.append(reason)
            print(f"✅ +{points} puntos: {reason}")
        else:
            sma_str = f"${sma_5:,.2f}" if sma_5 is not None else "N/A"
            print(f"❌ +0 puntos: Precio por debajo de SMA (${current_price:,.2f} vs {sma_str})")
        
        recommendation['debug_scores']['sma_comparison'] = {
            'current_price': current_price,
            'sma_5': sma_5,
            'above_sma': (sma_5 is not None) and (current_price > sma_5)
        }
        
        # CRITERIO ADICIONAL: Volatilidad reciente (bonus)
        slope = indicators.get('trend_slope', 0)
        if slope is not None and abs(slope) > 0:  # Hay movimiento
            points = 5
            buy_score += points
            reasons.append("Actividad de precio detectada")
            print(f"✅ +{points} puntos: Actividad de precio (slope: {slope:.2f})")
        
        print(f"\n📊 SCORE TOTAL: {buy_score} puntos")
        
        # UMBRAL REDUCIDO: De 40 a 25
        threshold = 25
        
        if buy_score >= threshold:
            recommendation.update({
                'recommendation': 'COMPRA',
                'confidence': min(90, 50 + buy_score),
                'reasons': reasons
            })
            print(f"🟢 RESULTADO: COMPRA (score {buy_score} >= {threshold})")
        else:
            recommendation['reasons'] = [f'Señales de compra insuficientes (score: {buy_score}/{threshold})']
            print(f"🔴 RESULTADO: MANTENER (score {buy_score} < {threshold})")
        
        recommendation['debug_scores']['total_score'] = buy_score
        recommendation['debug_scores']['threshold'] = threshold
        
        return recommendation
    
    def _debug_buy_opportunities_method(self, available_money, owned_tickers):
        """Debug del método completo analyze_market_for_buy_opportunities"""
        
        print(f"\n💰 Dinero disponible: ${available_money:,.2f}")
        print(f"🏛️ Tickers en cartera: {owned_tickers}")
        
        if available_money <= 0:
            print("❌ Sin dinero disponible - no hay análisis")
            return
        
        try:
            # Obtener activos disponibles
            all_tickers = self._get_available_tickers()
            
            print(f"📊 Tickers disponibles para análisis: {len(all_tickers)}")
            
            # Filtrar tickers que no se poseen
            new_tickers = [t for t in all_tickers if t not in owned_tickers]
            print(f"📊 Tickers nuevos (no en cartera): {len(new_tickers)}")
            print(f"🎯 Primeros 10: {new_tickers[:10]}")
            
            # Analizar primeros 5 tickers para debug
            print(f"\n🔍 ANALIZANDO PRIMEROS 5 TICKERS:")
            buy_opportunities = []
            
            for i, ticker in enumerate(new_tickers[:5]):
                print(f"\n--- TICKER {i+1}: {ticker} ---")
                
                try:
                    # Obtener datos directamente para control total
                    historical_data = self._get_detailed_historical_data(ticker)
                    
                    if historical_data.empty:
                        print(f"❌ Sin datos históricos")
                        continue
                    
                    current_price = self._get_detailed_current_price(ticker, historical_data)
                    if not current_price:
                        print(f"❌ Sin precio actual")
                        continue
                    
                    # Calcular indicadores
                    indicators = self._calculate_detailed_indicators(historical_data, current_price)
                    
                    if 'error' in indicators:
                        print(f"❌ Error en indicadores: {indicators['error']}")
                        continue
                    
                    # Generar recomendación
                    recommendation = self._debug_recommendation_logic(ticker, indicators, historical_data, current_price)
                    
                    print(f"📊 Resultado: {recommendation['recommendation']} (confianza: {recommendation['confidence']}%)")
                    
                    if recommendation['recommendation'] == 'COMPRA':
                        # Calcular inversión sugerida
                        suggested_investment = min(available_money * 0.2, 50000)
                        suggested_quantity = int(suggested_investment / current_price) if current_price > 0 else 0
                        
                        if suggested_quantity > 0:
                            opportunity = {
                                'ticker': ticker,
                                'recommendation': 'COMPRA',
                                'current_price': current_price,
                                'confidence': recommendation['confidence'],
                                'suggested_quantity': suggested_quantity,
                                'suggested_investment': suggested_quantity * current_price,
                                'reasons': recommendation['reasons']
                            }
                            
                            buy_opportunities.append(opportunity)
                            print(f"✅ OPORTUNIDAD ENCONTRADA: ${opportunity['suggested_investment']:,.0f}")
                        else:
                            print(f"⚠️ Cantidad sugerida = 0 (precio muy alto)")
                    else:
                        print(f"❌ No es oportunidad: {recommendation['reasons']}")
                
                except Exception as e:
                    print(f"❌ Error analizando {ticker}: {str(e)}")
                    continue
            
            print(f"\n🎯 RESUMEN FINAL:")
            print(f"📊 Tickers analizados: 5")
            print(f"🟢 Oportunidades encontradas: {len(buy_opportunities)}")
            
            for opp in buy_opportunities:
                print(f"   💰 {opp['ticker']}: ${opp['suggested_investment']:,.0f} (confianza {opp['confidence']}%)")
            
            if not buy_opportunities:
                print(f"\n🤔 POSIBLES AJUSTES REALIZADOS:")
                print(f"   ✅ Criterio posición: <50% (era <30%)")
                print(f"   ✅ Tendencia acepta FLAT (era solo UP)")
                print(f"   ✅ Umbral score: 25 (era 40)")
                print(f"   ✅ Mínimo datos: 3 (era 5)")
                print(f"\n🔄 Ejecuta de nuevo para ver si hay más oportunidades")
                
        except Exception as e:
            print(f"❌ Error en método buy_opportunities: {str(e)}")
            import traceback
            traceback.print_exc()

def run_complete_debug():
    """Ejecuta debugging completo con criterios ajustados"""
    debugger = AnalysisDebugger()
    
    # Debug con tickers específicos
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']  # Tickers conocidos
    
    debugger.debug_full_analysis_pipeline(sample_tickers=test_tickers)

if __name__ == "__main__":
    run_complete_debug()