# stock/portfolio_management.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class Portfolio(models.Model):
    """ポートフォリオ"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    name = models.CharField(max_length=100, verbose_name="ポートフォリオ名")
    description = models.TextField(blank=True, verbose_name="説明")
    base_currency = models.CharField(max_length=3, default='JPY', verbose_name="基準通貨")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"

class Position(models.Model):
    """保有ポジション"""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='positions')
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE)
    
    # 保有情報
    quantity = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="保有株数")
    average_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="平均取得価格")
    
    # 目標・制限
    target_weight = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="目標構成比(%)"
    )
    max_weight = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="最大構成比(%)"
    )
    stop_loss_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="ストップロス価格"
    )
    take_profit_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="利益確定価格"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['portfolio', 'stock']
    
    def __str__(self):
        return f"{self.portfolio.name} - {self.stock.code}"

class Transaction(models.Model):
    """取引履歴"""
    TRANSACTION_TYPES = [
        ('BUY', '買い'),
        ('SELL', '売り'),
        ('DIVIDEND', '配当'),
        ('SPLIT', '株式分割'),
        ('MERGER', '合併'),
    ]
    
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='transactions')
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    
    quantity = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="数量")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="価格")
    commission = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="手数料")
    tax = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="税金")
    
    transaction_date = models.DateTimeField(verbose_name="取引日時")
    settlement_date = models.DateField(null=True, blank=True, verbose_name="受渡日")
    
    note = models.TextField(blank=True, verbose_name="メモ")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def total_amount(self):
        """総額計算"""
        base_amount = self.quantity * self.price
        if self.transaction_type == 'BUY':
            return base_amount + self.commission + self.tax
        else:
            return base_amount - self.commission - self.tax

class PortfolioAnalyzer:
    """ポートフォリオ分析クラス"""
    
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.positions = portfolio.positions.select_related('stock').all()
    
    def get_portfolio_summary(self):
        """ポートフォリオサマリー取得"""
        total_value = Decimal('0')
        total_cost = Decimal('0')
        positions_data = []
        
        for position in self.positions:
            # 最新価格取得
            latest_indicator = position.stock.indicators.order_by('-date').first()
            current_price = latest_indicator.price if latest_indicator else position.average_price
            
            # 各種計算
            market_value = position.quantity * current_price
            cost_basis = position.quantity * position.average_price
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis) * 100 if cost_basis > 0 else 0
            
            total_value += market_value
            total_cost += cost_basis
            
            positions_data.append({
                'stock': position.stock,
                'quantity': position.quantity,
                'average_price': position.average_price,
                'current_price': current_price,
                'market_value': market_value,
                'cost_basis': cost_basis,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct,
                'weight': 0,  # 後で計算
                'target_weight': position.target_weight,
            })
        
        # 構成比計算
        for pos_data in positions_data:
            if total_value > 0:
                pos_data['weight'] = (pos_data['market_value'] / total_value) * 100
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'positions': positions_data,
            'num_positions': len(positions_data),
        }
    
    def calculate_portfolio_risk(self, days=252):
        """ポートフォリオリスク計算"""
        if len(self.positions) < 2:
            return None
        
        # 各銘柄の価格データ取得
        stock_codes = [pos.stock.code for pos in self.positions]
        weights = []
        returns_data = {}
        
        summary = self.get_portfolio_summary()
        
        for pos_data in summary['positions']:
            weights.append(float(pos_data['weight']) / 100)
            
            # 過去の価格データから日次リターン計算
            stock_code = pos_data['stock'].code
            price_history = self.get_price_history(stock_code, days)
            
            if len(price_history) > 1:
                returns = price_history.pct_change().dropna()
                returns_data[stock_code] = returns
        
        if len(returns_data) < 2:
            return None
        
        # リターンデータフレーム作成
        returns_df = pd.DataFrame(returns_data)
        
        # ポートフォリオのリスク計算
        portfolio_variance = np.dot(weights, np.dot(returns_df.cov() * 252, weights))
        portfolio_volatility = np.sqrt(portfolio_variance) * 100
        
        # 各銘柄の寄与度計算
        individual_risks = []
        for i, pos_data in enumerate(summary['positions']):
            stock_vol = returns_df[pos_data['stock'].code].std() * np.sqrt(252) * 100
            individual_risks.append({
                'stock': pos_data['stock'],
                'weight': weights[i] * 100,
                'volatility': stock_vol,
                'risk_contribution': weights[i] * stock_vol,
            })
        
        return {
            'portfolio_volatility': portfolio_volatility,
            'individual_risks': individual_risks,
            'correlation_matrix': returns_df.corr().to_dict(),
        }
    
    def get_rebalancing_recommendations(self):
        """リバランシング推奨"""
        summary = self.get_portfolio_summary()
        recommendations = []
        
        for pos_data in summary['positions']:
            if pos_data['target_weight'] is None:
                continue
            
            current_weight = pos_data['weight']
            target_weight = float(pos_data['target_weight'])
            deviation = current_weight - target_weight
            
            # 5%以上の乖離で推奨
            if abs(deviation) > 5:
                action = "売却" if deviation > 0 else "買い増し"
                target_value = summary['total_value'] * (target_weight / 100)
                adjustment_value = target_value - pos_data['market_value']
                
                recommendations.append({
                    'stock': pos_data['stock'],
                    'action': action,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'deviation': deviation,
                    'adjustment_value': adjustment_value,
                    'priority': 'high' if abs(deviation) > 10 else 'medium',
                })
        
        # 乖離度の大きい順にソート
        recommendations.sort(key=lambda x: abs(x['deviation']), reverse=True)
        
        return recommendations
    
    def calculate_sector_allocation(self):
        """セクター別配分分析"""
        summary = self.get_portfolio_summary()
        sector_allocation = {}
        
        for pos_data in summary['positions']:
            sector = pos_data['stock'].sector or '未分類'
            weight = pos_data['weight']
            
            if sector in sector_allocation:
                sector_allocation[sector] += weight
            else:
                sector_allocation[sector] = weight
        
        return sector_allocation
    
    def get_dividend_forecast(self):
        """配当予測"""
        annual_dividend = Decimal('0')
        dividend_details = []
        
        for position in self.positions:
            latest_indicator = position.stock.indicators.order_by('-date').first()
            
            if latest_indicator and latest_indicator.dividend_yield and latest_indicator.price:
                annual_dividend_per_share = (latest_indicator.price * latest_indicator.dividend_yield) / 100
                position_dividend = annual_dividend_per_share * position.quantity
                annual_dividend += position_dividend
                
                dividend_details.append({
                    'stock': position.stock,
                    'dividend_per_share': annual_dividend_per_share,
                    'total_dividend': position_dividend,
                    'yield': latest_indicator.dividend_yield,
                })
        
        summary = self.get_portfolio_summary()
        dividend_yield = (annual_dividend / summary['total_value']) * 100 if summary['total_value'] > 0 else 0
        
        return {
            'annual_dividend': annual_dividend,
            'portfolio_yield': dividend_yield,
            'dividend_details': dividend_details,
        }
    
    def get_price_history(self, stock_code, days):
        """価格履歴取得（サンプル実装）"""
        # 実際の実装では、Indicatorモデルから価格履歴を取得
        from .models import Indicator
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        indicators = Indicator.objects.filter(
            stock__code=stock_code,
            date__gte=start_date,
            date__lte=end_date,
            price__isnull=False
        ).order_by('date')
        
        prices = [float(ind.price) for ind in indicators]
        return pd.Series(prices)

class AlertManager:
    """アラート管理"""
    
    @staticmethod
    def check_price_alerts(portfolio):
        """価格アラートチェック"""
        alerts = []
        
        for position in portfolio.positions.all():
            latest_indicator = position.stock.indicators.order_by('-date').first()
            
            if not latest_indicator or not latest_indicator.price:
                continue
            
            current_price = latest_indicator.price
            
            # ストップロスアラート
            if position.stop_loss_price and current_price <= position.stop_loss_price:
                alerts.append({
                    'type': 'stop_loss',
                    'stock': position.stock,
                    'message': f'{position.stock.name}が損切りライン({position.stop_loss_price}円)に達しました',
                    'current_price': current_price,
                    'trigger_price': position.stop_loss_price,
                    'severity': 'high',
                })
            
            # 利益確定アラート
            if position.take_profit_price and current_price >= position.take_profit_price:
                alerts.append({
                    'type': 'take_profit',
                    'stock': position.stock,
                    'message': f'{position.stock.name}が利益確定ライン({position.take_profit_price}円)に達しました',
                    'current_price': current_price,
                    'trigger_price': position.take_profit_price,
                    'severity': 'medium',
                })
        
        return alerts
    
    @staticmethod
    def check_rebalancing_alerts(portfolio):
        """リバランシングアラート"""
        analyzer = PortfolioAnalyzer(portfolio)
        recommendations = analyzer.get_rebalancing_recommendations()
        
        alerts = []
        for rec in recommendations:
            if rec['priority'] == 'high':
                alerts.append({
                    'type': 'rebalancing',
                    'stock': rec['stock'],
                    'message': f'{rec["stock"].name}の構成比が目標から{abs(rec["deviation"]):.1f}%乖離しています',
                    'action': rec['action'],
                    'severity': 'medium',
                })
        
        return alerts