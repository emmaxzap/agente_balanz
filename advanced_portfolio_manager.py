# advanced_portfolio_manager.py - Sistema profesional con análisis de corto plazo
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ActionType(Enum):
    BUY_INITIAL = "compra_inicial"
    BUY_AVERAGING_DOWN = "promedio_a_la_baja"
    BUY_MOMENTUM = "compra_momentum"
    SELL_PROFIT_TAKING = "toma_ganancias"
    SELL_STOP_LOSS = "stop_loss"
    SELL_REBALANCE = "rebalanceo"
    SELL_TRAILING_STOP = "trailing_stop"
    HOLD = "mantener"
    REDUCE_POSITION = "reducir_posicion"

@dataclass
class PositionAnalysis:
    ticker: str
    current_shares: int
    avg_cost: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    days_held: int
    sector: str
    position_size_pct: float
    risk_score: float

@dataclass
class TradeRecommendation:
    ticker: str
    action: ActionType
    suggested_shares: int
    target_price: float
    confidence: float
    reasons: List[str]
    risk_assessment: str
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    max_position_size: Optional[float] = None

class AdvancedPortfolioManager:
    def __init__(self, db_manager, financial_analyzer):
        self.db = db_manager
        self.analyzer = financial_analyzer
        
        # Configuración profesional ajustada para diferentes plazos
        self.risk_config = {
            # Posiciones nuevas (0-3 días) - MÁS CONSERVADOR
            'new_position_stop_loss': 0.08,        # Stop loss -8% para posiciones nuevas
            'new_position_profit_taking': 0.15,    # Tomar ganancias a +15% en posiciones nuevas
            'new_position_max_risk': 0.12,         # Máximo 12% por posición nueva
            
            # Posiciones establecidas (4-30 días) - MODERADO
            'established_stop_loss': 0.12,         # Stop loss -12% para posiciones establecidas
            'established_profit_taking': 0.25,     # Tomar ganancias a +25%
            'established_max_risk': 0.15,          # Máximo 15% por posición establecida
            
            # Posiciones maduras (30+ días) - MÁS FLEXIBLE
            'mature_stop_loss': 0.20,              # Stop loss -20% para posiciones maduras
            'mature_profit_taking': 0.40,          # Tomar ganancias a +40%
            'mature_max_risk': 0.20,               # Máximo 20% por posición madura
            
            # Configuración general
            'max_sector_allocation': 0.30,         # Máximo 30% por sector
            'rebalance_threshold': 0.05,           # Rebalancear si desviación >5%
            'momentum_confirmation_days': 3,       # 3 días para confirmar momentum en corto plazo
            'technical_analysis_weight': 0.7,      # 70% peso al análisis técnico vs fundamental
            'daily_volatility_threshold': 0.05,    # 5% volatilidad diaria máxima aceptable
        }
        
        # Sectores mejorados
        self.sector_mapping = {
            # Tecnología
            'AAPL': 'tecnologia', 'MSFT': 'tecnologia', 'GOOGL': 'tecnologia', 'AMZN': 'tecnologia',
            'TSLA': 'tecnologia', 'NVDA': 'tecnologia', 'META': 'tecnologia', 'NFLX': 'tecnologia',
            
            # Financiero
            'BBAR': 'financiero', 'BMA': 'financiero', 'GGAL': 'financiero', 'SUPV': 'financiero',
            
            # Energía
            'YPFD': 'energia', 'PAM': 'energia', 'TGNO4': 'energia', 'TGSU2': 'energia',
            
            # Consumo
            'KO': 'consumo', 'PEP': 'consumo', 'WMT': 'consumo', 'PG': 'consumo',
            'COME': 'consumo', 'ALUA': 'industrial', 
            
            # Salud
            'JNJ': 'salud', 'UNH': 'salud', 'PFE': 'salud', 'ABBV': 'salud',
            
            # Minería y Materiales
            'LOMA': 'mineria', 'EDN': 'mineria', 'CEPU': 'mineria',
            
            # Servicios Públicos
            'METR': 'servicios_publicos', 'TECO2': 'telecom', 'TEF': 'telecom',
            
            # Industrial
            'MMM': 'industrial', 'CAT': 'industrial', 'BA': 'industrial',
        }
    
    def analyze_complete_portfolio(self, portfolio_data: Dict, available_cash: float) -> Dict:
        """Análisis completo profesional con manejo inteligente de diferentes plazos"""
        
        # 1. Analizar posiciones con criterios específicos por plazo
        positions = self._analyze_current_positions_with_timeframe(portfolio_data['activos'])
        
        # 2. Calcular métricas de cartera
        portfolio_metrics = self._calculate_portfolio_metrics(positions, available_cash)
        
        # 3. Análisis técnico intensivo para posiciones de corto plazo
        technical_analysis = self._perform_technical_analysis(positions)
        
        # 4. Generar recomendaciones inteligentes por plazo
        recommendations = {
            'short_term_trades': self._analyze_short_term_opportunities(positions, technical_analysis),
            'profit_taking': self._analyze_intelligent_profit_taking(positions, technical_analysis),
            'stop_losses': self._analyze_dynamic_stop_losses(positions, technical_analysis),
            'rebalancing': self._analyze_smart_rebalancing(positions, portfolio_metrics),
            'new_positions': self._analyze_new_position_opportunities(available_cash, positions),
        }
        
        # 5. Consolidar con lógica profesional
        consolidated_recs = self._consolidate_with_professional_logic(recommendations, technical_analysis)
        
        # 6. Aplicar límites de riesgo dinámicos
        risk_adjusted_recs = self._apply_dynamic_risk_limits(consolidated_recs, portfolio_metrics, available_cash)
        
        return {
            'positions_analysis': positions,
            'portfolio_metrics': portfolio_metrics,
            'technical_analysis': technical_analysis,
            'recommendations': risk_adjusted_recs,
            'risk_assessment': self._generate_professional_risk_assessment(positions, portfolio_metrics),
            'execution_plan': self._generate_intelligent_execution_plan(risk_adjusted_recs)
        }
    
    def _analyze_current_positions_with_timeframe(self, assets: List[Dict]) -> List[PositionAnalysis]:
        """Análisis de posiciones considerando diferentes marcos temporales"""
        positions = []
        
        for asset in assets:
            ticker = asset['ticker']
            days_held = max(asset.get('dias_tenencia', 0), 0)  # Asegurar que no sea negativo
            
            # Obtener datos históricos específicos según plazo
            if days_held <= 3:
                # Posiciones nuevas: análisis intradiario intensivo
                historical_data = self.analyzer._get_historical_data(ticker, days=7)
                timeframe_category = 'new'
            elif days_held <= 30:
                # Posiciones establecidas: análisis semanal
                historical_data = self.analyzer._get_historical_data(ticker, days=30)
                timeframe_category = 'established'
            else:
                # Posiciones maduras: análisis mensual
                historical_data = self.analyzer._get_historical_data(ticker, days=90)
                timeframe_category = 'mature'
            
            # Calcular métricas específicas por timeframe
            risk_score = self._calculate_timeframe_risk_score(
                asset, historical_data, timeframe_category
            )
            
            sector = self.sector_mapping.get(ticker, 'otros')
            
            position = PositionAnalysis(
                ticker=ticker,
                current_shares=asset['cantidad'],
                avg_cost=asset['precio_inicial_unitario'],
                current_price=asset['precio_actual_unitario'],
                current_value=asset['valor_actual_total'],
                unrealized_pnl=asset['ganancia_perdida_total'],
                unrealized_pnl_pct=asset['ganancia_perdida_porcentaje'],
                days_held=days_held,
                sector=sector,
                position_size_pct=0,  # Se calculará después
                risk_score=risk_score
            )
            
            positions.append(position)
        
        # Calcular tamaños relativos
        total_value = sum(p.current_value for p in positions)
        if total_value > 0:
            for position in positions:
                position.position_size_pct = position.current_value / total_value
        
        return positions
    
    def _calculate_timeframe_risk_score(self, asset: Dict, historical_data: pd.DataFrame, timeframe: str) -> float:
        """Calcula score de riesgo específico según el marco temporal"""
        base_risk = 5.0
        pnl_pct = asset['ganancia_perdida_porcentaje']
        days_held = asset.get('dias_tenencia', 0)
        
        if timeframe == 'new':
            # Posiciones nuevas: más peso a volatilidad reciente
            if abs(pnl_pct) > 8:  # Alta volatilidad inicial
                base_risk += 2.0
            if days_held == 0:  # Compra del mismo día
                base_risk += 1.0
                
        elif timeframe == 'established':
            # Posiciones establecidas: balance entre momentum y reversión
            if pnl_pct < -10:  # Pérdida significativa
                base_risk += 1.5
            elif pnl_pct > 20:  # Ganancia muy rápida
                base_risk += 0.5
                
        else:  # mature
            # Posiciones maduras: más tolerancia a volatilidad
            if pnl_pct < -25:
                base_risk += 2.0
            elif pnl_pct > 50:
                base_risk += 1.0
        
        # Ajustar por datos históricos disponibles
        if not historical_data.empty and len(historical_data) >= 5:
            volatility = historical_data['precio_cierre'].pct_change().std() * 100
            if volatility > 10:  # Alta volatilidad histórica
                base_risk += 1.0
        
        return min(10.0, max(0.0, base_risk))
    
    def _perform_technical_analysis(self, positions: List[PositionAnalysis]) -> Dict:
        """Análisis técnico intensivo para cada posición"""
        technical_data = {}
        
        for position in positions:
            try:
                # Análisis técnico específico
                analysis = self.analyzer.analyze_asset_for_decision(position.ticker, position.current_price)
                
                # Extraer indicadores clave
                indicators = analysis.get('indicators', {})
                
                # Calcular señales técnicas adicionales
                technical_signals = self._calculate_technical_signals(position.ticker, position.days_held)
                
                technical_data[position.ticker] = {
                    'trend': indicators.get('trend', 'FLAT'),
                    'trend_strength': abs(indicators.get('trend_slope', 0)),
                    'position_in_range': indicators.get('position_in_range', 0.5),
                    'volatility': indicators.get('volatility', 0),
                    'momentum': technical_signals.get('momentum', 'NEUTRAL'),
                    'support_level': technical_signals.get('support', position.current_price * 0.95),
                    'resistance_level': technical_signals.get('resistance', position.current_price * 1.05),
                    'buy_signal_strength': analysis.get('confidence', 50) if analysis.get('recommendation') == 'COMPRA' else 0,
                    'sell_signal_strength': 100 - analysis.get('confidence', 50) if analysis.get('recommendation') == 'MANTENER' else 0
                }
            except:
                # Datos por defecto si falla el análisis
                technical_data[position.ticker] = {
                    'trend': 'FLAT', 'trend_strength': 0, 'position_in_range': 0.5,
                    'volatility': 0, 'momentum': 'NEUTRAL',
                    'support_level': position.current_price * 0.95,
                    'resistance_level': position.current_price * 1.05,
                    'buy_signal_strength': 0, 'sell_signal_strength': 0
                }
        
        return technical_data
    
    def _calculate_technical_signals(self, ticker: str, days_held: int) -> Dict:
        """Calcula señales técnicas específicas"""
        try:
            # Obtener datos para análisis técnico
            lookback_days = max(14, days_held + 7)  # Al menos 14 días o días tenencia + 7
            historical_data = self.analyzer._get_historical_data(ticker, days=lookback_days)
            
            if historical_data.empty or len(historical_data) < 5:
                return {'momentum': 'NEUTRAL', 'support': None, 'resistance': None}
            
            prices = historical_data['precio_cierre'].values
            
            # Calcular momentum
            if len(prices) >= 5:
                recent_trend = np.polyfit(range(5), prices[-5:], 1)[0]
                if recent_trend > 0:
                    momentum = 'POSITIVE'
                elif recent_trend < 0:
                    momentum = 'NEGATIVE'
                else:
                    momentum = 'NEUTRAL'
            else:
                momentum = 'NEUTRAL'
            
            # Calcular soporte y resistencia
            recent_prices = prices[-min(10, len(prices)):]
            support = np.min(recent_prices)
            resistance = np.max(recent_prices)
            
            return {
                'momentum': momentum,
                'support': support,
                'resistance': resistance
            }
        except:
            return {'momentum': 'NEUTRAL', 'support': None, 'resistance': None}
    
    def _analyze_intelligent_profit_taking(self, positions: List[PositionAnalysis], technical_analysis: Dict) -> List[TradeRecommendation]:
        """Análisis inteligente de toma de ganancias según plazo y análisis técnico"""
        recommendations = []
        
        for position in positions:
            if position.unrealized_pnl_pct <= 5:  # Solo si hay ganancia mínima
                continue
            
            technical = technical_analysis.get(position.ticker, {})
            
            # Determinar umbral de profit taking según días de tenencia
            if position.days_held <= 3:
                profit_threshold = self.risk_config['new_position_profit_taking'] * 100
            elif position.days_held <= 30:
                profit_threshold = self.risk_config['established_profit_taking'] * 100
            else:
                profit_threshold = self.risk_config['mature_profit_taking'] * 100
            
            # Evaluar si es momento de tomar ganancias
            should_take_profit = False
            profit_reason = ""
            shares_to_sell = 0
            
            if position.unrealized_pnl_pct >= profit_threshold:
                # Ganancia alcanzó umbral - pero verificar momentum
                if technical.get('momentum') == 'POSITIVE' and technical.get('trend') == 'UP':
                    # Momentum positivo - tomar solo ganancias parciales
                    shares_to_sell = int(position.current_shares * 0.3)  # 30%
                    profit_reason = f"Toma ganancias parcial - target {profit_threshold:.0f}% alcanzado con momentum positivo"
                else:
                    # Sin momentum - tomar más ganancias
                    shares_to_sell = int(position.current_shares * 0.5)  # 50%
                    profit_reason = f"Toma ganancias - target {profit_threshold:.0f}% alcanzado sin momentum"
                
                should_take_profit = True
            
            elif position.unrealized_pnl_pct >= profit_threshold * 0.7:  # 70% del target
                # Cerca del target - evaluar resistencia técnica
                if position.current_price >= technical.get('resistance_level', float('inf')) * 0.98:
                    # Cerca de resistencia técnica
                    shares_to_sell = int(position.current_shares * 0.25)  # 25%
                    profit_reason = f"Cerca de resistencia técnica (${technical.get('resistance_level', 0):,.0f})"
                    should_take_profit = True
            
            if should_take_profit and shares_to_sell > 0:
                confidence = 70
                if technical.get('momentum') == 'NEGATIVE':
                    confidence += 15  # Mayor confianza si momentum es negativo
                
                recommendation = TradeRecommendation(
                    ticker=position.ticker,
                    action=ActionType.SELL_PROFIT_TAKING,
                    suggested_shares=shares_to_sell,
                    target_price=position.current_price,
                    confidence=confidence,
                    reasons=[profit_reason, f"Posición con {position.days_held} días de tenencia"],
                    risk_assessment="Riesgo bajo - toma de ganancias",
                    take_profit_price=position.current_price
                )
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_dynamic_stop_losses(self, positions: List[PositionAnalysis], technical_analysis: Dict) -> List[TradeRecommendation]:
        """Análisis de stop losses dinámicos según plazo y técnico"""
        recommendations = []
        
        for position in positions:
            technical = technical_analysis.get(position.ticker, {})
            
            # Determinar stop loss según días de tenencia
            if position.days_held <= 3:
                stop_threshold = -self.risk_config['new_position_stop_loss'] * 100
            elif position.days_held <= 30:
                stop_threshold = -self.risk_config['established_stop_loss'] * 100
            else:
                stop_threshold = -self.risk_config['mature_stop_loss'] * 100
            
            # Evaluar si activar stop loss
            should_stop = False
            stop_reason = ""
            
            if position.unrealized_pnl_pct <= stop_threshold:
                # Umbral alcanzado
                should_stop = True
                stop_reason = f"Stop loss activado - pérdida {position.unrealized_pnl_pct:.1f}% excede límite {stop_threshold:.0f}%"
            
            elif position.days_held <= 1 and position.unrealized_pnl_pct <= -5:
                # Posiciones del mismo día con pérdida significativa
                should_stop = True
                stop_reason = f"Stop loss rápido - pérdida {position.unrealized_pnl_pct:.1f}% en posición de {position.days_held} día(s)"
            
            elif technical.get('momentum') == 'NEGATIVE' and position.unrealized_pnl_pct <= stop_threshold * 0.7:
                # Momentum negativo con pérdida moderada
                should_stop = True
                stop_reason = f"Stop loss por momentum negativo y pérdida {position.unrealized_pnl_pct:.1f}%"
            
            if should_stop:
                # Ajustar precio de stop por soporte técnico
                support_level = technical.get('support_level')
                if support_level and support_level < position.current_price:
                    stop_price = max(support_level, position.current_price * (1 + stop_threshold/100))
                else:
                    stop_price = position.current_price
                
                recommendation = TradeRecommendation(
                    ticker=position.ticker,
                    action=ActionType.SELL_STOP_LOSS,
                    suggested_shares=position.current_shares,
                    target_price=stop_price,
                    confidence=90,
                    reasons=[stop_reason, f"Análisis técnico: {technical.get('momentum', 'NEUTRAL')} momentum"],
                    risk_assessment="Riesgo alto - protección de capital",
                    stop_loss_price=stop_price
                )
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_smart_rebalancing(self, positions: List[PositionAnalysis], portfolio_metrics: Dict) -> List[TradeRecommendation]:
        """Rebalanceo inteligente que considera momentum y plazo"""
        recommendations = []
        
        for position in positions:
            # Solo rebalancear posiciones que realmente excedan límites significativamente
            max_size = self._get_max_position_size_by_timeframe(position.days_held)
            
            if position.position_size_pct <= max_size + 0.05:  # 5% de tolerancia
                continue
            
            # Verificar si la posición está en tendencia positiva fuerte
            technical = self.analyzer.analyze_asset_for_decision(position.ticker)
            indicators = technical.get('indicators', {})
            
            # No rebalancear posiciones ganadoras en momentum fuerte si son recientes
            if (position.days_held <= 7 and 
                position.unrealized_pnl_pct > 5 and 
                indicators.get('trend') == 'UP' and 
                abs(indicators.get('trend_slope', 0)) > 100):
                continue
            
            # Calcular reducción necesaria
            target_size = max_size
            excess_pct = position.position_size_pct - target_size
            shares_to_sell = int(position.current_shares * (excess_pct / position.position_size_pct))
            
            if shares_to_sell > 0:
                confidence = 75
                if position.unrealized_pnl_pct > 20:  # Posición muy ganadora
                    confidence -= 10  # Menos confianza en vender ganador
                
                recommendation = TradeRecommendation(
                    ticker=position.ticker,
                    action=ActionType.SELL_REBALANCE,
                    suggested_shares=shares_to_sell,
                    target_price=position.current_price,
                    confidence=confidence,
                    reasons=[
                        f"Rebalanceo - posición {position.position_size_pct:.1%} excede límite {max_size:.1%}",
                        f"Considerando {position.days_held} días de tenencia y momentum actual"
                    ],
                    risk_assessment="Riesgo bajo - diversificación de cartera"
                )
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def _get_max_position_size_by_timeframe(self, days_held: int) -> float:
        """Retorna el tamaño máximo de posición según días de tenencia"""
        if days_held <= 3:
            return self.risk_config['new_position_max_risk']
        elif days_held <= 30:
            return self.risk_config['established_max_risk']
        else:
            return self.risk_config['mature_max_risk']
    
    def _analyze_short_term_opportunities(self, positions: List[PositionAnalysis], technical_analysis: Dict) -> List[TradeRecommendation]:
        """Analiza oportunidades específicas de corto plazo"""
        recommendations = []
        
        # Esta función busca oportunidades de trading rápido en posiciones existentes
        for position in positions:
            if position.days_held > 7:  # Solo para posiciones muy recientes
                continue
            
            technical = technical_analysis.get(position.ticker, {})
            
            # Buscar oportunidades de averaging down inteligente
            if (position.unrealized_pnl_pct < -3 and 
                position.unrealized_pnl_pct > -8 and
                technical.get('momentum') == 'POSITIVE'):
                
                # Oportunidad de promediar a la baja con momentum positivo
                additional_shares = min(
                    int(position.current_shares * 0.2),  # Máximo 20% más
                    int(10000 / position.current_price)   # O hasta $10k
                )
                
                if additional_shares > 0:
                    recommendation = TradeRecommendation(
                        ticker=position.ticker,
                        action=ActionType.BUY_AVERAGING_DOWN,
                        suggested_shares=additional_shares,
                        target_price=position.current_price,
                        confidence=65,
                        reasons=[
                            f"Averaging down en posición reciente ({position.days_held} días)",
                            f"Pérdida moderada {position.unrealized_pnl_pct:.1f}% con momentum positivo"
                        ],
                        risk_assessment="Riesgo moderado - averaging down táctico"
                    )
                    
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_new_position_opportunities(self, available_cash: float, current_positions: List[PositionAnalysis]) -> List[TradeRecommendation]:
        """Análisis de nuevas oportunidades con criterios específicos"""
        if available_cash < 5000:  # Mínimo para nueva posición
            return []
        
        owned_tickers = [p.ticker for p in current_positions]
        opportunities = self.analyzer.analyze_market_for_buy_opportunities(available_cash, owned_tickers)
        
        recommendations = []
        for opp in opportunities[:5]:  # Top 5
            if opp['confidence'] >= 80:  # Solo muy alta confianza
                # Tamaño de posición inicial conservador
                max_investment = min(
                    available_cash * self.risk_config['new_position_max_risk'],
                    15000  # Máximo $15k por posición nueva
                )
                suggested_shares = int(max_investment / opp['current_price'])
                
                if suggested_shares > 0:
                    recommendation = TradeRecommendation(
                        ticker=opp['ticker'],
                        action=ActionType.BUY_INITIAL,
                        suggested_shares=suggested_shares,
                        target_price=opp['current_price'],
                        confidence=opp['confidence'],
                        reasons=opp['reasons'] + ["Posición inicial con criterios conservadores"],
                        risk_assessment="Riesgo moderado - nueva posición",
                        stop_loss_price=opp['current_price'] * (1 - self.risk_config['new_position_stop_loss'])
                    )
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _consolidate_with_professional_logic(self, recommendations: Dict, technical_analysis: Dict) -> List[TradeRecommendation]:
        """Consolida recomendaciones con lógica profesional"""
        all_recs = []
        
        # Prioridad 1: Stop losses críticos (pérdidas importantes)
        stop_losses = recommendations.get('stop_losses', [])
        critical_stops = [r for r in stop_losses if r.confidence >= 90]
        all_recs.extend(critical_stops)
        
        # Prioridad 2: Profit taking en posiciones con alta ganancia
        profit_taking = recommendations.get('profit_taking', [])
        high_profit_takes = [r for r in profit_taking if r.confidence >= 80]
        all_recs.extend(high_profit_takes)
        
        # Prioridad 3: Stop losses menos críticos
        remaining_stops = [r for r in stop_losses if r.confidence < 90]
        all_recs.extend(remaining_stops)
        
        # Prioridad 4: Oportunidades de corto plazo
        short_term = recommendations.get('short_term_trades', [])
        all_recs.extend(short_term)
        
        # Prioridad 5: Rebalanceo inteligente (solo si no hay momentum fuerte)
        rebalancing = recommendations.get('rebalancing', [])
        all_recs.extend(rebalancing)
        
        # Prioridad 6: Nuevas posiciones
        new_positions = recommendations.get('new_positions', [])
        all_recs.extend(new_positions)
        
        # Eliminar duplicados manteniendo la recomendación de mayor prioridad
        seen_tickers = set()
        final_recs = []
        
        for rec in all_recs:
            if rec.ticker not in seen_tickers:
                seen_tickers.add(rec.ticker)
                final_recs.append(rec)
        
        return final_recs
    
    def _apply_dynamic_risk_limits(self, recommendations: List[TradeRecommendation], portfolio_metrics: Dict, available_cash: float) -> List[TradeRecommendation]:
        """Aplica límites de riesgo dinámicos"""
        risk_adjusted = []
        total_portfolio_value = portfolio_metrics['total_value']
        
        for rec in recommendations:
            # Verificar límites específicos por tipo de acción
            if rec.action in [ActionType.BUY_INITIAL, ActionType.BUY_AVERAGING_DOWN, ActionType.BUY_MOMENTUM]:
                investment_amount = rec.suggested_shares * rec.target_price
                
                # Verificar cash disponible
                if investment_amount > available_cash:
                    rec.suggested_shares = max(1, int(available_cash / rec.target_price))
                    rec.reasons.append("Ajustado por cash disponible")
                
                # Verificar límites de posición
                position_size_pct = investment_amount / total_portfolio_value
                max_size = self.risk_config['new_position_max_risk']  # Para nuevas posiciones
                
                if position_size_pct > max_size:
                    max_investment = total_portfolio_value * max_size
                    rec.suggested_shares = max(1, int(max_investment / rec.target_price))
                    rec.reasons.append(f"Ajustado por límite de posición ({max_size:.1%})")
                
                if rec.suggested_shares > 0:
                    risk_adjusted.append(rec)
            else:
                # Para ventas, aplicar tal como están
                risk_adjusted.append(rec)
        
        return risk_adjusted
    
    def _calculate_portfolio_metrics(self, positions: List[PositionAnalysis], available_cash: float) -> Dict:
        """Calcula métricas completas de la cartera"""
        if not positions:
            return {
                'total_value': available_cash,
                'total_invested': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'cash_allocation': 1.0,
                'number_of_positions': 0,
                'sector_allocation': {},
                'risk_metrics': {
                    'concentration_risk': 0,
                    'sharpe_ratio': 0,
                    'max_position_risk': 0,
                    'avg_days_held': 0
                },
                'positions_by_performance': {
                    'winners': 0,
                    'losers': 0,
                    'breakeven': 0
                }
            }
        
        # Cálculos básicos
        total_invested = sum(p.current_shares * p.avg_cost for p in positions)
        total_current_value = sum(p.current_value for p in positions)
        total_pnl = sum(p.unrealized_pnl for p in positions)
        total_value = total_current_value + available_cash
        
        # Asignación por sector
        sector_allocation = {}
        for position in positions:
            sector = position.sector
            if sector not in sector_allocation:
                sector_allocation[sector] = 0
            sector_allocation[sector] += position.current_value / total_current_value if total_current_value > 0 else 0
        
        # Métricas de riesgo
        hhi = sum((p.current_value / total_current_value) ** 2 for p in positions) if total_current_value > 0 else 0
        max_position_risk = max(p.position_size_pct for p in positions) if positions else 0
        
        # Sharpe ratio ajustado para corto plazo
        if positions and total_invested > 0:
            returns = [p.unrealized_pnl_pct for p in positions]
            avg_return = np.mean(returns)
            std_return = np.std(returns) if len(returns) > 1 else 1
            
            # Ajustar Sharpe para posiciones de corto plazo
            avg_days = np.mean([p.days_held for p in positions])
            if avg_days < 7:  # Ajuste para posiciones muy recientes
                time_adjustment = avg_days / 7  # Factor de ajuste temporal
                sharpe_ratio = (avg_return * time_adjustment) / std_return if std_return != 0 else 0
            else:
                sharpe_ratio = avg_return / std_return if std_return != 0 else 0
        else:
            sharpe_ratio = 0
        
        # Performance de posiciones
        winners = len([p for p in positions if p.unrealized_pnl > 0])
        losers = len([p for p in positions if p.unrealized_pnl < 0])
        breakeven = len([p for p in positions if p.unrealized_pnl == 0])
        
        # Días promedio de tenencia
        avg_days_held = np.mean([p.days_held for p in positions]) if positions else 0
        
        return {
            'total_value': total_value,
            'total_invested': total_invested,
            'total_pnl': total_pnl,
            'total_pnl_pct': (total_pnl / total_invested * 100) if total_invested > 0 else 0,
            'cash_allocation': available_cash / total_value if total_value > 0 else 1.0,
            'number_of_positions': len(positions),
            'sector_allocation': sector_allocation,
            'risk_metrics': {
                'concentration_risk': hhi,
                'sharpe_ratio': sharpe_ratio,
                'max_position_risk': max_position_risk,
                'avg_days_held': avg_days_held
            },
            'positions_by_performance': {
                'winners': winners,
                'losers': losers,
                'breakeven': breakeven
            }
        }
    
    def _generate_professional_risk_assessment(self, positions: List[PositionAnalysis], portfolio_metrics: Dict) -> Dict:
        """Genera evaluación de riesgo profesional considerando plazos de tenencia"""
        if not positions:
            return {'overall_risk': 'bajo', 'risk_factors': [], 'recommendations': []}
        
        risk_factors = []
        risk_score = 0
        
        # Factor 1: Concentración
        concentration = portfolio_metrics['risk_metrics']['concentration_risk']
        if concentration > 0.3:
            risk_factors.append(f"Alta concentración de cartera (HHI: {concentration:.2f})")
            risk_score += 2
        
        # Factor 2: Posiciones muy recientes (mayor riesgo)
        very_new_positions = [p for p in positions if p.days_held <= 1]
        if len(very_new_positions) >= 3:
            risk_factors.append(f"{len(very_new_positions)} posiciones con menos de 2 días de tenencia")
            risk_score += 2
        
        # Factor 3: Posiciones grandes con poco tiempo
        large_new_positions = [p for p in positions if p.days_held <= 3 and p.position_size_pct > 0.15]
        if large_new_positions:
            risk_factors.append(f"Posiciones grandes recientes: riesgo de volatilidad")
            risk_score += 1
        
        # Factor 4: Pérdidas acumuladas en posiciones recientes
        recent_losers = [p for p in positions if p.days_held <= 7 and p.unrealized_pnl_pct < -5]
        if recent_losers:
            risk_factors.append(f"{len(recent_losers)} posiciones recientes con pérdidas significativas")
            risk_score += len(recent_losers)
        
        # Factor 5: Cash allocation
        cash_pct = portfolio_metrics['cash_allocation']
        if cash_pct < 0.20:  # Menos del 20% en efectivo
            risk_factors.append("Baja liquidez disponible (<20% cash)")
            risk_score += 1
        
        # Determinar nivel de riesgo
        if risk_score >= 8:
            overall_risk = 'muy_alto'
        elif risk_score >= 5:
            overall_risk = 'alto'
        elif risk_score >= 3:
            overall_risk = 'moderado'
        else:
            overall_risk = 'bajo'
        
        # Recomendaciones específicas
        risk_recommendations = []
        if overall_risk in ['alto', 'muy_alto']:
            risk_recommendations.extend([
                "Considerar reducir tamaño de posiciones recientes",
                "Mantener más efectivo para oportunidades",
                "Implementar stops losses más estrictos para posiciones nuevas"
            ])
        
        return {
            'overall_risk': overall_risk,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendations': risk_recommendations,
            'metrics': {
                'concentration_hhi': concentration,
                'max_position_size': portfolio_metrics['risk_metrics']['max_position_risk'],
                'cash_allocation': cash_pct,
                'very_new_positions': len(very_new_positions),
                'recent_losers': len(recent_losers),
                'avg_days_held': portfolio_metrics['risk_metrics']['avg_days_held']
            }
        }
    
    def _generate_intelligent_execution_plan(self, recommendations: List[TradeRecommendation]) -> Dict:
        """Genera plan de ejecución inteligente considerando urgencia y plazos"""
        if not recommendations:
            return {'immediate_actions': [], 'planned_actions': [], 'monitoring_alerts': []}
        
        immediate_actions = []  # Ejecutar hoy
        planned_actions = []    # Esta semana
        monitoring_alerts = [] # Monitorear
        
        for rec in recommendations:
            action_desc = {
                'ticker': rec.ticker,
                'action': rec.action.value,
                'shares': rec.suggested_shares,
                'price_target': rec.target_price,
                'confidence': rec.confidence,
                'reasoning': rec.reasons[0] if rec.reasons else '',
                'stop_loss': rec.stop_loss_price,
                'take_profit': rec.take_profit_price
            }
            
            # Clasificar por urgencia y tipo
            if rec.action == ActionType.SELL_STOP_LOSS and rec.confidence >= 90:
                # Stop losses críticos - ejecutar inmediatamente
                immediate_actions.append(action_desc)
                
            elif rec.action == ActionType.SELL_PROFIT_TAKING and rec.confidence >= 85:
                # Toma de ganancias alta confianza - esta semana
                planned_actions.append(action_desc)
                
            elif rec.action in [ActionType.SELL_REBALANCE, ActionType.BUY_AVERAGING_DOWN]:
                # Rebalanceo y averaging down - planificado
                planned_actions.append(action_desc)
                
            elif rec.action == ActionType.BUY_INITIAL:
                # Nuevas posiciones - monitorear primero
                monitoring_alerts.append(action_desc)
                
            else:
                # Otras acciones - planificadas
                planned_actions.append(action_desc)
        
        return {
            'immediate_actions': immediate_actions,
            'planned_actions': planned_actions,
            'monitoring_alerts': monitoring_alerts,
            'execution_notes': [
                "Ejecutar acciones inmediatas dentro de las próximas 4 horas",
                "Acciones planificadas: ejecutar en los próximos 2-3 días",
                "Monitorear alertas durante 24-48 horas antes de ejecutar",
                "Considerar condiciones de mercado antes de cada operación"
            ]
        }