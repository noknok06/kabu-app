# stock/management/commands/analyze_advanced_metrics.py
from django.core.management.base import BaseCommand
from stock.models import Stock, AdvancedIndicator
from django.db.models import Avg, Max, Min, Count
import pandas as pd

class Command(BaseCommand):
    help = '高度指標の分析・統計レポート生成'
    
    def add_arguments(self, parser):
        parser.add_argument('--sector', type=str, help='特定業界の分析')
        parser.add_argument('--export', type=str, help='CSVファイルにエクスポート')
        parser.add_argument('--top', type=int, default=10, help='トップN銘柄を表示')
        
    def handle(self, *args, **options):
        self.stdout.write('高度指標分析レポートを生成中...')
        
        # 最新データの統計
        latest_indicators = AdvancedIndicator.objects.order_by('stock', '-date').distinct('stock')
        
        if not latest_indicators.exists():
            self.stdout.write(self.style.ERROR('高度指標データがありません'))
            return
        
        # 基本統計
        self.generate_basic_statistics(latest_indicators)
        
        # 業界別分析
        if options['sector']:
            self.analyze_by_sector(options['sector'])
        else:
            self.analyze_all_sectors()
        
        # トップパフォーマー
        self.show_top_performers(latest_indicators, options['top'])
        
        # CSV出力
        if options['export']:
            self.export_to_csv(latest_indicators, options['export'])
    
    def generate_basic_statistics(self, indicators):
        """基本統計の生成"""
        self.stdout.write('\n=== 基本統計 ===')
        
        # 各指標の統計
        metrics = ['roe', 'roa', 'roic', 'debt_equity_ratio', 'current_ratio', 'psr', 'ev_ebitda']
        
        for metric in metrics:
            values = [getattr(ind, metric) for ind in indicators if getattr(ind, metric) is not None]
            
            if values:
                values = [float(v) for v in values]
                avg_val = sum(values) / len(values)
                max_val = max(values)
                min_val = min(values)
                
                self.stdout.write(f'{metric.upper()}:')
                self.stdout.write(f'  平均: {avg_val:.2f}')
                self.stdout.write(f'  最大: {max_val:.2f}')
                self.stdout.write(f'  最小: {min_val:.2f}')
                self.stdout.write(f'  サンプル数: {len(values)}')
                self.stdout.write('')
    
    def analyze_by_sector(self, sector):
        """業界別分析"""
        self.stdout.write(f'\n=== {sector} 業界分析 ===')
        
        sector_stocks = Stock.objects.filter(sector__icontains=sector)
        
        if not sector_stocks.exists():
            self.stdout.write(f'業界 "{sector}" の銘柄が見つかりません')
            return
        
        # 業界内の高度指標
        sector_indicators = AdvancedIndicator.objects.filter(
            stock__in=sector_stocks
        ).order_by('stock', '-date').distinct('stock')
        
        self.stdout.write(f'対象銘柄数: {sector_indicators.count()}')
        
        # 業界平均の計算
        metrics = ['roe', 'roa', 'roic', 'debt_equity_ratio', 'current_ratio']
        
        for metric in metrics:
            values = [getattr(ind, metric) for ind in sector_indicators if getattr(ind, metric) is not None]
            
            if values:
                values = [float(v) for v in values]
                avg_val = sum(values) / len(values)
                self.stdout.write(f'{metric.upper()} 業界平均: {avg_val:.2f}')
        
        # 業界内トップ企業
        self.stdout.write(f'\n{sector} 業界トップ企業 (ROE順):')
        
        top_companies = sorted(
            [(ind.stock, getattr(ind, 'roe')) for ind in sector_indicators if getattr(ind, 'roe') is not None],
            key=lambda x: float(x[1]) if x[1] else 0,
            reverse=True
        )[:5]
        
        for i, (stock, roe) in enumerate(top_companies, 1):
            self.stdout.write(f'  {i}. {stock.code} - {stock.name}: ROE {roe}%')
    
    def analyze_all_sectors(self):
        """全業界の分析"""
        self.stdout.write('\n=== 業界別ROE平均 ===')
        
        sectors = Stock.objects.values_list('sector', flat=True).distinct()
        sector_roe = []
        
        for sector in sectors:
            if not sector:
                continue
            
            sector_stocks = Stock.objects.filter(sector=sector)
            sector_indicators = AdvancedIndicator.objects.filter(
                stock__in=sector_stocks,
                roe__isnull=False
            ).order_by('stock', '-date').distinct('stock')
            
            if sector_indicators.exists():
                avg_roe = sector_indicators.aggregate(Avg('roe'))['roe__avg']
                if avg_roe:
                    sector_roe.append((sector, float(avg_roe), sector_indicators.count()))
        
        # ROE順にソート
        sector_roe.sort(key=lambda x: x[1], reverse=True)
        
        for sector, avg_roe, count in sector_roe[:15]:
            self.stdout.write(f'{sector}: {avg_roe:.2f}% (サンプル数: {count})')
    
    def show_top_performers(self, indicators, top_n):
        """トップパフォーマーの表示"""
        self.stdout.write(f'\n=== トップ{top_n}銘柄 ===')
        
        # ROE順
        roe_rankings = sorted(
            [(ind.stock, getattr(ind, 'roe')) for ind in indicators if getattr(ind, 'roe') is not None],
            key=lambda x: float(x[1]) if x[1] else 0,
            reverse=True
        )[:top_n]
        
        self.stdout.write('\nROEトップ銘柄:')
        for i, (stock, roe) in enumerate(roe_rankings, 1):
            self.stdout.write(f'  {i}. {stock.code} - {stock.name}: {roe}%')
        
        # ROIC順
        roic_rankings = sorted(
            [(ind.stock, getattr(ind, 'roic')) for ind in indicators if getattr(ind, 'roic') is not None],
            key=lambda x: float(x[1]) if x[1] else 0,
            reverse=True
        )[:top_n]
        
        self.stdout.write('\nROICトップ銘柄:')
        for i, (stock, roic) in enumerate(roic_rankings, 1):
            self.stdout.write(f'  {i}. {stock.code} - {stock.name}: {roic}%')
    
    def export_to_csv(self, indicators, filename):
        """CSV出力"""
        self.stdout.write(f'\nCSVファイル出力中: {filename}')
        
        data = []
        for ind in indicators:
            data.append({
                'code': ind.stock.code,
                'name': ind.stock.name,
                'sector': ind.stock.sector,
                'roe': float(ind.roe) if ind.roe else None,
                'roa': float(ind.roa) if ind.roa else None,
                'roic': float(ind.roic) if ind.roic else None,
                'debt_equity_ratio': float(ind.debt_equity_ratio) if ind.debt_equity_ratio else None,
                'current_ratio': float(ind.current_ratio) if ind.current_ratio else None,
                'psr': float(ind.psr) if ind.psr else None,
                'ev_ebitda': float(ind.ev_ebitda) if ind.ev_ebitda else None,
                'date': ind.date,
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        self.stdout.write(self.style.SUCCESS(f'✓ CSVファイル出力完了: {filename}'))
        self.stdout.write(f'  出力件数: {len(data)}件')

# stock/management/commands/benchmark_advanced_data.py
from django.core.management.base import BaseCommand
from stock.models import Stock, AdvancedIndicator
from stock.industry_comparison import IndustryAnalyzer
import time

class Command(BaseCommand):
    help = '高度指標を使った業界ベンチマーク更新'
    
    def handle(self, *args, **options):
        self.stdout.write('高度指標ベースの業界ベンチマーク計算を開始...')
        
        # 業界別ベンチマーク計算
        sectors = Stock.objects.values_list('sector', flat=True).distinct()
        
        for sector in sectors:
            if not sector:
                continue
            
            self.stdout.write(f'処理中: {sector}', ending='... ')
            
            try:
                # 業界内の最新高度指標を取得
                sector_stocks = Stock.objects.filter(sector=sector)
                latest_indicators = AdvancedIndicator.objects.filter(
                    stock__in=sector_stocks
                ).order_by('stock', '-date').distinct('stock')
                
                if latest_indicators.count() >= 3:  # 最低3社必要
                    # 業界平均を計算
                    self.calculate_sector_benchmarks(sector, latest_indicators)
                    self.stdout.write(self.style.SUCCESS('✓'))
                else:
                    self.stdout.write(self.style.WARNING('スキップ（データ不足）'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'エラー: {e}'))
        
        self.stdout.write('\n業界ベンチマーク計算完了')
    
    def calculate_sector_benchmarks(self, sector, indicators):
        """業界ベンチマークの計算"""
        from stock.models import IndustryBenchmark
        from django.db.models import Avg
        
        # 平均値計算
        averages = {}
        metrics = ['roe', 'roa', 'roic', 'debt_equity_ratio', 'current_ratio', 'psr']
        
        for metric in metrics:
            values = [getattr(ind, metric) for ind in indicators if getattr(ind, metric) is not None]
            if values:
                averages[f'avg_{metric}'] = sum(float(v) for v in values) / len(values)
        
        # ベンチマーク更新
        benchmark, created = IndustryBenchmark.objects.update_or_create(
            sector=sector,
            sub_sector='',
            defaults={
                **averages,
                'sample_size': indicators.count(),
            }
        )
        
        return benchmark