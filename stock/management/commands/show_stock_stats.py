# 追加で作成: stock/management/commands/show_stock_stats.py
from django.core.management.base import BaseCommand
from stock.models import Stock, Indicator, Financial

class Command(BaseCommand):
    help = '現在の銘柄・データ統計を表示'
    
    def handle(self, *args, **options):
        self.stdout.write('=== 株式データ統計 ===')
        
        # 銘柄統計
        total_stock = Stock.objects.count()
        self.stdout.write(f'総銘柄数: {total_stock}件')
        
        if total_stock == 0:
            self.stdout.write(self.style.WARNING('銘柄データがありません'))
            self.stdout.write('以下のコマンドで銘柄を追加してください:')
            self.stdout.write('  python manage.py update_stock_list')
            self.stdout.write('  または')
            self.stdout.write('  python manage.py create_sample_stock')
            return
        
        # 市場区分別
        self.stdout.write('\n=== 市場区分別 ===')
        markets = Stock.objects.values_list('market', flat=True).distinct()
        for market in sorted(markets):
            count = Stock.objects.filter(market=market).count()
            self.stdout.write(f'{market}: {count}件')
        
        # 指標データ統計
        indicator_count = Indicator.objects.count()
        stock_with_indicators = Stock.objects.filter(indicators__isnull=False).distinct().count()
        self.stdout.write(f'\n=== 指標データ ===')
        self.stdout.write(f'指標データ総数: {indicator_count}件')
        self.stdout.write(f'指標データがある銘柄: {stock_with_indicators}件')
        
        if stock_with_indicators > 0:
            coverage = round(stock_with_indicators / total_stock * 100, 1)
            self.stdout.write(f'指標データカバー率: {coverage}%')
            
            # 最新の指標データ
            latest_indicator = Indicator.objects.order_by('-date').first()
            if latest_indicator:
                self.stdout.write(f'最新指標データ日付: {latest_indicator.date}')
        
        # 財務データ統計
        financial_count = Financial.objects.count()
        stock_with_financials = Stock.objects.filter(financials__isnull=False).distinct().count()
        self.stdout.write(f'\n=== 財務データ ===')
        self.stdout.write(f'財務データ総数: {financial_count}件')
        self.stdout.write(f'財務データがある銘柄: {stock_with_financials}件')
        
        if stock_with_financials > 0:
            coverage = round(stock_with_financials / total_stock * 100, 1)
            self.stdout.write(f'財務データカバー率: {coverage}%')
        
        # 推奨アクション
        self.stdout.write('\n=== 推奨アクション ===')
        if stock_with_indicators < 10:
            self.stdout.write('指標データを取得: python manage.py update_indicators --limit 10')
        if stock_with_financials < 5:
            self.stdout.write('財務データを取得: python manage.py update_financials --limit 5')
        
        self.stdout.write('スクリーニング画面: python manage.py runserver → http://127.0.0.1:8000/screening/')