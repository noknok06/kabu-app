# stock/models.py - プロフェッショナル版
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from decimal import Decimal
import numpy as np

class Stock(models.Model):
    """銘柄マスタ（拡張版）"""
    code = models.CharField(max_length=10, unique=True, verbose_name="銘柄コード", db_index=True)
    name = models.CharField(max_length=200, verbose_name="企業名", db_index=True)
    market = models.CharField(max_length=50, blank=True, verbose_name="市場区分", db_index=True)
    sector = models.CharField(max_length=100, blank=True, verbose_name="業種", db_index=True)
    
    # 企業基本情報
    listing_date = models.DateField(null=True, blank=True, verbose_name="上場日")
    employees = models.IntegerField(null=True, blank=True, verbose_name="従業員数")
    founded_year = models.IntegerField(null=True, blank=True, verbose_name="設立年")
    
    # 分類
    size_category = models.CharField(
        max_length=20, 
        choices=[
            ('large', '大型株'),
            ('mid', '中型株'),
            ('small', '小型株'),
            ('micro', '超小型株')
        ],
        blank=True,
        verbose_name="規模分類"
    )
    
    # メタデータ
    is_active = models.BooleanField(default=True, verbose_name="アクティブ")
    data_quality_score = models.IntegerField(default=0, verbose_name="データ品質スコア")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "銘柄"
        verbose_name_plural = "銘柄"
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['sector']),
            models.Index(fields=['market']),
            models.Index(fields=['size_category']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Financial(models.Model):
    """財務データ（拡張版）"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='financials')
    year = models.IntegerField(verbose_name="決算年度", db_index=True)
    quarter = models.IntegerField(
        null=True, blank=True,
        choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')],
        verbose_name="四半期"
    )
    
    # 損益計算書項目
    revenue = models.DecimalField(
        max_digits=20, decimal_places=0, 
        null=True, blank=True, verbose_name="売上高"
    )
    operating_income = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="営業利益"
    )
    ordinary_income = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="経常利益"
    )
    net_income = models.DecimalField(
        max_digits=20, decimal_places=0, 
        null=True, blank=True, verbose_name="純利益"
    )
    
    # 貸借対照表項目
    total_assets = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="総資産"
    )
    shareholders_equity = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="株主資本"
    )
    total_debt = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="有利子負債"
    )
    
    # キャッシュフロー項目
    operating_cf = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="営業CF"
    )
    investing_cf = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="投資CF"
    )
    financing_cf = models.DecimalField(
        max_digits=20, decimal_places=0,
        null=True, blank=True, verbose_name="財務CF"
    )
    
    # 1株あたり指標
    eps = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, verbose_name="EPS"
    )
    bps = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, verbose_name="BPS"
    )
    dividend_per_share = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, verbose_name="1株配当"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "財務データ"
        verbose_name_plural = "財務データ"
        unique_together = ['stock', 'year', 'quarter']
        ordering = ['stock', '-year', '-quarter']
        indexes = [
            models.Index(fields=['stock', 'year']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        quarter_str = f"Q{self.quarter}" if self.quarter else "通期"
        return f"{self.stock.code} - {self.year}年{quarter_str}"

class Indicator(models.Model):
    """基本指標データ（拡張版）"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='indicators')
    date = models.DateField(verbose_name="取得日", db_index=True)
    
    # バリュエーション指標
    per = models.DecimalField(
        max_digits=8, decimal_places=2, 
        null=True, blank=True, verbose_name="PER"
    )
    pbr = models.DecimalField(
        max_digits=8, decimal_places=2, 
        null=True, blank=True, verbose_name="PBR"
    )
    psr = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name="PSR"
    )
    pcfr = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True, verbose_name="PCFR"
    )
    
    # 配当指標
    dividend_yield = models.DecimalField(
        max_digits=5, decimal_places=2, 
        null=True, blank=True, 
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name="配当利回り(%)"
    )
    payout_ratio = models.DecimalField(
        max_digits=5, decimal_places=1,
        null=True, blank=True, verbose_name="配当性向(%)"
    )
    
    # 価格・時価総額
    price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, verbose_name="株価"
    )
    market_cap = models.DecimalField(
        max_digits=15, decimal_places=0,
        null=True, blank=True, verbose_name="時価総額"
    )
    
    # 出来高・流動性
    volume = models.BigIntegerField(
        null=True, blank=True, verbose_name="出来高"
    )
    volume_avg_20d = models.BigIntegerField(
        null=True, blank=True, verbose_name="20日平均出来高"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "指標データ"
        verbose_name_plural = "指標データ"
        unique_together = ['stock', 'date']
        ordering = ['stock', '-date']
        indexes = [
            models.Index(fields=['stock', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.stock.code} - {self.date}"

class AdvancedIndicator(models.Model):
    """高度指標データ（プロ向け）"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='advanced_indicators')
    date = models.DateField(verbose_name="取得日", db_index=True)
    
    # 収益性指標
    roe = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="ROE(%)")
    roa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="ROA(%)")
    roic = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="ROIC(%)")
    roe_3y_avg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="ROE3年平均(%)")
    
    # 利益率指標
    operating_margin = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="営業利益率(%)")
    net_margin = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="純利益率(%)")
    gross_margin = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="売上総利益率(%)")
    
    # バリュエーション（高度）
    peg_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="PEGレシオ")
    ev_ebitda = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="EV/EBITDA")
    ev_sales = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="EV/Sales")
    
    # 安全性指標
    debt_equity_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="D/Eレシオ")
    current_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="流動比率")
    quick_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="当座比率")
    equity_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="自己資本比率(%)")
    interest_coverage = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="インタレストカバレッジ")
    
    # 効率性指標
    asset_turnover = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="総資産回転率")
    inventory_turnover = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="棚卸回転率")
    receivables_turnover = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="売掛金回転率")
    
    # 成長率（1年）
    revenue_growth_1y = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="売上成長率1年(%)")
    operating_growth_1y = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="営業利益成長率1年(%)")
    net_growth_1y = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="純利益成長率1年(%)")
    
    # 成長率（3年CAGR）
    revenue_cagr_3y = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="売上CAGR3年(%)")
    operating_cagr_3y = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="営業利益CAGR3年(%)")
    net_cagr_3y = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="純利益CAGR3年(%)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['stock', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['stock', 'date']),
            models.Index(fields=['roe']),
            models.Index(fields=['roa']),
            models.Index(fields=['peg_ratio']),
        ]
    
    def __str__(self):
        return f"{self.stock.code} - {self.date} (高度指標)"

class TechnicalIndicator(models.Model):
    """テクニカル指標データ"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='technical_indicators')
    date = models.DateField(verbose_name="分析日", db_index=True)
    
    # 移動平均
    ma_5 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="5日移動平均")
    ma_25 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="25日移動平均")
    ma_75 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="75日移動平均")
    ma_200 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="200日移動平均")
    
    # オシレーター
    rsi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="RSI")
    macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MACD")
    macd_signal = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MACDシグナル")
    stochastic_k = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="ストキャスティクス%K")
    
    # ボリンジャーバンド
    bb_upper = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ボリンジャー上限")
    bb_middle = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ボリンジャー中央")
    bb_lower = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ボリンジャー下限")
    
    # ボラティリティ・モメンタム
    volatility = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name="ボラティリティ")
    momentum_1d = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="1日モメンタム")
    momentum_5d = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="5日モメンタム")
    momentum_20d = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="20日モメンタム")
    
    # トレンド判定
    trend = models.CharField(max_length=50, blank=True, verbose_name="トレンド")
    support_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="サポートレベル")
    resistance_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="レジスタンスレベル")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['stock', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['stock', 'date']),
            models.Index(fields=['rsi']),
            models.Index(fields=['trend']),
        ]

class AnalystEstimate(models.Model):
    """アナリスト予想データ"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='analyst_estimates')
    target_year = models.IntegerField(verbose_name="予想対象年度")
    
    # 業績予想
    revenue_estimate = models.DecimalField(max_digits=20, decimal_places=0, null=True, blank=True, verbose_name="売上予想")
    operating_estimate = models.DecimalField(max_digits=20, decimal_places=0, null=True, blank=True, verbose_name="営業利益予想")
    net_estimate = models.DecimalField(max_digits=20, decimal_places=0, null=True, blank=True, verbose_name="純利益予想")
    eps_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="EPS予想")
    
    # 株価予想
    target_price_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="目標株価上限")
    target_price_avg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="目標株価平均")
    target_price_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="目標株価下限")
    
    # レーティング
    rating_buy = models.IntegerField(default=0, verbose_name="買い推奨数")
    rating_hold = models.IntegerField(default=0, verbose_name="ホールド数")
    rating_sell = models.IntegerField(default=0, verbose_name="売り推奨数")
    
    # メタデータ
    analyst_count = models.IntegerField(default=0, verbose_name="アナリスト数")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最終更新")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['stock', 'target_year']
        ordering = ['stock', '-target_year']

class IndustryBenchmark(models.Model):
    """業界ベンチマークデータ"""
    sector = models.CharField(max_length=100, verbose_name="業種", db_index=True)
    date = models.DateField(verbose_name="データ日付", db_index=True)
    
    # 平均指標
    avg_per = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="平均PER")
    avg_pbr = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="平均PBR")
    avg_roe = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="平均ROE")
    avg_roa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="平均ROA")
    avg_dividend_yield = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="平均配当利回り")
    avg_debt_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="平均負債比率")
    
    # 中央値
    median_per = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="中央値PER")
    median_pbr = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="中央値PBR")
    median_roe = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="中央値ROE")
    
    # 成長率
    avg_revenue_growth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="平均売上成長率")
    avg_profit_growth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="平均利益成長率")
    
    # メタデータ
    sample_count = models.IntegerField(default=0, verbose_name="サンプル数")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['sector', 'date']
        ordering = ['sector', '-date']
        indexes = [
            models.Index(fields=['sector', 'date']),
        ]

class MarketIndex(models.Model):
    """市場指数データ"""
    INDEX_CHOICES = [
        ('nikkei225', '日経平均'),
        ('topix', 'TOPIX'),
        ('mothers', 'マザーズ指数'),
        ('jasdaq', 'JASDAQ指数'),
        ('jpx400', 'JPX日経400'),
    ]
    
    index_name = models.CharField(max_length=20, choices=INDEX_CHOICES, verbose_name="指数名", db_index=True)
    date = models.DateField(verbose_name="日付", db_index=True)
    
    # 価格データ
    open_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="始値")
    high_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="高値")
    low_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="安値")
    close_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="終値")
    
    # 変化率
    change_points = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="前日比ポイント")
    change_percent = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="前日比率(%)")
    
    # 出来高
    volume = models.BigIntegerField(null=True, blank=True, verbose_name="出来高")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['index_name', 'date']
        ordering = ['index_name', '-date']
        indexes = [
            models.Index(fields=['index_name', 'date']),
        ]

class UserWatchlist(models.Model):
    """ユーザーウォッチリスト"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    name = models.CharField(max_length=100, verbose_name="ウォッチリスト名")
    description = models.TextField(blank=True, verbose_name="説明")
    is_default = models.BooleanField(default=False, verbose_name="デフォルト")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['user', 'name']

class WatchlistItem(models.Model):
    """ウォッチリスト項目"""
    watchlist = models.ForeignKey(UserWatchlist, on_delete=models.CASCADE, related_name='items')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    
    # 個人設定
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="目標価格")
    stop_loss_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ストップロス価格")
    notes = models.TextField(blank=True, verbose_name="メモ")
    
    # 追加日時
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['watchlist', 'stock']
        ordering = ['watchlist', 'added_at']

class StockAlert(models.Model):
    """株価アラート"""
    ALERT_TYPES = [
        ('price_above', '価格上昇'),
        ('price_below', '価格下落'),
        ('volume_spike', '出来高急増'),
        ('per_change', 'PER変化'),
        ('rating_change', 'レーティング変更'),
        ('earnings_surprise', '決算サプライズ'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name="アラート種類")
    
    # 条件設定
    trigger_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="発火値")
    condition_data = models.JSONField(default=dict, verbose_name="条件データ")
    
    # 状態
    is_active = models.BooleanField(default=True, verbose_name="有効")
    last_triggered = models.DateTimeField(null=True, blank=True, verbose_name="最終発火日時")
    trigger_count = models.IntegerField(default=0, verbose_name="発火回数")
    
    # 通知設定
    email_notification = models.BooleanField(default=True, verbose_name="メール通知")
    app_notification = models.BooleanField(default=True, verbose_name="アプリ通知")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['stock', 'alert_type']),
        ]