# advanced_portfolio_manager.py - Sistema completo de gestión profesional de carteras
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
        
        # Configuración de gestión de riesgo
        self.risk_config = {
            'max_position_size': 0.15,          # Máximo 15% por posición
            'max_sector_allocation': 0.25,      # Máximo 25% por sector
            'max_drawdown_per_position': 0.40,  # Stop loss a -40%
            'trailing_stop_activation': 0.20,   # Activar trailing stop con +20%
            'trailing_stop_distance': 0.10,     # Trailing stop a -10% del máximo
            'profit_taking_levels': [0.30, 0.50, 0.75],  # Toma ganancias graduales
            'averaging_down_max_attempts': 3,    # Máximo 3 compras adicionales
            'averaging_down_drop_threshold': 0.15,  # Comprar si baja >15%
            'rebalance_threshold': 0.05,         # Rebalancear si desviación >5%
            'momentum_confirmation_days': 5,     # Días para confirmar momentum
            'volatility_adjustment_factor': 1.2  # Factor de ajuste por volatilidad
        }
        
        # Sectores para diversificación
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
            
            # Salud
            'JNJ': 'salud', 'UNH': 'salud', 'PFE': 'salud', 'ABBV': 'salud',
            
            # Industrial
            'MMM': 'industrial', 'CAT': 'industrial', 'BA': 'industrial',
            
            # Telecom
            'TECO2': 'telecom', 'TEF': 'telecom',
            
            # Default para no clasificados
        }
    
    def analyze_complete_portfolio(self, portfolio_data: Dict, available_cash: float) -> Dict:
        """Análisis completo de cartera con todas las estrategias profesionales"""
        
        # 1. Analizar posiciones actuales
        positions = self._analyze_current_positions(portfolio_data['activos'])
        
        # 2. Calcular métricas de cartera
        portfolio_metrics = self._calculate_portfolio_metrics(positions, available_cash)
        
        # 3. Generar recomendaciones por estrategia
        recommendations = {
            'averaging_down': self._analyze_averaging_down_opportunities(positions),
            'profit_taking': self._analyze_profit_taking_opportunities(positions),
            'stop_losses': self._analyze_stop_loss_triggers(positions),
            'trailing_stops': self._analyze_trailing_stops(positions),
            'momentum_plays': self._analyze_momentum_opportunities(available_cash, positions),
            'rebalancing': self._analyze_rebalancing_needs(positions, portfolio_metrics),
            'new_positions': self._analyze_new_position_opportunities(available_cash, positions),
            'risk_reduction': self._analyze_risk_reduction_needs(positions, portfolio_metrics)
        }
        
        # 4. Consolidar y priorizar recomendaciones
        consolidated_recs = self._consolidate_recommendations(recommendations)
        
        # 5. Verificar límites de riesgo
        risk_adjusted_recs = self._apply_risk_limits(consolidated_recs, portfolio_metrics, available_cash)
        
        return {
            'positions_analysis': positions,
            'portfolio_metrics': portfolio_metrics,
            'recommendations': risk_adjusted_recs,
            'risk_assessment': self._generate_risk_assessment(positions, portfolio_metrics),
            'execution_plan': self._generate_execution_plan(risk_adjusted_recs)
        }
    
    def _analyze_current_positions(self, assets: List[Dict]) -> List[PositionAnalysis]:
        """Analiza las posiciones actuales con métricas avanzadas"""
        positions = []
        
        for asset in assets:
            ticker = asset['ticker']
            
            # Obtener datos históricos para análisis de volatilidad y tendencia
            historical_data = self.analyzer._get_historical_data(ticker, days=90)
            
            # Calcular volatilidad histórica
            if not historical_data.empty:
                returns = historical_data['precio_cierre'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252) * 100  # Volatilidad anualizada
                beta = self._calculate_beta(returns)  # Beta vs mercado (simplificado)
            else:
                volatility = 25.0  # Default
                beta = 1.0
            
            # Determinar sector
            sector = self.sector_mapping.get(ticker, 'otros')
            
            # Calcular score de riesgo
            risk_score = self._calculate_risk_score(
                asset['ganancia_perdida_porcentaje'],
                volatility,
                beta,
                asset.get('dias_tenencia', 1)
            )
            
            position = PositionAnalysis(
                ticker=ticker,
                current_shares=asset['cantidad'],
                avg_cost=asset['precio_inicial_unitario'],
                current_price=asset['precio_actual_unitario'],
                current_value=asset['valor_actual_total'],
                unrealized_pnl=asset['ganancia_perdida_total'],
                unrealized_pnl_pct=asset['ganancia_perdida_porcentaje'],
                days_held=asset.get('dias_tenencia', 1),
                sector=sector,
                position_size_pct=0,  # Se calculará después
                risk_score=risk_score
            )
            
            positions.append(position)
        
        # Calcular tamaños relativos de posición
        total_value = sum(p.current_value for p in positions)
        if total_value > 0:
            for position in positions:
                position.position_size_pct = position.current_value / total_value
        
        return positions
    
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
        # Concentración (Herfindahl-Hirschman Index)
        hhi = sum((p.current_value / total_current_value) ** 2 for p in positions) if total_current_value > 0 else 0
        
        # Posición más grande
        max_position_risk = max(p.position_size_pct for p in positions) if positions else 0
        
        # Sharpe ratio simplificado
        if positions and total_invested > 0:
            returns = [p.unrealized_pnl_pct for p in positions]
            avg_return = np.mean(returns)
            std_return = np.std(returns) if len(returns) > 1 else 1
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
    
    def _analyze_averaging_down_opportunities(self, positions: List[PositionAnalysis]) -> List[TradeRecommendation]:
        """Analiza oportunidades de averaging down con gestión de riesgo"""
        recommendations = []
        
        for position in positions:
            # Solo considerar averaging down si está en pérdidas
            if position.unrealized_pnl_pct >= -5:  # No averaging down si pérdida < 5%
                continue
            
            # Verificar que no hayamos hecho demasiados averaging down
            averaging_attempts = self._get_averaging_attempts_count(position.ticker)
            if averaging_attempts >= self.risk_config['averaging_down_max_attempts']:
                continue
            
            # Verificar que la caída sea significativa
            if position.unrealized_pnl_pct > -self.risk_config['averaging_down_drop_threshold'] * 100:
                continue
            
            # Análisis técnico para confirmar si es buena oportunidad
            technical_analysis = self.analyzer.analyze_asset_for_decision(position.ticker, position.current_price)
            
            # Solo averaging down si el análisis técnico es favorable o neutral
            if 'bajista' in str(technical_analysis.get('reasons', [])).lower():
                continue
            
            # Calcular tamaño de posición para averaging down
            current_position_value = position.current_value
            max_additional_investment = current_position_value * 0.5  # Máximo 50% más
            
            suggested_shares = int(max_additional_investment / position.current_price)
            
            if suggested_shares > 0:
                # Calcular nuevo precio promedio
                new_total_shares = position.current_shares + suggested_shares
                new_total_cost = (position.current_shares * position.avg_cost) + (suggested_shares * position.current_price)
                new_avg_cost = new_total_cost / new_total_shares
                
                # Stop loss para la posición completa
                stop_loss_price = new_avg_cost * (1 - self.risk_config['max_drawdown_per_position'])
                
                confidence = min(80, 40 + abs(position.unrealized_pnl_pct))
                
                reasons = [
                    f"Posición en pérdida del {position.unrealized_pnl_pct:.1f}%",
                    f"Reducirá precio promedio de ${position.avg_cost:.2f} a ${new_avg_cost:.2f}",
                    f"Intento {averaging_attempts + 1} de {self.risk_config['averaging_down_max_attempts']} máximo",
                ]
                
                if technical_analysis.get('recommendation') == 'COMPRA':
                    reasons.append("Análisis técnico favorable para compra")
                    confidence += 15
                
                recommendation = TradeRecommendation(
                    ticker=position.ticker,
                    action=ActionType.BUY_AVERAGING_DOWN,
                    suggested_shares=suggested_shares,
                    target_price=position.current_price,
                    confidence=confidence,
                    reasons=reasons,
                    risk_assessment=f"Riesgo moderado - averaging down {averaging_attempts + 1}/{self.risk_config['averaging_down_max_attempts']}",
                    stop_loss_price=stop_loss_price
                )
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_profit_taking_opportunities(self, positions: List[PositionAnalysis]) -> List[TradeRecommendation]:
        """Analiza oportunidades de toma de ganancias graduales"""
        recommendations = []
        
        for position in positions:
            if position.unrealized_pnl_pct <= 10:  # Solo considerar si ganancia > 10%
                continue
            
            profit_level = position.unrealized_pnl_pct / 100
            
            # Determinar nivel de toma de ganancias
            shares_to_sell = 0
            profit_taking_reason = ""
            
            if profit_level >= 0.75:  # 75%+ ganancia
                shares_to_sell = int(position.current_shares * 0.5)  # Vender 50%
                profit_taking_reason = "Ganancia excepcional del 75%+ - toma de ganancias agresiva"
            elif profit_level >= 0.50:  # 50%+ ganancia
                shares_to_sell = int(position.current_shares * 0.33)  # Vender 33%
                profit_taking_reason = "Ganancia sólida del 50%+ - toma de ganancias moderada"
            elif profit_level >= 0.30:  # 30%+ ganancia
                shares_to_sell = int(position.current_shares * 0.25)  # Vender 25%
                profit_taking_reason = "Ganancia buena del 30%+ - toma de ganancias conservadora"
            
            if shares_to_sell > 0:
                # Verificar momentum - no vender si hay fuerte momentum alcista
                technical_analysis = self.analyzer.analyze_asset_for_decision(position.ticker)
                
                confidence = 70
                reasons = [profit_taking_reason]
                
                # Ajustar por momentum
                if technical_analysis.get('indicators', {}).get('trend') == 'UP':
                    trend_slope = technical_analysis.get('indicators', {}).get('trend_slope', 0)
                    if abs(trend_slope) > 200:  # Momentum muy fuerte
                        shares_to_sell = int(shares_to_sell * 0.5)  # Reducir venta a la mitad
                        reasons.append("Momentum alcista fuerte - reduciendo toma de ganancias")
                        confidence -= 15
                
                if shares_to_sell > 0:
                    recommendation = TradeRecommendation(
                        ticker=position.ticker,
                        action=ActionType.SELL_PROFIT_TAKING,
                        suggested_shares=shares_to_sell,
                        target_price=position.current_price,
                        confidence=confidence,
                        reasons=reasons,
                        risk_assessment="Riesgo bajo - toma de ganancias",
                        take_profit_price=position.current_price
                    )
                    
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_stop_loss_triggers(self, positions: List[PositionAnalysis]) -> List[TradeRecommendation]:
        """Analiza triggers de stop loss"""
        recommendations = []
        
        for position in positions:
            # Stop loss fijo
            if position.unrealized_pnl_pct <= -self.risk_config['max_drawdown_per_position'] * 100:
                recommendation = TradeRecommendation(
                    ticker=position.ticker,
                    action=ActionType.SELL_STOP_LOSS,
                    suggested_shares=position.current_shares,
                    target_price=position.current_price,
                    confidence=95,
                    reasons=[f"Stop loss activado - pérdida del {position.unrealized_pnl_pct:.1f}% excede límite del {self.risk_config['max_drawdown_per_position']*100:.0f}%"],
                    risk_assessment="Riesgo alto - stop loss obligatorio",
                    stop_loss_price=position.current_price
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_trailing_stops(self, positions: List[PositionAnalysis]) -> List[TradeRecommendation]:
        """Analiza trailing stops dinámicos"""
        recommendations = []
        
        for position in positions:
            # Solo activar trailing stop si hay ganancia significativa
            if position.unrealized_pnl_pct < self.risk_config['trailing_stop_activation'] * 100:
                continue
            
            # Obtener precio máximo histórico desde la compra
            max_price = self._get_max_price_since_purchase(position.ticker, position.days_held)
            
            if max_price is None:
                continue
            
            # Calcular trailing stop price
            trailing_stop_price = max_price * (1 - self.risk_config['trailing_stop_distance'])
            
            # Activar si precio actual está cerca del trailing stop
            if position.current_price <= trailing_stop_price * 1.02:  # 2% de margen
                recommendation = TradeRecommendation(
                    ticker=position.ticker,
                    action=ActionType.SELL_TRAILING_STOP,
                    suggested_shares=position.current_shares,
                    target_price=trailing_stop_price,
                    confidence=85,
                    reasons=[
                        f"Trailing stop activado desde máximo de ${max_price:.2f}",
                        f"Precio actual ${position.current_price:.2f} cerca de stop ${trailing_stop_price:.2f}"
                    ],
                    risk_assessment="Riesgo medio - protección de ganancias",
                    stop_loss_price=trailing_stop_price
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_momentum_opportunities(self, available_cash: float, current_positions: List[PositionAnalysis]) -> List[TradeRecommendation]:
        """Analiza oportunidades de momentum trading"""
        recommendations = []
        
        if available_cash < 10000:  # Mínimo para momentum plays
            return recommendations
        
        # Obtener tickers no poseídos actualmente
        owned_tickers = [p.ticker for p in current_positions]
        
        # Buscar oportunidades con fuerte momentum
        opportunities = self.analyzer.analyze_market_for_buy_opportunities(available_cash, owned_tickers)
        
        for opp in opportunities:
            if opp['confidence'] < 80:  # Solo momentum plays de alta confianza
                continue
            
            # Verificar que sea realmente momentum (no solo compra normal)
            score_details = opp.get('score_details', {})
            trend_info = score_details.get('breakdown', {}).get('trend', {})
            
            if trend_info.get('value') == 'UP' and abs(trend_info.get('slope', 0)) > 150:
                # Posición más pequeña para momentum (más riesgoso)
                max_investment = min(available_cash * 0.08, 25000)  # 8% o $25k máximo
                suggested_shares = int(max_investment / opp['current_price'])
                
                if suggested_shares > 0:
                    # Stop loss más cercano para momentum
                    stop_loss_price = opp['current_price'] * 0.92  # -8% stop loss
                    
                    recommendation = TradeRecommendation(
                        ticker=opp['ticker'],
                        action=ActionType.BUY_MOMENTUM,
                        suggested_shares=suggested_shares,
                        target_price=opp['current_price'],
                        confidence=opp['confidence'],
                        reasons=opp['reasons'] + ["Momentum trading - tendencia alcista fuerte"],
                        risk_assessment="Riesgo alto - momentum trading",
                        stop_loss_price=stop_loss_price
                    )
                    
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_rebalancing_needs(self, positions: List[PositionAnalysis], portfolio_metrics: Dict) -> List[TradeRecommendation]:
        """Analiza necesidades de rebalanceo"""
        recommendations = []
        
        # Rebalanceo por tamaño de posición
        for position in positions:
            if position.position_size_pct > self.risk_config['max_position_size'] + self.risk_config['rebalance_threshold']:
                # Posición demasiado grande - reducir
                target_size = self.risk_config['max_position_size']
                shares_to_sell = int(position.current_shares * (1 - target_size / position.position_size_pct))
                
                if shares_to_sell > 0:
                    recommendation = TradeRecommendation(
                        ticker=position.ticker,
                        action=ActionType.SELL_REBALANCE,
                        suggested_shares=shares_to_sell,
                        target_price=position.current_price,
                        confidence=75,
                        reasons=[f"Rebalanceo - posición del {position.position_size_pct:.1%} excede límite del {self.risk_config['max_position_size']:.1%}"],
                        risk_assessment="Riesgo bajo - rebalanceo de cartera"
                    )
                    recommendations.append(recommendation)
        
        # Rebalanceo por sector
        sector_allocation = portfolio_metrics.get('sector_allocation', {})
        for sector, allocation in sector_allocation.items():
            if allocation > self.risk_config['max_sector_allocation'] + self.risk_config['rebalance_threshold']:
                # Sector sobreexpuesto - identificar posiciones a reducir
                sector_positions = [p for p in positions if p.sector == sector]
                largest_position = max(sector_positions, key=lambda x: x.position_size_pct)
                
                # Reducir la posición más grande del sector
                reduction_needed = allocation - self.risk_config['max_sector_allocation']
                shares_to_sell = int(largest_position.current_shares * (reduction_needed / allocation))
                
                if shares_to_sell > 0:
                    recommendation = TradeRecommendation(
                        ticker=largest_position.ticker,
                        action=ActionType.SELL_REBALANCE,
                        suggested_shares=shares_to_sell,
                        target_price=largest_position.current_price,
                        confidence=70,
                        reasons=[f"Rebalanceo sectorial - sector {sector} con {allocation:.1%} excede límite del {self.risk_config['max_sector_allocation']:.1%}"],
                        risk_assessment="Riesgo bajo - diversificación sectorial"
                    )
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_new_position_opportunities(self, available_cash: float, current_positions: List[PositionAnalysis]) -> List[TradeRecommendation]:
        """Analiza oportunidades de nuevas posiciones"""
        if available_cash < 15000:  # Mínimo para nueva posición
            return []
        
        owned_tickers = [p.ticker for p in current_positions]
        opportunities = self.analyzer.analyze_market_for_buy_opportunities(available_cash, owned_tickers)
        
        recommendations = []
        for opp in opportunities[:3]:  # Top 3 oportunidades
            if opp['confidence'] >= 70:  # Solo oportunidades sólidas
                # Tamaño de posición inicial conservador
                max_investment = min(available_cash * self.risk_config['max_position_size'], 30000)
                suggested_shares = int(max_investment / opp['current_price'])
                
                if suggested_shares > 0:
                    recommendation = TradeRecommendation(
                        ticker=opp['ticker'],
                        action=ActionType.BUY_INITIAL,
                        suggested_shares=suggested_shares,
                        target_price=opp['current_price'],
                        confidence=opp['confidence'],
                        reasons=opp['reasons'],
                        risk_assessment="Riesgo moderado - nueva posición",
                        stop_loss_price=opp['current_price'] * 0.85  # -15% stop loss inicial
                    )
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_risk_reduction_needs(self, positions: List[PositionAnalysis], portfolio_metrics: Dict) -> List[TradeRecommendation]:
        """Analiza necesidades de reducción de riesgo"""
        recommendations = []
        
        # Identificar posiciones de alto riesgo
        high_risk_positions = [p for p in positions if p.risk_score > 7.5]
        
        for position in high_risk_positions:
            # Reducir posiciones de muy alto riesgo
            shares_to_sell = int(position.current_shares * 0.3)  # Reducir 30%
            
            if shares_to_sell > 0:
                recommendation = TradeRecommendation(
                    ticker=position.ticker,
                    action=ActionType.REDUCE_POSITION,
                    suggested_shares=shares_to_sell,
                    target_price=position.current_price,
                    confidence=60,
                    reasons=[f"Reducción de riesgo - score de riesgo {position.risk_score:.1f}/10"],
                    risk_assessment="Riesgo alto - reducir exposición"
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    # Funciones auxiliares
    def _calculate_risk_score(self, pnl_pct: float, volatility: float, beta: float, days_held: int) -> float:
        """Calcula score de riesgo de 0-10"""
        risk_score = 5.0  # Base
        
        # Ajuste por P&L
        if pnl_pct < -30:
            risk_score += 2.0
        elif pnl_pct < -15:
            risk_score += 1.0
        elif pnl_pct > 50:
            risk_score += 0.5  # Ganancia grande también es riesgo
        
        # Ajuste por volatilidad
        if volatility > 40:
            risk_score += 1.5
        elif volatility > 25:
            risk_score += 0.5
        
        # Ajuste por beta
        if beta > 1.5:
            risk_score += 1.0
        elif beta < 0.5:
            risk_score -= 0.5
        
        # Ajuste por tiempo de tenencia
        if days_held < 30:
            risk_score += 0.5  # Posiciones nuevas son más riesgosas
        
        return min(10.0, max(0.0, risk_score))
    
    def _calculate_beta(self, returns: pd.Series) -> float:
        """Calcula beta simplificado (vs mercado promedio)"""
        # Simplificado - en realidad necesitarías un índice de referencia
        return min(2.0, max(0.0, returns.std() / 0.02))  # Normalizado
    
    def _get_averaging_attempts_count(self, ticker: str) -> int:
        """Obtiene número de intentos de averaging down (simplificado)"""
        # En implementación real, esto vendría de una base de datos de trades
        return 0  # Por ahora retorna 0
    
    def _get_max_price_since_purchase(self, ticker: str, days_held: int) -> Optional[float]:
        """Obtiene precio máximo desde la compra"""
        try:
            historical_data = self.analyzer._get_historical_data(ticker, days=days_held + 10)
            if not historical_data.empty:
                return historical_data['precio_cierre'].max()
        except:
            pass
        return None
    
    def _consolidate_recommendations(self, recommendations: Dict) -> List[TradeRecommendation]:
        """Consolida y prioriza todas las recomendaciones"""
        all_recs = []
        
        # Prioridad 1: Stop losses (crítico)
        all_recs.extend(recommendations['stop_losses'])
        
        # Prioridad 2: Trailing stops (protección de ganancias)
        all_recs.extend(recommendations['trailing_stops'])
        
        # Prioridad 3: Rebalanceo (gestión de riesgo)
        all_recs.extend(recommendations['rebalancing'])
        
        # Prioridad 4: Toma de ganancias
        all_recs.extend(recommendations['profit_taking'])
        
        # Prioridad 5: Averaging down (oportunidad)
        all_recs.extend(recommendations['averaging_down'])
        
        # Prioridad 6: Reducción de riesgo
        all_recs.extend(recommendations['risk_reduction'])
        
        # Prioridad 7: Momentum plays
        all_recs.extend(recommendations['momentum_plays'])
        
        # Prioridad 8: Nuevas posiciones
        all_recs.extend(recommendations['new_positions'])
        
        # Eliminar duplicados por ticker (mantener la recomendación de mayor prioridad)
        seen_tickers = set()
        final_recs = []
        
        for rec in all_recs:
            if rec.ticker not in seen_tickers:
                seen_tickers.add(rec.ticker)
                final_recs.append(rec)
        
        return final_recs
    
    def _apply_risk_limits(self, recommendations: List[TradeRecommendation], portfolio_metrics: Dict, available_cash: float) -> List[TradeRecommendation]:
        """Aplica límites de riesgo a las recomendaciones"""
        risk_adjusted = []
        total_portfolio_value = portfolio_metrics['total_value'] + available_cash
        
        for rec in recommendations:
            # Verificar límites de posición
            if rec.action in [ActionType.BUY_INITIAL, ActionType.BUY_AVERAGING_DOWN, ActionType.BUY_MOMENTUM]:
                investment_amount = rec.suggested_shares * rec.target_price
                position_size_pct = investment_amount / total_portfolio_value
                
                # No exceder límite de posición individual
                if position_size_pct > self.risk_config['max_position_size']:
                    max_investment = total_portfolio_value * self.risk_config['max_position_size']
                    rec.suggested_shares = int(max_investment / rec.target_price)
                    rec.reasons.append("Ajustado por límite de tamaño de posición")
                
                # Verificar cash disponible
                if investment_amount > available_cash:
                    rec.suggested_shares = int(available_cash / rec.target_price)
                    rec.reasons.append("Ajustado por cash disponible")
                
                if rec.suggested_shares > 0:
                    risk_adjusted.append(rec)
            else:
                # Para ventas, aplicar tal como están
                risk_adjusted.append(rec)
        
        return risk_adjusted
    
    def _generate_risk_assessment(self, positions: List[PositionAnalysis], portfolio_metrics: Dict) -> Dict:
        """Genera evaluación completa de riesgo de la cartera"""
        if not positions:
            return {'overall_risk': 'bajo', 'risk_factors': [], 'recommendations': []}
        
        risk_factors = []
        risk_score = 0
        
        # Factor 1: Concentración
        concentration = portfolio_metrics['risk_metrics']['concentration_risk']
        if concentration > 0.3:  # HHI > 0.3 indica alta concentración
            risk_factors.append(f"Alta concentración de cartera (HHI: {concentration:.2f})")
            risk_score += 2
        
        # Factor 2: Posiciones grandes
        max_position = portfolio_metrics['risk_metrics']['max_position_risk']
        if max_position > 0.2:
            risk_factors.append(f"Posición individual muy grande ({max_position:.1%})")
            risk_score += 2
        
        # Factor 3: Exposición sectorial
        sector_allocation = portfolio_metrics['sector_allocation']
        for sector, allocation in sector_allocation.items():
            if allocation > 0.3:
                risk_factors.append(f"Sobreexposición al sector {sector} ({allocation:.1%})")
                risk_score += 1
        
        # Factor 4: Posiciones en pérdida significativa
        big_losers = [p for p in positions if p.unrealized_pnl_pct < -25]
        if big_losers:
            risk_factors.append(f"{len(big_losers)} posiciones con pérdidas >25%")
            risk_score += len(big_losers)
        
        # Factor 5: Cash allocation muy baja
        cash_pct = portfolio_metrics['cash_allocation']
        if cash_pct < 0.05:  # Menos del 5% en efectivo
            risk_factors.append("Muy poco efectivo disponible (<5%)")
            risk_score += 1
        
        # Determinar nivel de riesgo general
        if risk_score >= 8:
            overall_risk = 'muy_alto'
        elif risk_score >= 5:
            overall_risk = 'alto'
        elif risk_score >= 3:
            overall_risk = 'moderado'
        else:
            overall_risk = 'bajo'
        
        risk_recommendations = []
        if overall_risk in ['alto', 'muy_alto']:
            risk_recommendations.extend([
                "Considerar reducir posiciones grandes",
                "Aumentar diversificación sectorial",
                "Mantener más efectivo disponible",
                "Implementar stops losses más estrictos"
            ])
        
        return {
            'overall_risk': overall_risk,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendations': risk_recommendations,
            'metrics': {
                'concentration_hhi': concentration,
                'max_position_size': max_position,
                'cash_allocation': cash_pct,
                'positions_at_loss': len(big_losers),
                'avg_risk_score': np.mean([p.risk_score for p in positions])
            }
        }
    
    def _generate_execution_plan(self, recommendations: List[TradeRecommendation]) -> Dict:
        """Genera plan de ejecución priorizado"""
        if not recommendations:
            return {'immediate_actions': [], 'planned_actions': [], 'monitoring_alerts': []}
        
        immediate_actions = []
        planned_actions = []
        monitoring_alerts = []
        
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
            
            # Clasificar por urgencia
            if rec.action in [ActionType.SELL_STOP_LOSS, ActionType.SELL_TRAILING_STOP]:
                immediate_actions.append(action_desc)
            elif rec.action in [ActionType.SELL_PROFIT_TAKING, ActionType.SELL_REBALANCE, ActionType.BUY_AVERAGING_DOWN]:
                planned_actions.append(action_desc)
            else:
                monitoring_alerts.append(action_desc)
        
        return {
            'immediate_actions': immediate_actions,
            'planned_actions': planned_actions,
            'monitoring_alerts': monitoring_alerts,
            'execution_notes': [
                "Ejecutar acciones inmediatas dentro de 24 horas",
                "Acciones planificadas pueden ejecutarse durante la semana",
                "Monitorear alertas y ejecutar si las condiciones se mantienen"
            ]
        }