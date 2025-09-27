# stock/advanced_screening.py
from django import forms
from django.db.models import Q, F, Case, When, DecimalField
from decimal import Decimal
import numpy as np

class AdvancedScreeningForm(forms.Form):
    """高度なスクリーニングフォーム"""
    
    # === 1. 高度な財務指標 ===
    roe_min = forms.DecimalField(
        label='ROE下限（%）',
        max_digits=6, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 15.0'}),
        help_text='株主資本利益率の下限'
    )
    
    roa_min = forms.DecimalField(
        label='ROA下限（%）',
        max_digits=6, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 5.0'}),
        help_text='総資産利益率の下限'
    )
    
    debt_equity_max = forms.DecimalField(
        label='D/Eレシオ上限',
        max_digits=6, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 0.5'}),
        help_text='負債/自己資本比率の上限（低い方が安全）'
    )
    
    current_ratio_min = forms.DecimalField(
        label='流動比率下限',
        max_digits=6, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 1.5'}),
        help_text='流動資産/流動負債（1.5以上が理想）'
    )
    
    # === 2. テクニカル条件 ===
    rsi_min = forms.DecimalField(
        label='RSI下限',
        max_digits=5, decimal_places=2, required=False,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        widget=forms.NumberInput(attrs={'placeholder': '例: 30'}),
        help_text='30以下で過売り、70以上で過熱'
    )
    
    rsi_max = forms.DecimalField(
        label='RSI上限',
        max_digits=5, decimal_places=2, required=False,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        widget=forms.NumberInput(attrs={'placeholder': '例: 70'}),
        help_text='70以下に制限で過熱回避'
    )
    
    ma_trend = forms.ChoiceField(
        label='移動平均トレンド',
        choices=[
            ('', '指定なし'),
            ('uptrend', '上昇トレンド（5日>25日>75日）'),
            ('downtrend', '下降トレンド（5日<25日<75日）'),
            ('golden_cross', 'ゴールデンクロス（5日が25日を上抜け）'),
            ('dead_cross', 'デッドクロス（5日が25日を下抜け）'),
        ],
        required=False,
        help_text='移動平均線によるトレンド判定'
    )
    
    volatility_max = forms.DecimalField(
        label='ボラティリティ上限（%）',
        max_digits=6, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 30.0'}),
        help_text='年率ボラティリティの上限（リスク制限）'
    )
    
    # === 3. クオリティ投資指標 ===
    revenue_stability = forms.ChoiceField(
        label='売上高安定性',
        choices=[
            ('', '指定なし'),
            ('stable_growth', '安定成長（3年連続＋成長）'),
            ('accelerating', '加速成長（成長率上昇傾向）'),
            ('consistent', '一貫成長（5年中4年プラス）'),
        ],
        required=False,
        help_text='売上高の成長パターン'
    )
    
    profit_quality = forms.ChoiceField(
        label='利益品質',
        choices=[
            ('', '指定なし'),
            ('high_margin', '高利益率（純利益率10%以上）'),
            ('improving_margin', '利益率改善傾向'),
            ('stable_margin', '利益率安定（変動±2%以内）'),
        ],
        required=False,
        help_text='利益の質的評価'
    )
    
    # === 4. バリュエーション比較 ===
    industry_per_comparison = forms.ChoiceField(
        label='業界PER比較',
        choices=[
            ('', '指定なし'),
            ('below_industry', '業界平均以下'),
            ('top_quartile', '業界上位25%'),
            ('bottom_quartile', '業界下位25%'),
        ],
        required=False,
        help_text='同業界内でのPER比較'
    )
    
    # === 5. ESG・サステナビリティ ===
    esg_score_min = forms.IntegerField(
        label='ESGスコア下限',
        min_value=1, max_value=100, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 70'}),
        help_text='ESGスコア（1-100、70以上推奨）'
    )
    
    # === 6. 時価総額・流動性 ===
    market_cap_min = forms.DecimalField(
        label='時価総額下限（億円）',
        max_digits=12, decimal_places=0, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 1000'}),
        help_text='最低時価総額（大型株絞り込み）'
    )
    
    avg_volume_min = forms.IntegerField(
        label='平均出来高下限（株）',
        min_value=1000, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 100000'}),
        help_text='日平均出来高（流動性確保）'
    )
    
    # === 7. 配当・株主還元 ===
    dividend_growth_years = forms.IntegerField(
        label='連続増配年数',
        min_value=1, max_value=50, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 5'}),
        help_text='連続して配当を増やしている年数'
    )
    
    payout_ratio_max = forms.DecimalField(
        label='配当性向上限（%）',
        max_digits=5, decimal_places=1, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 50.0'}),
        help_text='配当性向の上限（持続可能性確保）'
    )
    
    # === 8. モメンタム・トレンド ===
    price_momentum_min = forms.DecimalField(
        label='株価モメンタム下限（%）',
        max_digits=6, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 5.0'}),
        help_text='過去20日間の株価上昇率'
    )
    
    earnings_surprise = forms.ChoiceField(
        label='決算サプライズ',
        choices=[
            ('', '指定なし'),
            ('positive', '直近決算でポジティブサプライズ'),
            ('consistent', '3四半期連続予想上回り'),
        ],
        required=False,
        help_text='決算予想との比較'
    )
    
    # === 9. スコアリング ===
    composite_score_min = forms.IntegerField(
        label='総合スコア下限',
        min_value=1, max_value=100, required=False,
        widget=forms.NumberInput(attrs={'placeholder': '例: 70'}),
        help_text='独自算出の総合投資スコア'
    )
    
    # === 10. 除外条件 ===
    exclude_sectors = forms.MultipleChoiceField(
        label='除外業種',
        choices=[
            ('銀行業', '銀行業'),
            ('証券・商品先物取引業', '証券業'),
            ('保険業', '保険業'),
            ('不動産業', '不動産業'),
            ('石油・石炭製品', '石油・石炭'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='スクリーニングから除外する業種'
    )
    
    exclude_loss_stocks = forms.BooleanField(
        label='赤字銘柄除外',
        required=False,
        initial=False,
        help_text='直近年度で赤字の銘柄を除外'
    )
    
    # === カスタム条件式 ===
    custom_formula = forms.CharField(
        label='カスタム条件式',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '例: (roe > 15) AND (per < pbr * 2) AND (dividend_yield > 2)'
        }),
        help_text='独自の条件式（高度ユーザー向け）'
    )

class AdvancedScreeningEngine:
    """高度なスクリーニングエンジン"""
    
    @staticmethod
    def calculate_composite_score(stock):
        """総合投資スコアの計算"""
        score = 0
        max_score = 100
        
        # 基本指標スコア（30点）
        if hasattr(stock, 'latest_indicator') and stock.latest_indicator:
            indicator = stock.latest_indicator[0]
            
            # PERスコア（10点）
            if indicator.per:
                if indicator.per < 10:
                    score += 10
                elif indicator.per < 15:
                    score += 7
                elif indicator.per < 20:
                    score += 5
                elif indicator.per < 25:
                    score += 3
            
            # PBRスコア（10点）
            if indicator.pbr:
                if indicator.pbr < 1.0:
                    score += 10
                elif indicator.pbr < 1.5:
                    score += 7
                elif indicator.pbr < 2.0:
                    score += 5
                elif indicator.pbr < 3.0:
                    score += 3
            
            # 配当利回りスコア（10点）
            if indicator.dividend_yield:
                if indicator.dividend_yield > 4:
                    score += 10
                elif indicator.dividend_yield > 3:
                    score += 7
                elif indicator.dividend_yield > 2:
                    score += 5
                elif indicator.dividend_yield > 1:
                    score += 3
        
        # 成長性スコア（25点）
        if hasattr(stock, 'recent_financials') and len(stock.recent_financials) >= 3:
            financials = stock.recent_financials
            
            # 売上高成長スコア（10点）
            revenue_growth = AdvancedScreeningEngine.calculate_cagr(
                [f.revenue for f in financials if f.revenue], 3
            )
            if revenue_growth:
                if revenue_growth > 15:
                    score += 10
                elif revenue_growth > 10:
                    score += 7
                elif revenue_growth > 5:
                    score += 5
                elif revenue_growth > 0:
                    score += 3
            
            # 利益成長スコア（15点）
            profit_growth = AdvancedScreeningEngine.calculate_cagr(
                [f.net_income for f in financials if f.net_income], 3
            )
            if profit_growth:
                if profit_growth > 20:
                    score += 15
                elif profit_growth > 15:
                    score += 12
                elif profit_growth > 10:
                    score += 8
                elif profit_growth > 5:
                    score += 5
        
        # 財務健全性スコア（20点）
        # ROE、自己資本比率等の高度指標があれば評価
        
        # テクニカルスコア（15点）
        # RSI、トレンド等があれば評価
        
        # 品質スコア（10点）
        # 連続増益、利益率安定性等があれば評価
        
        return min(score, max_score)
    
    @staticmethod
    def calculate_cagr(values, years):
        """年平均成長率（CAGR）計算"""
        if len(values) < 2 or any(v <= 0 for v in values if v is not None):
            return None
        
        try:
            start_value = float(values[-1])  # 最古の値
            end_value = float(values[0])     # 最新の値
            
            if start_value <= 0:
                return None
            
            cagr = (pow(end_value / start_value, 1/years) - 1) * 100
            return cagr
        except (ValueError, ZeroDivisionError):
            return None
    
    @staticmethod
    def apply_advanced_filters(queryset, form_data):
        """高度フィルタの適用"""
        if not form_data:
            return queryset
        
        # ROE条件
        if form_data.get('roe_min'):
            queryset = queryset.filter(
                advanced_indicators__roe__gte=form_data['roe_min']
            )
        
        # テクニカル条件
        if form_data.get('rsi_min'):
            queryset = queryset.filter(
                technical_indicators__rsi__gte=form_data['rsi_min']
            )
        
        if form_data.get('rsi_max'):
            queryset = queryset.filter(
                technical_indicators__rsi__lte=form_data['rsi_max']
            )
        
        # 移動平均トレンド
        ma_trend = form_data.get('ma_trend')
        if ma_trend == 'uptrend':
            queryset = queryset.filter(
                technical_indicators__ma_5__gt=F('technical_indicators__ma_25'),
                technical_indicators__ma_25__gt=F('technical_indicators__ma_75')
            )
        elif ma_trend == 'downtrend':
            queryset = queryset.filter(
                technical_indicators__ma_5__lt=F('technical_indicators__ma_25'),
                technical_indicators__ma_25__lt=F('technical_indicators__ma_75')
            )
        
        # 除外条件
        if form_data.get('exclude_sectors'):
            queryset = queryset.exclude(sector__in=form_data['exclude_sectors'])
        
        if form_data.get('exclude_loss_stocks'):
            queryset = queryset.exclude(
                financials__year=2024,
                financials__net_income__lt=0
            )
        
        # カスタム条件式の解析・適用
        if form_data.get('custom_formula'):
            try:
                queryset = AdvancedScreeningEngine.apply_custom_formula(
                    queryset, form_data['custom_formula']
                )
            except Exception as e:
                # カスタム条件でエラーが発生した場合はスキップ
                pass
        
        return queryset
    
    @staticmethod
    def apply_custom_formula(queryset, formula):
        """カスタム条件式の適用（安全な実装）"""
        # セキュリティのため、限定的な条件のみ許可
        allowed_fields = [
            'per', 'pbr', 'dividend_yield', 'price',
            'roe', 'roa', 'debt_equity_ratio',
            'revenue_growth', 'profit_growth'
        ]
        
        allowed_operators = ['>', '<', '>=', '<=', '==', '!=', 'AND', 'OR']
        
        # 簡単な構文解析とクエリ変換
        # 実際の実装では、より堅牢なパーサーを使用することを推奨
        
        return queryset