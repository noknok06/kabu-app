# stock/management/commands/create_sample_stock.py
from django.core.management.base import BaseCommand
from stock.utils import StockDataFetcher

class Command(BaseCommand):
    help = 'サンプル銘柄を作成（JPX取得が失敗した場合の代替）'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存の銘柄データを上書き更新',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('サンプル銘柄の作成を開始...')
        
        try:
            created_count = StockDataFetcher.create_sample_stock()
            
            if created_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ サンプル銘柄作成完了: {created_count}件の新規銘柄を追加'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('既存の銘柄データがあるため、新規作成は0件です')
                )
            
            # 作成後の統計表示
            from stock.models import Stock
            total_stock = Stock.objects.count()
            self.stdout.write(f'現在の総銘柄数: {total_stock}件')
            
            # 市場区分別の内訳
            markets = Stock.objects.values_list('market', flat=True).distinct()
            for market in markets:
                count = Stock.objects.filter(market=market).count()
                self.stdout.write(f'  {market}: {count}件')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'エラーが発生しました: {e}')
            )


