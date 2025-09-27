# stock/management/commands/update_stock_list.py
from django.core.management.base import BaseCommand
from stock.utils import StockDataFetcher

class Command(BaseCommand):
    help = 'JPXから上場銘柄一覧を取得・更新'
    
    def handle(self, *args, **options):
        self.stdout.write('JPXから銘柄リスト更新を開始...')
        
        try:
            # JPXからのデータ取得
            created_count = StockDataFetcher.fetch_jpx_stock_list()
            
            if created_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ JPX銘柄リスト更新完了: {created_count}件の新規銘柄を追加'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'JPXからの新規銘柄取得は0件でした'
                    )
                )
            
            # 結果統計の表示
            from stock.models import Stock
            total_count = Stock.objects.count()
            self.stdout.write(f'現在の総銘柄数: {total_count}件')
            
            # 市場区分別の内訳
            markets = Stock.objects.values_list('market', flat=True).distinct()
            for market in markets:
                count = Stock.objects.filter(market=market).count()
                self.stdout.write(f'  {market}: {count}件')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'エラーが発生しました: {e}')
            )