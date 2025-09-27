# stock/management/commands/update_advanced_indicators.py (修正版)
from django.core.management.base import BaseCommand
from django.utils import timezone
from stock.models import Stock
from stock.advanced_data_fetcher import AdvancedDataFetcher
import time

class Command(BaseCommand):
    help = '高度指標データの更新（修正版）'
    
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, help='更新する銘柄数の上限')
        parser.add_argument('--code', type=str, help='特定の銘柄コードのみ更新')
        parser.add_argument('--validate', action='store_true', help='データ検証のみ実行')
        parser.add_argument('--missing-report', action='store_true', help='欠損データレポート生成')
        parser.add_argument('--delay', type=float, default=1, help='API呼び出し間の遅延時間')
        parser.add_argument('--force', action='store_true', help='既存データを強制更新')
        
    def handle(self, *args, **options):
        start_time = timezone.now()
        
        # データ検証のみ
        if options['validate']:
            self.run_validation()
            return
        
        # 欠損データレポート
        if options['missing_report']:
            self.generate_missing_report()
            return
        
        # 特定銘柄の更新
        if options['code']:
            self.update_single_stock(options['code'])
            return
        
        # 一括更新
        self.run_batch_update(options, start_time)
    
    def run_validation(self):
        """データ検証実行"""
        self.stdout.write('高度指標データの検証を開始...')
        
        try:
            # AdvancedIndicator モデルが存在しない場合の対応
            from stock.models import AdvancedIndicator
        except ImportError:
            self.stdout.write(
                self.style.ERROR('AdvancedIndicator モデルが見つかりません。')
            )
            self.stdout.write('まず以下を実行してください：')
            self.stdout.write('1. models.py に AdvancedIndicator モデルを追加')
            self.stdout.write('2. python manage.py makemigrations')
            self.stdout.write('3. python manage.py migrate')
            return
        
        # 基本統計
        try:
            total_indicators = AdvancedIndicator.objects.count()
            self.stdout.write(f'総高度指標レコード数: {total_indicators}')
            
            if total_indicators == 0:
                self.stdout.write(self.style.WARNING('高度指標データがありません'))
                return
            
            # 最新データの確認
            latest = AdvancedIndicator.objects.order_by('-date').first()
            if latest:
                self.stdout.write(f'最新データ日付: {latest.date}')
                self.stdout.write(f'最新データ銘柄: {latest.stock.code} - {latest.stock.name}')
            
            # フィールド別データ存在率
            fields = ['roe', 'roa', 'roic', 'debt_equity_ratio', 'current_ratio', 'psr']
            for field in fields:
                count = AdvancedIndicator.objects.filter(**{f'{field}__isnull': False}).count()
                rate = (count / total_indicators * 100) if total_indicators > 0 else 0
                self.stdout.write(f'{field}: {count}件 ({rate:.1f}%)')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'検証エラー: {e}'))
    
    def generate_missing_report(self):
        """欠損データレポート生成"""
        self.stdout.write('欠損データレポートを生成中...')
        
        try:
            from stock.models import AdvancedIndicator
            
            stocks = Stock.objects.all()
            
            no_data = []
            outdated_data = []
            incomplete_data = []
            
            cutoff_date = timezone.now().date() - timezone.timedelta(days=30)
            
            for stock in stocks[:50]:  # 最初の50銘柄で確認
                try:
                    latest_advanced = stock.advanced_indicators.order_by('-date').first()
                    
                    if not latest_advanced:
                        no_data.append(stock.code)
                    elif latest_advanced.date < cutoff_date:
                        outdated_data.append((stock.code, latest_advanced.date))
                    else:
                        # データ完全性チェック
                        required_fields = ['roe', 'roa']
                        missing_fields = []
                        for field in required_fields:
                            if getattr(latest_advanced, field) is None:
                                missing_fields.append(field)
                        
                        if missing_fields:
                            incomplete_data.append((stock.code, missing_fields))
                
                except Exception as e:
                    self.stdout.write(f'エラー {stock.code}: {e}')
            
            self.stdout.write('\n=== 欠損データレポート ===')
            self.stdout.write(f"高度指標データなし: {len(no_data)}銘柄")
            self.stdout.write(f"データ古い: {len(outdated_data)}銘柄")
            self.stdout.write(f"データ不完全: {len(incomplete_data)}銘柄")
            
            if no_data:
                self.stdout.write('\n高度指標データがない銘柄:')
                for code in no_data[:10]:
                    self.stdout.write(f'  {code}')
                if len(no_data) > 10:
                    self.stdout.write(f'  ... 他{len(no_data) - 10}件')
            
        except ImportError:
            self.stdout.write(self.style.ERROR('AdvancedIndicator モデルが見つかりません'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'レポート生成エラー: {e}'))
    
    def update_single_stock(self, stock_code):
        """特定銘柄の更新"""
        self.stdout.write(f"銘柄 {stock_code} の高度指標更新を開始...")
        
        try:
            # 銘柄存在確認
            stock = Stock.objects.get(code=stock_code)
            self.stdout.write(f"対象銘柄: {stock.code} - {stock.name}")
            
            # 更新実行
            success = AdvancedDataFetcher.fetch_advanced_indicators(stock_code)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f"✓ 銘柄 {stock_code} の更新完了"))
                
                # 更新内容の表示
                try:
                    from stock.models import AdvancedIndicator
                    latest = stock.advanced_indicators.order_by('-date').first()
                    
                    if latest:
                        self.stdout.write('\n取得データ:')
                        fields = ['roe', 'roa', 'roic', 'debt_equity_ratio', 'current_ratio', 'psr']
                        for field in fields:
                            value = getattr(latest, field)
                            if value is not None:
                                self.stdout.write(f'  {field}: {value}')
                            else:
                                self.stdout.write(f'  {field}: データなし')
                    else:
                        self.stdout.write('更新されたデータが見つかりません')
                        
                except ImportError:
                    self.stdout.write('AdvancedIndicator モデルが見つかりません')
                
            else:
                self.stdout.write(self.style.ERROR(f"✗ 銘柄 {stock_code} の更新に失敗"))
                self.stdout.write('考えられる原因:')
                self.stdout.write('- Yahoo Financeでデータが提供されていない')
                self.stdout.write('- 一時的なネットワーク問題')
                self.stdout.write('- 銘柄コードが正しくない')
                
        except Stock.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'銘柄 {stock_code} が見つかりません'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'エラー: {e}'))
    
    def run_batch_update(self, options, start_time):
        """一括更新の実行"""
        limit = options.get('limit')
        delay = options.get('delay')
        force = options.get('force')
        
        # 更新対象銘柄の選択（修正版）
        stocks = Stock.objects.all().order_by('code')
        
        if not force:
            # より安全な方法で優先度を決定
            try:
                from stock.models import AdvancedIndicator
                
                cutoff_date = timezone.now().date() - timezone.timedelta(days=7)
                
                # データなし銘柄のIDを取得
                stocks_with_data = Stock.objects.filter(
                    advanced_indicators__isnull=False
                ).values_list('id', flat=True).distinct()
                
                # 古いデータ銘柄のIDを取得
                stocks_with_recent_data = Stock.objects.filter(
                    advanced_indicators__date__gte=cutoff_date
                ).values_list('id', flat=True).distinct()
                
                # 分類
                stocks_without_data = stocks.exclude(id__in=stocks_with_data)
                stocks_with_old_data = stocks.filter(
                    id__in=stocks_with_data
                ).exclude(id__in=stocks_with_recent_data)
                stocks_with_recent_data_qs = stocks.filter(id__in=stocks_with_recent_data)
                
                # Pythonレベルで結合（SQLiteの制限回避）
                ordered_stocks = (
                    list(stocks_without_data[:100]) +
                    list(stocks_with_old_data[:100]) +
                    list(stocks_with_recent_data_qs[:100])
                )
                
                self.stdout.write(f'優先度別内訳:')
                self.stdout.write(f'  データなし: {stocks_without_data.count()}銘柄')
                self.stdout.write(f'  古いデータ: {stocks_with_old_data.count()}銘柄')
                self.stdout.write(f'  最新データ: {stocks_with_recent_data_qs.count()}銘柄')
                
                stocks = ordered_stocks
                
            except ImportError:
                self.stdout.write(self.style.WARNING('AdvancedIndicator モデルが見つかりません。全銘柄を対象とします。'))
                stocks = list(stocks)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'優先度決定エラー: {e}。全銘柄を対象とします。'))
                stocks = list(stocks)
        else:
            stocks = list(stocks)
        
        if limit:
            stocks = stocks[:limit]
            self.stdout.write(f'制限モード: 最初の {limit} 銘柄を更新')
        
        total_count = len(stocks)
        
        self.stdout.write(f'\n高度指標一括更新開始: 対象 {total_count} 銘柄')
        self.stdout.write(f'遅延時間: {delay}秒')
        
        # バッチ処理実行
        batch_size = 10  # SQLiteの制限を考慮して小さくする
        success_count = 0
        error_count = 0
        
        for i in range(0, total_count, batch_size):
            batch_end = min(i + batch_size, total_count)
            batch = stocks[i:batch_end]
            
            self.stdout.write(f'\n--- バッチ {i//batch_size + 1} 開始 ({i+1}-{batch_end}/{total_count}) ---')
            
            batch_success = 0
            for stock in batch:
                try:
                    # Stockオブジェクトの場合とidの場合を処理
                    if hasattr(stock, 'code'):
                        stock_code = stock.code
                        stock_name = stock.name
                    else:
                        stock_code = stock.code
                        stock_name = stock.name
                    
                    self.stdout.write(f'処理中: {stock_code} - {stock_name}', ending='... ')
                    
                    success = AdvancedDataFetcher.fetch_advanced_indicators(stock_code)
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
            if batch_end < total_count:
                self.stdout.write('次のバッチまで5秒待機...')
                time.sleep(5)
        
        # 結果サマリー
        self.print_summary(start_time, total_count, success_count, error_count)
    
    def print_summary(self, start_time, total_count, success_count, error_count):
        """結果サマリーの表示"""
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('高度指標更新完了')
        self.stdout.write(f'実行時間: {duration/60:.1f}分 ({duration:.1f}秒)')
        self.stdout.write(f'対象銘柄数: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'成功: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'失敗: {error_count}'))
        
        processed_count = success_count + error_count
        if processed_count > 0:
            self.stdout.write(f'成功率: {success_count/processed_count*100:.1f}%')
        
        # 最新統計
        try:
            from stock.models import AdvancedIndicator
            total_advanced_data = AdvancedIndicator.objects.count()
            stocks_with_data = Stock.objects.filter(
                advanced_indicators__isnull=False
            ).distinct().count()
            total_stocks = Stock.objects.count()
            coverage = (stocks_with_data / total_stocks * 100) if total_stocks > 0 else 0
            
            self.stdout.write(f'\n最新統計:')
            self.stdout.write(f'  総高度指標レコード数: {total_advanced_data}')
            self.stdout.write(f'  高度指標データがある銘柄: {stocks_with_data}')
            self.stdout.write(f'  カバー率: {coverage:.1f}%')
        except ImportError:
            self.stdout.write('AdvancedIndicator モデルが見つかりません')
        except Exception as e:
            self.stdout.write(f'統計取得エラー: {e}')
        
        self.stdout.write('='*60)
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\n注意: 一部銘柄の更新に失敗しました。'
                    '\n原因として以下が考えられます：'
                    '\n- Yahoo Financeで財務データが公開されていない'
                    '\n- 上場廃止や統合された銘柄'
                    '\n- APIの一時的な制限'
                    '\n- 財務諸表の項目名が標準と異なる'
                    '\n\n対処法:'
                    '\n- --code オプションで個別銘柄を再試行'
                    '\n- --validate オプションで異常値を確認'
                    '\n- --missing-report オプションで欠損データを確認'
                )
            )

