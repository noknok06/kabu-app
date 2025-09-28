# stock/templatetags/stock_filters.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def intcomma(value):
    """整数を3桁区切りでフォーマット"""
    if value is None:
        return "-"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

@register.filter
def floatcomma(value, decimal_places=1):
    """小数点付き数値を3桁区切りでフォーマット"""
    if value is None:
        return "-"
    try:
        decimal_places = int(decimal_places)
        format_str = f"{{:,.{decimal_places}f}}"
        return format_str.format(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def percentage(value, decimal_places=1):
    """パーセンテージ表示"""
    if value is None:
        return "-"
    try:
        decimal_places = int(decimal_places)
        format_str = f"{{:.{decimal_places}f}}%"
        return format_str.format(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def growth_class(value):
    """成長率に応じたCSSクラスを返す"""
    if value is None:
        return "text-muted"
    try:
        val = float(value)
        if val > 5:
            return "text-success fw-bold"
        elif val > 0:
            return "text-success"
        elif val < -5:
            return "text-danger fw-bold"
        elif val < 0:
            return "text-danger"
        else:
            return "text-muted"
    except (ValueError, TypeError):
        return "text-muted"

@register.filter
def trend_icon(trend):
    """トレンドに応じたアイコンを返す"""
    trend_map = {
        'increasing': '<i class="fas fa-arrow-trend-up text-success"></i>',
        'decreasing': '<i class="fas fa-arrow-trend-down text-danger"></i>',
        'stable': '<i class="fas fa-minus text-muted"></i>',
        'flat': '<i class="fas fa-minus text-muted"></i>',
    }
    return trend_map.get(trend, '<i class="fas fa-question text-muted"></i>')

@register.filter
def safe_divide(value, divisor):
    """安全な除算"""
    try:
        if float(divisor) == 0:
            return None
        return float(value) / float(divisor)
    except (ValueError, TypeError, ZeroDivisionError):
        return None

@register.filter
def multiply(value, multiplier):
    """乗算"""
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return None

@register.filter
def format_large_number(value):
    """大きな数値を読みやすく表示（億、兆単位）"""
    if value is None:
        return "-"
    try:
        val = float(value)
        if abs(val) >= 1_000_000:  # 100万以上
            if abs(val) >= 100_000_000:  # 1億以上
                return f"{val/100_000_000:.1f}億"
            else:
                return f"{val/10_000:.0f}万"
        else:
            return f"{val:,.0f}"
    except (ValueError, TypeError):
        return value

@register.filter
def comparison_width(stock_value, industry_value):
    """比較バーの幅を計算"""
    try:
        if float(industry_value) == 0:
            return 100
        ratio = float(stock_value) / float(industry_value)
        # 最大200%、最小10%で制限
        return min(max(ratio * 100, 10), 200)
    except (ValueError, TypeError, ZeroDivisionError):
        return 100

@register.filter
def comparison_color(stock_value, industry_value):
    """比較結果に応じた色を返す"""
    try:
        ratio = float(stock_value) / float(industry_value)
        if ratio > 1.2:
            return "bg-warning"
        elif ratio > 0.8:
            return "bg-primary"
        else:
            return "bg-success"
    except (ValueError, TypeError, ZeroDivisionError):
        return "bg-secondary"

# stock/templatetags/__init__.py
# 空ファイル（必須）

@register.filter
def widthof(value):
    """銘柄数に応じたテーブル幅の計算"""
    try:
        count = int(value)
        if count == 2:
            return 40
        elif count == 3:
            return 26
        elif count == 4:
            return 20
        else:
            return 15
    except (ValueError, TypeError):
        return 15

@register.filter 
def stock_count_class(value):
    """銘柄数に応じたCSSクラス"""
    try:
        count = int(value)
        return f"stock-count-{count}"
    except (ValueError, TypeError):
        return "stock-count-default"

@register.filter
def color_by_index(index):
    """インデックスに応じた色を返す"""
    colors = ['#667eea', '#764ba2', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1', '#e83e8c']
    try:
        return colors[int(index) % len(colors)]
    except (ValueError, TypeError, IndexError):
        return '#667eea'

@register.filter
def metric_status(value, metric_type):
    """指標の状態を評価"""
    if value is None:
        return "unknown"
    
    try:
        val = float(value)
        
        if metric_type == 'per':
            if val < 10:
                return "excellent"
            elif val < 15:
                return "good"
            elif val < 25:
                return "average"
            else:
                return "poor"
        elif metric_type == 'pbr':
            if val < 1:
                return "excellent"
            elif val < 1.5:
                return "good"
            elif val < 3:
                return "average"
            else:
                return "poor"
        elif metric_type == 'roe':
            if val > 20:
                return "excellent"
            elif val > 15:
                return "good"
            elif val > 10:
                return "average"
            else:
                return "poor"
        elif metric_type == 'dividend':
            if val > 4:
                return "excellent"
            elif val > 2:
                return "good"
            elif val > 1:
                return "average"
            else:
                return "poor"
    except (ValueError, TypeError):
        pass
    
    return "unknown"

@register.filter
def score_class(score):
    """スコアに応じたCSSクラス"""
    try:
        val = float(score)
        if val >= 20:
            return "score-excellent"
        elif val >= 15:
            return "score-good"
        elif val >= 8:
            return "score-average"
        else:
            return "score-poor"
    except (ValueError, TypeError):
        return "score-poor"

# stock/templatetags/__init__.py
# 空ファイル（必須）