# stock/alert_monitoring.py
from django.db import models
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from celery import shared_task
import json
from decimal import Decimal
from datetime import datetime, timedelta

class WatchList(models.Model):
    """ウォッチリスト"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    name = models.CharField(max_length=100, verbose_name="ウォッチリスト名")
    description = models.TextField(blank=True, verbose_name="説明")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"

class WatchListItem(models.Model):
    """ウォッチリスト項目"""
    watchlist = models.ForeignKey(WatchList, on_delete=models.CASCADE, related_name='items')
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE)
    note = models.TextField(blank=True, verbose_name="メモ")
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['watchlist', 'stock']

class AlertRule(models.Model):
    """アラートルール"""
    ALERT_TYPES = [
        ('price_above', '価格上昇'),
        ('price_below', '価格下落'),
        ('volume_spike', '出来高急増'),
        ('per_change', 'PER変化'),
        ('earnings_date', '決算発表日'),
        ('technical_signal', 'テクニカルシグナル'),
        ('news_keyword', 'ニュースキーワード'),
        ('insider_trading', 'インサイダー取引'),
        ('analyst_rating', 'アナリスト格付け'),
    ]
    
    FREQUENCY_CHOICES = [
        ('realtime', 'リアルタイム'),
        ('hourly', '1時間毎'),
        ('daily', '日次'),
        ('weekly', '週次'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alert_rules')
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, null=True, blank=True)
    watchlist = models.ForeignKey(WatchList, on_delete=models.CASCADE, null=True, blank=True)
    
    name = models.CharField(max_length=100, verbose_name="アラート名")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name="アラート種類")
    
    # 条件設定
    condition_data = models.JSONField(default=dict, verbose_name="条件データ")
    
    # 通知設定
    email_enabled = models.BooleanField(default=True, verbose_name="メール通知")
    app_notification = models.BooleanField(default=True, verbose_name="アプリ通知")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='realtime')
    
    # 状態管理
    is_active = models.BooleanField(default=True, verbose_name="有効")
    last_triggered = models.DateTimeField(null=True, blank=True, verbose_name="最終発火日時")
    trigger_count = models.IntegerField(default=0, verbose_name="発火回数")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"

class AlertLog(models.Model):
    """アラートログ"""
    SEVERITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '緊急'),
    ]
    
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='logs')
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE)
    
    message = models.TextField(verbose_name="アラートメッセージ")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    
    # 発火時のデータ
    trigger_data = models.JSONField(default=dict, verbose_name="発火時データ")
    
    # 通知状態
    email_sent = models.BooleanField(default=False, verbose_name="メール送信済み")
    read = models.BooleanField(default=False, verbose_name="既読")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class MarketAlert(models.Model):
    """市場全体アラート"""
    MARKET_ALERT_TYPES = [
        ('market_crash', '市場急落'),
        ('market_rally', '市場急騰'),
        ('sector_rotation', 'セクターローテーション'),
        ('volatility_spike', 'ボラティリティ急増'),
        ('unusual_volume', '異常出来高'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=MARKET_ALERT_TYPES)
    title = models.CharField(max_length=200, verbose_name="タイトル")
    description = models.TextField(verbose_name="説明")
    severity = models.CharField(max_length=10, choices=AlertLog.SEVERITY_CHOICES)
    
    # 影響データ
    affected_stocks = models.ManyToManyField('Stock', blank=True)
    market_data = models.JSONField(default=dict, verbose_name="市場データ")
    
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class AlertProcessor:
    """アラート処理エンジン"""
    
    @staticmethod
    def check_price_alerts():
        """価格アラートのチェック"""
        price_rules = AlertRule.objects.filter(
            is_active=True,
            alert_type__in=['price_above', 'price_below']
        ).select_related('stock', 'user')
        
        triggered_alerts = []
        
        for rule in price_rules:
            if not rule.stock:
                continue
            
            # 最新価格取得
            latest_indicator = rule.stock.indicators.order_by('-date').first()
            if not latest_indicator or not latest_indicator.price:
                continue
            
            current_price = latest_indicator.price
            target_price = Decimal(str(rule.condition_data.get('target_price', 0)))
            
            should_trigger = False
            
            if rule.alert_type == 'price_above' and current_price >= target_price:
                should_trigger = True
            elif rule.alert_type == 'price_below' and current_price <= target_price:
                should_trigger = True
            
            if should_trigger:
                # 重複チェック（同日内は1回のみ）
                today = timezone.now().date()
                if rule.last_triggered and rule.last_triggered.date() == today:
                    continue
                
                alert_log = AlertProcessor.create_alert_log(
                    rule=rule,
                    stock=rule.stock,
                    message=f"{rule.stock.name}の株価が{current_price}円になりました（目標: {target_price}円）",
                    trigger_data={
                        'current_price': float(current_price),
                        'target_price': float(target_price),
                        'timestamp': timezone.now().isoformat(),
                    }
                )
                
                triggered_alerts.append(alert_log)
                
                # 発火回数更新
                rule.last_triggered = timezone.now()
                rule.trigger_count += 1
                rule.save()
        
        return triggered_alerts
    
    @staticmethod
    def check_volume_alerts():
        """出来高アラートのチェック"""
        volume_rules = AlertRule.objects.filter(
            is_active=True,
            alert_type='volume_spike'
        ).select_related('stock', 'user')
        
        triggered_alerts = []
        
        for rule in volume_rules:
            if not rule.stock:
                continue
            
            # 出来高データ分析
            volume_analysis = AlertProcessor.analyze_volume_spike(rule.stock)
            
            if volume_analysis and volume_analysis['is_spike']:
                alert_log = AlertProcessor.create_alert_log(
                    rule=rule,
                    stock=rule.stock,
                    message=f"{rule.stock.name}で出来高急増を検知（通常の{volume_analysis['spike_ratio']:.1f}倍）",
                    trigger_data=volume_analysis,
                    severity='medium'
                )
                
                triggered_alerts.append(alert_log)
        
        return triggered_alerts
    
    @staticmethod
    def check_technical_alerts():
        """テクニカルアラートのチェック"""
        technical_rules = AlertRule.objects.filter(
            is_active=True,
            alert_type='technical_signal'
        ).select_related('stock', 'user')
        
        triggered_alerts = []
        
        for rule in technical_rules:
            if not rule.stock:
                continue
            
            # テクニカルシグナル分析
            signals = AlertProcessor.analyze_technical_signals(rule.stock)
            
            target_signals = rule.condition_data.get('target_signals', [])
            
            for signal in signals:
                if signal['type'] in target_signals:
                    alert_log = AlertProcessor.create_alert_log(
                        rule=rule,
                        stock=rule.stock,
                        message=f"{rule.stock.name}で{signal['reason']}を検知",
                        trigger_data=signal,
                        severity=signal.get('strength', 'medium')
                    )
                    
                    triggered_alerts.append(alert_log)
        
        return triggered_alerts
    
    @staticmethod
    def check_earnings_alerts():
        """決算アラートのチェック"""
        # 決算発表予定のチェック
        upcoming_earnings = AlertProcessor.get_upcoming_earnings()
        
        earnings_rules = AlertRule.objects.filter(
            is_active=True,
            alert_type='earnings_date'
        ).select_related('stock', 'user')
        
        triggered_alerts = []
        
        for rule in earnings_rules:
            days_ahead = rule.condition_data.get('days_ahead', 3)
            
            for earning in upcoming_earnings:
                if (earning['stock'] == rule.stock and 
                    earning['days_until'] <= days_ahead):
                    
                    alert_log = AlertProcessor.create_alert_log(
                        rule=rule,
                        stock=rule.stock,
                        message=f"{rule.stock.name}の決算発表が{earning['days_until']}日後に予定されています",
                        trigger_data=earning,
                        severity='low'
                    )
                    
                    triggered_alerts.append(alert_log)
        
        return triggered_alerts
    
    @staticmethod
    def create_alert_log(rule, stock, message, trigger_data=None, severity='medium'):
        """アラートログ作成"""
        alert_log = AlertLog.objects.create(
            rule=rule,
            stock=stock,
            message=message,
            severity=severity,
            trigger_data=trigger_data or {}
        )
        
        # 通知送信
        if rule.email_enabled:
            AlertProcessor.send_email_notification(rule.user, alert_log)
        
        if rule.app_notification:
            AlertProcessor.send_app_notification(rule.user, alert_log)
        
        return alert_log
    
    @staticmethod
    def send_email_notification(user, alert_log):
        """メール通知送信"""
        try:
            subject = f"株式アラート: {alert_log.stock.name}"
            message = f"""
{alert_log.message}

銘柄: {alert_log.stock.code} - {alert_log.stock.name}
重要度: {alert_log.get_severity_display()}
発生時刻: {alert_log.created_at.strftime('%Y年%m月%d日 %H:%M')}

詳細はアプリでご確認ください。
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email='noreply@stock-screening.com',
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            alert_log.email_sent = True
            alert_log.save()
            
        except Exception as e:
            print(f"メール送信エラー: {e}")
    
    @staticmethod
    def send_app_notification(user, alert_log):
        """アプリ内通知送信"""
        # WebSocket経由でリアルタイム通知
        # 実装例: Django Channels使用
        pass
    
    @staticmethod
    def analyze_volume_spike(stock):
        """出来高急増分析"""
        # 過去20日間の出来高データ取得
        recent_indicators = stock.indicators.order_by('-date')[:20]
        
        if len(recent_indicators) < 20:
            return None
        
        # 現在の出来高（仮想的に取得）
        current_volume = 1000000  # 実際はリアルタイムデータから取得
        
        # 平均出来高計算
        avg_volume = sum(1000000 for _ in recent_indicators) / len(recent_indicators)  # 仮想データ
        
        spike_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        return {
            'current_volume': current_volume,
            'avg_volume': avg_volume,
            'spike_ratio': spike_ratio,
            'is_spike': spike_ratio > 2.0,  # 2倍以上で急増判定
            'timestamp': timezone.now().isoformat(),
        }
    
    @staticmethod
    def analyze_technical_signals(stock):
        """テクニカルシグナル分析"""
        # テクニカル分析結果取得
        latest_technical = stock.technical_indicators.order_by('-date').first()
        
        if not latest_technical:
            return []
        
        signals = []
        
        # RSIシグナル
        if latest_technical.rsi:
            if latest_technical.rsi > 70:
                signals.append({
                    'type': 'rsi_overbought',
                    'reason': 'RSI過熱圏（70超）',
                    'strength': 'medium',
                    'value': float(latest_technical.rsi)
                })
            elif latest_technical.rsi < 30:
                signals.append({
                    'type': 'rsi_oversold',
                    'reason': 'RSI過売り圏（30以下）',
                    'strength': 'medium',
                    'value': float(latest_technical.rsi)
                })
        
        # 移動平均シグナル
        if (latest_technical.ma_5 and latest_technical.ma_25):
            if latest_technical.ma_5 > latest_technical.ma_25:
                # 前日データと比較してクロスを検知
                signals.append({
                    'type': 'golden_cross',
                    'reason': '短期移動平均が長期を上抜け',
                    'strength': 'high',
                })
        
        return signals
    
    @staticmethod
    def get_upcoming_earnings():
        """決算発表予定取得"""
        # 実際の実装では外部APIから決算予定を取得
        # ここではサンプルデータを返す
        from .models import Stock
        
        upcoming = []
        stocks = Stock.objects.all()[:10]  # サンプル
        
        for i, stock in enumerate(stocks):
            days_until = (i % 7) + 1  # 1-7日後のランダム
            upcoming.append({
                'stock': stock,
                'earnings_date': timezone.now().date() + timedelta(days=days_until),
                'days_until': days_until,
                'is_confirmed': True,
            })
        
        return upcoming

# Celeryタスク定義
@shared_task
def run_alert_monitoring():
    """定期アラート監視タスク"""
    try:
        # 各種アラートチェック実行
        price_alerts = AlertProcessor.check_price_alerts()
        volume_alerts = AlertProcessor.check_volume_alerts()
        technical_alerts = AlertProcessor.check_technical_alerts()
        earnings_alerts = AlertProcessor.check_earnings_alerts()
        
        total_alerts = len(price_alerts + volume_alerts + technical_alerts + earnings_alerts)
        
        print(f"アラート監視完了: {total_alerts}件のアラートを発火")
        return total_alerts
        
    except Exception as e:
        print(f"アラート監視エラー: {e}")
        return 0

@shared_task
def market_anomaly_detection():
    """市場異常検知タスク"""
    try:
        # 市場全体の異常検知
        anomalies = []
        
        # 急落検知
        market_drop = detect_market_drop()
        if market_drop:
            anomalies.append(market_drop)
        
        # セクターローテーション検知
        sector_rotation = detect_sector_rotation()
        if sector_rotation:
            anomalies.append(sector_rotation)
        
        # 市場アラート作成
        for anomaly in anomalies:
            MarketAlert.objects.create(**anomaly)
        
        return len(anomalies)
        
    except Exception as e:
        print(f"市場異常検知エラー: {e}")
        return 0

def detect_market_drop():
    """市場急落検知"""
    # 実装例: TOPIX等の指数データから急落を検知
    # ここではサンプル実装
    return None

def detect_sector_rotation():
    """セクターローテーション検知"""
    # 実装例: セクター別パフォーマンスから rotation を検知
    # ここではサンプル実装
    return None