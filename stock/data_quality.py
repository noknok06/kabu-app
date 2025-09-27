# stock/data_quality.py
from django.db import models
from django.core.mail import send_mail
from decimal import Decimal
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataQualityRule(models.Model):
    """データ品質ルール"""
    RULE_TYPES = [
        ('range_check', '範囲チェック'),
        ('logical_check', '論理チェック'),
        ('consistency_check', '整合性チェック'),
        ('completeness_check', '完全性チェック'),
        ('freshness_check', '鮮度チェック'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="ルール名")
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES, verbose_name="ルールタイプ")
    description = models.TextField(verbose_name="説明")
    
    # ルール設定
    target_fields = models.JSONField(default=list, verbose_name="対象フィールド")
    rule_config = models.JSONField(default=dict, verbose_name="ルール設定")
    
    # アクション設定
    severity = models.CharField(
        max_length=10,
        choices=[('low', '低'), ('medium', '中'), ('high', '高'), ('critical', '緊急')],
        default='medium',
        verbose_name="重要度"
    )
    auto_fix = models.BooleanField(default=False, verbose_name="自動修正")
    notify_admin = models.BooleanField(default=True, verbose_name="管理者通知")
    
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class DataQualityIssue(models.Model):
    """データ品質問題"""
    rule = models.ForeignKey(DataQualityRule, on_delete=models.CASCADE, related_name='issues')
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, related_name='quality_issues')
    
    # 問題詳細
    field_name = models.CharField(max_length=50, verbose_name="問題フィールド")
    current_value = models.TextField(verbose_name="現在値")
    expected_value = models.TextField(null=True, blank=True, verbose_name="期待値")
    
    # 問題情報
    issue_description = models.TextField(verbose_name="問題説明")
    severity = models.CharField(max_length=10, verbose_name="重要度")
    
    # 対応状況
    status = models.CharField(
        max_length=20,
        choices=[
            ('open', '未対応'),
            ('investigating', '調査中'),
            ('fixed', '修正済み'),
            ('ignored', '無視'),
            ('false_positive', '誤検知'),
        ],
        default='open',
        verbose_name="ステータス"
    )
    
    # 修正情報
    fixed_value = models.TextField(null=True, blank=True, verbose_name="修正値")
    fix_method = models.CharField(
        max_length=50,
        null=True, blank=True,
        choices=[
            ('auto', '自動修正'),
            ('manual', '手動修正'),
            ('external_source', '外部ソース'),
            ('calculation', '再計算'),
        ],
        verbose_name="修正方法"
    )
    
    detected_at = models.DateTimeField(auto_now_add=True, verbose_name="検知日時")
    fixed_at = models.DateTimeField(null=True, blank=True, verbose_name="修正日時")
    
    class Meta:
        ordering = ['-detected_at']

class DataQualityManager:
    """データ品質管理エンジン"""
    
    @staticmethod
    def run_quality_checks(stock_codes=None):
        """品質チェック実行"""
        from .models import Stock, AdvancedIndicator
        
        if stock_codes:
            stocks = Stock.objects.filter(code__in=stock_codes)
        else:
            stocks = Stock.objects.all()
        
        # アクティブなルールを取得
        active_rules = DataQualityRule.objects.filter(is_active=True)
        
        total_issues = 0
        
        for rule in active_rules:
            logger.info(f"品質チェック実行: {rule.name}")
            
            if rule.rule_type == 'range_check':
                issues = DataQualityManager.check_value_ranges(stocks, rule)
            elif rule.rule_type == 'logical_check':
                issues = DataQualityManager.check_logical_consistency(stocks, rule)
            elif rule.rule_type == 'consistency_check':
                issues = DataQualityManager.check_data_consistency(stocks, rule)
            elif rule.rule_type == 'completeness_check':
                issues = DataQualityManager.check_data_completeness(stocks, rule)
            elif rule.rule_type == 'freshness_check':
                issues = DataQualityManager.check_data_freshness(stocks, rule)
            else:
                continue
            
            total_issues += len(issues)
            
            # 問題の記録
            for issue_data in issues:
                DataQualityManager.record_issue(rule, issue_data)
        
        logger.info(f"品質チェック完了: {total_issues}件の問題を検出")
        return total_issues
    
    @staticmethod
    def check_value_ranges(stocks, rule):
        """値範囲チェック"""
        issues = []
        config = rule.rule_config
        
        for stock in stocks:
            latest_indicator = stock.advanced_indicators.order_by('-date').first()
            if not latest_indicator:
                continue
            
            for field_name in rule.target_fields:
                value = getattr(latest_indicator, field_name, None)
                if value is None:
                    continue
                
                value_float = float(value)
                min_val = config.get(f'{field_name}_min')
                max_val = config.get(f'{field_name}_max')
                
                issue_found = False
                
                if min_val is not None and value_float < min_val:
                    issues.append({
                        'stock': stock,
                        'field_name': field_name,
                        'current_value': str(value),
                        'issue_description': f'{field_name}が最小値{min_val}を下回っています',
                        'severity': rule.severity,
                    })
                    issue_found = True
                
                if max_val is not None and value_float > max_val:
                    issues.append({
                        'stock': stock,
                        'field_name': field_name,
                        'current_value': str(value),
                        'issue_description': f'{field_name}が最大値{max_val}を超えています',
                        'severity': rule.severity,
                    })
                    issue_found = True
        
        return issues
    
    @staticmethod
    def check_logical_consistency(stocks, rule):
        """論理整合性チェック"""
        issues = []
        config = rule.rule_config
        
        for stock in stocks:
            latest_indicator = stock.advanced_indicators.order_by('-date').first()
            if not latest_indicator:
                continue
            
            # ROE vs ROA の関係チェック
            if 'roe_roa_consistency' in config:
                roe = getattr(latest_indicator, 'roe', None)
                roa = getattr(latest_indicator, 'roa', None)
                
                if roe and roa:
                    roe_float = float(roe)
                    roa_float = float(roa)
                    
                    # 通常、ROE >= ROA であるべき
                    if roe_float < roa_float - 5:  # 5%の余裕
                        issues.append({
                            'stock': stock,
                            'field_name': 'roe_roa',
                            'current_value': f'ROE:{roe}, ROA:{roa}',
                            'issue_description': 'ROEがROAを大幅に下回っています（論理的に異常）',
                            'severity': rule.severity,
                        })
            
            # 流動比率と当座比率の関係
            if 'liquidity_consistency' in config:
                current_ratio = getattr(latest_indicator, 'current_ratio', None)
                # 当座比率は別途取得が必要（実装時に追加）
            
            # PERとEPSの整合性
            if 'per_eps_consistency' in config:
                # 株価、PER、EPSの整合性チェック
                pass
        
        return issues
    
    @staticmethod
    def check_data_consistency(stocks, rule):
        """データ整合性チェック"""
        issues = []
        config = rule.rule_config
        
        for stock in stocks:
            # 複数データソース間の整合性
            indicators = stock.indicators.order_by('-date')[:1]
            advanced_indicators = stock.advanced_indicators.order_by('-date')[:1]
            
            if not indicators or not advanced_indicators:
                continue
            
            indicator = indicators[0]
            advanced = advanced_indicators[0]
            
            # PERの整合性チェック
            if 'per_consistency' in config:
                basic_per = indicator.per
                # 高度指標から計算したPERと比較
                if basic_per and abs(float(basic_per) - 0) > config.get('per_tolerance', 10):
                    # 実装時に詳細な比較ロジックを追加
                    pass
        
        return issues
    
    @staticmethod
    def check_data_completeness(stocks, rule):
        """データ完全性チェック"""
        issues = []
        config = rule.rule_config
        
        required_fields = config.get('required_fields', [])
        
        for stock in stocks:
            latest_indicator = stock.advanced_indicators.order_by('-date').first()
            if not latest_indicator:
                issues.append({
                    'stock': stock,
                    'field_name': 'all',
                    'current_value': 'None',
                    'issue_description': '高度指標データが存在しません',
                    'severity': rule.severity,
                })
                continue
            
            # 必須フィールドの存在チェック
            for field_name in required_fields:
                value = getattr(latest_indicator, field_name, None)
                if value is None:
                    issues.append({
                        'stock': stock,
                        'field_name': field_name,
                        'current_value': 'None',
                        'issue_description': f'必須フィールド {field_name} が欠損しています',
                        'severity': rule.severity,
                    })
        
        return issues
    
    @staticmethod
    def check_data_freshness(stocks, rule):
        """データ鮮度チェック"""
        issues = []
        config = rule.rule_config
        
        max_age_days = config.get('max_age_days', 30)
        cutoff_date = datetime.now().date() - timedelta(days=max_age_days)
        
        for stock in stocks:
            latest_indicator = stock.advanced_indicators.order_by('-date').first()
            
            if not latest_indicator:
                issues.append({
                    'stock': stock,
                    'field_name': 'date',
                    'current_value': 'None',
                    'issue_description': '高度指標データが存在しません',
                    'severity': rule.severity,
                })
            elif latest_indicator.date < cutoff_date:
                days_old = (datetime.now().date() - latest_indicator.date).days
                issues.append({
                    'stock': stock,
                    'field_name': 'date',
                    'current_value': str(latest_indicator.date),
                    'issue_description': f'データが古すぎます（{days_old}日前）',
                    'severity': rule.severity,
                })
        
        return issues
    
    @staticmethod
    def record_issue(rule, issue_data):
        """問題の記録"""
        # 既存の同じ問題があるかチェック
        existing_issue = DataQualityIssue.objects.filter(
            rule=rule,
            stock=issue_data['stock'],
            field_name=issue_data['field_name'],
            status__in=['open', 'investigating']
        ).first()
        
        if existing_issue:
            # 既存問題の更新
            existing_issue.current_value = issue_data['current_value']
            existing_issue.issue_description = issue_data['issue_description']
            existing_issue.save()
        else:
            # 新しい問題の作成
            DataQualityIssue.objects.create(
                rule=rule,
                stock=issue_data['stock'],
                field_name=issue_data['field_name'],
                current_value=issue_data['current_value'],
                issue_description=issue_data['issue_description'],
                severity=issue_data['severity'],
            )
            
            # 通知送信
            if rule.notify_admin:
                DataQualityManager.send_quality_alert(rule, issue_data)
    
    @staticmethod
    def send_quality_alert(rule, issue_data):
        """品質アラート送信"""
        try:
            subject = f"データ品質アラート: {rule.name}"
            message = f"""
データ品質問題が検出されました。

ルール: {rule.name}
銘柄: {issue_data['stock'].code} - {issue_data['stock'].name}
フィールド: {issue_data['field_name']}
現在値: {issue_data['current_value']}
問題: {issue_data['issue_description']}
重要度: {issue_data['severity']}

検出時刻: {datetime.now()}
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email='system@stock-screening.com',
                recipient_list=['admin@example.com'],  # 設定から取得
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"品質アラート送信エラー: {e}")
    
    @staticmethod
    def auto_fix_issues():
        """自動修正の実行"""
        auto_fixable_issues = DataQualityIssue.objects.filter(
            rule__auto_fix=True,
            status='open'
        )
        
        fixed_count = 0
        
        for issue in auto_fixable_issues:
            try:
                if DataQualityManager.apply_auto_fix(issue):
                    issue.status = 'fixed'
                    issue.fix_method = 'auto'
                    issue.fixed_at = datetime.now()
                    issue.save()
                    fixed_count += 1
            except Exception as e:
                logger.error(f"自動修正エラー {issue.id}: {e}")
        
        logger.info(f"自動修正完了: {fixed_count}件")
        return fixed_count
    
    @staticmethod
    def apply_auto_fix(issue):
        """個別問題の自動修正"""
        rule = issue.rule
        
        if rule.rule_type == 'range_check':
            return DataQualityManager.fix_range_issue(issue)
        elif rule.rule_type == 'freshness_check':
            return DataQualityManager.fix_freshness_issue(issue)
        
        return False
    
    @staticmethod
    def fix_range_issue(issue):
        """範囲問題の修正"""
        # 異常値を業界平均で置換
        from .industry_comparison import IndustryAnalyzer
        
        try:
            stock = issue.stock
            field_name = issue.field_name
            
            # 業界平均取得
            sector_average = IndustryAnalyzer.get_sector_average(
                stock.sector, field_name
            )
            
            if sector_average:
                # 最新の高度指標を更新
                latest_indicator = stock.advanced_indicators.order_by('-date').first()
                if latest_indicator:
                    setattr(latest_indicator, field_name, Decimal(str(sector_average)))
                    latest_indicator.save()
                    
                    issue.fixed_value = str(sector_average)
                    return True
            
        except Exception as e:
            logger.error(f"範囲問題修正エラー: {e}")
        
        return False
    
    @staticmethod
    def fix_freshness_issue(issue):
        """鮮度問題の修正"""
        # データの再取得
        from .advanced_data_fetcher import AdvancedDataFetcher
        
        try:
            stock = issue.stock
            success = AdvancedDataFetcher.fetch_advanced_indicators(stock.code)
            
            if success:
                issue.fixed_value = f"データ再取得成功: {datetime.now().date()}"
                return True
            
        except Exception as e:
            logger.error(f"鮮度問題修正エラー: {e}")
        
        return False
    
    @staticmethod
    def generate_quality_report():
        """品質レポート生成"""
        issues = DataQualityIssue.objects.all()
        
        # 統計計算
        total_issues = issues.count()
        open_issues = issues.filter(status='open').count()
        critical_issues = issues.filter(severity='critical', status='open').count()
        
        # 規則別集計
        rule_stats = {}
        for rule in DataQualityRule.objects.filter(is_active=True):
            rule_issues = issues.filter(rule=rule)
            rule_stats[rule.name] = {
                'total': rule_issues.count(),
                'open': rule_issues.filter(status='open').count(),
                'fixed': rule_issues.filter(status='fixed').count(),
            }
        
        # フィールド別集計
        field_stats = {}
        for issue in issues.filter(status='open'):
            field = issue.field_name
            if field not in field_stats:
                field_stats[field] = 0
            field_stats[field] += 1
        
        report = {
            'summary': {
                'total_issues': total_issues,
                'open_issues': open_issues,
                'critical_issues': critical_issues,
                'fix_rate': ((total_issues - open_issues) / total_issues * 100) if total_issues > 0 else 0,
            },
            'by_rule': rule_stats,
            'by_field': field_stats,
            'recent_issues': list(issues.filter(
                detected_at__gte=datetime.now() - timedelta(days=7)
            ).values('stock__code', 'field_name', 'issue_description', 'severity')),
        }
        
        return report

# 品質ルール設定の例
def setup_default_quality_rules():
    """デフォルト品質ルールの設定"""
    
    # ROE範囲チェック
    DataQualityRule.objects.get_or_create(
        name='ROE範囲チェック',
        defaults={
            'rule_type': 'range_check',
            'description': 'ROEが-100%から200%の範囲内であることをチェック',
            'target_fields': ['roe'],
            'rule_config': {
                'roe_min': -100,
                'roe_max': 200,
            },
            'severity': 'medium',
            'auto_fix': True,
        }
    )
    
    # データ鮮度チェック
    DataQualityRule.objects.get_or_create(
        name='データ鮮度チェック',
        defaults={
            'rule_type': 'freshness_check',
            'description': '高度指標データが30日以内に更新されていることをチェック',
            'target_fields': ['date'],
            'rule_config': {
                'max_age_days': 30,
            },
            'severity': 'high',
            'auto_fix': True,
        }
    )
    
    # 必須フィールド完全性チェック
    DataQualityRule.objects.get_or_create(
        name='必須フィールドチェック',
        defaults={
            'rule_type': 'completeness_check',
            'description': '重要な財務指標が欠損していないことをチェック',
            'target_fields': ['roe', 'roa', 'debt_equity_ratio'],
            'rule_config': {
                'required_fields': ['roe', 'roa', 'debt_equity_ratio'],
            },
            'severity': 'medium',
            'auto_fix': False,
        }
    )