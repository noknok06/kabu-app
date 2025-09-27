# stock/utils.py - 完全版
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Stock, Financial, Indicator
from decimal import Decimal, InvalidOperation
import logging
import io
import tempfile
import os

logger = logging.getLogger(__name__)

class StockDataFetcher:
    """株式データ取得クラス"""
    
    @staticmethod
    def safe_decimal_convert(value):
        """安全にDecimal型に変換（NaN値やNone値を適切に処理）"""
        if value is None:
            return None
        
        # pandas/numpy NaN値のチェック
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        
        # numpy NaN値のチェック
        try:
            if isinstance(value, (int, float)) and np.isnan(value):
                return None
        except (TypeError, ValueError):
            pass
        
        # 文字列で'nan'の場合
        if isinstance(value, str) and value.lower() in ['nan', 'null', '', 'none']:
            return None
        
        # 無限大の値をチェック
        try:
            if isinstance(value, (int, float)) and (np.isinf(value) or abs(value) > 1e15):
                return None
        except (TypeError, ValueError):
            pass
        
        try:
            # 数値を文字列に変換してからDecimalに
            decimal_value = Decimal(str(value))
            # 異常に大きな値や小さな値をフィルタ
            if abs(decimal_value) > Decimal('1e15'):
                return None
            return decimal_value
        except (InvalidOperation, ValueError, TypeError, OverflowError):
            return None
    
    @staticmethod
    def fetch_jpx_stock_list():
        """JPXから上場銘柄一覧を取得（複数フォーマット対応）"""
        try:
            # JPXの上場銘柄一覧URL
            urls = [
                "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls",
                "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx"
            ]
            
            df = None
            used_url = None
            
            # 複数のURLとエンジンで試行
            for url in urls:
                try:
                    logger.info(f"JPXデータ取得試行: {url}")
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    
                    # 複数のExcelエンジンで試行
                    engines = ['openpyxl', 'xlrd', None]
                    
                    for engine in engines:
                        try:
                            logger.info(f"Excelエンジン試行: {engine}")
                            if engine:
                                df = pd.read_excel(io.BytesIO(response.content), engine=engine)
                            else:
                                df = pd.read_excel(io.BytesIO(response.content))
                            
                            used_url = url
                            logger.info(f"✓ 読み込み成功: {engine or 'default'} エンジン")
                            break
                            
                        except Exception as e:
                            logger.warning(f"エンジン {engine} での読み込み失敗: {e}")
                            continue
                    
                    if df is not None:
                        break
                        
                except requests.RequestException as e:
                    logger.warning(f"URL {url} でのダウンロード失敗: {e}")
                    continue
            
            if df is None:
                logger.error("すべてのURL・エンジンでの取得に失敗")
                return 0
            
            logger.info(f"データ取得成功: {df.shape[0]}行 × {df.shape[1]}列")
            logger.info(f"使用URL: {used_url}")
            
            # データ構造の確認と正規化
            return StockDataFetcher._parse_jpx_data(df)
            
        except Exception as e:
            logger.error(f"JPXデータ取得で予期しないエラー: {e}")
            return 0
    
    @staticmethod
    def _parse_jpx_data(df):
        """JPXデータの解析と銘柄登録"""
        try:
            logger.info(f"データ解析開始: {df.shape}")
            logger.info(f"カラム名: {df.columns.tolist()}")
            
            # カラム名の自動判定
            columns_mapping = StockDataFetcher._detect_column_mapping(df)
            
            if not columns_mapping:
                logger.error("カラムマッピングの判定に失敗")
                return 0
            
            stock_created = 0
            stock_updated = 0
            processed_count = 0
            
            for index, row in df.iterrows():
                try:
                    processed_count += 1
                    
                    # データ抽出
                    code = str(row.get(columns_mapping.get('code', ''), '') or '').strip()
                    name = str(row.get(columns_mapping.get('name', ''), '') or '').strip()
                    market = str(row.get(columns_mapping.get('market', ''), '') or '').strip()
                    sector = str(row.get(columns_mapping.get('sector', ''), '') or '').strip()
                    
                    # 最初の20行をデバッグ出力
                    if index < 20:
                        logger.info(f"行{index}: コード={code}, 銘柄名={name}, 市場={market}")
                    
                    # バリデーション
                    if not StockDataFetcher._validate_stock_data(code, name, market):
                        continue
                    
                    # データベース保存
                    stock, created = Stock.objects.get_or_create(
                        code=code,
                        defaults={
                            'name': name,
                            'market': market,
                            'sector': sector
                        }
                    )
                    
                    if created:
                        stock_created += 1
                        if stock_created <= 10:  # 最初の10件のみログ出力
                            logger.info(f"新規追加: {code} - {name}")
                    else:
                        # 既存銘柄の更新
                        updated = False
                        if stock.name != name:
                            stock.name = name
                            updated = True
                        if stock.market != market:
                            stock.market = market
                            updated = True
                        if stock.sector != sector:
                            stock.sector = sector
                            updated = True
                        
                        if updated:
                            stock.save()
                            stock_updated += 1
                
                except Exception as e:
                    logger.warning(f"行 {index} の処理エラー: {e}")
                    continue
            
            logger.info(f"処理完了: 処理{processed_count}行, 新規{stock_created}件, 更新{stock_updated}件")
            return stock_created
            
        except Exception as e:
            logger.error(f"データ解析エラー: {e}")
            return 0
    
    @staticmethod
    def _detect_column_mapping(df):
        """カラムマッピングの自動判定"""
        columns = df.columns.tolist()
        mapping = {}
        
        # カラム名パターンの定義
        patterns = {
            'code': ['コード', 'Code', '銘柄コード', 'ticker'],
            'name': ['銘柄名', 'Name', '名称', '会社名'],
            'market': ['市場', 'Market', '市場・商品区分', '市場区分'],
            'sector': ['業種', 'Sector', '33業種区分', '業種区分', '17業種区分']
        }
        
        # パターンマッチングでカラムを特定
        for key, pattern_list in patterns.items():
            for col in columns:
                for pattern in pattern_list:
                    if pattern in str(col):
                        mapping[key] = col
                        logger.info(f"カラムマッピング: {key} -> {col}")
                        break
                if key in mapping:
                    break
        
        # 位置ベースのフォールバック（JPXの一般的な構造）
        if len(columns) >= 4 and len(mapping) < 3:
            logger.info("位置ベースのカラムマッピングを使用")
            mapping = {
                'code': columns[1],      # 2列目: コード
                'name': columns[2],      # 3列目: 銘柄名
                'market': columns[3],    # 4列目: 市場区分
                'sector': columns[5] if len(columns) > 5 else columns[3]  # 6列目: 業種
            }
        
        logger.info(f"最終カラムマッピング: {mapping}")
        return mapping if len(mapping) >= 3 else None
    
    @staticmethod
    def _validate_stock_data(code, name, market):
        """銘柄データのバリデーション"""
        # 基本チェック
        if not code or not name:
            return False
        
        # 4桁数字のチェック
        if not (code.isdigit() and len(code) == 4):
            return False
        
        # ETF・ETN等を除外
        exclude_markets = [
            'ETF・ETN',
            'REIT・ベンチャーファンド・カントリーファンド・インフラファンド',
            'REIT',
            'ETF',
            'ETN'
        ]
        
        if any(exclude in market for exclude in exclude_markets):
            return False
        
        # 有効な市場のみ（より柔軟に）
        valid_market_keywords = ['プライム', 'スタンダード', 'グロース', '内国株式']
        if not any(keyword in market for keyword in valid_market_keywords):
            return False
        
        return True
    
    @staticmethod
    def create_sample_stock():
        """サンプル銘柄の作成（JPX取得が失敗した場合の代替）"""
        sample_stock = [
            ('1301', '極洋', 'プライム（内国株式）', '水産・農林業'),
            ('1332', '日本水産', 'プライム（内国株式）', '水産・農林業'),
            ('2002', '日清製粉グループ本社', 'プライム（内国株式）', '食料品'),
            ('2269', '明治ホールディングス', 'プライム（内国株式）', '食料品'),
            ('2914', 'ＪＴ', 'プライム（内国株式）', '食料品'),
            ('4063', '信越化学工業', 'プライム（内国株式）', '化学'),
            ('4502', '武田薬品工業', 'プライム（内国株式）', '医薬品'),
            ('4519', '中外製薬', 'プライム（内国株式）', '医薬品'),
            ('6758', 'ソニーグループ', 'プライム（内国株式）', '電気機器'),
            ('6861', 'キーエンス', 'プライム（内国株式）', '電気機器'),
            ('7203', 'トヨタ自動車', 'プライム（内国株式）', '輸送用機器'),
            ('7267', 'ホンダ', 'プライム（内国株式）', '輸送用機器'),
            ('7974', '任天堂', 'プライム（内国株式）', 'その他製品'),
            ('8306', '三菱ＵＦＪフィナンシャル・グループ', 'プライム（内国株式）', '銀行業'),
            ('8316', '三井住友フィナンシャルグループ', 'プライム（内国株式）', '銀行業'),
            ('9432', 'ＮＴＴ', 'プライム（内国株式）', '情報・通信業'),
            ('9983', 'ファーストリテイリング', 'プライム（内国株式）', '小売業'),
            ('9984', 'ソフトバンクグループ', 'プライム（内国株式）', '情報・通信業'),
        ]
        
        created_count = 0
        for code, name, market, sector in sample_stock:
            stock, created = Stock.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'market': market,
                    'sector': sector
                }
            )
            if created:
                created_count += 1
                logger.info(f"サンプル銘柄作成: {code} - {name}")
        
        logger.info(f"サンプル銘柄作成完了: {created_count}件")
        return created_count
    
    @staticmethod
    def fetch_stock_indicators(stock_code, days_back=30):
        """指定銘柄の指標データを取得（NaN値対応版）"""
        try:
            # Yahoo Financeでは日本株は「XXXX.T」形式
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            
            # 基本情報取得
            info = ticker.info
            
            # 現在日付
            today = timezone.now().date()
            
            # 指標データ取得と安全な変換
            per = StockDataFetcher.safe_decimal_convert(info.get('trailingPE'))
            pbr = StockDataFetcher.safe_decimal_convert(info.get('priceToBook'))
            
            # 配当利回り処理
            dividend_yield_raw = info.get('dividendYield')
            dividend_yield = None
            if dividend_yield_raw is not None:
                dividend_yield_percent = StockDataFetcher.safe_decimal_convert(dividend_yield_raw)
                if dividend_yield_percent is not None:
                    dividend_yield = dividend_yield_percent * 100  # パーセント表示
            
            # 株価取得
            price = None
            try:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price_raw = hist['Close'].iloc[-1]
                    price = StockDataFetcher.safe_decimal_convert(price_raw)
            except Exception as e:
                logger.warning(f"株価取得エラー {stock_code}: {e}")
            
            # データベース保存
            stock = Stock.objects.get(code=stock_code)
            indicator, created = Indicator.objects.get_or_create(
                stock=stock,
                date=today,
                defaults={
                    'per': per,
                    'pbr': pbr,
                    'dividend_yield': dividend_yield,
                    'price': price
                }
            )
            
            if not created:
                # 既存データを更新
                indicator.per = per
                indicator.pbr = pbr
                indicator.dividend_yield = dividend_yield
                indicator.price = price
                indicator.save()
            
            logger.info(f"指標データ更新成功: {stock_code}")
            return True
            
        except Stock.DoesNotExist:
            logger.error(f"銘柄コード {stock_code} が見つかりません")
            return False
        except Exception as e:
            logger.error(f"銘柄 {stock_code} の指標データ取得エラー: {e}")
            return False
    
    @staticmethod
    def fetch_financial_data(stock_code, years=5):
        """指定銘柄の財務データを取得（NaN値対応版）"""
        try:
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            
            # 財務データ取得
            financials = ticker.financials
            if financials.empty:
                logger.warning(f"銘柄 {stock_code} の財務データが取得できませんでした")
                return False
            
            stock = Stock.objects.get(code=stock_code)
            
            financials_saved = 0
            for date, data in financials.items():
                year = date.year
                
                # 売上高（複数のキーを試行）
                revenue_raw = (data.get('Total Revenue') or 
                              data.get('Operating Revenue') or 
                              data.get('Revenue'))
                
                # 純利益（複数のキーを試行）
                net_income_raw = (data.get('Net Income') or 
                                 data.get('Net Income Common Stockholders') or
                                 data.get('Net Income Continuous Operations'))
                
                # 安全にDecimal変換
                revenue = StockDataFetcher.safe_decimal_convert(revenue_raw)
                net_income = StockDataFetcher.safe_decimal_convert(net_income_raw)
                
                # EPS情報取得
                eps = None
                try:
                    info = ticker.info
                    eps_raw = info.get('trailingEps')
                    eps = StockDataFetcher.safe_decimal_convert(eps_raw)
                except Exception as e:
                    logger.warning(f"EPS取得エラー {stock_code}: {e}")
                
                # データが全てNoneの場合はスキップ
                if all(v is None for v in [revenue, net_income, eps]):
                    continue
                
                try:
                    financial, created = Financial.objects.update_or_create(
                        stock=stock,
                        year=year,
                        defaults={
                            'revenue': revenue,
                            'net_income': net_income,
                            'eps': eps
                        }
                    )
                    
                    if created or any([revenue, net_income, eps]):
                        financials_saved += 1
                        
                except Exception as e:
                    logger.error(f"財務データ保存エラー {stock_code} {year}年: {e}")
                    continue
            
            if financials_saved > 0:
                logger.info(f"財務データ更新成功: {stock_code} - {financials_saved}年分")
                return True
            else:
                logger.warning(f"財務データ保存件数が0: {stock_code}")
                return False
            
        except Stock.DoesNotExist:
            logger.error(f"銘柄コード {stock_code} が見つかりません")
            return False
        except Exception as e:
            logger.error(f"銘柄 {stock_code} の財務データ取得エラー: {e}")
            return False
    
    @staticmethod
    def check_consecutive_profit_growth(stock, years=5):
        """連続増益判定"""
        try:
            financials = stock.financials.filter(
                net_income__isnull=False
            ).order_by('-year')[:years]
            
            if len(financials) < years:
                return False
            
            for i in range(len(financials) - 1):
                current_year = financials[i]
                previous_year = financials[i + 1]
                
                if current_year.net_income <= previous_year.net_income:
                    return False
            
            return True
        except Exception as e:
            logger.error(f"連続増益判定エラー: {e}")
            return False
    
    @staticmethod
    def batch_update_indicators(limit=None):
        """全銘柄の指標データを一括更新"""
        try:
            stock = Stock.objects.all()
            if limit:
                stock = stock[:limit]
            
            success_count = 0
            total_count = len(stock)
            
            for i, stock in enumerate(stock, 1):
                logger.info(f"指標データ更新中: {i}/{total_count} - {stock.code}")
                if StockDataFetcher.fetch_stock_indicators(stock.code):
                    success_count += 1
                
                # APIレート制限対策（1秒待機）
                import time
                time.sleep(1)
            
            logger.info(f"指標データ更新完了: {success_count}/{total_count}")
            return success_count
        except Exception as e:
            logger.error(f"一括指標データ更新エラー: {e}")
            return 0
    
    @staticmethod
    def fetch_jpx_stock_list_debug():
        """JPXデータの構造確認用（デバッグ専用）"""
        try:
            url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            import io
            df = pd.read_excel(io.BytesIO(response.content))
            
            print("=== JPXデータ構造確認 ===")
            print(f"データ形状: {df.shape}")
            print(f"カラム名: {df.columns.tolist()}")
            print("\n=== 最初の5行 ===")
            print(df.head())
            print("\n=== データ型 ===")
            print(df.dtypes)
            print("\n=== 市場区分の種類 ===")
            if '市場・商品区分' in df.columns:
                print(df['市場・商品区分'].value_counts())
            elif len(df.columns) >= 4:
                print(df.iloc[:, 3].value_counts())  # 4番目のカラム
            
            # サンプルデータを保存
            df.head(20).to_csv('jpx_sample.csv', encoding='utf-8')
            print("\nサンプルデータを jpx_sample.csv に保存しました")
            
            return df
            
        except Exception as e:
            print(f"デバッグ実行エラー: {e}")
            return None