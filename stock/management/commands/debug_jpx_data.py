# stock/management/commands/debug_jpx_data.py
from django.core.management.base import BaseCommand
from stock.utils import StockDataFetcher
import pandas as pd
import requests
import io

class Command(BaseCommand):
    help = 'JPXデータの構造を確認・デバッグ'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--save-sample',
            action='store_true',
            help='サンプルデータをCSVファイルに保存',
        )
        parser.add_argument(
            '--test-parsing',
            action='store_true',
            help='データ解析のテスト実行',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('JPXデータ構造の確認を開始...')
        
        try:
            url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
            
            # データダウンロード
            self.stdout.write('データをダウンロード中...')
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Excelファイル読み込み
            df = pd.read_excel(io.BytesIO(response.content))
            
            self.stdout.write(f'✓ ダウンロード成功')
            self.stdout.write(f'データサイズ: {df.shape[0]}行 × {df.shape[1]}列')
            
            # カラム情報表示
            self.stdout.write('\n=== カラム情報 ===')
            for i, col in enumerate(df.columns):
                self.stdout.write(f'{i}: {col}')
            
            # 先頭データ表示
            self.stdout.write('\n=== 先頭5行のデータ ===')
            for index, row in df.head().iterrows():
                self.stdout.write(f'行{index}: {row.tolist()}')
            
            # データ型確認
            self.stdout.write('\n=== データ型 ===')
            for col, dtype in df.dtypes.items():
                self.stdout.write(f'{col}: {dtype}')
            
            # 市場区分の分析
            if len(df.columns) >= 4:
                market_col = df.columns[3]  # 4番目のカラム（市場・商品区分と推定）
                self.stdout.write(f'\n=== {market_col} の分布 ===')
                market_counts = df[market_col].value_counts()
                for market, count in market_counts.head(10).items():
                    self.stdout.write(f'{market}: {count}件')
            
            # 銘柄コードの分析
            if len(df.columns) >= 2:
                code_col = df.columns[1]  # 2番目のカラム（コードと推定）
                self.stdout.write(f'\n=== {code_col} の分析 ===')
                
                # 4桁数字の銘柄をカウント
                codes = df[code_col].astype(str)
                four_digit_codes = codes[codes.str.isdigit() & (codes.str.len() == 4)]
                self.stdout.write(f'4桁数字の銘柄: {len(four_digit_codes)}件')
                
                # サンプル表示
                self.stdout.write('サンプル銘柄コード:')
                for code in four_digit_codes.head(10):
                    self.stdout.write(f'  {code}')
            
            # サンプルファイル保存
            if options['save_sample']:
                sample_file = 'jpx_data_sample.csv'
                df.head(50).to_csv(sample_file, encoding='utf-8', index=False)
                self.stdout.write(f'\n✓ サンプルデータを {sample_file} に保存しました')
            
            # テスト解析実行
            if options['test_parsing']:
                self.stdout.write('\n=== テスト解析実行 ===')
                self.test_data_parsing(df)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'エラーが発生しました: {e}')
            )
    
    def test_data_parsing(self, df):
        """データ解析のテスト"""
        try:
            # カラム名を推定して設定
            if len(df.columns) >= 10:
                df.columns = ['日付', 'コード', '銘柄名', '市場・商品区分', '33業種コード', '33業種区分', 
                             '17業種コード', '17業種区分', '規模コード', '規模区分']
            
            valid_count = 0
            invalid_count = 0
            
            for index, row in df.head(100).iterrows():  # 最初の100行をテスト
                code = str(row.get('コード', '') or '').strip()
                name = str(row.get('銘柄名', '') or '').strip()
                market = str(row.get('市場・商品区分', '') or '').strip()
                
                # バリデーション
                if not code or not name:
                    invalid_count += 1
                    continue
                
                if not (code.isdigit() and len(code) == 4):
                    invalid_count += 1
                    continue
                
                if market in ['ETF・ETN', 'REIT・ベンチャーファンド・カントリーファンド・インフラファンド']:
                    invalid_count += 1
                    continue
                
                valid_markets = ['プライム（内国株式）', 'スタンダード（内国株式）', 'グロース（内国株式）']
                if market not in valid_markets:
                    invalid_count += 1
                    continue
                
                valid_count += 1
                
                # 有効な銘柄の最初の10件を表示
                if valid_count <= 10:
                    self.stdout.write(f'  有効銘柄: {code} - {name} ({market})')
            
            self.stdout.write(f'テスト結果: 有効 {valid_count}件, 無効 {invalid_count}件')
            
        except Exception as e:
            self.stdout.write(f'テスト解析エラー: {e}')
