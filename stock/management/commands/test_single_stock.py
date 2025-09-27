# stock/management/commands/test_single_stock.py
from django.core.management.base import BaseCommand
from stock.utils import StockDataFetcher
from stock.models import Stock

class Command(BaseCommand):
    help = '個別銘柄のデータ取得をテスト'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            default='7203',  # トヨタ自動車
            help='テスト対象の銘柄コード（デフォルト: 7203）',
        )
        parser.add_argument(
            '--create-stock',
            action='store_true',
            help='銘柄マスタに存在しない場合、テスト用に作成',
        )
    
    def handle(self, *args, **options):
        stock_code = options['code']
        
        self.stdout.write(f'銘柄 {stock_code} のデータ取得テストを開始...')
        
        # 銘柄マスタの確認/作成
        try:
            stock = Stock.objects.get(code=stock_code)
            self.stdout.write(f'✓ 銘柄マスタに存在: {stock.code} - {stock.name}')
        except Stock.DoesNotExist:
            if options['create_stock']:
                stock = Stock.objects.create(
                    code=stock_code,
                    name=f'テスト銘柄{stock_code}',
                    market='テスト'
                )
                self.stdout.write(f'✓ テスト用銘柄を作成: {stock_code}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'銘柄 {stock_code} がマスタに存在しません。--create-stock オプションを使用してください。')
                )
                return
        
        # 指標データ取得テスト
        self.stdout.write('\n=== 指標データ取得テスト ===')
        success = StockDataFetcher.fetch_stock_indicators(stock_code)
        if success:
            self.stdout.write(self.style.SUCCESS('✓ 指標データ取得成功'))
            
            # 取得した指標データを表示
            indicators = stock.indicators.order_by('-date')[:1]
            if indicators:
                indicator = indicators[0]
                self.stdout.write(f'  PER: {indicator.per}')
                self.stdout.write(f'  PBR: {indicator.pbr}')
                self.stdout.write(f'  配当利回り: {indicator.dividend_yield}%')
                self.stdout.write(f'  株価: ¥{indicator.price}')
                self.stdout.write(f'  取得日: {indicator.date}')
        else:
            self.stdout.write(self.style.ERROR('✗ 指標データ取得失敗'))
        
        # 財務データ取得テスト
        self.stdout.write('\n=== 財務データ取得テスト ===')
        success = StockDataFetcher.fetch_financial_data(stock_code)
        if success:
            self.stdout.write(self.style.SUCCESS('✓ 財務データ取得成功'))
            
            # 取得した財務データを表示
            financials = stock.financials.order_by('-year')[:3]
            for financial in financials:
                self.stdout.write(f'  {financial.year}年: 売上高={financial.revenue}, 純利益={financial.net_income}')
        else:
            self.stdout.write(self.style.ERROR('✗ 財務データ取得失敗'))
        
        # 連続増益判定テスト
        self.stdout.write('\n=== 連続増益判定テスト ===')
        is_consecutive = StockDataFetcher.check_consecutive_profit_growth(stock, 5)
        if is_consecutive:
            self.stdout.write(self.style.SUCCESS('✓ 5年連続増益'))
        else:
            self.stdout.write('✗ 5年連続増益ではない')
        
        self.stdout.write('\nテスト完了')