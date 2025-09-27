# stocks/forms.py - 連続増益年数指定機能強化版
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class StockScreeningForm(forms.Form):
    """株式スクリーニングフォーム（連続増益年数指定強化版）"""
    
    per_max = forms.DecimalField(
        label='PER上限',
        max_digits=6,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 15.0',
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'max': '1000'
        }),
        help_text='PER（株価収益率）の上限値'
    )
    
    pbr_max = forms.DecimalField(
        label='PBR上限',
        max_digits=6,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 1.0',
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'max': '100'
        }),
        help_text='PBR（株価純資産倍率）の上限値'
    )
    
    dividend_yield_min = forms.DecimalField(
        label='配当利回り下限',
        max_digits=5,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('50'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 2.0',
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'max': '50'
        }),
        help_text='配当利回りの下限値（%）'
    )
    
    # 連続増益年数の選択肢
    PROFIT_GROWTH_CHOICES = [
        ('', '指定なし'),
        ('1', '1年連続増益'),
        ('2', '2年連続増益'),
        ('3', '3年連続増益'),
        ('4', '4年連続増益'),
        ('5', '5年連続増益'),
        ('6', '6年連続増益'),
        ('7', '7年連続増益'),
        ('8', '8年連続増益'),
        ('9', '9年連続増益'),
        ('10', '10年連続増益'),
    ]
    
    consecutive_profit_years = forms.ChoiceField(
        label='連続増益条件',
        choices=PROFIT_GROWTH_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='指定年数の連続増益銘柄に絞り込み'
    )
    
    # 売上高成長率条件（新機能）
    GROWTH_RATE_CHOICES = [
        ('', '指定なし'),
        ('0', '売上高成長（成長率 > 0%）'),
        ('5', '安定成長（成長率 > 5%）'),
        ('10', '高成長（成長率 > 10%）'),
        ('20', '急成長（成長率 > 20%）'),
    ]
    
    revenue_growth_min = forms.ChoiceField(
        label='売上高成長率',
        choices=GROWTH_RATE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='直近年度の売上高成長率条件'
    )
    
    # 純利益成長率条件（新機能）
    profit_growth_min = forms.ChoiceField(
        label='純利益成長率',
        choices=GROWTH_RATE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='直近年度の純利益成長率条件'
    )
    
    market = forms.CharField(
        label='市場区分',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '例: プライム, スタンダード',
            'class': 'form-control',
            'list': 'market-list'
        }),
        help_text='市場区分で絞り込み（部分一致）'
    )
    
    sector = forms.CharField(
        label='業種',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '例: 医薬品, 電気機器',
            'class': 'form-control',
            'list': 'sector-list'
        }),
        help_text='業種で絞り込み（部分一致）'
    )
    
    sort_by = forms.ChoiceField(
        label='並び替え',
        choices=[
            ('code', '銘柄コード（昇順）'),
            ('per', 'PER（低い順）'),
            ('-per', 'PER（高い順）'),
            ('pbr', 'PBR（低い順）'),
            ('-pbr', 'PBR（高い順）'),
            ('dividend_yield', '配当利回り（低い順）'),
            ('-dividend_yield', '配当利回り（高い順）'),
            ('price', '株価（安い順）'),
            ('-price', '株価（高い順）'),
            ('market_cap', '時価総額（小さい順）'),
            ('-market_cap', '時価総額（大きい順）'),
        ],
        required=False,
        initial='code',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    # 表示件数制限
    limit = forms.ChoiceField(
        label='表示件数',
        choices=[
            ('50', '50件'),
            ('100', '100件'),
            ('200', '200件'),
            ('500', '500件'),
            ('', '全件'),
        ],
        required=False,
        initial='100',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='検索結果の表示件数'
    )
    
    def clean_consecutive_profit_years(self):
        """連続増益年数のバリデーション"""
        years = self.cleaned_data.get('consecutive_profit_years')
        if years and years.isdigit():
            years_int = int(years)
            if years_int < 1 or years_int > 10:
                raise forms.ValidationError('連続増益年数は1年から10年の間で指定してください。')
            return years_int
        return None
    
    def clean_revenue_growth_min(self):
        """売上高成長率のバリデーション"""
        growth = self.cleaned_data.get('revenue_growth_min')
        if growth and growth.isdigit():
            return int(growth)
        return None
    
    def clean_profit_growth_min(self):
        """純利益成長率のバリデーション"""
        growth = self.cleaned_data.get('profit_growth_min')
        if growth and growth.isdigit():
            return int(growth)
        return None
    
    def clean_limit(self):
        """表示件数制限のバリデーション"""
        limit = self.cleaned_data.get('limit')
        if limit and limit.isdigit():
            return int(limit)
        return None
    
    def clean(self):
        """フォーム全体のバリデーション"""
        cleaned_data = super().clean()
        per_max = cleaned_data.get('per_max')
        pbr_max = cleaned_data.get('pbr_max')
        dividend_yield_min = cleaned_data.get('dividend_yield_min')
        consecutive_profit_years = cleaned_data.get('consecutive_profit_years')
        revenue_growth_min = cleaned_data.get('revenue_growth_min')
        profit_growth_min = cleaned_data.get('profit_growth_min')
        market = cleaned_data.get('market')
        sector = cleaned_data.get('sector')
        
        # 少なくとも1つの条件が入力されているかチェック
        has_condition = any([
            per_max is not None,
            pbr_max is not None,
            dividend_yield_min is not None,
            consecutive_profit_years is not None,
            revenue_growth_min is not None,
            profit_growth_min is not None,
            market and market.strip(),
            sector and sector.strip()
        ])
        
        if not has_condition:
            raise forms.ValidationError(
                '少なくとも1つの検索条件を入力してください。'
            )
        
        return cleaned_data
    
    def get_search_summary(self):
        """検索条件のサマリーを生成"""
        if not self.is_valid():
            return None
        
        conditions = []
        
        if self.cleaned_data.get('per_max'):
            conditions.append(f"PER ≤ {self.cleaned_data['per_max']}")
        
        if self.cleaned_data.get('pbr_max'):
            conditions.append(f"PBR ≤ {self.cleaned_data['pbr_max']}")
        
        if self.cleaned_data.get('dividend_yield_min'):
            conditions.append(f"配当利回り ≥ {self.cleaned_data['dividend_yield_min']}%")
        
        if self.cleaned_data.get('consecutive_profit_years'):
            conditions.append(f"{self.cleaned_data['consecutive_profit_years']}年連続増益")
        
        if self.cleaned_data.get('revenue_growth_min'):
            conditions.append(f"売上成長率 > {self.cleaned_data['revenue_growth_min']}%")
        
        if self.cleaned_data.get('profit_growth_min'):
            conditions.append(f"利益成長率 > {self.cleaned_data['profit_growth_min']}%")
        
        if self.cleaned_data.get('market'):
            conditions.append(f"市場: {self.cleaned_data['market']}")
        
        if self.cleaned_data.get('sector'):
            conditions.append(f"業種: {self.cleaned_data['sector']}")
        
        return " & ".join(conditions) if conditions else "条件なし"