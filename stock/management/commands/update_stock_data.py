# stock/management/commands/update_stock_data.py
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from stock.models import Stock, Indicator, Financial, AdvancedIndicator
from stock.utils import StockDataFetcher
from stock.advanced_data_fetcher import AdvancedDataFetcher
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'プロフェッショナル版：株式データの一括更新'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            choices=['stocks', 'indicators', 'financials', 'advanced', 'all'],
            default='all',
            help='更新モード'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='処理銘柄数の上限'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制更新（既存データも上書き）'
        )
        
        parser.add_argument(
            '--specific-stocks',
            nargs='+',
            help='特定銘柄のみ更新（銘柄コードを指定）'
        )
        
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='API呼び出し間隔（秒）'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際の更新は行わず、処理内容のみ表示'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== プロフェッショナル株式データ更新ツール ===')
        )
        
        mode = options['mode']
        limit = options['limit']
        force = options['force']
        specific_stocks = options['specific_stocks']
        delay = options['delay']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('*** ドライランモード ***'))
        
        try:
            if mode in ['stocks', 'all']:
                self.update_stock_list(dry_run)
            
            if mode in ['indicators', 'all']:
                self.update_indicators(limit, force, specific_stocks, delay, dry_run)
            
            if mode in ['financials', 'all']:
                self.update_financials(limit, force, specific_stocks, delay, dry_run)
            
            if mode in ['advanced', 'all']:
                self.update_advanced_indicators(limit, force, specific_stocks, delay, dry_run)
            
            self.stdout.write(
                self.style.SUCCESS('データ更新が完了しました。')
            )
            
        except Exception as e:
            raise CommandError(f'データ更新中にエラーが発生しました: {e}')

    def update_stock_list(self, dry_run=False):
        """銘柄リスト更新"""
        self.stdout.write('1. 銘柄リスト更新開始...')
        
        if dry_run:
            self.stdout.write('   → JPXから銘柄リストを取得（ドライラン）')
            return
        
        try:
            created_count = StockDataFetcher.fetch_jpx_stock_list()
            self.stdout.write(
                self.style.SUCCESS(f'   → 新規銘柄: {created_count}件')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   → エラー: {e}')
            )

    def update_indicators(self, limit, force, specific_stocks, delay, dry_run):
        """基本指標更新"""
        self.stdout.write('2. 基本指標データ更新開始...')
        
        # 対象銘柄の選定
        if specific_stocks:
            target_stocks = Stock.objects.filter(code__in=specific_stocks)
        else:
            target_stocks = Stock.objects.all()[:limit]
        
        if dry_run:
            self.stdout.write(f'   → 対象銘柄: {target_stocks.count()}件（ドライラン）')
            return
        
        success_count = 0
        error_count = 0
        
        for i, stock in enumerate(target_stocks, 1):
            self.stdout.write(f'   処理中: {i}/{target_stocks.count()} - {stock.code}')
            
            try:
                success = StockDataFetcher.fetch_stock_indicators(stock.code)
                if success:
                    success_count += 1
                    self.stdout.write(f'     ✓ 成功')
                else:
                    error_count += 1
                    self.stdout.write(f'     ✗ 失敗')
                
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(f'     ✗ エラー: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'   → 成功: {success_count}件, 失敗: {error_count}件')
        )

    def update_financials(self, limit, force, specific_stocks, delay, dry_run):
        """財務データ更新"""
        self.stdout.write('3. 財務データ更新開始...')
        
        # 対象銘柄の選定
        if specific_stocks:
            target_stocks = Stock.objects.filter(code__in=specific_stocks)
        else:
            target_stocks = Stock.objects.all()[:limit]
        
        if dry_run:
            self.stdout.write(f'   → 対象銘柄: {target_stocks.count()}件（ドライラン）')
            return
        
        success_count = 0
        error_count = 0
        
        for i, stock in enumerate(target_stocks, 1):
            self.stdout.write(f'   処理中: {i}/{target_stocks.count()} - {stock.code}')
            
            try:
                success = StockDataFetcher.fetch_financial_data(stock.code)
                if success:
                    success_count += 1
                    self.stdout.write(f'     ✓ 成功')
                else:
                    error_count += 1
                    self.stdout.write(f'     ✗ 失敗')
                
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(f'     ✗ エラー: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'   → 成功: {success_count}件, 失敗: {error_count}件')
        )

    def update_advanced_indicators(self, limit, force, specific_stocks, delay, dry_run):
        """高度指標更新"""
        self.stdout.write('4. 高度指標データ更新開始...')
        
        # 対象銘柄の選定
        if specific_stocks:
            target_stocks = Stock.objects.filter(code__in=specific_stocks)
        else:
            target_stocks = Stock.objects.all()[:limit]
        
        if dry_run:
            self.stdout.write(f'   → 対象銘柄: {target_stocks.count()}件（ドライラン）')
            return
        
        success_count = 0
        error_count = 0
        
        for i, stock in enumerate(target_stocks, 1):
            self.stdout.write(f'   処理中: {i}/{target_stocks.count()} - {stock.code}')
            
            try:
                success = AdvancedDataFetcher.fetch_advanced_indicators(stock.code)
                if success:
                    success_count += 1
                    self.stdout.write(f'     ✓ 成功')
                else:
                    error_count += 1
                    self.stdout.write(f'     ✗ 失敗')
                
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(f'     ✗ エラー: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'   → 成功: {success_count}件, 失敗: {error_count}件')
        )


# stock/management/commands/calculate_scores.py
from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from stock.models import Stock, Indicator, Financial, AdvancedIndicator
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '全銘柄のスコア計算とランキング更新'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recalculate',
            action='store_true',
            help='全てのスコアを再計算'
        )

    def handle(self, *args, **options):
        self.stdout.write('=== 投資スコア計算開始 ===')
        
        recalculate = options['recalculate']
        
        # 対象銘柄取得
        stocks = Stock.objects.filter(is_active=True)
        total_count = stocks.count()
        
        self.stdout.write(f'対象銘柄数: {total_count}')
        
        scores_calculated = 0
        
        for i, stock in enumerate(stocks, 1):
            if i % 100 == 0:
                self.stdout.write(f'進捗: {i}/{total_count}')
            
            try:
                score_data = self.calculate_comprehensive_score(stock)
                if score_data:
                    # スコアをモデルに保存（実際の実装では専用モデルを作成）
                    self.save_score_data(stock, score_data)
                    scores_calculated += 1
                    
            except Exception as e:
                logger.error(f'スコア計算エラー {stock.code}: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'スコア計算完了: {scores_calculated}件')
        )

    def calculate_comprehensive_score(self, stock):
        """包括的投資スコア計算"""
        # 最新データ取得
        latest_indicator = stock.indicators.order_by('-date').first()
        latest_advanced = stock.advanced_indicators.order_by('-date').first()
        recent_financials = stock.financials.order_by('-year')[:5]
        
        if not latest_indicator:
            return None
        
        scores = {
            'valuation_score': 0,
            'profitability_score': 0,
            'growth_score': 0,
            'safety_score': 0,
            'quality_score': 0,
            'momentum_score': 0
        }
        
        # 1. バリュエーションスコア（0-20点）
        scores['valuation_score'] = self.calculate_valuation_score(latest_indicator)
        
        # 2. 収益性スコア（0-20点）
        if latest_advanced:
            scores['profitability_score'] = self.calculate_profitability_score(latest_advanced)
        
        # 3. 成長性スコア（0-20点）
        scores['growth_score'] = self.calculate_growth_score(recent_financials)
        
        # 4. 安全性スコア（0-20点）
        if latest_advanced:
            scores['safety_score'] = self.calculate_safety_score(latest_advanced)
        
        # 5. 品質スコア（0-10点）
        scores['quality_score'] = self.calculate_quality_score(stock, recent_financials)
        
        # 6. モメンタムスコア（0-10点）
        scores['momentum_score'] = self.calculate_momentum_score(stock)
        
        # 総合スコア
        total_score = sum(scores.values())
        scores['total_score'] = total_score
        
        # ランク付け（S, A, B, C, D）
        if total_score >= 80:
            rank = 'S'
        elif total_score >= 65:
            rank = 'A'
        elif total_score >= 50:
            rank = 'B'
        elif total_score >= 35:
            rank = 'C'
        else:
            rank = 'D'
        
        scores['rank'] = rank
        
        return scores

    def calculate_valuation_score(self, indicator):
        """バリュエーションスコア（0-20点）"""
        score = 0
        
        # PERスコア（0-10点）
        if indicator.per:
            per = float(indicator.per)
            if per < 5:
                score += 10
            elif per < 8:
                score += 8
            elif per < 12:
                score += 6
            elif per < 15:
                score += 4
            elif per < 20:
                score += 2
        
        # PBRスコア（0-10点）
        if indicator.pbr:
            pbr = float(indicator.pbr)
            if pbr < 0.7:
                score += 10
            elif pbr < 1.0:
                score += 8
            elif pbr < 1.5:
                score += 6
            elif pbr < 2.0:
                score += 4
            elif pbr < 3.0:
                score += 2
        
        return min(score, 20)

    def calculate_profitability_score(self, advanced):
        """収益性スコア（0-20点）"""
        score = 0
        
        # ROEスコア（0-8点）
        if advanced.roe:
            roe = float(advanced.roe)
            if roe > 25:
                score += 8
            elif roe > 20:
                score += 7
            elif roe > 15:
                score += 6
            elif roe > 10:
                score += 4
            elif roe > 5:
                score += 2
        
        # ROAスコア（0-6点）
        if advanced.roa:
            roa = float(advanced.roa)
            if roa > 15:
                score += 6
            elif roa > 10:
                score += 5
            elif roa > 7:
                score += 4
            elif roa > 5:
                score += 3
            elif roa > 2:
                score += 1
        
        # 営業利益率スコア（0-6点）
        if advanced.operating_margin:
            margin = float(advanced.operating_margin)
            if margin > 20:
                score += 6
            elif margin > 15:
                score += 5
            elif margin > 10:
                score += 4
            elif margin > 5:
                score += 2
            elif margin > 0:
                score += 1
        
        return min(score, 20)

    def calculate_growth_score(self, financials):
        """成長性スコア（0-20点）"""
        if len(financials) < 3:
            return 0
        
        score = 0
        
        try:
            # 売上高CAGR（3年）（0-10点）
            revenue_values = [f.revenue for f in financials if f.revenue]
            if len(revenue_values) >= 3:
                revenue_cagr = self.calculate_cagr(revenue_values, 3)
                if revenue_cagr:
                    if revenue_cagr > 20:
                        score += 10
                    elif revenue_cagr > 15:
                        score += 8
                    elif revenue_cagr > 10:
                        score += 6
                    elif revenue_cagr > 5:
                        score += 4
                    elif revenue_cagr > 0:
                        score += 2
            
            # 純利益CAGR（3年）（0-10点）
            profit_values = [f.net_income for f in financials if f.net_income and f.net_income > 0]
            if len(profit_values) >= 3:
                profit_cagr = self.calculate_cagr(profit_values, 3)
                if profit_cagr:
                    if profit_cagr > 25:
                        score += 10
                    elif profit_cagr > 20:
                        score += 8
                    elif profit_cagr > 15:
                        score += 6
                    elif profit_cagr > 10:
                        score += 4
                    elif profit_cagr > 5:
                        score += 2
        
        except Exception as e:
            logger.error(f'成長性スコア計算エラー: {e}')
        
        return min(score, 20)

    def calculate_safety_score(self, advanced):
        """安全性スコア（0-20点）"""
        score = 0
        
        # 自己資本比率スコア（0-8点）
        if advanced.equity_ratio:
            ratio = float(advanced.equity_ratio)
            if ratio > 80:
                score += 8
            elif ratio > 60:
                score += 6
            elif ratio > 40:
                score += 4
            elif ratio > 30:
                score += 2
        
        # 流動比率スコア（0-6点）
        if advanced.current_ratio:
            ratio = float(advanced.current_ratio)
            if ratio > 3.0:
                score += 6
            elif ratio > 2.0:
                score += 5
            elif ratio > 1.5:
                score += 4
            elif ratio > 1.2:
                score += 2
            elif ratio > 1.0:
                score += 1
        
        # D/Eレシオスコア（0-6点）
        if advanced.debt_equity_ratio is not None:
            ratio = float(advanced.debt_equity_ratio)
            if ratio < 0.1:
                score += 6
            elif ratio < 0.3:
                score += 5
            elif ratio < 0.5:
                score += 4
            elif ratio < 1.0:
                score += 2
            elif ratio < 2.0:
                score += 1
        
        return min(score, 20)

    def calculate_quality_score(self, stock, financials):
        """品質スコア（0-10点）"""
        score = 0
        
        # 連続増益年数（0-5点）
        consecutive_years = self.count_consecutive_profit_years(financials)
        if consecutive_years >= 10:
            score += 5
        elif consecutive_years >= 5:
            score += 4
        elif consecutive_years >= 3:
            score += 3
        elif consecutive_years >= 2:
            score += 2
        elif consecutive_years >= 1:
            score += 1
        
        # 利益の安定性（0-3点）
        if len(financials) >= 5:
            profit_stability = self.calculate_profit_stability(financials)
            if profit_stability > 0.8:
                score += 3
            elif profit_stability > 0.6:
                score += 2
            elif profit_stability > 0.4:
                score += 1
        
        # データ品質（0-2点）
        if stock.data_quality_score > 80:
            score += 2
        elif stock.data_quality_score > 60:
            score += 1
        
        return min(score, 10)

    def calculate_momentum_score(self, stock):
        """モメンタムスコア（0-10点）"""
        # 実際の実装では株価のモメンタム、出来高、テクニカル指標を使用
        # ここではプレースホルダー
        return 5

    def calculate_cagr(self, values, years):
        """年平均成長率計算"""
        if len(values) < 2:
            return None
        
        try:
            start_value = float(values[-1])
            end_value = float(values[0])
            
            if start_value <= 0:
                return None
            
            cagr = (pow(end_value / start_value, 1/years) - 1) * 100
            return cagr
        except (ValueError, ZeroDivisionError):
            return None

    def count_consecutive_profit_years(self, financials):
        """連続増益年数計算"""
        if len(financials) < 2:
            return 0
        
        consecutive = 0
        for i in range(len(financials) - 1):
            current = financials[i]
            previous = financials[i + 1]
            
            if (current.net_income and previous.net_income and 
                current.net_income > previous.net_income):
                consecutive += 1
            else:
                break
        
        return consecutive

    def calculate_profit_stability(self, financials):
        """利益安定性計算"""
        profit_values = [float(f.net_income) for f in financials if f.net_income]
        if len(profit_values) < 3:
            return 0
        
        # 変動係数の逆数を安定性スコアとする
        import statistics
        try:
            mean_profit = statistics.mean(profit_values)
            if mean_profit <= 0:
                return 0
            
            stdev_profit = statistics.stdev(profit_values)
            cv = stdev_profit / mean_profit  # 変動係数
            stability = 1 / (1 + cv)  # 0-1の範囲に正規化
            return stability
        except:
            return 0

    def save_score_data(self, stock, score_data):
        """スコアデータ保存"""
        # 実際の実装では専用のモデルに保存
        # ここではサンプル実装
        pass


# stock/management/commands/update_industry_benchmarks.py
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from django.utils import timezone
from stock.models import Stock, Indicator, AdvancedIndicator, IndustryBenchmark

class Command(BaseCommand):
    help = '業界ベンチマークデータの更新'

    def handle(self, *args, **options):
        self.stdout.write('=== 業界ベンチマーク更新開始 ===')
        
        today = timezone.now().date()
        
        # 業種別に処理
        sectors = Stock.objects.values_list('sector', flat=True).distinct()
        sectors = [s for s in sectors if s]  # 空文字列を除外
        
        updated_count = 0
        
        for sector in sectors:
            try:
                benchmark_data = self.calculate_sector_benchmark(sector, today)
                if benchmark_data:
                    IndustryBenchmark.objects.update_or_create(
                        sector=sector,
                        date=today,
                        defaults=benchmark_data
                    )
                    updated_count += 1
                    self.stdout.write(f'  ✓ {sector}')
                
            except Exception as e:
                self.stdout.write(f'  ✗ {sector}: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'業界ベンチマーク更新完了: {updated_count}業種')
        )

    def calculate_sector_benchmark(self, sector, date):
        """業種別ベンチマーク計算"""
        # 同業種の銘柄を取得
        sector_stocks = Stock.objects.filter(sector=sector)
        
        # 最新の指標データを集計
        latest_indicators = Indicator.objects.filter(
            stock__in=sector_stocks,
            date__gte=date - timezone.timedelta(days=30)
        )
        
        latest_advanced = AdvancedIndicator.objects.filter(
            stock__in=sector_stocks,
            date__gte=date - timezone.timedelta(days=30)
        )
        
        if not latest_indicators.exists():
            return None
        
        # 基本統計の計算
        basic_stats = latest_indicators.aggregate(
            avg_per=Avg('per'),
            avg_pbr=Avg('pbr'),
            avg_dividend_yield=Avg('dividend_yield')
        )
        
        advanced_stats = latest_advanced.aggregate(
            avg_roe=Avg('roe'),
            avg_roa=Avg('roa'),
            avg_debt_ratio=Avg('debt_equity_ratio')
        )
        
        return {
            'avg_per': basic_stats['avg_per'],
            'avg_pbr': basic_stats['avg_pbr'],
            'avg_roe': advanced_stats['avg_roe'],
            'avg_roa': advanced_stats['avg_roa'],
            'avg_dividend_yield': basic_stats['avg_dividend_yield'],
            'avg_debt_ratio': advanced_stats['avg_debt_ratio'],
            'sample_count': latest_indicators.count()
        }


# stock/management/__init__.py
# 空ファイル（必須）

# stock/management/commands/__init__.py  
# 空ファイル（必須）