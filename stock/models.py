# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Stock(models.Model):
    """銘柄マスタ"""
    code = models.CharField(max_length=10, unique=True, verbose_name="銘柄コード")
    name = models.CharField(max_length=200, verbose_name="企業名")
    market = models.CharField(max_length=50, blank=True, verbose_name="市場区分")
    sector = models.CharField(max_length=100, blank=True, verbose_name="業種")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "銘柄"
        verbose_name_plural = "銘柄"
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Financial(models.Model):
    """財務データ"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='financials')
    year = models.IntegerField(verbose_name="決算年度")
    revenue = models.DecimalField(
        max_digits=20, decimal_places=0, 
        null=True, blank=True, verbose_name="売上高"
    )
    net_income = models.DecimalField(
        max_digits=20, decimal_places=0, 
        null=True, blank=True, verbose_name="純利益"
    )
    eps = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, verbose_name="EPS"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "財務データ"
        verbose_name_plural = "財務データ"
        unique_together = ['stock', 'year']
        ordering = ['stock', '-year']
    
    def __str__(self):
        return f"{self.stock.code} - {self.year}年"


class Indicator(models.Model):
    """指標データ"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='indicators')
    date = models.DateField(verbose_name="取得日")
    per = models.DecimalField(
        max_digits=8, decimal_places=2, 
        null=True, blank=True, verbose_name="PER"
    )
    pbr = models.DecimalField(
        max_digits=8, decimal_places=2, 
        null=True, blank=True, verbose_name="PBR"
    )
    dividend_yield = models.DecimalField(
        max_digits=5, decimal_places=2, 
        null=True, blank=True, 
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name="配当利回り(%)"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, verbose_name="株価"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "指標データ"
        verbose_name_plural = "指標データ"
        unique_together = ['stock', 'date']
        ordering = ['stock', '-date']
    
    def __str__(self):
        return f"{self.stock.code} - {self.date}"
    
# stock/models.py に追加

class AdvancedIndicator(models.Model):
    """高度指標データ"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='advanced_indicators')
    date = models.DateField(verbose_name="取得日")
    
    # 収益性指標
    roe = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="ROE")
    roa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="ROA")
    roic = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="ROIC")
    
    # バリュエーション
    psr = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="PSR")
    ev_ebitda = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="EV/EBITDA")
    
    # 安全性指標
    debt_equity_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="D/Eレシオ")
    current_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="流動比率")
    equity_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="自己資本比率")
    
    # 効率性指標
    asset_turnover = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="総資産回転率")
    inventory_turnover = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="棚卸回転率")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['stock', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.stock.code} - {self.date}"    