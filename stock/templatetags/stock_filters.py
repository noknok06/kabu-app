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