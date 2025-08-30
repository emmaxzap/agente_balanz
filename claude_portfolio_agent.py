# claude_portfolio_agent.py - Versión mejorada sin respuestas hardcodeadas
import json
from datetime import date, timedelta
from typing import Dict, List
import anthropic
import os
import pandas as pd
import numpy as np

class ClaudePortfolioAgent:
    def __init__(self, db_manager, page=None):
        self.db = db_manager
        self.page = page  # Para scraping de datos fundamentales
        # Configurar cliente de Anthropic
        self.client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        
        # Importar scraper fundamental si hay página disponible
        if self.page:
            try:
                from scraper.fundamental_data_scraper import FundamentalDataScraper
                self.fundamental_scraper = FundamentalDataScraper(self.page)
            except ImportError:
                print("⚠️ FundamentalDataScraper no disponible")
                self.fundamental_scraper = None
        else:
            self.fundamental_scraper = None
    
    def analyze_portfolio_with_expert_agent(self, portfolio_data: Dict, available_cash: float) -> Dict:
        """Análisis completo usando agente experto con datos reales - SIN FALLBACKS HARDCODEADOS"""
        try:
            print("\n🤖 INICIANDO ANÁLISIS CON AGENTE EXPERTO")
            print("-" * 50)
            
            # 1. Debug de datos de entrada
            print("🔍 DEBUG: Verificando datos de entrada...")
            print(f"   📊 Portfolio keys: {list(portfolio_data.keys())}")
            print(f"   💰 Available cash: ${available_cash:,.2f}")
            
            activos = portfolio_data.get('activos', [])
            print(f"   📊 Activos count: {len(activos)}")
            for activo in activos:
                ticker = activo.get('ticker', 'N/A')
                dias = activo.get('dias_tenencia', 0)
                pnl = activo.get('ganancia_perdida_porcentaje', 0)
                print(f"      • {ticker}: {dias} días, {pnl:+.1f}%")
            
            # 2. Recopilar datos completos con información real
            print("🔍 DEBUG: Recopilando datos completos...")
            complete_data = self._gather_complete_portfolio_data_improved(portfolio_data, available_cash)
            print(f"   📊 Complete data keys: {list(complete_data.keys())}")
            print(f"   📊 Positions count: {len(complete_data.get('positions', []))}")
            
            # 3. Verificar que tenemos datos técnicos reales
            has_real_data = self._verify_real_technical_data(complete_data)
            if not has_real_data:
                print("❌ No hay datos técnicos reales suficientes - abortando análisis experto")
                return self._create_minimal_analysis()
            
            # 4. Crear prompt mejorado
            print("🔍 DEBUG: Creando prompt...")
            expert_prompt = self._create_expert_prompt_improved(complete_data)
            print(f"   📊 Prompt length: {len(expert_prompt)} chars")
            print(f"   📊 Prompt preview: {expert_prompt[:200]}...")
            
            # 5. Consultar agente - CON VALIDACIÓN ESTRICTA
            print("🔍 DEBUG: Consultando agente experto...")
            expert_response = self._query_expert_agent_with_validation(expert_prompt)
            
            if not expert_response:
                print("❌ No se obtuvo respuesta válida del agente experto")
                return self._create_minimal_analysis()
            
            print(f"   📊 Response length: {len(expert_response)} chars")
            print(f"   📊 Response preview: {expert_response[:200]}...")
            
            # 6. Parsear respuesta CON VALIDACIÓN
            print("🔍 DEBUG: Parseando respuesta...")
            parsed_analysis = self._parse_expert_response_strict(expert_response)
            
            if not self._validate_analysis_quality(parsed_analysis):
                print("❌ Análisis del experto no cumple estándares de calidad")
                return self._create_minimal_analysis()
            
            print(f"   📊 Parsed type: {type(parsed_analysis)}")
            print(f"   📊 Parsed keys: {list(parsed_analysis.keys()) if isinstance(parsed_analysis, dict) else 'Not dict'}")
            
            print("✅ Análisis experto de alta calidad completado")
            return parsed_analysis
            
        except Exception as e:
            print(f"❌ Error en análisis experto: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_minimal_analysis()
    
    def _verify_real_technical_data(self, complete_data: Dict) -> bool:
        """Verifica que tenemos datos técnicos reales, no simulados"""
        positions = complete_data.get('positions', [])
        
        if not positions:
            return False
        
        real_data_count = 0
        
        for pos in positions:
            # Verificar datos históricos reales
            historical = pos.get('historical_data', {})
            if historical.get('data_points', 0) >= 10:  # Mínimo 10 días de datos
                real_data_count += 1
            
            # Verificar indicadores técnicos calculados
            tech_indicators = pos.get('technical_indicators', {})
            if (tech_indicators.get('rsi_14') and 
                not tech_indicators.get('insufficient_data') and
                tech_indicators.get('rsi_14') != 50):  # 50 es valor por defecto
                real_data_count += 1
        
        # Al menos 70% de posiciones deben tener datos reales
        min_required = len(positions) * 0.7
        has_sufficient_data = real_data_count >= min_required
        
        print(f"🔍 Verificación datos reales: {real_data_count}/{len(positions)} posiciones con datos técnicos reales")
        return has_sufficient_data
    
    def _query_expert_agent_with_validation(self, prompt: str) -> str:
        """Consulta al agente experto CON VALIDACIÓN estricta"""
        try:
            print("🔍 DEBUG: Verificando configuración API...")
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                print("❌ ANTHROPIC_API_KEY no configurada")
                return ""
            
            print(f"   📊 API Key configured: {api_key[:10]}...")
            
            print("🔍 DEBUG: Enviando request a Claude...")
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_content = message.content[0].text
            print(f"   📊 Claude response length: {len(response_content)} chars")
            print(f"   📊 Claude response type: {type(response_content)}")
            
            # Validar que la respuesta no esté vacía
            if len(response_content.strip()) < 100:
                print("❌ Respuesta de Claude demasiado corta")
                return ""
            
            # Validar que contiene JSON
            if '{' not in response_content or '}' not in response_content:
                print("❌ Respuesta de Claude no contiene JSON válido")
                return ""
            
            return response_content
            
        except Exception as e:
            print(f"❌ Error consultando agente experto: {str(e)}")
            return ""
    
    def _parse_expert_response_strict(self, response: str) -> Dict:
        """Parsea la respuesta del agente experto CON VALIDACIÓN ESTRICTA"""
        try:
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                if isinstance(parsed, dict):
                    return parsed
            
            print("❌ No se pudo parsear JSON válido de la respuesta")
            return {}
            
        except json.JSONDecodeError as e:
            print(f"❌ Error JSON parseando respuesta experta: {str(e)}")
            return {}
        except Exception as e:
            print(f"❌ Error general parseando respuesta experta: {str(e)}")
            return {}
    
    def _validate_analysis_quality(self, analysis: Dict) -> bool:
        """Valida que el análisis cumple estándares de calidad (no es genérico)"""
        if not isinstance(analysis, dict) or not analysis:
            return False
        
        # Verificar estructura básica
        required_keys = ['analisis_tecnico', 'gestion_riesgo']
        if not all(key in analysis for key in required_keys):
            print("❌ Análisis no tiene estructura completa")
            return False
        
        # Verificar análisis técnico por activo
        analisis_tecnico = analysis.get('analisis_tecnico', {})
        por_activo = analisis_tecnico.get('por_activo', {}) if isinstance(analisis_tecnico, dict) else {}
        
        if not por_activo:
            print("❌ No hay análisis técnico por activo")
            return False
        
        # Verificar que NO sean valores genéricos/hardcodeados
        real_analysis_indicators = 0
        
        for ticker, asset_analysis in por_activo.items():
            rsi_analysis = asset_analysis.get('rsi_analysis', '')
            
            # Verificar que RSI no sea genérico
            if rsi_analysis and 'no_calculado' not in rsi_analysis:
                # Buscar valores numéricos específicos en RSI
                import re
                rsi_numbers = re.findall(r'\d+\.?\d*', rsi_analysis)
                if rsi_numbers:
                    rsi_value = float(rsi_numbers[0])
                    # Verificar que no sea valor hardcodeado típico (50, 30, 70)
                    if rsi_value not in [30.0, 50.0, 70.0]:
                        real_analysis_indicators += 1
        
        # Verificar razonamiento específico
        razonamiento = analysis.get('razonamiento_integral', '')
        
        # Frases que indican análisis genérico/hardcodeado
        generic_phrases = [
            'posiciones muy recientes (1 día promedio)',
            'pérdidas actuales son normales',
            'análisis de respaldo',
            'datos técnicos no disponibles'
        ]
        
        is_generic = any(phrase in razonamiento.lower() for phrase in generic_phrases)
        
        if is_generic:
            print("❌ Análisis contiene texto genérico/hardcodeado")
            return False
        
        # Verificar que haya suficientes indicadores reales
        min_real_indicators = max(1, len(por_activo) // 2)  # Al menos 50% de activos con análisis real
        
        quality_check = real_analysis_indicators >= min_real_indicators
        print(f"🔍 Validación calidad: {real_analysis_indicators}/{len(por_activo)} activos con análisis real")
        
        return quality_check
    
    def _create_minimal_analysis(self) -> Dict:
        """Crea análisis MÍNIMO sin hardcodeo cuando no hay datos de Claude"""
        return {
            "analisis_tecnico": {
                "por_activo": {},
                "mercado_general": "Análisis técnico no disponible"
            },
            "acciones_inmediatas": [],
            "acciones_corto_plazo": [],
            "gestion_riesgo": {
                "riesgo_cartera": 5,
                "volatilidad_observada": "No calculada",
                "recomendaciones_sizing": []
            },
            "razonamiento_integral": "El análisis técnico avanzado no está disponible en este momento. Consulta las recomendaciones del sistema de reglas.",
            "analysis_source": "minimal_fallback",
            "claude_api_available": False
        }
    
    def _gather_complete_portfolio_data_improved(self, portfolio_data: Dict, available_cash: float) -> Dict:
        """Recopila datos completos con información real scrapeada"""
        complete_data = {
            'portfolio_summary': {
                'cash_available': available_cash,
                'total_invested': portfolio_data.get('total_invertido', 0),
                'current_value': portfolio_data.get('valor_total_cartera', 0),
                'total_pnl': portfolio_data.get('ganancia_perdida_total', 0),
                'positions_count': len(portfolio_data.get('activos', []))
            },
            'positions': [],
            'market_data': {},
            'economic_context': self._get_economic_context()
        }
        
        # Recopilar datos detallados por posición con información real
        for asset in portfolio_data.get('activos', []):
            ticker = asset['ticker']
            
            print(f"   🔍 Procesando {ticker}...")
            
            # Datos básicos de la posición
            position_data = {
                'ticker': ticker,
                'shares': asset['cantidad'],
                'avg_cost': asset['precio_inicial_unitario'],
                'current_price': asset['precio_actual_unitario'],
                'current_value': asset['valor_actual_total'],
                'initial_value': asset['valor_inicial_total'],
                'pnl': asset['ganancia_perdida_total'],
                'pnl_pct': asset['ganancia_perdida_porcentaje'],
                'days_held': asset.get('dias_tenencia', 0),
                'position_size_pct': asset['valor_actual_total'] / portfolio_data.get('valor_total_cartera', 1)
            }
            
            # NUEVO: Datos históricos completos (30 días)
            historical_data = self._get_comprehensive_historical_data_improved(ticker)
            position_data['historical_data'] = historical_data
            
            # NUEVO: Indicadores técnicos calculados
            technical_indicators = self._calculate_technical_indicators(historical_data)
            position_data['technical_indicators'] = technical_indicators
            
            # NUEVO: Datos fundamentales reales (scrapeando desde Balanz)
            fundamental_data = self._get_real_fundamental_data(ticker)
            position_data['fundamental_data'] = fundamental_data
            
            complete_data['positions'].append(position_data)
            
            print(f"   ✅ {ticker} procesado - Datos históricos: {historical_data.get('data_points', 0)} días")
        
        # Datos de mercado general
        complete_data['market_data'] = self._get_market_context()
        
        return complete_data
    
    def _get_comprehensive_historical_data_improved(self, ticker: str) -> Dict:
        """Obtiene serie histórica completa de últimos 30 días"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            result = self.db.supabase.table('precios_historico')\
                .select('fecha, precio_cierre')\
                .eq('ticker', ticker)\
                .gte('fecha', start_date.isoformat())\
                .order('fecha')\
                .execute()
            
            if not result.data:
                print(f"      ⚠️ Sin datos históricos para {ticker}")
                return {'daily_prices': [], 'data_points': 0, 'prices_array': []}
            
            # Convertir a array de precios diarios
            daily_prices = []
            prices_only = []
            
            for row in result.data:
                daily_prices.append({
                    'fecha': row['fecha'],
                    'precio': float(row['precio_cierre'])
                })
                prices_only.append(float(row['precio_cierre']))
            
            return {
                'daily_prices': daily_prices,
                'data_points': len(daily_prices),
                'prices_array': prices_only  # Para cálculos técnicos
            }
            
        except Exception as e:
            print(f"      ❌ Error obteniendo históricos de {ticker}: {str(e)}")
            return {'daily_prices': [], 'data_points': 0, 'prices_array': []}
    
    def _calculate_technical_indicators(self, historical_data: Dict) -> Dict:
        """Calcula indicadores técnicos RSI, MACD, etc."""
        try:
            prices_array = historical_data.get('prices_array', [])
            
            if len(prices_array) < 14:  # Mínimo para RSI
                return {'insufficient_data': True, 'reason': f'Solo {len(prices_array)} días, mínimo 14'}
            
            prices = np.array(prices_array)
            indicators = {}
            
            # RSI (14 períodos)
            indicators['rsi_14'] = self._calculate_rsi(prices, 14)
            
            # MACD
            macd_data = self._calculate_macd(prices)
            indicators['macd'] = macd_data
            
            # Medias móviles
            if len(prices) >= 20:
                indicators['sma_20'] = float(np.mean(prices[-20:]))
            if len(prices) >= 10:
                indicators['sma_10'] = float(np.mean(prices[-10:]))
            if len(prices) >= 5:
                indicators['sma_5'] = float(np.mean(prices[-5:]))
            
            # Bandas de Bollinger
            if len(prices) >= 20:
                bollinger = self._calculate_bollinger_bands(prices, 20, 2)
                indicators['bollinger'] = bollinger
            
            # Volatilidad
            if len(prices) >= 10:
                returns = np.diff(prices) / prices[:-1]
                indicators['volatility_10d'] = float(np.std(returns) * 100)
                indicators['volatility_annualized'] = float(np.std(returns) * np.sqrt(252) * 100)
            
            # Momentum simple
            if len(prices) >= 10:
                momentum_5d = (prices[-1] - prices[-6]) / prices[-6] * 100 if len(prices) >= 6 else 0
                momentum_10d = (prices[-1] - prices[-11]) / prices[-11] * 100 if len(prices) >= 11 else 0
                indicators['momentum_5d'] = float(momentum_5d)
                indicators['momentum_10d'] = float(momentum_10d)
            
            return indicators
            
        except Exception as e:
            print(f"      ❌ Error calculando indicadores técnicos: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_rsi(self, prices: np.array, period: int = 14) -> float:
        """Calcula RSI (Relative Strength Index)"""
        try:
            if len(prices) < period + 1:
                return 50.0
                
            delta = np.diff(prices)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            avg_gain = np.mean(gain[-period:])
            avg_loss = np.mean(loss[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi)
        except:
            return 50.0
    
    def _calculate_macd(self, prices: np.array) -> Dict:
        """Calcula MACD (Moving Average Convergence Divergence)"""
        try:
            if len(prices) < 26:
                return {'macd': 0, 'signal': 0, 'histogram': 0, 'trend': 'neutral'}
            
            # EMA 12 y 26
            ema_12 = self._calculate_ema(prices, 12)
            ema_26 = self._calculate_ema(prices, 26)
            
            macd_line = ema_12 - ema_26
            
            # Signal line (EMA 9 del MACD) - simplificado para este caso
            signal_line = macd_line * 0.9  # Aproximación simple
            histogram = macd_line - signal_line
            
            # Determinar tendencia
            trend = 'bullish' if histogram > 0 else 'bearish' if histogram < 0 else 'neutral'
            
            return {
                'macd': float(macd_line),
                'signal': float(signal_line),
                'histogram': float(histogram),
                'trend': trend
            }
        except:
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'trend': 'neutral'}
    
    def _calculate_ema(self, prices: np.array, period: int) -> float:
        """Calcula Media Móvil Exponencial"""
        try:
            if len(prices) < period:
                return float(np.mean(prices)) if len(prices) > 0 else 0.0
            
            multiplier = 2 / (period + 1)
            ema = prices[0]
            
            for price in prices[1:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return float(ema)
        except:
            return float(np.mean(prices)) if len(prices) > 0 else 0.0
    
    def _calculate_bollinger_bands(self, prices: np.array, period: int = 20, std_dev: int = 2) -> Dict:
        """Calcula Bandas de Bollinger"""
        try:
            if len(prices) < period:
                return {'upper': 0, 'middle': 0, 'lower': 0, 'position': 'neutral'}
            
            recent_prices = prices[-period:]
            sma = np.mean(recent_prices)
            std = np.std(recent_prices)
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            # Determinar posición del precio actual
            current_price = prices[-1]
            if current_price > upper:
                position = 'above_upper'
            elif current_price < lower:
                position = 'below_lower'
            elif current_price > sma:
                position = 'above_middle'
            else:
                position = 'below_middle'
            
            return {
                'upper': float(upper),
                'middle': float(sma),
                'lower': float(lower),
                'position': position
            }
        except:
            return {'upper': 0, 'middle': 0, 'lower': 0, 'position': 'neutral'}
    
    def _get_real_fundamental_data(self, ticker: str) -> Dict:
        """Obtiene datos fundamentales reales desde Balanz (SIN hardcodeo)"""
        try:
            if not self.fundamental_scraper:
                print(f"      ⚠️ Scraper fundamental no disponible para {ticker}")
                return {
                    'sector': None,
                    'industry': None,
                    'daily_volume': None,
                    'data_source': 'scraper_not_available'
                }
            
            # Scrapear datos reales
            fundamental_data = self.fundamental_scraper.scrape_asset_fundamentals(ticker)
            return fundamental_data
            
        except Exception as e:
            print(f"      ❌ Error obteniendo datos fundamentales de {ticker}: {str(e)}")
            return {'error': str(e), 'data_source': 'scraping_failed'}
    
    def _get_economic_context(self) -> Dict:
        """Obtiene contexto económico actualizado"""
        return {
            'market_date': date.today().isoformat(),
            'currency': 'ARS',
            'market': 'Argentina',
            'context': 'Analysis based on real 30-day historical data and calculated technical indicators',
            'data_quality': 'enhanced_real_data'
        }
    
    def _get_market_context(self) -> Dict:
        """Obtiene contexto de mercado"""
        return {
            'market_session': 'Regular trading',
            'data_source': 'balanz_real_time_scraping',
            'analysis_depth': 'full_technical_indicators_calculated'
        }
    
    def _create_expert_prompt_improved(self, data: Dict) -> str:
        """Crea prompt mejorado con datos reales y técnicos - CON INSTRUCCIONES ESPECÍFICAS"""
        
        prompt = f"""Eres un asesor financiero experto que debe dar recomendaciones ESPECÍFICAS y ACCIONABLES para una cartera real.

INSTRUCCIONES CRÍTICAS:
- Debes generar recomendaciones específicas: "Comprar X cantidad a precio Y" o "Vender Z cantidad si precio baja a W"
- Tu análisis será enviado por email a inversores que NO son expertos en finanzas
- Usa lenguaje simple y claro, evita jerga técnica
- Las recomendaciones deben ser ejecutables HOY o en días específicos
- NUNCA uses texto genérico como "monitorear evolución" - sé específico

DATOS REALES DE LA CARTERA:

**RESUMEN FINANCIERO:**
- Capital Disponible: ${data['portfolio_summary']['cash_available']:,.2f}
- Valor Invertido: ${data['portfolio_summary']['current_value']:,.2f}
- Ganancia/Pérdida: ${data['portfolio_summary']['total_pnl']:,.2f}
- Número de Inversiones: {data['portfolio_summary']['positions_count']}

**ANÁLISIS DETALLADO CON DATOS HISTÓRICOS REALES:**"""
        
        for pos in data['positions']:
            days_held = pos['days_held']
            timeframe = "Muy Reciente" if days_held <= 3 else "Reciente" if days_held <= 30 else "Establecida"
            
            # Datos históricos reales
            historical = pos.get('historical_data', {})
            data_points = historical.get('data_points', 0)
            
            # Indicadores técnicos calculados
            tech_indicators = pos.get('technical_indicators', {})
            
            # Datos fundamentales reales
            fundamental = pos.get('fundamental_data', {})
            
            prompt += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pos['ticker']} - Inversión {timeframe} ({days_held} días)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💼 POSICIÓN: {pos['shares']} acciones compradas a ${pos['avg_cost']:.2f} (Precio actual: ${pos['current_price']:.2f})
💰 Ganancia/Pérdida: ${pos['pnl']:.2f} ({pos['pnl_pct']:+.1f}%) | Peso en cartera: {pos['position_size_pct']:.1%}"""
            
            # Datos fundamentales reales
            if fundamental.get('scraping_success'):
                prompt += f"""
🏭 INFORMACIÓN DE LA EMPRESA:"""
                if fundamental.get('sector'):
                    prompt += f"\n   • Sector: {fundamental['sector']}"
                if fundamental.get('industry'):
                    prompt += f"\n   • Industria: {fundamental['industry']}"
                if fundamental.get('daily_volume'):
                    prompt += f"\n   • Volumen Diario: {fundamental['daily_volume']}"
            
            # Serie histórica completa
            if data_points >= 10:
                daily_prices = historical.get('daily_prices', [])
                prompt += f"""

📈 HISTORIAL DE PRECIOS REALES ({data_points} días):"""
                
                # Últimos 15 días para no saturar el prompt
                recent_prices = daily_prices[-15:] if len(daily_prices) > 15 else daily_prices
                for day in recent_prices:
                    prompt += f"\n   {day['fecha']}: ${day['precio']:.2f}"
            
            # Indicadores técnicos calculados
            if not tech_indicators.get('insufficient_data'):
                prompt += f"""

🔢 INDICADORES TÉCNICOS CALCULADOS:"""
                
                if 'rsi_14' in tech_indicators:
                    rsi = tech_indicators['rsi_14']
                    if rsi > 70:
                        rsi_status = 'SOBRECOMPRADO (muy caro)'
                    elif rsi < 30:
                        rsi_status = 'SOBREVENDIDO (posible oportunidad)'
                    else:
                        rsi_status = 'NORMAL'
                    prompt += f"\n   • RSI: {rsi:.1f} - {rsi_status}"
                
                if 'macd' in tech_indicators:
                    macd = tech_indicators['macd']
                    trend_text = 'ALCISTA' if macd.get('trend') == 'bullish' else 'BAJISTA' if macd.get('trend') == 'bearish' else 'NEUTRAL'
                    prompt += f"\n   • MACD: {trend_text}"
                
                if 'volatility_annualized' in tech_indicators:
                    vol_annual = tech_indicators['volatility_annualized']
                    vol_category = 'MUY ALTA' if vol_annual > 60 else 'ALTA' if vol_annual > 40 else 'MODERADA' if vol_annual > 20 else 'BAJA'
                    prompt += f"\n   • Volatilidad: {vol_annual:.1f}% anual - {vol_category}"
        
        prompt += f"""

**TU TRABAJO:**

Analiza cada inversión y genera recomendaciones ESPECÍFICAS Y EJECUTABLES:

**FORMATO DE RESPUESTA REQUERIDO:**
```json
{{
  "acciones_inmediatas": [
    {{
      "ticker": "TICKER_EXACTO",
      "accion": "comprar/vender/mantener",
      "cantidad": numero_exacto_de_acciones,
      "precio_objetivo": precio_especifico,
      "razon": "Explicación simple: RSI en X indica Y, precio bajó/subió por Z",
      "urgencia": "alta/media/baja",
      "inversion_total": cantidad * precio (solo para compras),
      "stop_loss": precio_de_proteccion,
      "take_profit": precio_de_venta_ganadora
    }}
  ],
  "acciones_corto_plazo": [
    {{
      "ticker": "TICKER",
      "accion": "accion_especifica",
      "timeframe": "en X días específicos",
      "condiciones": "Cuando el precio llegue a $X o RSI llegue a Y",
      "trigger_price": precio_especifico_numerico,
      "explicacion_simple": "Por qué y cuándo hacerlo en palabras simples"
    }}
  ],
  "gestion_riesgo": {{
    "riesgo_cartera": numero_1_a_10,
    "stop_loss_sugeridos": {{
      "TICKER": precio_especifico_de_proteccion
    }},
    "recomendaciones_sizing": ["frases específicas sobre cuánto invertir"]
  }},
  "analisis_tecnico": {{
    "por_activo": {{
      "TICKER": {{
        "momentum": "alcista/bajista/neutral",
        "rsi_analysis": "sobrecomprado/sobrevendido/normal (valor_exacto)",
        "macd_signal": "bullish/bearish/neutral",
        "volatility_assessment": "alta/moderada/baja (valor_calculado)",
        "recomendacion": "Qué hacer basado en los indicadores reales"
      }}
    }}
  }},
  "razonamiento_integral": "Análisis completo en 2-3 oraciones explicando la situación actual y por qué recomiendas estas acciones específicas"
}}