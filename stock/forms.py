# stock/forms.py - プロフェッショナル版
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class StockScreeningForm(forms.Form):
    """プロフェッショナル・スクリーニングフォーム"""
    
    # ===================
    # バリュエーション指標
    # ===================
    per_min = forms.DecimalField(
        label='PER下限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='株価収益率の下限値'
    )
    
    per_max = forms.DecimalField(
        label='PER上限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 20.0',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='株価収益率の上限値'
    )
    
    pbr_min = forms.DecimalField(
        label='PBR下限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 0.5',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='株価純資産倍率の下限値'
    )
    
    pbr_max = forms.DecimalField(
        label='PBR上限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 2.0',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='株価純資産倍率の上限値'
    )
    
    peg_min = forms.DecimalField(
        label='PEGレシオ下限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 0.5',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='PER/成長率 (1.0以下が理想)'
    )
    
    peg_max = forms.DecimalField(
        label='PEGレシオ上限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 1.5',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='PER/成長率の上限値'
    )
    
    ev_ebitda_min = forms.DecimalField(
        label='EV/EBITDA下限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 3.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='企業価値/EBITDA倍率の下限'
    )
    
    ev_ebitda_max = forms.DecimalField(
        label='EV/EBITDA上限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 15.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='企業価値/EBITDA倍率の上限'
    )
    
    # ===================
    # 収益性・効率性指標
    # ===================
    roe_min = forms.DecimalField(
        label='ROE下限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('200'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 15.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='株主資本利益率の下限（%）'
    )
    
    roe_max = forms.DecimalField(
        label='ROE上限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('200'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 50.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='株主資本利益率の上限（%）'
    )
    
    roa_min = forms.DecimalField(
        label='ROA下限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='総資産利益率の下限（%）'
    )
    
    roa_max = forms.DecimalField(
        label='ROA上限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 30.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='総資産利益率の上限（%）'
    )
    
    roic_min = forms.DecimalField(
        label='ROIC下限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 10.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='投下資本利益率の下限（%）'
    )
    
    roic_max = forms.DecimalField(
        label='ROIC上限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 40.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='投下資本利益率の上限（%）'
    )
    
    operating_margin_min = forms.DecimalField(
        label='営業利益率下限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='営業利益/売上高の下限（%）'
    )
    
    operating_margin_max = forms.DecimalField(
        label='営業利益率上限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 50.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='営業利益/売上高の上限（%）'
    )
    
    net_margin_min = forms.DecimalField(
        label='純利益率下限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 3.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='純利益/売上高の下限（%）'
    )
    
    net_margin_max = forms.DecimalField(
        label='純利益率上限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 30.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='純利益/売上高の上限（%）'
    )
    
    # ===================
    # 成長性指標
    # ===================
    revenue_growth_min = forms.DecimalField(
        label='売上成長率下限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='年間売上高成長率の下限（%）'
    )
    
    revenue_growth_max = forms.DecimalField(
        label='売上成長率上限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 50.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='年間売上高成長率の上限（%）'
    )
    
    profit_growth_min = forms.DecimalField(
        label='純利益成長率下限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 10.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='年間純利益成長率の下限（%）'
    )
    
    profit_growth_max = forms.DecimalField(
        label='純利益成長率上限（%）',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('1000'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 100.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='年間純利益成長率の上限（%）'
    )
    
    consecutive_profit_years = forms.IntegerField(
        label='連続増益年数',
        required=False,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5',
            'class': 'form-control',
            'step': '1'
        }),
        help_text='指定年数の連続増益銘柄（1-20年）'
    )
    
    consecutive_dividend_years = forms.IntegerField(
        label='連続増配年数',
        required=False,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5',
            'class': 'form-control',
            'step': '1'
        }),
        help_text='指定年数の連続増配銘柄（1-30年）'
    )
    
    # ===================
    # 安全性・配当指標
    # ===================
    equity_ratio_min = forms.DecimalField(
        label='自己資本比率下限（%）',
        max_digits=5, decimal_places=1, required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 40.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='自己資本/総資産の下限（%）'
    )
    
    equity_ratio_max = forms.DecimalField(
        label='自己資本比率上限（%）',
        max_digits=5, decimal_places=1, required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 90.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='自己資本/総資産の上限（%）'
    )
    
    current_ratio_min = forms.DecimalField(
        label='流動比率下限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 1.5',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='流動資産/流動負債の下限（1.5以上推奨）'
    )
    
    current_ratio_max = forms.DecimalField(
        label='流動比率上限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0.1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 5.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='流動資産/流動負債の上限'
    )
    
    debt_equity_ratio_max = forms.DecimalField(
        label='D/Eレシオ上限',
        max_digits=8, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 0.5',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='負債/自己資本の上限（低いほど安全）'
    )
    
    dividend_yield_min = forms.DecimalField(
        label='配当利回り下限（%）',
        max_digits=5, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('50'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 2.0',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='年間配当/株価の下限（%）'
    )
    
    dividend_yield_max = forms.DecimalField(
        label='配当利回り上限（%）',
        max_digits=5, decimal_places=2, required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('50'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 10.0',
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='年間配当/株価の上限（%）'
    )
    
    payout_ratio_min = forms.DecimalField(
        label='配当性向下限（%）',
        max_digits=5, decimal_places=1, required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('200'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 20.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='配当/純利益の下限（%）'
    )
    
    payout_ratio_max = forms.DecimalField(
        label='配当性向上限（%）',
        max_digits=5, decimal_places=1, required=False,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('200'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 60.0',
            'class': 'form-control',
            'step': '0.1'
        }),
        help_text='配当/純利益の上限（%）'
    )
    
    # ===================
    # 市場・業種・規模
    # ===================
    market = forms.ChoiceField(
        label='市場区分',
        choices=[
            ('', '全市場'),
            ('プライム', 'プライム市場'),
            ('スタンダード', 'スタンダード市場'),
            ('グロース', 'グロース市場'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sector = forms.ChoiceField(
        label='業種',
        choices=[
            ('', '全業種'),
            ('医薬品', '医薬品'),
            ('電気機器', '電気機器'),
            ('情報・通信業', '情報・通信業'),
            ('輸送用機器', '輸送用機器'),
            ('銀行業', '銀行業'),
            ('食料品', '食料品'),
            ('化学', '化学'),
            ('機械', '機械'),
            ('小売業', '小売業'),
            ('建設業', '建設業'),
            ('不動産業', '不動産業'),
            ('証券・商品先物取引業', '証券業'),
            ('保険業', '保険業'),
            ('石油・石炭製品', '石油・石炭'),
            ('鉄鋼', '鉄鋼'),
            ('非鉄金属', '非鉄金属'),
            ('ガラス・土石製品', 'ガラス・土石'),
            ('繊維製品', '繊維製品'),
            ('パルプ・紙', 'パルプ・紙'),
            ('その他製品', 'その他製品'),
            ('サービス業', 'サービス業'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    size_category = forms.ChoiceField(
        label='企業規模',
        choices=[
            ('', '全規模'),
            ('large', '大型株'),
            ('mid', '中型株'),
            ('small', '小型株'),
            ('micro', '超小型株'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    market_cap_min = forms.DecimalField(
        label='時価総額下限（億円）',
        max_digits=12, decimal_places=0, required=False,
        validators=[MinValueValidator(Decimal('1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 1000',
            'class': 'form-control'
        }),
        help_text='最低時価総額（億円）'
    )
    
    market_cap_max = forms.DecimalField(
        label='時価総額上限（億円）',
        max_digits=12, decimal_places=0, required=False,
        validators=[MinValueValidator(Decimal('1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 100000',
            'class': 'form-control'
        }),
        help_text='最大時価総額（億円）'
    )
    
    price_min = forms.DecimalField(
        label='株価下限（円）',
        max_digits=10, decimal_places=0, required=False,
        validators=[MinValueValidator(Decimal('1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 500',
            'class': 'form-control'
        }),
        help_text='投資しやすい価格帯の下限'
    )
    
    price_max = forms.DecimalField(
        label='株価上限（円）',
        max_digits=10, decimal_places=0, required=False,
        validators=[MinValueValidator(Decimal('1'))],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 10000',
            'class': 'form-control'
        }),
        help_text='投資しやすい価格帯の上限'
    )
    
    # ===================
    # カスタム計算式
    # ===================
    custom_formula = forms.CharField(
        label='カスタム条件式',
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': '例: (roe > 15) AND (per < pbr * 2) AND (dividend_yield > 2)\n\n使用可能な変数: per, pbr, roe, roa, roic, dividend_yield, price, market_cap'
        }),
        help_text='独自の条件式（高度ユーザー向け）'
    )
    
    # ===================
    # 表示・ソート設定
    # ===================
    sort_by = forms.ChoiceField(
        label='並び替え',
        choices=[
            ('total_score', '総合スコア（高い順）'),
            ('-total_score', '総合スコア（低い順）'),
            ('per', 'PER（低い順）'),
            ('-per', 'PER（高い順）'),
            ('pbr', 'PBR（低い順）'),
            ('-pbr', 'PBR（高い順）'),
            ('-roe', 'ROE（高い順）'),
            ('roe', 'ROE（低い順）'),
            ('-dividend_yield', '配当利回り（高い順）'),
            ('dividend_yield', '配当利回り（低い順）'),
            ('price', '株価（安い順）'),
            ('-price', '株価（高い順）'),
            ('-market_cap', '時価総額（大きい順）'),
            ('market_cap', '時価総額（小さい順）'),
            ('code', '銘柄コード（昇順）'),
        ],
        required=False,
        initial='total_score',
        widget=forms.Select(attrs={'class': 'form-select'})
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
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # ===================
    # 詳細フィルター
    # ===================
    exclude_loss_stocks = forms.BooleanField(
        label='赤字銘柄除外',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='直近年度で純利益がマイナスの銘柄を除外'
    )
    
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
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='特定業種を除外'
    )
    
    min_trading_volume = forms.IntegerField(
        label='最低出来高（株）',
        required=False,
        validators=[MinValueValidator(1000)],
        widget=forms.NumberInput(attrs={
            'placeholder': '例: 100000',
            'class': 'form-control'
        }),
        help_text='流動性確保のための最低日平均出来高'
    )
    
    def clean(self):
        """フォーム全体のバリデーション"""
        cleaned_data = super().clean()
        
        # 範囲チェック（下限 ≤ 上限）
        range_fields = [
            ('per_min', 'per_max', 'PER'),
            ('pbr_min', 'pbr_max', 'PBR'),
            ('roe_min', 'roe_max', 'ROE'),
            ('roa_min', 'roa_max', 'ROA'),
            ('dividend_yield_min', 'dividend_yield_max', '配当利回り'),
            ('price_min', 'price_max', '株価'),
            ('market_cap_min', 'market_cap_max', '時価総額'),
        ]
        
        for min_field, max_field, field_name in range_fields:
            min_val = cleaned_data.get(min_field)
            max_val = cleaned_data.get(max_field)
            
            if min_val is not None and max_val is not None and min_val > max_val:
                self.add_error(max_field, f'{field_name}の上限は下限より大きい値を設定してください。')
        
        # 少なくとも1つの条件が入力されているかチェック
        search_fields = [
            'per_min', 'per_max', 'pbr_min', 'pbr_max', 'roe_min', 'roe_max',
            'roa_min', 'roa_max', 'dividend_yield_min', 'dividend_yield_max',
            'price_min', 'price_max', 'market_cap_min', 'market_cap_max',
            'consecutive_profit_years', 'revenue_growth_min', 'profit_growth_min',
            'market', 'sector', 'custom_formula'
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
            return "無効な条件"
        
        conditions = []
        data = self.cleaned_data
        
        # バリュエーション条件
        if data.get('per_min') or data.get('per_max'):
            per_range = f"PER {data.get('per_min', '')}〜{data.get('per_max', '')}"
            conditions.append(per_range.replace('〜', '≤').replace('〜', '≥'))
        
        if data.get('pbr_min') or data.get('pbr_max'):
            pbr_range = f"PBR {data.get('pbr_min', '')}〜{data.get('pbr_max', '')}"
            conditions.append(pbr_range.replace('〜', '≤').replace('〜', '≥'))
        
        # 収益性条件
        if data.get('roe_min'):
            conditions.append(f"ROE≥{data['roe_min']}%")
        if data.get('roa_min'):
            conditions.append(f"ROA≥{data['roa_min']}%")
        
        # 成長性条件
        if data.get('consecutive_profit_years'):
            conditions.append(f"{data['consecutive_profit_years']}年連続増益")
        if data.get('revenue_growth_min'):
            conditions.append(f"売上成長率≥{data['revenue_growth_min']}%")
        
        # 配当条件
        if data.get('dividend_yield_min'):
            conditions.append(f"配当利回り≥{data['dividend_yield_min']}%")
        
        # 安全性条件
        if data.get('equity_ratio_min'):
            conditions.append(f"自己資本比率≥{data['equity_ratio_min']}%")
        
        # 市場・業種条件
        if data.get('market'):
            conditions.append(f"市場:{data['market']}")
        if data.get('sector'):
            conditions.append(f"業種:{data['sector']}")
        
        # カスタム条件
        if data.get('custom_formula'):
            conditions.append("カスタム条件あり")
        
        return " & ".join(conditions) if conditions else "条件なし"

class WatchlistForm(forms.Form):
    """ウォッチリストフォーム"""
    name = forms.CharField(
        label='ウォッチリスト名',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'マイポートフォリオ'
        })
    )
    
    description = forms.CharField(
        label='説明',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'このウォッチリストの説明...'
        })
    )

class AlertForm(forms.Form):
    """アラートフォーム"""
    ALERT_TYPE_CHOICES = [
        ('price_above', '価格上昇'),
        ('price_below', '価格下落'),
        ('volume_spike', '出来高急増'),
        ('per_change', 'PER変化'),
        ('rating_change', 'レーティング変更'),
    ]
    
    stock_code = forms.CharField(
        label='銘柄コード',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '7203'
        })
    )
    
    alert_type = forms.ChoiceField(
        label='アラート種類',
        choices=ALERT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    trigger_value = forms.DecimalField(
        label='発火値',
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '例: 3000'
        }),
        help_text='価格アラートの場合は株価、出来高アラートの場合は倍率'
    )
    
    email_notification = forms.BooleanField(
        label='メール通知',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )