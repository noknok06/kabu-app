# stock/forms.py - 連続増益条件数値指定版
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class StockScreeningForm(forms.Form):
    """株式スクリーニングフォーム（拡張版 - 数値指定対応）"""
    
    # ===================
    # 基本指標条件
    # ===================
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
    
    per_min = forms.DecimalField(
        label='PER下限',
        max_digits=6,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'max': '1000'
        }),
        help_text='PER（株価収益率）の下限値'
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
    
    pbr_min = forms.DecimalField(
        label='PBR下限',
        max_digits=6,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 0.5',
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'max': '100'
        }),
        help_text='PBR（株価純資産倍率）の下限値'
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
    
    dividend_yield_max = forms.DecimalField(
        label='配当利回り上限',
        max_digits=5,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('50'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 10.0',
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'max': '50'
        }),
        help_text='配当利回りの上限値（%）'
    )
    
    # ===================
    # 株価・時価総額条件
    # ===================
    price_min = forms.DecimalField(
        label='株価下限（円）',
        max_digits=10,
        decimal_places=0,
        required=False,
        validators=[MinValueValidator(Decimal('1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 1000',
            'class': 'form-control',
            'step': '1',
            'min': '1'
        }),
        help_text='株価の下限値（円）'
    )
    
    price_max = forms.DecimalField(
        label='株価上限（円）',
        max_digits=10,
        decimal_places=0,
        required=False,
        validators=[MinValueValidator(Decimal('1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 10000',
            'class': 'form-control',
            'step': '1',
            'min': '1'
        }),
        help_text='株価の上限値（円）'
    )
    
    # ===================
    # 成長率条件（数値指定）
    # ===================
    consecutive_profit_years = forms.IntegerField(
        label='連続増益年数',
        required=False,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5',
            'class': 'form-control',
            'step': '1',
            'min': '1',
            'max': '20'
        }),
        help_text='指定年数の連続増益銘柄に絞り込み（1-20年）'
    )
    
    revenue_growth_min = forms.DecimalField(
        label='売上高成長率下限（%）',
        max_digits=5,
        decimal_places=1,
        required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.1',
            'min': '-100',
            'max': '1000'
        }),
        help_text='直近年度の売上高成長率下限（%）'
    )
    
    revenue_growth_max = forms.DecimalField(
        label='売上高成長率上限（%）',
        max_digits=5,
        decimal_places=1,
        required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 50.0',
            'class': 'form-control',
            'step': '0.1',
            'min': '-100',
            'max': '1000'
        }),
        help_text='直近年度の売上高成長率上限（%）'
    )
    
    profit_growth_min = forms.DecimalField(
        label='純利益成長率下限（%）',
        max_digits=5,
        decimal_places=1,
        required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 10.0',
            'class': 'form-control',
            'step': '0.1',
            'min': '-100',
            'max': '1000'
        }),
        help_text='直近年度の純利益成長率下限（%）'
    )
    
    profit_growth_max = forms.DecimalField(
        label='純利益成長率上限（%）',
        max_digits=5,
        decimal_places=1,
        required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 100.0',
            'class': 'form-control',
            'step': '0.1',
            'min': '-100',
            'max': '1000'
        }),
        help_text='直近年度の純利益成長率上限（%）'
    )
    
    # ===================
    # 財務健全性条件
    # ===================
    profit_margin_min = forms.DecimalField(
        label='純利益率下限（%）',
        max_digits=5,
        decimal_places=1,
        required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.1',
            'min': '-100',
            'max': '100'
        }),
        help_text='純利益/売上高の下限値（%）'
    )
    
    # ===================
    # 市場・業種条件
    # ===================
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
    
    # ===================
    # 表示設定
    # ===================
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
            ('profit_margin', '純利益率（低い順）'),
            ('-profit_margin', '純利益率（高い順）'),
        ],
        required=False,
        initial='code',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    limit = forms.ChoiceField(
        label='表示件数',
        choices=[
            ('20', '20件'),
            ('50', '50件'),
            ('100', '100件'),
            ('200', '200件'),
            ('500', '500件'),
            ('', '全件'),
        ],
        required=False,
        initial='50',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='検索結果の表示件数'
    )
    
    # ===================
    # クイック設定プリセット
    # ===================
    preset = forms.ChoiceField(
        label='クイック設定',
        choices=[
            ('', '手動設定'),
            ('value', '割安株（PER<15, PBR<1.5）'),
            ('dividend', '高配当株（配当利回り>3%）'),
            ('growth', '成長株（5年連続増益）'),
            ('quality', '優良株（連続増益+高利益率）'),
            ('defensive', '安定株（低PER+高配当）'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'applyPreset(this.value)'
        }),
        help_text='事前定義された検索条件'
    )
    
    def clean_consecutive_profit_years(self):
        """連続増益年数のバリデーション"""
        years = self.cleaned_data.get('consecutive_profit_years')
        if years is not None:
            if years < 1 or years > 20:
                raise forms.ValidationError('連続増益年数は1年から20年の間で指定してください。')
        return years
    
    def clean_per_max(self):
        """PER上限のバリデーション"""
        per_max = self.cleaned_data.get('per_max')
        per_min = self.cleaned_data.get('per_min')
        
        if per_max is not None and per_min is not None:
            if per_max <= per_min:
                raise forms.ValidationError('PER上限は下限より大きい値を設定してください。')
        return per_max
    
    def clean_pbr_max(self):
        """PBR上限のバリデーション"""
        pbr_max = self.cleaned_data.get('pbr_max')
        pbr_min = self.cleaned_data.get('pbr_min')
        
        if pbr_max is not None and pbr_min is not None:
            if pbr_max <= pbr_min:
                raise forms.ValidationError('PBR上限は下限より大きい値を設定してください。')
        return pbr_max
    
    def clean_dividend_yield_max(self):
        """配当利回り上限のバリデーション"""
        dividend_max = self.cleaned_data.get('dividend_yield_max')
        dividend_min = self.cleaned_data.get('dividend_yield_min')
        
        if dividend_max is not None and dividend_min is not None:
            if dividend_max <= dividend_min:
                raise forms.ValidationError('配当利回り上限は下限より大きい値を設定してください。')
        return dividend_max
    
    def clean_price_max(self):
        """株価上限のバリデーション"""
        price_max = self.cleaned_data.get('price_max')
        price_min = self.cleaned_data.get('price_min')
        
        if price_max is not None and price_min is not None:
            if price_max <= price_min:
                raise forms.ValidationError('株価上限は下限より大きい値を設定してください。')
        return price_max
    
    def clean_revenue_growth_max(self):
        """売上成長率上限のバリデーション"""
        growth_max = self.cleaned_data.get('revenue_growth_max')
        growth_min = self.cleaned_data.get('revenue_growth_min')
        
        if growth_max is not None and growth_min is not None:
            if growth_max <= growth_min:
                raise forms.ValidationError('売上成長率上限は下限より大きい値を設定してください。')
        return growth_max
    
    def clean_profit_growth_max(self):
        """純利益成長率上限のバリデーション"""
        growth_max = self.cleaned_data.get('profit_growth_max')
        growth_min = self.cleaned_data.get('profit_growth_min')
        
        if growth_max is not None and growth_min is not None:
            if growth_max <= growth_min:
                raise forms.ValidationError('純利益成長率上限は下限より大きい値を設定してください。')
        return growth_max
    
    def clean(self):
        """フォーム全体のバリデーション"""
        cleaned_data = super().clean()
        
        # 少なくとも1つの条件が入力されているかチェック
        search_fields = [
            'per_max', 'per_min', 'pbr_max', 'pbr_min',
            'dividend_yield_min', 'dividend_yield_max',
            'price_min', 'price_max',
            'consecutive_profit_years', 'revenue_growth_min', 'revenue_growth_max',
            'profit_growth_min', 'profit_growth_max', 'profit_margin_min',
            'market', 'sector'
        ]
        
        has_condition = any(
            cleaned_data.get(field) is not None and cleaned_data.get(field) != ''
            for field in search_fields
        )
        
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
        
        # 基本指標
        if self.cleaned_data.get('per_min') and self.cleaned_data.get('per_max'):
            conditions.append(f"PER {self.cleaned_data['per_min']}-{self.cleaned_data['per_max']}")
        elif self.cleaned_data.get('per_max'):
            conditions.append(f"PER ≤ {self.cleaned_data['per_max']}")
        elif self.cleaned_data.get('per_min'):
            conditions.append(f"PER ≥ {self.cleaned_data['per_min']}")
        
        if self.cleaned_data.get('pbr_min') and self.cleaned_data.get('pbr_max'):
            conditions.append(f"PBR {self.cleaned_data['pbr_min']}-{self.cleaned_data['pbr_max']}")
        elif self.cleaned_data.get('pbr_max'):
            conditions.append(f"PBR ≤ {self.cleaned_data['pbr_max']}")
        elif self.cleaned_data.get('pbr_min'):
            conditions.append(f"PBR ≥ {self.cleaned_data['pbr_min']}")
        
        # 配当利回り
        if self.cleaned_data.get('dividend_yield_min') and self.cleaned_data.get('dividend_yield_max'):
            conditions.append(f"配当利回り {self.cleaned_data['dividend_yield_min']}-{self.cleaned_data['dividend_yield_max']}%")
        elif self.cleaned_data.get('dividend_yield_min'):
            conditions.append(f"配当利回り ≥ {self.cleaned_data['dividend_yield_min']}%")
        elif self.cleaned_data.get('dividend_yield_max'):
            conditions.append(f"配当利回り ≤ {self.cleaned_data['dividend_yield_max']}%")
        
        # 成長性
        if self.cleaned_data.get('consecutive_profit_years'):
            conditions.append(f"{self.cleaned_data['consecutive_profit_years']}年連続増益")
        
        if self.cleaned_data.get('revenue_growth_min'):
            conditions.append(f"売上成長率 ≥ {self.cleaned_data['revenue_growth_min']}%")
        
        if self.cleaned_data.get('profit_growth_min'):
            conditions.append(f"利益成長率 ≥ {self.cleaned_data['profit_growth_min']}%")
        
        # 市場・業種
        if self.cleaned_data.get('market'):
            conditions.append(f"市場: {self.cleaned_data['market']}")
        
        if self.cleaned_data.get('sector'):
            conditions.append(f"業種: {self.cleaned_data['sector']}")
        
        return " & ".join(conditions) if conditions else "条件なし"
    
    def get_preset_data(self, preset_type):
        """プリセット設定データを返す"""
        presets = {
            'value': {  # 割安株
                'per_max': 15,
                'pbr_max': 1.5,
                'sort_by': 'per'
            },
            'dividend': {  # 高配当株
                'dividend_yield_min': 3.0,
                'sort_by': '-dividend_yield'
            },
            'growth': {  # 成長株
                'consecutive_profit_years': 5,
                'revenue_growth_min': 5.0,
                'sort_by': '-profit_growth'
            },
            'quality': {  # 優良株
                'consecutive_profit_years': 3,
                'profit_margin_min': 5.0,
                'per_max': 20,
                'sort_by': '-profit_margin'
            },
            'defensive': {  # 安定株
                'per_max': 12,
                'dividend_yield_min': 2.5,
                'sort_by': 'per'
            }
        }
        return presets.get(preset_type, {})