# stock/management/commands/update_financials_safe.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from stock.models import Stock
from stock.utils import StockDataFetcher
import time

class Command(BaseCommand):
    help = '財務データを更新（NaN値対応版）'
    
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, help='更新する銘柄数の上限')
        parser.add_argument('--delay', type=float, default=2.0, help='API呼び出し間の遅延時間（秒）')
    
    def handle(self, *args, **options):
        limit = options.get('limit')
        delay = options.get('delay')
        
        stock = Stock.objects.all()
        if limit:
            stock = stock[:limit]
        
        success_count = 0
        error_count = 0
        total_count = len(stock)
        
        self.stdout.write(f'財務データ更新開始（NaN値対応版）: 対象 {total_count} 銘柄')
        
        for i, stock in enumerate(stock, 1):
            try:
                self.stdout.write(f'処理中: {i}/{total_count} - {stock.code} {stock.name}', ending='... ')
                
                if StockDataFetcher.fetch_financial_data(stock.code):
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS('✓'))
                else:
                    error_count += 1
                    self.stdout.write(self.style.WARNING('⚠'))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'✗ エラー: {e}'))
            
            time.sleep(delay)
        
        self.stdout.write(f'\n財務データ更新完了: 成功 {success_count}/{total_count}