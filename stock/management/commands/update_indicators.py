# stock/management/commands/update_indicators.py - 修正版
from django.core.management.base import BaseCommand
from django.utils import timezone
from stock.models import Stock
from stock.utils import StockDataFetcher
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '全銘柄の指標データ（PER, PBR, 配当利回り）を更新'
    
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, help='更新する銘柄数の上限')
        parser.add_argument('--code', type=str, help='特定の銘柄コードのみ更新')
        parser.add_argument('--batch-size', type=int, default=50, help='バッチサイズ')
        parser.add_argument('--delay', type=float, default=1.0, help='API呼び出し間の遅延時間（秒）')
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        limit = options.get('limit')
        specific_code = options.get('code')
        batch_size = options.get('batch_size')
        delay = options.get('delay')
        
        # 特定銘柄の更新
        if specific_code:
            self.stdout.write(f'銘柄 {specific_code} の指標データ更新を開始...')
            success = StockDataFetcher.fetch_stock_indicators(specific_code)
            if success:
                self.stdout.write(self.style.SUCCESS(f'✓ 銘柄 {specific_code} の更新完了'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ 銘柄 {specific_code} の更新に失敗'))
            return

        # 全銘柄または制限付きでの更新
        stocks = Stock.objects.all().order_by('code')  # ★修正: 変数名をstockに
        if limit:
            stocks = stocks[:limit]

        total_count = stocks.count()
        success_count = 0
        error_count = 0
        
        self.stdout.write(f'指標データ更新開始: 対象 {total_count} 銘柄')
        self.stdout.write(f'バッチサイズ: {batch_size}, 遅延: {delay}秒')
        
        # バッチ処理
        for i in range(0, total_count, batch_size):
            batch = stocks[i:i + batch_size]  # ← QuerySet なのでスライスOK
            self.stdout.write(f'\n--- バッチ {i//batch_size + 1} 開始 ({i+1}-{min(i+batch_size, total_count)}/{total_count}) ---')
            
            batch_success = 0
            for stock in batch:
                try:
                    self.stdout.write(f'処理中: {stock.code} - {stock.name}', ending='... ')
                    
                    success = StockDataFetcher.fetch_stock_indicators(stock.code)
                    if success:
                        success_count += 1
                        batch_success += 1
                        self.stdout.write(self.style.SUCCESS('✓'))
                    else:
                        error_count += 1
                        self.stdout.write(self.style.WARNING('⚠'))
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'✗ エラー: {e}'))
                
                # API制限対策
                if delay > 0:
                    time.sleep(delay)
            
            self.stdout.write(f'バッチ完了: 成功 {batch_success}/{len(batch)}')
            
            # バッチ間の休憩
            if i + batch_size < total_count:
                self.stdout.write('次のバッチまで5秒待機...')
                time.sleep(5)
        
        # 結果サマリー
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('指標データ更新完了')
        self.stdout.write(f'実行時間: {duration:.1f}秒')
        self.stdout.write(f'対象銘柄数: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'成功: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'失敗: {error_count}'))
        self.stdout.write(f'成功率: {success_count/total_count*100:.1f}%')
        self.stdout.write('='*50)