# stock/management/commands/setup_advanced_models.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'AdvancedIndicator モデルのセットアップ'
    
    def handle(self, *args, **options):
        self.stdout.write('AdvancedIndicator モデルセットアップガイド')
        self.stdout.write('\n以下の手順でセットアップしてください:')
        
        self.stdout.write('\n1. models.py に AdvancedIndicator モデルを追加:')
        model_code = '''
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
        '''
        
        self.stdout.write(model_code)
        
        self.stdout.write('\n2. マイグレーション実行:')
        self.stdout.write('  python manage.py makemigrations')
        self.stdout.write('  python manage.py migrate')
        
        self.stdout.write('\n3. advanced_data_fetcher.py の配置:')
        self.stdout.write('  stock/advanced_data_fetcher.py ファイルを作成')
        
        self.stdout.write('\n4. テスト実行:')
        self.stdout.write('  python manage.py update_advanced_indicators --code 7203')
        
        self.stdout.write('\n完了後、以下で動作確認:')
        self.stdout.write('  python manage.py update_advanced_indicators --validate')