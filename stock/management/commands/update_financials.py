# stocks/management/commands/update_financials.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from stock.models import Stock, Financial
from stock.utils import StockDataFetcher
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '財務データ（売上高、純利益、EPS）を更新'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='更新する銘柄数の上限',
        )
        parser.add_argument(
            '--code',
            type=str,
            help='特定の銘柄コードのみ更新',
        )
        parser.add_argument(
            '--years',
            type=int,
            default=5,
            help='取得する財務データの年数（デフォルト: 5年）',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=20,
            help='バッチサイズ（財務データは重いため小さめ）',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='API呼び出し間の遅延時間（秒、財務データは長め）',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存の財務データを強制更新',
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        limit = options.get('limit')
        specific_code = options.get('code')
        years = options.get('years')
        batch_size = options.get('batch_size')
        delay = options.get('delay')
        force_update = options.get('force')
        
        # 特定銘柄の更新
        if specific_code:
            self.stdout.write(f'銘柄 {specific_code} の財務データ更新を開始...')
            self.stdout.write(f'取得年数: {years}年')

            success = StockDataFetcher.fetch_financial_data(specific_code, years)
            if success:
                # 更新後の財務データ確認
                try:
                    stocks = Stock.objects.get(code=specific_code)
                    financial_count = stocks.financials.count()
                    latest_year = stocks.financials.first().year if financial_count > 0 else None
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ 銘柄 {specific_code} の更新完了\n'
                            f'  財務データ件数: {financial_count}\n'
                            f'  最新年度: {latest_year}'
                        )
                    )
                except stocks.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'銘柄 {specific_code} が見つかりません'))
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ 銘柄 {specific_code} の更新に失敗')
                )
            return
        
        # 全銘柄または制限付きでの更新
        stocks = Stock.objects.all().order_by('code')
                
        # 既存財務データがない銘柄を優先（force_updateでない場合）
        if not force_update:
            stocks_without_financials = stocks.filter(financials__isnull=True).distinct()
            stocks_with_financials = stocks.filter(financials__isnull=False).distinct()
            # 財務データがない銘柄を優先
            stocks = list(stocks_without_financials) + list(stocks_with_financials)

        if limit:
            stocks = stocks[:limit]
            self.stdout.write(f'制限モード: 最初の {limit} 銘柄を更新')

        total_count = len(stocks)
        success_count = 0
        error_count = 0
        skip_count = 0
        
        self.stdout.write(f'財務データ更新開始: 対象 {total_count} 銘柄')
        self.stdout.write(f'取得年数: {years}年')
        self.stdout.write(f'バッチサイズ: {batch_size}, 遅延: {delay}秒')
        self.stdout.write(f'強制更新: {"有効" if force_update else "無効"}')
        
        # バッチ処理
        for i in range(0, total_count, batch_size):
            batch_end = min(i + batch_size, total_count)
            batch = stocks[i:batch_end]
            
            self.stdout.write(f'\n--- バッチ {i//batch_size + 1} 開始 ({i+1}-{batch_end}/{total_count}) ---')
            
            batch_success = 0
            for stock in batch:  # ★ 単数形に修正
                try:
                    if not force_update:
                        existing_count = stock.financials.count()
                        if existing_count >= years:
                            skip_count += 1
                            self.stdout.write(
                                f'スキップ: {stock.code} - {stock.name} '
                                f'(既存データ {existing_count}件)'
                            )
                            continue

                    self.stdout.write(f'処理中: {stock.code} - {stock.name}', ending='... ')
                    
                    success = StockDataFetcher.fetch_financial_data(stock.code, years)  # ★クラス名修正
                    if success:
                        updated_count = stock.financials.count()
                        success_count += 1
                        batch_success += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ ({updated_count}件)'))
                    else:
                        error_count += 1
                        self.stdout.write(self.style.WARNING('⚠'))
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'✗ エラー: {e}'))
                
                # 財務データは重いのでより長い間隔
                if delay > 0:
                    time.sleep(delay)
            
            self.stdout.write(f'バッチ完了: 成功 {batch_success}/{len(batch)}')
            
            # バッチ間の長い休憩
            if batch_end < total_count:
                self.stdout.write('次のバッチまで10秒待機...')
                time.sleep(10)
        
        # 結果サマリー
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'財務データ更新完了')
        self.stdout.write(f'実行時間: {duration/60:.1f}分 ({duration:.1f}秒)')
        self.stdout.write(f'対象銘柄数: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'成功: {success_count}'))
        if skip_count > 0:
            self.stdout.write(f'スキップ: {skip_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'失敗: {error_count}'))
        
        processed_count = success_count + error_count
        if processed_count > 0:
            self.stdout.write(f'成功率: {success_count/processed_count*100:.1f}%')
        
        # 財務データ統計
        total_financial_records = Financial.objects.count()
        self.stdout.write(f'総財務データ件数: {total_financial_records}')
        self.stdout.write('='*60)
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\n注意: 一部銘柄の更新に失敗しました。'
                    '\n原因として以下が考えられます：'
                    '\n- Yahoo Financeで財務データが公開されていない'
                    '\n- 上場廃止や統合された銘柄'
                    '\n- APIの一時的な制限'
                    '\n\n対処法:'
                    '\n- --code オプションで個別銘柄を再試行'
                    '\n- --force オプションで強制更新'
                )
            )