# macro_data_collector.py - Recolector de datos macroeconómicos
import requests
import pandas as pd
from datetime import date, timedelta
from typing import Dict, Optional
import time

class MacroDataCollector:
    def __init__(self, db_manager):
        self.db = db_manager
        
        # APIs gratuitas disponibles
        self.apis = {
            'dolar_blue': 'https://api.bluelytics.com.ar/v2/latest',
            'bcra': 'https://api.bcra.gob.ar/centralweb/v1/cotizaciones',
            'ambito_riesgo': 'https://api.ambito.com/v2/mercados/riesgo-pais/valor',
        }
    
    def get_current_macro_snapshot(self) -> Dict:
        """Obtiene snapshot actual de todos los datos macro"""
        snapshot = {
            'fecha': date.today().isoformat(),
            'timestamp': pd.Timestamp.now(),
            'dolar_data': {},
            'bcra_data': {},
            'riesgo_pais': None,
            'success_flags': {}
        }
        
        print("🌍 OBTENIENDO DATOS MACROECONÓMICOS ACTUALES...")
        print("-" * 50)
        
        # 1. Dólar Blue
        dolar_data = self._get_dolar_blue_data()
        if dolar_data:
            snapshot['dolar_data'] = dolar_data
            snapshot['success_flags']['dolar_blue'] = True
            print(f"✅ Dólar Blue: ${dolar_data.get('blue_buy', 0):.0f} / ${dolar_data.get('blue_sell', 0):.0f}")
        else:
            snapshot['success_flags']['dolar_blue'] = False
            print("❌ Error obteniendo dólar blue")
        
        # 2. BCRA (dólar oficial, tasas)
        bcra_data = self._get_bcra_data()
        if bcra_data:
            snapshot['bcra_data'] = bcra_data
            snapshot['success_flags']['bcra'] = True
            print(f"✅ BCRA: Oficial ${bcra_data.get('usd_oficial', 0):.0f}, Leliq {bcra_data.get('leliq', 0):.1f}%")
        else:
            snapshot['success_flags']['bcra'] = False
            print("❌ Error obteniendo datos BCRA")
        
        # 3. Riesgo País
        riesgo_pais = self._get_riesgo_pais()
        if riesgo_pais:
            snapshot['riesgo_pais'] = riesgo_pais
            snapshot['success_flags']['riesgo_pais'] = True
            print(f"✅ Riesgo País: {riesgo_pais:.0f} puntos")
        else:
            snapshot['success_flags']['riesgo_pais'] = False
            print("❌ Error obteniendo riesgo país")
        
        return snapshot
    
    def _get_dolar_blue_data(self) -> Optional[Dict]:
        """Obtiene cotización del dólar blue"""
        try:
            response = requests.get(self.apis['dolar_blue'], timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'blue_buy': data['blue']['value_buy'],
                    'blue_sell': data['blue']['value_sell'],
                    'oficial_buy': data['oficial']['value_buy'],
                    'oficial_sell': data['oficial']['value_sell'],
                    'brecha': ((data['blue']['value_sell'] - data['oficial']['value_sell']) / data['oficial']['value_sell'] * 100)
                }
        except Exception as e:
            print(f"   ⚠️ Error dólar blue: {str(e)}")
            return None
    
    def _get_bcra_data(self) -> Optional[Dict]:
        """Obtiene datos del BCRA"""
        try:
            response = requests.get(self.apis['bcra'], timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                bcra_data = {}
                for item in data.get('results', []):
                    if item['descripcion'] == 'Dólar U.S.A. (Comunicación "A" 3500)':
                        bcra_data['usd_oficial'] = item['valor']
                    elif 'LELIQ' in item['descripcion']:
                        bcra_data['leliq'] = item['valor']
                
                return bcra_data
        except Exception as e:
            print(f"   ⚠️ Error BCRA: {str(e)}")
            return None
    
    def _get_riesgo_pais(self) -> Optional[float]:
        """Obtiene riesgo país de Ámbito"""
        try:
            response = requests.get(self.apis['ambito_riesgo'], timeout=10)
            if response.status_code == 200:
                data = response.json()
                return float(data['valor'])
        except Exception as e:
            print(f"   ⚠️ Error riesgo país: {str(e)}")
            return None
    
    def get_macro_context_for_analysis(self) -> Dict:
        """Genera contexto macro para el análisis de cartera"""
        current_snapshot = self.get_current_macro_snapshot()
        historical_context = self._get_macro_historical_context()
        
        # Analizar situación macro
        macro_analysis = self._analyze_macro_situation(current_snapshot, historical_context)
        
        return {
            'current_snapshot': current_snapshot,
            'historical_trends': historical_context,
            'macro_analysis': macro_analysis,
            'investment_implications': self._generate_investment_implications(macro_analysis)
        }
    
    def _get_macro_historical_context(self) -> Dict:
        """Obtiene contexto histórico de datos macro (últimos 30 días)"""
        try:
            # Buscar datos históricos en tu BD (si los tienes guardados)
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            result = self.db.supabase.table('macro_historico')\
                .select('*')\
                .gte('fecha', start_date.isoformat())\
                .order('fecha')\
                .execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                
                # Calcular tendencias
                trends = {}
                if 'dolar_blue' in df.columns:
                    blue_change_30d = ((df['dolar_blue'].iloc[-1] - df['dolar_blue'].iloc[0]) / df['dolar_blue'].iloc[0] * 100)
                    trends['dolar_blue_30d_change'] = blue_change_30d
                
                if 'riesgo_pais' in df.columns:
                    rp_change_30d = df['riesgo_pais'].iloc[-1] - df['riesgo_pais'].iloc[0]
                    trends['riesgo_pais_30d_change'] = rp_change_30d
                
                return trends
            
            return {}
            
        except Exception as e:
            print(f"   ⚠️ Sin contexto histórico macro: {str(e)}")
            return {}
    
    def _analyze_macro_situation(self, current: Dict, historical: Dict) -> Dict:
        """Analiza la situación macro actual"""
        analysis = {
            'market_stress_level': 'medium',  # low, medium, high, extreme
            'currency_pressure': 'medium',
            'investment_environment': 'neutral'
        }
        
        # Analizar nivel de stress del mercado
        riesgo_pais = current.get('riesgo_pais', 1000)
        if riesgo_pais > 2000:
            analysis['market_stress_level'] = 'extreme'
        elif riesgo_pais > 1500:
            analysis['market_stress_level'] = 'high'
        elif riesgo_pais > 1000:
            analysis['market_stress_level'] = 'medium'
        else:
            analysis['market_stress_level'] = 'low'
        
        # Analizar presión cambiaria
        dolar_data = current.get('dolar_data', {})
        brecha = dolar_data.get('brecha', 0)
        if brecha > 50:
            analysis['currency_pressure'] = 'high'
        elif brecha > 30:
            analysis['currency_pressure'] = 'medium'
        else:
            analysis['currency_pressure'] = 'low'
        
        # Ambiente de inversión general
        if (analysis['market_stress_level'] in ['extreme', 'high'] and 
            analysis['currency_pressure'] == 'high'):
            analysis['investment_environment'] = 'defensive'
        elif (analysis['market_stress_level'] == 'low' and 
              analysis['currency_pressure'] == 'low'):
            analysis['investment_environment'] = 'aggressive'
        else:
            analysis['investment_environment'] = 'neutral'
        
        return analysis
    
    def _generate_investment_implications(self, macro_analysis: Dict) -> Dict:
        """Genera implicaciones específicas para inversión"""
        implications = {
            'portfolio_bias': 'neutral',
            'sector_preferences': [],
            'risk_adjustments': [],
            'currency_hedge_needed': False
        }
        
        stress_level = macro_analysis['market_stress_level']
        currency_pressure = macro_analysis['currency_pressure']
        
        # Ajustes por stress de mercado
        if stress_level == 'extreme':
            implications['portfolio_bias'] = 'defensive'
            implications['risk_adjustments'] = [
                'Reducir tamaños de posición en 30%',
                'Aumentar stops loss (más estrictos)',
                'Priorizar blue chips'
            ]
        elif stress_level == 'low':
            implications['portfolio_bias'] = 'aggressive'
            implications['risk_adjustments'] = [
                'Permitir posiciones más grandes',
                'Stops loss más flexibles',
                'Considerar acciones de menor cap'
            ]
        
        # Sectores preferidos según macro
        if currency_pressure == 'high':
            implications['sector_preferences'] = [
                'Exportadores (ALUA, agro)',
                'CEDEARs dolarizados',
                'Energía (YPFD)'
            ]
            implications['currency_hedge_needed'] = True
        
        return implications
    
    def save_macro_snapshot_to_db(self, snapshot: Dict) -> bool:
        """Guarda snapshot macro en la BD"""
        try:
            macro_record = {
                'fecha': snapshot['fecha'],
                'dolar_blue_buy': snapshot['dolar_data'].get('blue_buy'),
                'dolar_blue_sell': snapshot['dolar_data'].get('blue_sell'),
                'dolar_oficial': snapshot['dolar_data'].get('oficial_sell'),
                'brecha_cambiaria': snapshot['dolar_data'].get('brecha'),
                'riesgo_pais': snapshot.get('riesgo_pais'),
                'leliq_rate': snapshot['bcra_data'].get('leliq'),
                'data_quality': len([v for v in snapshot['success_flags'].values() if v])
            }
            
            # Usar upsert para evitar duplicados
            result = self.db.supabase.table('macro_historico').upsert(macro_record).execute()
            
            print(f"✅ Datos macro guardados en BD")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando macro data: {str(e)}")
            return False

# EJEMPLO DE INTEGRACIÓN CON TU ANÁLISIS EXISTENTE
class MacroEnhancedPortfolioAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        self.macro_collector = MacroDataCollector(db_manager)
    
    def analyze_portfolio_with_macro_context(self, portfolio_data: Dict) -> Dict:
        """Análisis de cartera enriquecido con contexto macro"""
        
        # 1. Obtener contexto macro actual
        macro_context = self.macro_collector.get_macro_context_for_analysis()
        
        # 2. Ajustar recomendaciones según macro
        base_analysis = self._get_base_technical_analysis(portfolio_data)
        macro_adjusted_analysis = self._adjust_recommendations_for_macro(
            base_analysis, macro_context
        )
        
        return {
            'base_technical_analysis': base_analysis,
            'macro_context': macro_context,
            'final_recommendations': macro_adjusted_analysis,
            'macro_enhanced': True
        }
    
    def _adjust_recommendations_for_macro(self, base_analysis: Dict, macro_context: Dict) -> Dict:
        """Ajusta recomendaciones técnicas según contexto macro"""
        
        macro_analysis = macro_context['macro_analysis']
        implications = macro_context['investment_implications']
        
        adjusted_recs = base_analysis.copy()
        
        # Ajustar según stress de mercado
        if macro_analysis['market_stress_level'] == 'extreme':
            # En stress extremo: ser más conservador
            for rec in adjusted_recs.get('buy_recommendations', []):
                rec['suggested_quantity'] = int(rec['suggested_quantity'] * 0.5)  # Reducir 50%
                rec['confidence'] -= 15  # Menos confianza
                rec['macro_adjustment'] = 'Reducido por stress extremo de mercado'
        
        elif macro_analysis['market_stress_level'] == 'low':
            # En calma: ser más agresivo
            for rec in adjusted_recs.get('buy_recommendations', []):
                rec['suggested_quantity'] = int(rec['suggested_quantity'] * 1.3)  # Aumentar 30%
                rec['confidence'] += 10
                rec['macro_adjustment'] = 'Aumentado por ambiente favorable'
        
        # Ajustar por presión cambiaria
        if implications['currency_hedge_needed']:
            # Favorecer CEDEARs y exportadores
            cedear_recs = [rec for rec in adjusted_recs.get('buy_recommendations', []) 
                          if self._is_cedear_or_exporter(rec['ticker'])]
            
            for rec in cedear_recs:
                rec['confidence'] += 15
                rec['macro_adjustment'] = 'Favorecido por presión cambiaria'
        
        return adjusted_recs
    
    def _is_cedear_or_exporter(self, ticker: str) -> bool:
        """Identifica si es CEDEAR o exportador"""
        cedears = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NFLX']
        exporters = ['ALUA', 'YPFD', 'LOMA', 'CEPU']  # Minería, petróleo, agro
        
        return ticker in cedears + exporters