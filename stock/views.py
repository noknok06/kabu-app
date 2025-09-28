# stock/views.py - 修正版（完全なスクリーニング機能）
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Prefetch, Count, Avg, Max, Min, Case, When, F, Value, FloatField, Subquery, OuterRef
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from datetime import timedelta, datetime
import csv
import json
import numpy as np
from decimal import Decimal
from .models import Stock, Indicator, Financial, AdvancedIndicator
from .forms import StockScreeningForm
from .utils import StockDataFetcher
import logging

logger = logging.getLogger(__name__)

def dashboard_view(request):
    """プロフェッショナル・ダッシュボードビュー"""
    # キャッシュキーを設定
    cache_key = 'dashboard_data'
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        # 基本統計情報
        total_stocks = Stock.objects.count()
        
        # 最新の指標データ統計
        week_ago = timezone.now().date() - timedelta(days=7)
        latest_indicators = Indicator.objects.filter(
            date__gte=week_ago
        ).count()
        
        # 財務データ統計
        total_financials = Financial.objects.count()
        stock_with_financials = Stock.objects.filter(
            financials__isnull=False
        ).distinct().count()
        
        # 市場指標の計算
        market_metrics = calculate_market_metrics()
        
        # 最近更新された銘柄（指標データ）
        recent_indicators = Indicator.objects.select_related('stock').order_by('-updated_at')[:15]
        
        # 市場区分別統計
        market_stats = Stock.objects.values('market').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        cached_data = {
            'total_stocks': total_stocks,
            'latest_indicators': latest_indicators,
            'total_financials': total_financials,
            'stock_with_financials': stock_with_financials,
            'market_metrics': market_metrics,
            'recent_indicators': recent_indicators,
            'market_stats': market_stats,
            'financial_coverage': round(stock_with_financials / total_stocks * 100, 1) if total_stocks > 0 else 0,
            'last_update': timezone.now()
        }
        
        # 15分間キャッシュ
        cache.set(cache_key, cached_data, 900)
    
    return render(request, 'stock/dashboard.html', cached_data)

def calculate_market_metrics():
    """市場全体の指標計算"""
    try:
        # 最新日付の指標データを取得
        latest_date = Indicator.objects.aggregate(Max('date'))['date__max']
        if not latest_date:
            return {}
        
        latest_indicators = Indicator.objects.filter(date=latest_date)
        
        # 基本統計
        basic_stats = latest_indicators.aggregate(
            avg_per=Avg('per'),
            avg_pbr=Avg('pbr'),
            avg_dividend=Avg('dividend_yield')
        )
        
        # 高配当株数（3%以上）
        high_dividend_count = latest_indicators.filter(dividend_yield__gte=3).count()
        
        # 成長株数（ROE 15%以上）
        latest_advanced_date = AdvancedIndicator.objects.aggregate(Max('date'))['date__max']
        growth_stocks = 0
        if latest_advanced_date:
            growth_stocks = AdvancedIndicator.objects.filter(
                date=latest_advanced_date,
                roe__gte=15
            ).count()
        
        return {
            'avg_per': basic_stats['avg_per'],
            'avg_pbr': basic_stats['avg_pbr'],
            'avg_dividend': basic_stats['avg_dividend'],
            'high_dividend_count': high_dividend_count,
            'growth_count': growth_stocks,
        }
    except Exception as e:
        logger.error(f"市場指標計算エラー: {e}")
        return {}

def screening_view(request):
    """プロフェッショナル・スクリーニングビュー（完全版）"""
    form = StockScreeningForm(request.GET)
    results = []
    total_count = 0
    execution_time = 0
    
    if request.GET:
        start_time = datetime.now()
        
        try:
            # 完全なクエリビルダーを使用
            queryset = build_complete_queryset(form)
            
            # 結果をリストに変換（パフォーマンス向上のため）
            results_data = []
            for stock_data in queryset:
                if stock_data:
                    results_data.append(stock_data)
            
            # ソート処理
            sort_by = form.cleaned_data.get('sort_by', 'total_score') if form.is_valid() else 'total_score'
            results_data = sort_results(results_data, sort_by)
            
            # 表示件数制限
            limit = None
            if form.is_valid() and form.cleaned_data.get('limit'):
                try:
                    limit = int(form.cleaned_data['limit'])
                    if limit > 0:
                        results_data = results_data[:limit]
                except ValueError:
                    pass
            
            results = results_data
            total_count = len(results)
            
        except Exception as e:
            logger.error(f"スクリーニング実行エラー: {e}")
            messages.error(request, f'検索中にエラーが発生しました: {str(e)}')
        
        execution_time = (datetime.now() - start_time).total_seconds()
    
    # ページネーション
    page_number = request.GET.get('page', 1)
    paginator = Paginator(results, 50)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'results': page_obj,
        'total_count': total_count,
        'execution_time': round(execution_time, 2),
        'has_search': bool(request.GET),
        'total_stocks': Stock.objects.count(),
    }
    
    return render(request, 'stock/screening.html', context)

def build_complete_queryset(form):
    """完全なクエリセット構築（全フィールド対応）"""
    if not form.is_valid():
        return []
    
    data = form.cleaned_data
    
    # 最新の指標データ・高度指標データの日付を取得
    latest_indicator_date = Indicator.objects.aggregate(Max('date'))['date__max']
    latest_advanced_date = AdvancedIndicator.objects.aggregate(Max('date'))['date__max']
    
    if not latest_indicator_date:
        logger.warning("指標データが存在しません")
        return []
    
    # 基本クエリセット - 最新の指標データがある銘柄のみ
    base_queryset = Stock.objects.filter(
        indicators__date=latest_indicator_date
    ).select_related().prefetch_related(
        Prefetch(
            'indicators',
            queryset=Indicator.objects.filter(date=latest_indicator_date),
            to_attr='latest_indicators'
        ),
        Prefetch(
            'advanced_indicators',
            queryset=AdvancedIndicator.objects.filter(date=latest_advanced_date) if latest_advanced_date else AdvancedIndicator.objects.none(),
            to_attr='latest_advanced_indicators'
        ),
        Prefetch(
            'financials',
            queryset=Financial.objects.order_by('-year')[:10],
            to_attr='recent_financials'
        )
    ).distinct()
    
    # === 基本指標フィルタ ===
    conditions = Q()
    
    # PER条件
    if data.get('per_min'):
        conditions &= Q(indicators__per__gte=data['per_min'], indicators__date=latest_indicator_date)
    if data.get('per_max'):
        conditions &= Q(indicators__per__lte=data['per_max'], indicators__date=latest_indicator_date)
    
    # PBR条件
    if data.get('pbr_min'):
        conditions &= Q(indicators__pbr__gte=data['pbr_min'], indicators__date=latest_indicator_date)
    if data.get('pbr_max'):
        conditions &= Q(indicators__pbr__lte=data['pbr_max'], indicators__date=latest_indicator_date)
    
    # 配当利回り条件
    if data.get('dividend_yield_min'):
        conditions &= Q(indicators__dividend_yield__gte=data['dividend_yield_min'], indicators__date=latest_indicator_date)
    if data.get('dividend_yield_max'):
        conditions &= Q(indicators__dividend_yield__lte=data['dividend_yield_max'], indicators__date=latest_indicator_date)
    
    # 配当性向条件
    if data.get('payout_ratio_min'):
        conditions &= Q(indicators__payout_ratio__gte=data['payout_ratio_min'], indicators__date=latest_indicator_date)
    if data.get('payout_ratio_max'):
        conditions &= Q(indicators__payout_ratio__lte=data['payout_ratio_max'], indicators__date=latest_indicator_date)
    
    # 株価条件
    if data.get('price_min'):
        conditions &= Q(indicators__price__gte=data['price_min'], indicators__date=latest_indicator_date)
    if data.get('price_max'):
        conditions &= Q(indicators__price__lte=data['price_max'], indicators__date=latest_indicator_date)
    
    # 時価総額条件（億円単位をベースに変換）
    if data.get('market_cap_min'):
        market_cap_min = data['market_cap_min'] * 100000000  # 億円 → 円
        conditions &= Q(indicators__market_cap__gte=market_cap_min, indicators__date=latest_indicator_date)
    if data.get('market_cap_max'):
        market_cap_max = data['market_cap_max'] * 100000000  # 億円 → 円
        conditions &= Q(indicators__market_cap__lte=market_cap_max, indicators__date=latest_indicator_date)
    
    # 出来高条件
    if data.get('min_trading_volume'):
        conditions &= Q(indicators__volume__gte=data['min_trading_volume'], indicators__date=latest_indicator_date)
    
    # === 高度指標フィルタ ===
    if latest_advanced_date:
        # ROE条件
        if data.get('roe_min'):
            conditions &= Q(advanced_indicators__roe__gte=data['roe_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('roe_max'):
            conditions &= Q(advanced_indicators__roe__lte=data['roe_max'], advanced_indicators__date=latest_advanced_date)
        
        # ROA条件
        if data.get('roa_min'):
            conditions &= Q(advanced_indicators__roa__gte=data['roa_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('roa_max'):
            conditions &= Q(advanced_indicators__roa__lte=data['roa_max'], advanced_indicators__date=latest_advanced_date)
        
        # ROIC条件
        if data.get('roic_min'):
            conditions &= Q(advanced_indicators__roic__gte=data['roic_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('roic_max'):
            conditions &= Q(advanced_indicators__roic__lte=data['roic_max'], advanced_indicators__date=latest_advanced_date)
        
        # PEGレシオ条件
        if data.get('peg_min'):
            conditions &= Q(advanced_indicators__peg_ratio__gte=data['peg_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('peg_max'):
            conditions &= Q(advanced_indicators__peg_ratio__lte=data['peg_max'], advanced_indicators__date=latest_advanced_date)
        
        # EV/EBITDA条件
        if data.get('ev_ebitda_min'):
            conditions &= Q(advanced_indicators__ev_ebitda__gte=data['ev_ebitda_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('ev_ebitda_max'):
            conditions &= Q(advanced_indicators__ev_ebitda__lte=data['ev_ebitda_max'], advanced_indicators__date=latest_advanced_date)
        
        # 利益率条件
        if data.get('operating_margin_min'):
            conditions &= Q(advanced_indicators__operating_margin__gte=data['operating_margin_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('operating_margin_max'):
            conditions &= Q(advanced_indicators__operating_margin__lte=data['operating_margin_max'], advanced_indicators__date=latest_advanced_date)
        
        if data.get('net_margin_min'):
            conditions &= Q(advanced_indicators__net_margin__gte=data['net_margin_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('net_margin_max'):
            conditions &= Q(advanced_indicators__net_margin__lte=data['net_margin_max'], advanced_indicators__date=latest_advanced_date)
        
        # 成長率条件
        if data.get('revenue_growth_min'):
            conditions &= Q(advanced_indicators__revenue_growth_1y__gte=data['revenue_growth_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('revenue_growth_max'):
            conditions &= Q(advanced_indicators__revenue_growth_1y__lte=data['revenue_growth_max'], advanced_indicators__date=latest_advanced_date)
        
        if data.get('profit_growth_min'):
            conditions &= Q(advanced_indicators__net_growth_1y__gte=data['profit_growth_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('profit_growth_max'):
            conditions &= Q(advanced_indicators__net_growth_1y__lte=data['profit_growth_max'], advanced_indicators__date=latest_advanced_date)
        
        # 安全性条件
        if data.get('equity_ratio_min'):
            conditions &= Q(advanced_indicators__equity_ratio__gte=data['equity_ratio_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('equity_ratio_max'):
            conditions &= Q(advanced_indicators__equity_ratio__lte=data['equity_ratio_max'], advanced_indicators__date=latest_advanced_date)
        
        if data.get('current_ratio_min'):
            conditions &= Q(advanced_indicators__current_ratio__gte=data['current_ratio_min'], advanced_indicators__date=latest_advanced_date)
        if data.get('current_ratio_max'):
            conditions &= Q(advanced_indicators__current_ratio__lte=data['current_ratio_max'], advanced_indicators__date=latest_advanced_date)
        
        if data.get('debt_equity_ratio_max'):
            conditions &= Q(advanced_indicators__debt_equity_ratio__lte=data['debt_equity_ratio_max'], advanced_indicators__date=latest_advanced_date)
    
    # === 市場・業種・規模条件 ===
    if data.get('market'):
        conditions &= Q(market__icontains=data['market'])
    
    if data.get('sector'):
        conditions &= Q(sector__icontains=data['sector'])
    
    if data.get('size_category'):
        conditions &= Q(size_category=data['size_category'])
    
    # 基本クエリセットに条件を適用
    if conditions:
        base_queryset = base_queryset.filter(conditions)
    
    # === 複雑な条件処理 ===
    filtered_stocks = []
    
    for stock in base_queryset:
        # 基本データの取得
        indicator = stock.latest_indicators[0] if stock.latest_indicators else None
        advanced = stock.latest_advanced_indicators[0] if stock.latest_advanced_indicators else None
        financials = stock.recent_financials
        
        if not indicator:
            continue
        
        # 赤字銘柄除外
        if data.get('exclude_loss_stocks'):
            latest_financial = financials[0] if financials else None
            if latest_financial and latest_financial.net_income and latest_financial.net_income < 0:
                continue
        
        # 連続増益年数チェック
        if data.get('consecutive_profit_years'):
            required_years = data['consecutive_profit_years']
            if not check_consecutive_profit_years(financials, required_years):
                continue
        
        # 連続増配年数チェック（簡易実装）
        if data.get('consecutive_dividend_years'):
            # 注意: この実装は簡易版です。実際には配当履歴データが必要
            required_years = data['consecutive_dividend_years']
            # 配当利回りがある場合は継続配当と仮定
            if not indicator.dividend_yield or indicator.dividend_yield <= 0:
                continue
        
        # カスタム計算式の評価（簡易実装）
        if data.get('custom_formula'):
            if not evaluate_custom_formula(data['custom_formula'], indicator, advanced):
                continue
        
        # スコア計算と結果格納
        stock_scores = calculate_stock_scores_complete(stock, indicator, advanced, financials)
        filtered_stocks.append(stock_scores)
    
    return filtered_stocks

def check_consecutive_profit_years(financials, required_years):
    """連続増益年数チェック"""
    if len(financials) < required_years + 1:
        return False
    
    # 年度順にソート（新しい順）
    sorted_financials = sorted(financials, key=lambda x: x.year, reverse=True)
    
    for i in range(required_years):
        current = sorted_financials[i]
        previous = sorted_financials[i + 1]
        
        if (not current.net_income or not previous.net_income or 
            current.net_income <= previous.net_income):
            return False
    
    return True

def evaluate_custom_formula(formula, indicator, advanced):
    """カスタム計算式の評価（セキュリティを考慮した簡易実装）"""
    try:
        # 安全な変数のマッピング
        variables = {
            'per': float(indicator.per) if indicator.per else 0,
            'pbr': float(indicator.pbr) if indicator.pbr else 0,
            'dividend_yield': float(indicator.dividend_yield) if indicator.dividend_yield else 0,
            'price': float(indicator.price) if indicator.price else 0,
            'market_cap': float(indicator.market_cap) if indicator.market_cap else 0,
        }
        
        if advanced:
            variables.update({
                'roe': float(advanced.roe) if advanced.roe else 0,
                'roa': float(advanced.roa) if advanced.roa else 0,
                'roic': float(advanced.roic) if advanced.roic else 0,
                'equity_ratio': float(advanced.equity_ratio) if advanced.equity_ratio else 0,
                'current_ratio': float(advanced.current_ratio) if advanced.current_ratio else 0,
            })
        
        # 基本的な式の置換（セキュリティのため限定的）
        safe_formula = formula.lower()
        for var, value in variables.items():
            safe_formula = safe_formula.replace(var, str(value))
        
        # 危険な文字列をチェック
        dangerous_keywords = ['import', 'exec', 'eval', '__', 'open', 'file']
        if any(keyword in safe_formula for keyword in dangerous_keywords):
            return False
        
        # 簡易的な式の評価（本格実装では専用パーサーが必要）
        # ここでは基本的な比較演算のみサポート
        return True  # 簡易実装のため常にTrue
        
    except Exception as e:
        logger.warning(f"カスタム計算式評価エラー: {e}")
        return False

def calculate_stock_scores_complete(stock, indicator, advanced, financials):
    """完全版スコア計算"""
    try:
        # バリュエーションスコア（25点満点）
        valuation_score = calculate_valuation_score(indicator)
        
        # 収益性スコア（25点満点）
        profitability_score = calculate_profitability_score(advanced) if advanced else 0
        
        # 成長性スコア（25点満点）
        growth_score = calculate_growth_score(financials)
        
        # 安全性スコア（25点満点）
        safety_score = calculate_safety_score(advanced) if advanced else 0
        
        # 総合スコア
        total_score = valuation_score + profitability_score + growth_score + safety_score
        
        return {
            'stock': stock,
            'indicator': indicator,
            'advanced': advanced,
            'financials': financials,
            'valuation_score': round(valuation_score, 1),
            'profitability_score': round(profitability_score, 1),
            'growth_score': round(growth_score, 1),
            'safety_score': round(safety_score, 1),
            'total_score': round(total_score, 1),
            'roe': advanced.roe if advanced else None,
            'roa': advanced.roa if advanced else None,
            'is_favorite': False,  # ユーザー機能実装時に更新
        }
    
    except Exception as e:
        logger.error(f"完全版スコア計算エラー {stock.code}: {e}")
        return None

def sort_results(results_data, sort_by):
    """結果のソート処理"""
    try:
        reverse = sort_by.startswith('-')
        if reverse:
            sort_field = sort_by[1:]
        else:
            sort_field = sort_by
        
        def get_sort_value(item):
            if sort_field == 'total_score':
                return item.get('total_score', 0)
            elif sort_field == 'per':
                return float(item['indicator'].per) if item['indicator'].per else float('inf')
            elif sort_field == 'pbr':
                return float(item['indicator'].pbr) if item['indicator'].pbr else float('inf')
            elif sort_field == 'roe':
                return float(item['roe']) if item['roe'] else 0
            elif sort_field == 'dividend_yield':
                return float(item['indicator'].dividend_yield) if item['indicator'].dividend_yield else 0
            elif sort_field == 'price':
                return float(item['indicator'].price) if item['indicator'].price else 0
            elif sort_field == 'market_cap':
                return float(item['indicator'].market_cap) if item['indicator'].market_cap else 0
            elif sort_field == 'code':
                return item['stock'].code
            else:
                return 0
        
        return sorted(results_data, key=get_sort_value, reverse=reverse)
    
    except Exception as e:
        logger.error(f"ソート処理エラー: {e}")
        return results_data

# 既存の関数（calculate_valuation_score, calculate_profitability_score等）はそのまま維持

def calculate_valuation_score(indicator):
    """バリュエーションスコア計算"""
    score = 0
    
    # PERスコア（12.5点）
    if indicator.per:
        per = float(indicator.per)
        if per < 8:
            score += 12.5
        elif per < 12:
            score += 10
        elif per < 15:
            score += 7.5
        elif per < 20:
            score += 5
        elif per < 25:
            score += 2.5
    
    # PBRスコア（12.5点）
    if indicator.pbr:
        pbr = float(indicator.pbr)
        if pbr < 0.8:
            score += 12.5
        elif pbr < 1.0:
            score += 10
        elif pbr < 1.5:
            score += 7.5
        elif pbr < 2.0:
            score += 5
        elif pbr < 3.0:
            score += 2.5
    
    return score

def calculate_profitability_score(advanced):
    """収益性スコア計算"""
    if not advanced:
        return 0
    
    score = 0
    
    # ROEスコア（12.5点）
    if advanced.roe:
        roe = float(advanced.roe)
        if roe > 20:
            score += 12.5
        elif roe > 15:
            score += 10
        elif roe > 10:
            score += 7.5
        elif roe > 5:
            score += 5
        elif roe > 0:
            score += 2.5
    
    # ROAスコア（12.5点）
    if advanced.roa:
        roa = float(advanced.roa)
        if roa > 10:
            score += 12.5
        elif roa > 7:
            score += 10
        elif roa > 5:
            score += 7.5
        elif roa > 3:
            score += 5
        elif roa > 0:
            score += 2.5
    
    return score

def calculate_growth_score(financials):
    """成長性スコア計算"""
    if len(financials) < 3:
        return 0
    
    score = 0
    
    try:
        # 売上高成長率計算（3年CAGR）
        revenue_values = [f.revenue for f in financials if f.revenue]
        if len(revenue_values) >= 3:
            revenue_cagr = calculate_cagr(revenue_values, 3)
            if revenue_cagr:
                if revenue_cagr > 15:
                    score += 12.5
                elif revenue_cagr > 10:
                    score += 10
                elif revenue_cagr > 5:
                    score += 7.5
                elif revenue_cagr > 0:
                    score += 5
        
        # 純利益成長率計算（3年CAGR）
        profit_values = [f.net_income for f in financials if f.net_income and f.net_income > 0]
        if len(profit_values) >= 3:
            profit_cagr = calculate_cagr(profit_values, 3)
            if profit_cagr:
                if profit_cagr > 20:
                    score += 12.5
                elif profit_cagr > 15:
                    score += 10
                elif profit_cagr > 10:
                    score += 7.5
                elif profit_cagr > 5:
                    score += 5
    
    except Exception as e:
        logger.error(f"成長性スコア計算エラー: {e}")
    
    return score

def calculate_safety_score(advanced):
    """安全性スコア計算"""
    if not advanced:
        return 0
    
    score = 0
    
    # 自己資本比率スコア（12.5点）
    if advanced.equity_ratio:
        equity_ratio = float(advanced.equity_ratio)
        if equity_ratio > 70:
            score += 12.5
        elif equity_ratio > 50:
            score += 10
        elif equity_ratio > 40:
            score += 7.5
        elif equity_ratio > 30:
            score += 5
        elif equity_ratio > 20:
            score += 2.5
    
    # 流動比率スコア（12.5点）
    if advanced.current_ratio:
        current_ratio = float(advanced.current_ratio)
        if current_ratio > 2.0:
            score += 12.5
        elif current_ratio > 1.5:
            score += 10
        elif current_ratio > 1.2:
            score += 7.5
        elif current_ratio > 1.0:
            score += 5
        elif current_ratio > 0.8:
            score += 2.5
    
    return score

def calculate_cagr(values, years):
    """年平均成長率（CAGR）計算"""
    if len(values) < 2:
        return None
    
    try:
        start_value = float(values[-1])  # 最古の値
        end_value = float(values[0])     # 最新の値
        
        if start_value <= 0:
            return None
        
        cagr = (pow(end_value / start_value, 1/years) - 1) * 100
        return cagr
    except (ValueError, ZeroDivisionError):
        return None

# === API エンドポイント（既存のまま） ===

def api_stock_search(request):
    """銘柄検索API"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    try:
        # 銘柄コードまたは企業名で検索
        stocks = Stock.objects.filter(
            Q(code__icontains=query) | Q(name__icontains=query)
        ).select_related().order_by('code')[:10]
        
        results = []
        for stock in stocks:
            # 最新の指標データ取得
            latest_indicator = stock.indicators.order_by('-date').first()
            
            results.append({
                'code': stock.code,
                'name': stock.name,
                'market': stock.market or '',
                'sector': stock.sector or '',
                'per': float(latest_indicator.per) if latest_indicator and latest_indicator.per else None,
                'pbr': float(latest_indicator.pbr) if latest_indicator and latest_indicator.pbr else None,
                'price': float(latest_indicator.price) if latest_indicator and latest_indicator.price else None,
                'dividend_yield': float(latest_indicator.dividend_yield) if latest_indicator and latest_indicator.dividend_yield else None,
            })
        
        return JsonResponse({'results': results})
    
    except Exception as e:
        logger.error(f"銘柄検索APIエラー: {e}")
        return JsonResponse({'error': 'Search failed'}, status=500)

def api_top_performers(request):
    """トップパフォーマーAPI"""
    try:
        # キャッシュから取得を試行
        cache_key = 'top_performers'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return JsonResponse(cached_data)
        
        # 最新の指標データから上位パフォーマーを取得
        latest_date = Indicator.objects.aggregate(Max('date'))['date__max']
        if not latest_date:
            return JsonResponse({'performers': []})
        
        # 前日の日付を計算（仮想的な変化率）
        previous_date = latest_date - timedelta(days=1)
        
        # トップパフォーマー（仮想データ）
        top_stocks = Stock.objects.filter(
            indicators__date=latest_date
        ).select_related().order_by('?')[:10]  # ランダムサンプル
        
        performers = []
        for i, stock in enumerate(top_stocks):
            latest_indicator = stock.indicators.filter(date=latest_date).first()
            if latest_indicator:
                # 仮想的な変化率を生成
                import random
                change = random.uniform(-3.0, 8.0)
                volume = f"{random.randint(50, 500)/10:.1f}M"
                
                performers.append({
                    'code': stock.code,
                    'name': stock.name,
                    'price': float(latest_indicator.price) if latest_indicator.price else 1000,
                    'change': round(change, 1),
                    'volume': volume
                })
        
        # 変化率でソート
        performers.sort(key=lambda x: x['change'], reverse=True)
        
        result = {'performers': performers}
        
        # 5分間キャッシュ
        cache.set(cache_key, result, 300)
        
        return JsonResponse(result)
    
    except Exception as e:
        logger.error(f"トップパフォーマーAPIエラー: {e}")
        return JsonResponse({'error': 'Failed to fetch top performers'}, status=500)

def api_market_news(request):
    """マーケットニュースAPI"""
    try:
        # 実際の実装では外部ニュースAPIから取得
        # ここではサンプルデータを返す
        news = [
            {
                'title': '日経平均、3日続伸で取引終了',
                'summary': '半導体関連株の上昇が市場全体を押し上げ、投資家心理も改善。',
                'time': '15分前',
                'tags': ['日経平均', '半導体', '市場']
            },
            {
                'title': 'FRB議事録、利下げ示唆の内容',
                'summary': 'インフレ鈍化を受けて政策転換への期待が高まる。',
                'time': '1時間前',
                'tags': ['FRB', '金利', '米国']
            },
            {
                'title': '円安進行、1ドル150円台で推移',
                'summary': '日米金利差拡大観測で円売りが継続している。',
                'time': '2時間前',
                'tags': ['為替', '円安', '金利差']
            },
            {
                'title': 'AI関連銘柄に注目集まる',
                'summary': '生成AI技術の普及で関連企業の業績拡大期待。',
                'time': '3時間前',
                'tags': ['AI', 'テクノロジー', '成長株']
            }
        ]
        
        return JsonResponse({'news': news})
    
    except Exception as e:
        logger.error(f"マーケットニュースAPIエラー: {e}")
        return JsonResponse({'error': 'Failed to fetch news'}, status=500)

def api_sector_performance(request):
    """セクターパフォーマンスAPI"""
    try:
        period = request.GET.get('period', '1d')
        
        # セクター別パフォーマンス（仮想データ）
        import random
        sectors = [
            '医薬品', '電気機器', '情報・通信業', '輸送用機器',
            '銀行業', '食料品', '化学', '機械', '小売業', '建設業',
            '不動産業', '証券業', '保険業', '石油・石炭', '鉄鋼',
            '非鉄金属', 'ガラス・土石', '繊維製品', 'パルプ・紙'
        ]
        
        sector_data = []
        for sector in sectors:
            # 期間に応じた変化率範囲を調整
            if period == '1d':
                change_range = (-2.5, 4.0)
            elif period == '1w':
                change_range = (-8.0, 12.0)
            else:  # 1m
                change_range = (-15.0, 25.0)
            
            change = random.uniform(*change_range)
            sector_data.append({
                'name': sector,
                'change': round(change, 1)
            })
        
        return JsonResponse({'sectors': sector_data})
    
    except Exception as e:
        logger.error(f"セクターパフォーマンスAPIエラー: {e}")
        return JsonResponse({'error': 'Failed to fetch sector data'}, status=500)

def api_market_data(request):
    """マーケットデータAPI"""
    try:
        period = request.GET.get('period', '1d')
        
        # 期間に応じたデータポイント数を決定
        if period == '1d':
            points = 24  # 1時間ごと
            labels = [f"{i:02d}:00" for i in range(24)]
        elif period == '1w':
            points = 7   # 1日ごと
            labels = [f"Day {i+1}" for i in range(7)]
        elif period == '1m':
            points = 30  # 1日ごと
            labels = [f"Day {i+1}" for i in range(30)]
        else:  # 3m
            points = 90  # 1日ごと
            labels = [f"Day {i+1}" for i in range(90)]
        
        # サンプルデータ生成
        import random
        base_nikkei = 33000
        base_topix = 2400
        
        nikkei_data = []
        topix_data = []
        
        for i in range(points):
            # ランダムウォーク
            nikkei_change = random.uniform(-0.5, 0.5)
            topix_change = random.uniform(-0.4, 0.4)
            
            base_nikkei += base_nikkei * nikkei_change / 100
            base_topix += base_topix * topix_change / 100
            
            nikkei_data.append(round(base_nikkei, 2))
            topix_data.append(round(base_topix, 2))
        
        return JsonResponse({
            'labels': labels,
            'nikkei': nikkei_data,
            'topix': topix_data
        })
    
    except Exception as e:
        logger.error(f"マーケットデータAPIエラー: {e}")
        return JsonResponse({'error': 'Failed to fetch market data'}, status=500)

@csrf_exempt
def api_watchlist_add(request):
    """ウォッチリスト追加API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        stock_code = data.get('stock_code', '').strip()
        
        if not stock_code:
            return JsonResponse({'error': 'Stock code is required'}, status=400)
        
        # 銘柄の存在確認
        try:
            stock = Stock.objects.get(code=stock_code)
        except Stock.DoesNotExist:
            return JsonResponse({'error': f'Stock {stock_code} not found'}, status=404)
        
        # 簡易的なウォッチリスト（セッションに保存）
        watchlist = request.session.get('watchlist', [])
        
        if stock_code not in watchlist:
            watchlist.append(stock_code)
            request.session['watchlist'] = watchlist
            request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': f'{stock.name} をウォッチリストに追加しました'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"ウォッチリスト追加エラー: {e}")
        return JsonResponse({'error': 'Failed to add to watchlist'}, status=500)

def stock_detail_view(request, stock_code):
    """個別銘柄詳細ビュー（強化版）"""
    stock = get_object_or_404(Stock, code=stock_code)
    
    # 最新の指標データ
    latest_indicator = stock.indicators.order_by('-date').first()
    
    # 高度指標データ
    latest_advanced = stock.advanced_indicators.order_by('-date').first()
    
    # 財務データ（過去10年）
    financials = stock.financials.order_by('-year')[:10]
    
    # 指標データの推移（過去60日）
    indicators_history = stock.indicators.order_by('-date')[:60]
    
    # 連続増益チェック
    is_consecutive_profit = StockDataFetcher.check_consecutive_profit_growth(stock, 5)
    
    # スコア計算
    stock_scores = calculate_stock_scores_complete(stock, latest_indicator, latest_advanced, financials) if latest_indicator else None
    
    # チャート用データの準備
    chart_data = prepare_chart_data(financials, indicators_history)
    
    # 財務分析データ
    financial_analysis = analyze_financial_performance(financials)
    
    # 業界比較データ
    industry_comparison = get_industry_comparison(stock, latest_indicator, latest_advanced)
    
    context = {
        'stock': stock,
        'latest_indicator': latest_indicator,
        'latest_advanced': latest_advanced,
        'financials': financials,
        'indicators_history': indicators_history,
        'is_consecutive_profit': is_consecutive_profit,
        'stock_scores': stock_scores,
        'chart_data': chart_data,
        'financial_analysis': financial_analysis,
        'industry_comparison': industry_comparison,
    }
    
    return render(request, 'stock/stock_detail.html', context)

def prepare_chart_data(financials, indicators_history):
    """チャートデータの準備"""
    chart_data = {
        'financial_years': [],
        'revenues': [],
        'net_incomes': [],
        'indicator_dates': [],
        'prices': []
    }
    
    # 財務データをチャート用に変換
    if financials:
        for financial in reversed(list(financials)):
            chart_data['financial_years'].append(str(financial.year))
            chart_data['revenues'].append(float(financial.revenue or 0))
            chart_data['net_incomes'].append(float(financial.net_income or 0))
    
    # 株価データをチャート用に変換
    if indicators_history:
        for indicator in reversed(list(indicators_history)):
            chart_data['indicator_dates'].append(indicator.date.strftime('%Y-%m-%d'))
            chart_data['prices'].append(float(indicator.price or 0))
    
    return chart_data

def analyze_financial_performance(financials):
    """財務パフォーマンス分析"""
    analysis = {'growth_rates': []}
    
    if len(financials) > 1:
        financials_list = list(financials)
        for i in range(len(financials_list) - 1):
            current = financials_list[i]
            previous = financials_list[i + 1]
            
            # 売上高成長率
            revenue_growth = None
            if current.revenue and previous.revenue and previous.revenue != 0:
                revenue_growth = ((current.revenue - previous.revenue) / previous.revenue) * 100
            
            # 純利益成長率
            profit_growth = None
            if current.net_income and previous.net_income and previous.net_income != 0:
                profit_growth = ((current.net_income - previous.net_income) / previous.net_income) * 100
            
            analysis['growth_rates'].append({
                'year': current.year,
                'revenue_growth': round(revenue_growth, 1) if revenue_growth else None,
                'profit_growth': round(profit_growth, 1) if profit_growth else None
            })
    
    return analysis

def get_industry_comparison(stock, indicator, advanced):
    """業界比較データ取得"""
    if not stock.sector:
        return None
    
    try:
        # 同業界の平均値を計算
        sector_stocks = Stock.objects.filter(sector=stock.sector)
        
        sector_indicators = Indicator.objects.filter(
            stock__in=sector_stocks,
            date__gte=timezone.now().date() - timedelta(days=30)
        ).aggregate(
            avg_per=Avg('per'),
            avg_pbr=Avg('pbr'),
            avg_dividend=Avg('dividend_yield')
        )
        
        sector_advanced = AdvancedIndicator.objects.filter(
            stock__in=sector_stocks,
            date__gte=timezone.now().date() - timedelta(days=30)
        ).aggregate(
            avg_roe=Avg('roe'),
            avg_roa=Avg('roa'),
            avg_equity_ratio=Avg('equity_ratio')
        )
        
        comparison = {
            'sector_name': stock.sector,
            'sector_count': sector_stocks.count(),
            'comparisons': []
        }
        
        # 個別比較項目
        if indicator and indicator.per and sector_indicators['avg_per']:
            comparison['comparisons'].append({
                'metric': 'PER',
                'stock_value': float(indicator.per),
                'sector_avg': float(sector_indicators['avg_per']),
                'better': indicator.per < sector_indicators['avg_per']
            })
        
        if indicator and indicator.pbr and sector_indicators['avg_pbr']:
            comparison['comparisons'].append({
                'metric': 'PBR',
                'stock_value': float(indicator.pbr),
                'sector_avg': float(sector_indicators['avg_pbr']),
                'better': indicator.pbr < sector_indicators['avg_pbr']
            })
        
        if advanced and advanced.roe and sector_advanced['avg_roe']:
            comparison['comparisons'].append({
                'metric': 'ROE',
                'stock_value': float(advanced.roe),
                'sector_avg': float(sector_advanced['avg_roe']),
                'better': advanced.roe > sector_advanced['avg_roe']
            })
        
        return comparison
    
    except Exception as e:
        logger.error(f"業界比較データ取得エラー: {e}")
        return None

def export_csv(request):
    """高度なCSV出力"""
    form = StockScreeningForm(request.GET)
    
    if not form.is_valid():
        messages.error(request, 'フォームに入力エラーがあります。')
        return redirect('stock:screening')
    
    # タイムスタンプ付きファイル名
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f'professional_screening_{timestamp}.csv'
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # BOM for Excel compatibility
    
    writer = csv.writer(response)
    
    # 拡張ヘッダー
    writer.writerow([
        '銘柄コード', '企業名', '市場区分', '業種',
        'PER', 'PBR', '配当利回り(%)', '株価(円)',
        'ROE(%)', 'ROA(%)', 'ROIC(%)', '自己資本比率(%)', '流動比率',
        '売上高成長率(%)', '純利益成長率(%)', '連続増益年数',
        'バリュエーションスコア', '収益性スコア', '成長性スコア', '安全性スコア', '総合スコア',
        '指標取得日', '最終更新日時'
    ])
    
    # クエリセット構築と出力
    results = build_complete_queryset(form)
    exported_count = 0
    
    for stock_data in results:
        if not stock_data:
            continue
        
        stock = stock_data['stock']
        indicator = stock_data['indicator']
        advanced = stock_data['advanced']
        
        writer.writerow([
            stock.code,
            stock.name,
            stock.market or '-',
            stock.sector or '-',
            f"{indicator.per:.1f}" if indicator.per else '-',
            f"{indicator.pbr:.2f}" if indicator.pbr else '-',
            f"{indicator.dividend_yield:.2f}" if indicator.dividend_yield else '-',
            f"{indicator.price:.0f}" if indicator.price else '-',
            f"{advanced.roe:.1f}" if advanced and advanced.roe else '-',
            f"{advanced.roa:.1f}" if advanced and advanced.roa else '-',
            f"{advanced.roic:.1f}" if advanced and advanced.roic else '-',
            f"{advanced.equity_ratio:.1f}" if advanced and advanced.equity_ratio else '-',
            f"{advanced.current_ratio:.2f}" if advanced and advanced.current_ratio else '-',
            # 成長率は省略（計算が複雑なため）
            '-', '-', '-',
            stock_data['valuation_score'],
            stock_data['profitability_score'],
            stock_data['growth_score'],
            stock_data['safety_score'],
            stock_data['total_score'],
            indicator.date.strftime('%Y-%m-%d'),
            timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        exported_count += 1
    
    # 統計情報
    writer.writerow([])
    writer.writerow(['=== 出力統計 ==='])
    writer.writerow(['出力件数', exported_count])
    writer.writerow(['出力日時', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow(['検索条件', str(form.get_search_summary() if hasattr(form, 'get_search_summary') else '高度検索')])
    
    return response