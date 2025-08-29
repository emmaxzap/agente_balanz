# claude_portfolio_agent.py - Agente experto en gestión de carteras
import json
from datetime import date, timedelta
from typing import Dict, List
import anthropic
import os

class ClaudePortfolioAgent:
    def __init__(self, db_manager):
        self.db = db_manager
        # Configurar cliente de Anthropic (necesitarás tu API key)
        self.client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')  # Agregar tu API key
        )
    
    def analyze_portfolio_with_expert_agent(self, portfolio_data: Dict, available_cash: float) -> Dict:
        """Análisis completo usando agente experto de Claude"""
        try:
            print("\n🤖 INICIANDO ANÁLISIS CON AGENTE EXPERTO")
            print("-" * 50)
            
            # 1. Recopilar datos completos
            complete_data = self._gather_complete_portfolio_data(portfolio_data, available_cash)
            
            # 2. Crear prompt especializado
            expert_prompt = self._create_expert_prompt(complete_data)
            
            # 3. Consultar al agente experto
            expert_response = self._query_expert_agent(expert_prompt)
            
            # 4. Parsear respuesta
            parsed_analysis = self._parse_expert_response(expert_response)
            
            print("✅ Análisis experto completado")
            
            return parsed_analysis
            
        except Exception as e:
            print(f"❌ Error en análisis experto: {str(e)}")
            return self._create_fallback_analysis()
    
    def _gather_complete_portfolio_data(self, portfolio_data: Dict, available_cash: float) -> Dict:
        """Recopila todos los datos necesarios para el análisis experto"""
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
        
        # Recopilar datos detallados por posición
        for asset in portfolio_data.get('activos', []):
            ticker = asset['ticker']
            
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
            
            # Datos históricos y técnicos
            historical_data = self._get_comprehensive_historical_data(ticker)
            position_data['historical_analysis'] = historical_data
            
            # Datos fundamentales básicos
            fundamental_data = self._get_fundamental_data(ticker)
            position_data['fundamental_analysis'] = fundamental_data
            
            complete_data['positions'].append(position_data)
        
        # Datos de mercado general
        complete_data['market_data'] = self._get_market_context()
        
        return complete_data
    
    def _get_comprehensive_historical_data(self, ticker: str) -> Dict:
        """Obtiene análisis histórico completo de un activo"""
        try:
            # Obtener datos de diferentes períodos
            data_7d = self._get_historical_data_period(ticker, 7)
            data_30d = self._get_historical_data_period(ticker, 30)
            data_90d = self._get_historical_data_period(ticker, 90)
            
            return {
                'last_7_days': data_7d,
                'last_30_days': data_30d,
                'last_90_days': data_90d,
                'volatility_metrics': self._calculate_volatility_metrics(ticker),
                'trend_analysis': self._calculate_trend_analysis(ticker)
            }
        except:
            return {'error': 'Historical data not available'}
    
    def _get_historical_data_period(self, ticker: str, days: int) -> Dict:
        """Obtiene datos históricos para un período específico"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            result = self.db.supabase.table('precios_historico')\
                .select('fecha, precio_cierre')\
                .eq('ticker', ticker)\
                .gte('fecha', start_date.isoformat())\
                .order('fecha')\
                .execute()
            
            if not result.data:
                return {'error': 'No data available'}
            
            prices = [float(row['precio_cierre']) for row in result.data]
            dates = [row['fecha'] for row in result.data]
            
            if len(prices) < 2:
                return {'error': 'Insufficient data'}
            
            # Calcular métricas básicas
            return {
                'data_points': len(prices),
                'price_range': {
                    'min': min(prices),
                    'max': max(prices),
                    'current': prices[-1] if prices else 0
                },
                'performance': {
                    'total_return_pct': ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0,
                    'volatility': self._calculate_simple_volatility(prices)
                },
                'recent_trend': 'up' if prices[-1] > prices[0] else 'down' if prices[-1] < prices[0] else 'flat'
            }
        except:
            return {'error': 'Data processing failed'}
    
    def _calculate_simple_volatility(self, prices: List[float]) -> float:
        """Calcula volatilidad simple"""
        if len(prices) < 2:
            return 0
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        if not returns:
            return 0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        return (variance ** 0.5) * 100
    
    def _calculate_volatility_metrics(self, ticker: str) -> Dict:
        """Calcula métricas de volatilidad"""
        try:
            data_30d = self._get_historical_data_period(ticker, 30)
            return {
                'volatility_30d': data_30d.get('performance', {}).get('volatility', 0),
                'volatility_category': 'high' if data_30d.get('performance', {}).get('volatility', 0) > 8 else 'moderate' if data_30d.get('performance', {}).get('volatility', 0) > 4 else 'low'
            }
        except:
            return {'error': 'Volatility calculation failed'}
    
    def _calculate_trend_analysis(self, ticker: str) -> Dict:
        """Calcula análisis de tendencia"""
        try:
            data_7d = self._get_historical_data_period(ticker, 7)
            data_30d = self._get_historical_data_period(ticker, 30)
            
            return {
                'short_term_trend': data_7d.get('recent_trend', 'flat'),
                'medium_term_trend': data_30d.get('recent_trend', 'flat'),
                'trend_strength': 'strong' if abs(data_7d.get('performance', {}).get('total_return_pct', 0)) > 5 else 'weak'
            }
        except:
            return {'error': 'Trend analysis failed'}
    
    def _get_fundamental_data(self, ticker: str) -> Dict:
        """Obtiene datos fundamentales básicos (simulados por ahora)"""
        # Mapeo básico de sectores y características conocidas
        fundamental_map = {
            'ALUA': {'sector': 'Industrial', 'market_cap': 'large', 'liquidity': 'high'},
            'COME': {'sector': 'Consumer', 'market_cap': 'medium', 'liquidity': 'medium'},
            'EDN': {'sector': 'Mining', 'market_cap': 'large', 'liquidity': 'high'},
            'METR': {'sector': 'Utilities', 'market_cap': 'large', 'liquidity': 'high'},
            'TECO2': {'sector': 'Telecom', 'market_cap': 'large', 'liquidity': 'high'},
            'CEPU': {'sector': 'Mining', 'market_cap': 'medium', 'liquidity': 'medium'},
            'SUPV': {'sector': 'Financial', 'market_cap': 'large', 'liquidity': 'high'},
            'LOMA': {'sector': 'Mining', 'market_cap': 'medium', 'liquidity': 'medium'}
        }
        
        return fundamental_map.get(ticker, {'sector': 'Unknown', 'market_cap': 'unknown', 'liquidity': 'unknown'})
    
    def _get_economic_context(self) -> Dict:
        """Obtiene contexto económico general"""
        return {
            'market_date': date.today().isoformat(),
            'currency': 'ARS',
            'market': 'Argentina',
            'context': 'Portfolio contains recent positions (1 day average holding period)',
            'risk_factors': ['High inflation environment', 'Currency volatility', 'Political uncertainty']
        }
    
    def _get_market_context(self) -> Dict:
        """Obtiene contexto de mercado"""
        return {
            'market_session': 'Regular trading',
            'volatility_environment': 'Moderate to high',
            'sector_performance': 'Mixed - some sectors outperforming others'
        }
    
    def _create_expert_prompt(self, data: Dict) -> str:
        """Crea prompt profesional comprehensivo para análisis de cartera"""
        
        prompt = f"""Eres un gestor de carteras institucional senior con 25+ años de experiencia gestionando fondos de inversión en mercados emergentes, especializado en análisis técnico avanzado, gestión de riesgo cuantitativo y timing de mercado. 

Tu expertise incluye: análisis técnico (RSI, MACD, Bandas de Bollinger, patrones chartistas), análisis fundamental (ratios P/E, ROE, flujo de caja), gestión de riesgo (VaR, drawdown, correlaciones), estrategias de timing (momentum, reversión a la media), y productos de renta fija (plazos fijos, cauciones).

CARTERA BAJO ANÁLISIS:

**MÉTRICAS GENERALES:**
- Capital Total: ${data['portfolio_summary']['cash_available'] + data['portfolio_summary']['current_value']:,.2f} (Invertido: ${data['portfolio_summary']['current_value']:,.2f}, Efectivo: ${data['portfolio_summary']['cash_available']:,.2f})
- P&L Neto: ${data['portfolio_summary']['total_pnl']:,.2f}
- Número de Posiciones: {data['portfolio_summary']['positions_count']}
- Diversificación: {len(set([pos['fundamental_analysis']['sector'] for pos in data['positions']]))} sectores

**ANÁLISIS DETALLADO POR POSICIÓN:**"""
        
        for pos in data['positions']:
            days_held = pos['days_held']
            timeframe = "Muy Corto Plazo" if days_held <= 7 else "Corto Plazo" if days_held <= 30 else "Mediano Plazo" if days_held <= 180 else "Largo Plazo"
            
            volatility_7d = pos['historical_analysis'].get('last_7_days', {}).get('performance', {}).get('volatility', 0)
            volatility_30d = pos['historical_analysis'].get('last_30_days', {}).get('performance', {}).get('volatility', 0)
            
            prompt += f"""

{pos['ticker']} - {timeframe} ({days_held} días)
• Posición: {pos['shares']} nominales a ${pos['avg_cost']:.2f} (Actual: ${pos['current_price']:.2f})
• P&L: ${pos['pnl']:.2f} ({pos['pnl_pct']:+.1f}%) | Peso: {pos['position_size_pct']:.1%}
• Sector: {pos['fundamental_analysis'].get('sector')} | Cap: {pos['fundamental_analysis'].get('market_cap')}
• Volatilidad: 7d={volatility_7d:.1f}%, 30d={volatility_30d:.1f}%
• Tendencias: 7d={pos['historical_analysis'].get('last_7_days', {}).get('recent_trend', 'N/A')}, 30d={pos['historical_analysis'].get('last_30_days', {}).get('recent_trend', 'N/A')}, 90d={pos['historical_analysis'].get('last_90_days', {}).get('recent_trend', 'N/A')}
• Rendimiento Histórico: 7d={pos['historical_analysis'].get('last_7_days', {}).get('performance', {}).get('total_return_pct', 0):+.1f}%, 30d={pos['historical_analysis'].get('last_30_days', {}).get('performance', {}).get('total_return_pct', 0):+.1f}%, 90d={pos['historical_analysis'].get('last_90_days', {}).get('performance', {}).get('total_return_pct', 0):+.1f}%"""
        
        prompt += f"""

**CONTEXTO DE MERCADO:**
- Mercado: Argentina (ARS)
- Ambiente: Alta inflación, volatilidad cambiaria, incertidumbre política
- Tasas de referencia: ~100% anual (oportunidad de colocaciones a plazo fijo)

**ANÁLISIS REQUERIDO:**

Realiza un análisis profesional integral considerando:

**1. ANÁLISIS TÉCNICO AVANZADO:**
- Evalúa cada posición usando conceptos de soporte/resistencia, momentum, reversión a la media
- Identifica patrones técnicos (triangulos, cabeza y hombros, etc.)
- Analiza si las posiciones están sobrecompradas/sobrevendidas
- Evalúa divergencias entre precio y volumen/momentum
- Determina niveles de stop loss técnicos y take profit óptimos

**2. GESTIÓN DE RIESGO CUANTITATIVO:**
- Calcula el riesgo individual por posición y riesgo total de cartera
- Evalúa correlaciones entre activos para identificar concentración de riesgo
- Determina sizing óptimo de posiciones según volatilidad y correlación
- Analiza máximo drawdown potencial y escenarios de stress

**3. ESTRATEGIAS DE TIMING:**
- Para posiciones ganadoras: ¿conviene tomar ganancias parciales o dejar correr?
- Para posiciones perdedoras: ¿stop loss, averaging down, o hold?
- ¿Hay señales de momentum continuation o exhaustion?
- ¿Qué posiciones están cerca de puntos de inflexión técnicos?

**4. ASIGNACIÓN DE CAPITAL:**
- ¿El nivel actual de efectivo es óptimo o hay oportunidades de inversión?
- ¿Conviene rebalancear entre posiciones existentes?
- ¿Hay oportunidades de arbitraje sectorial?
- ¿Es momento de aumentar/reducir exposición total al mercado?

**5. ALTERNATIVAS DE INVERSIÓN:**
- Dado el contexto de alta inflación (100% anual), ¿conviene mantener tanto efectivo?
- ¿Hay oportunidades en plazos fijos, cauciones bursátiles o FCI de renta fija?
- ¿Qué porcentaje del efectivo debería destinarse a colocaciones de corto plazo vs oportunidades de equity?

**6. PLAN DE ACCIÓN TEMPORAL:**
- Acciones inmediatas (próximas 4-8 horas de trading)
- Acciones de corto plazo (1-5 días)
- Estrategia de mediano plazo (1-4 semanas)
- Revisiones programadas y triggers para cambios de estrategia

**FORMATO DE RESPUESTA:**
Estructura tu análisis en JSON con estas secciones:
```json
{{
  "analisis_tecnico": {{
    "por_activo": {{"TICKER": {{"soporte": precio, "resistencia": precio, "momentum": "alcista/bajista/neutral", "recomendacion": "texto", "stop_loss": precio, "take_profit": precio}}}},
    "mercado_general": "texto"
  }},
  "gestion_riesgo": {{
    "riesgo_cartera": "1-10",
    "concentraciones_riesgo": ["texto"],
    "sizing_recomendado": {{"TICKER": "porcentaje_cartera"}},
    "escenarios_stress": "texto"
  }},
  "acciones_inmediatas": [
    {{"ticker": "X", "accion": "comprar/vender/mantener", "cantidad": numero, "precio_objetivo": precio, "razon": "texto", "urgencia": "alta/media/baja"}}
  ],
  "acciones_corto_plazo": [
    {{"ticker": "X", "accion": "texto", "timeframe": "dias", "condiciones": "texto"}}
  ],
  "estrategia_efectivo": {{
    "efectivo_optimo": "porcentaje",
    "colocaciones_sugeridas": [
      {{"instrumento": "plazo_fijo/caucion/fci", "monto": "monto", "plazo": "dias", "tasa_esperada": "porcentaje"}}
    ]
  }},
  "plan_mediano_plazo": {{
    "objetivos_1_mes": ["texto"],
    "triggers_revision": ["condiciones_mercado"]
  }},
  "razonamiento_integral": "análisis_completo_profesional"
}}
```

**IMPORTANTE:** 
- No asumas que las posiciones son recientes - analiza cada timeframe apropiadamente
- Considera tanto análisis técnico como oportunidades de renta fija
- Ten en cuenta el contexto argentino (inflación, volatilidad)
- Sé específico con precios, cantidades y timeframes
- Balancea conservación de capital con generación de alpha"""

        return prompt
    
    def _query_expert_agent(self, prompt: str) -> str:
        """Consulta al agente experto de Claude"""
        try:
            if not os.getenv('ANTHROPIC_API_KEY'):
                return self._create_mock_expert_response()
            
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Modelo corregido
                max_tokens=4000,
                temperature=0.3,  # Menos creatividad, más consistencia
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"⚠️ Error consultando agente experto: {str(e)}")
            return self._create_mock_expert_response()
    
    def _create_mock_expert_response(self) -> str:
        """Crea respuesta simulada profesional completa para testing"""
        return """{
  "analisis_tecnico": {
    "por_activo": {
      "ALUA": {
        "soporte": 680,
        "resistencia": 740,
        "momentum": "bajista",
        "recomendacion": "Stop loss técnico en $680. Romper soporte confirmaría debilidad.",
        "stop_loss": 680,
        "take_profit": null
      },
      "EDN": {
        "soporte": 1470,
        "resistencia": 1580,
        "momentum": "alcista",
        "recomendacion": "Momentum positivo pero cerca de resistencia. Considerar toma de ganancias parcial.",
        "stop_loss": 1420,
        "take_profit": 1570
      },
      "TECO2": {
        "soporte": 2360,
        "resistencia": 2450,
        "momentum": "neutral",
        "recomendacion": "Trading en rango. Mantener mientras respete soporte en $2360.",
        "stop_loss": 2340,
        "take_profit": 2430
      },
      "COME": {
        "soporte": 43,
        "resistencia": 47,
        "momentum": "bajista",
        "recomendacion": "Debilidad técnica. Vigilar soporte en $43.",
        "stop_loss": 42,
        "take_profit": null
      },
      "METR": {
        "soporte": 1625,
        "resistencia": 1720,
        "momentum": "neutral",
        "recomendacion": "Consolidación en rango. Sin señales claras de dirección.",
        "stop_loss": 1600,
        "take_profit": 1700
      }
    },
    "mercado_general": "Mercado argentino en fase de consolidación después de movimientos recientes. Volatilidad elevada por contexto macro. Sectores defensivos (servicios públicos) muestran fortaleza relativa vs industriales."
  },
  "gestion_riesgo": {
    "riesgo_cartera": 6,
    "concentraciones_riesgo": [
      "Alta concentración en 5 activos sin diversificación geográfica",
      "Exposición concentrada al mercado argentino sin cobertura cambiaria",
      "41% en efectivo puede ser subóptimo en contexto inflacionario"
    ],
    "sizing_recomendado": {
      "EDN": "15%",
      "TECO2": "15%", 
      "METR": "12%",
      "ALUA": "8%",
      "COME": "10%"
    },
    "escenarios_stress": "En escenario de caída 15% del mercado, cartera podría perder 8-10% considerando correlaciones actuales. Alta liquidez permite defensive positioning."
  },
  "acciones_inmediatas": [
    {
      "ticker": "ALUA",
      "accion": "colocar_stop_loss",
      "cantidad": 0,
      "precio_objetivo": 680,
      "razon": "Precio rompió soporte técnico en $690. Stop loss en $680 para limitar pérdidas.",
      "urgencia": "alta"
    }
  ],
  "acciones_corto_plazo": [
    {
      "ticker": "EDN",
      "accion": "toma_ganancias_parcial",
      "timeframe": "2-3 días",
      "condiciones": "Vender 30% de posición si alcanza $1570 o si momentum se debilita"
    },
    {
      "ticker": "COME",
      "accion": "evaluar_averaging_down",
      "timeframe": "3-5 días",
      "condiciones": "Si mantiene soporte en $43, considerar compra adicional del 20%"
    }
  ],
  "estrategia_efectivo": {
    "efectivo_optimo": "25-30%",
    "colocaciones_sugeridas": [
      {
        "instrumento": "plazo_fijo",
        "monto": "15000",
        "plazo": "30 días",
        "tasa_esperada": "95-105%"
      },
      {
        "instrumento": "caucion_bursatil",
        "monto": "10000", 
        "plazo": "7 días",
        "tasa_esperada": "90-100%"
      }
    ]
  },
  "plan_mediano_plazo": {
    "objetivos_1_mes": [
      "Reducir efectivo de 41% a 25-30% mediante colocaciones de renta fija",
      "Diversificar en 2-3 activos adicionales para reducir concentración",
      "Establecer sistema de stops dinámicos en todas las posiciones"
    ],
    "triggers_revision": [
      "Movimiento >5% en dólar oficial",
      "Cambios en tasas de referencia del BCRA",
      "Resultados trimestrales de empresas en cartera"
    ]
  },
  "razonamiento_integral": "La cartera presenta buen balance riesgo/retorno pero requiere optimización. El 41% en efectivo es excesivo en contexto inflacionario del 100% anual - debe colocarse en instrumentos de renta fija. Las posiciones en equity muestran sizing adecuado pero necesitan stops técnicos más estrictos. EDN presenta mejor setup técnico para mantener, mientras ALUA requiere atención inmediata por ruptura de soporte. El contexto macro argentino favorece estrategia defensiva con alta liquidez, pero el cash debe trabajar en plazos fijos o cauciones para mantener poder adquisitivo."
}"""
    
    def _parse_expert_response(self, response: str) -> Dict:
        """Parsea la respuesta del agente experto"""
        try:
            # Intentar parsear JSON
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                # Validar estructura
                required_keys = ['immediate_actions', 'short_term_actions', 'risk_assessment', 'strategic_recommendations']
                if all(key in parsed for key in required_keys):
                    return parsed
            
            # Si no se puede parsear, crear estructura básica
            return self._create_fallback_analysis()
            
        except Exception as e:
            print(f"⚠️ Error parseando respuesta experta: {str(e)}")
            return self._create_fallback_analysis()
    
    def _create_fallback_analysis(self) -> Dict:
        """Crea análisis de respaldo si falla el agente experto"""
        return {
            "immediate_actions": [],
            "short_term_actions": [],
            "risk_assessment": {
                "overall_risk_level": 5,
                "key_risks": ["Expert analysis not available"],
                "position_sizing": "Unable to assess"
            },
            "strategic_recommendations": ["Consult with financial advisor"],
            "reasoning": "Expert agent analysis failed, using conservative fallback"
        }