# stock/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Prefetch, Count, Avg, OuterRef
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from datetime import timedelta, datetime
import csv
import json
from .models import Stock, Indicator, Financial
from .forms import stockcreeningForm
from .utils import StockDataFetcher

def dashboard_view(request):
    """ダッシュボードビュー"""
    # 基本統計情報
    total_stock = Stock.objects.count()
    
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
    
    # 最近更新された銘柄（指標データ）
    recent_indicators = Indicator.objects.select_related('stock').order_by('-updated_at')[:15]
    
    # 市場区分別統計
    market_stats = Stock.objects.values('market').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # PER/PBR分布統計（最新データ）
    latest_date = Indicator.objects.order_by('-date').first()
    distribution_stats = {}
    
    if latest_date:
        latest_indicators_qs = Indicator.objects.filter(
            date=latest_date.date,
            per__isnull=False,
            pbr__isnull=False
        )
        
        if latest_indicators_qs.exists():
            distribution_stats = {
                'avg_per': latest_indicators_qs.aggregate(Avg('per'))['per__avg'],
                'avg_pbr': latest_indicators_qs.aggregate(Avg('pbr'))['pbr__avg'],
                'low_per_count': latest_indicators_qs.filter(per__lt=15).count(),
                'low_pbr_count': latest_indicators_qs.filter(pbr__lt=1.5).count(),
                'high_dividend_count': latest_indicators_qs.filter(dividend_yield__gt=3).count(),
                'latest_date': latest_date.date
            }
    
    context = {
        'total_stock': total_stock,
        'latest_indicators': latest_indicators,
        'total_financials': total_financials,
        'stock_with_financials': stock_with_financials,
        'recent_indicators': recent_indicators,
        'market_stats': market_stats,
        'distribution_stats': distribution_stats,
        'financial_coverage': round(stock_with_financials / total_stock * 100, 1) if total_stock > 0 else 0,
    }
    
    return render(request, 'stock/dashboard.html', context)

def screening_view(request):
    """株式スクリーニングビュー"""
    form = stockcreeningForm(request.GET)
    results = []
    total_count = 0
    execution_time = 0
    
    if request.GET:
        start_time = datetime.now()
        
        # 最新の指標データを持つ銘柄を取得
        # 各銘柄の最新指標データをPrefetchで効率的に取得
        
        queryset = Stock.objects.prefetch_related(
            Prefetch(
                'indicators',
                queryset=Indicator.objects.order_by('-date')[:1],
                to_attr='latest_indicator'
            ),
            Prefetch(
                'financials',
                queryset=Financial.objects.order_by('-year'),
                to_attr='recent_financials'
            )
        ).filter(
            indicators__isnull=False
        ).distinct()
        
        # フィルタリング条件を適用
        if form.is_valid():
            per_max = form.cleaned_data.get('per_max')
            pbr_max = form.cleaned_data.get('pbr_max')
            dividend_yield_min = form.cleaned_data.get('dividend_yield_min')
            consecutive_profit_years = form.cleaned_data.get('consecutive_profit_years')
            market = form.cleaned_data.get('market')
            sort_by = form.cleaned_data.get('sort_by') or 'code'
            
            # 結果を格納するリスト
            filtered_stock = []
            
            for stock in queryset:
                # 最新の指標データ取得
                if not stock.latest_indicator:
                    continue
                
                indicator = stock.latest_indicator[0]
                
                # PER条件チェック
                if per_max and (indicator.per is None or indicator.per > per_max):
                    continue
                
                # PBR条件チェック
                if pbr_max and (indicator.pbr is None or indicator.pbr > pbr_max):
                    continue
                
                # 配当利回り条件チェック
                if dividend_yield_min and (indicator.dividend_yield is None or indicator.dividend_yield < dividend_yield_min):
                    continue
                
                # 市場区分条件チェック
                if market and market.lower() not in stock.market.lower():
                    continue
                
                # 連続増益条件チェック
                is_consecutive_profit = False
                if consecutive_profit_years:
                    is_consecutive_profit = StockDataFetcher.check_consecutive_profit_growth(
                        stock, consecutive_profit_years
                    )
                    if not is_consecutive_profit:
                        continue
                else:
                    # 連続増益チェックボックスがない場合でも、5年連続増益かどうかを表示用に計算
                    is_consecutive_profit = StockDataFetcher.check_consecutive_profit_growth(stock, 5)
                
                # 条件をクリアした銘柄を追加
                stock_data = {
                    'stock': stock,
                    'indicator': indicator,
                    'is_consecutive_profit': is_consecutive_profit,
                    'financial_years': len(stock.recent_financials),
                }
                
                # ソート用の値を事前計算
                if sort_by == 'per':
                    stock_data['sort_value'] = indicator.per or 999999
                elif sort_by == '-per':
                    stock_data['sort_value'] = indicator.per or 0
                elif sort_by == 'pbr':
                    stock_data['sort_value'] = indicator.pbr or 999999
                elif sort_by == '-pbr':
                    stock_data['sort_value'] = indicator.pbr or 0
                elif sort_by == 'dividend_yield':
                    stock_data['sort_value'] = indicator.dividend_yield or 0
                elif sort_by == '-dividend_yield':
                    stock_data['sort_value'] = indicator.dividend_yield or 0
                else:  # code
                    stock_data['sort_value'] = stock.code
                
                filtered_stock.append(stock_data)
            
            # ソート処理
            reverse_sort = sort_by.startswith('-')
            filtered_stock.sort(
                key=lambda x: x['sort_value'], 
                reverse=reverse_sort
            )
            
            results = filtered_stock
            total_count = len(results)
            
            execution_time = (datetime.now() - start_time).total_seconds()
    
    # ページネーション
    page_number = request.GET.get('page', 1)
    paginator = Paginator(results, 50)  # 1ページ50件
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'results': page_obj,
        'total_count': total_count,
        'execution_time': round(execution_time, 2),
        'has_search': bool(request.GET),
    }
    
    return render(request, 'stock/screening.html', context)

def export_csv(request):
    """スクリーニング結果をCSV出力"""
    # screening_viewと同じロジックでデータを取得
    form = stockcreeningForm(request.GET)
    
    if not form.is_valid():
        messages.error(request, 'フォームに入力エラーがあります。')
        return redirect('stock:screening')
    
    # ファイル名に日時を含める
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f'screening_results_{timestamp}.csv'
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # BOM for Excel compatibility
    
    writer = csv.writer(response)
    writer.writerow([
        '銘柄コード', '企業名', '市場区分', 'PER', 'PBR', 
        '配当利回り(%)', '株価(円)', '5年連続増益', '財務データ年数', '指標取得日'
    ])
    
    # screening_viewのロジックを再利用（簡略化）
    queryset = Stock.objects.prefetch_related(
        Prefetch(
            'indicators',
            queryset=Indicator.objects.order_by('-date')[:1],
            to_attr='latest_indicator'
        ),
        Prefetch(
            'financials',
            queryset=Financial.objects.order_by('-year'),
            to_attr='recent_financials'
        )
    ).filter(indicators__isnull=False).distinct()
    
    # フィルタリング（簡略版）
    per_max = form.cleaned_data.get('per_max')
    pbr_max = form.cleaned_data.get('pbr_max')
    dividend_yield_min = form.cleaned_data.get('dividend_yield_min')
    consecutive_profit_years = form.cleaned_data.get('consecutive_profit_years')
    market = form.cleaned_data.get('market')
    
    exported_count = 0
    for stock in queryset:
        if not stock.latest_indicator:
            continue
            
        indicator = stock.latest_indicator[0]
        
        # 簡単なフィルタリング
        if per_max and (indicator.per is None or indicator.per > per_max):
            continue
        if pbr_max and (indicator.pbr is None or indicator.pbr > pbr_max):
            continue
        if dividend_yield_min and (indicator.dividend_yield is None or indicator.dividend_yield < dividend_yield_min):
            continue
        if market and market.lower() not in stock.market.lower():
            continue
        
        is_consecutive_profit = StockDataFetcher.check_consecutive_profit_growth(
            stock, consecutive_profit_years or 5
        )
        
        if consecutive_profit_years and not is_consecutive_profit:
            continue
        
        # CSV行を書き込み
        writer.writerow([
            stock.code,
            stock.name,
            stock.market or '-',
            indicator.per or '-',
            indicator.pbr or '-',
            indicator.dividend_yield or '-',
            indicator.price or '-',
            '○' if is_consecutive_profit else '-',
            len(stock.recent_financials),
            indicator.date.strftime('%Y-%m-%d')
        ])
        exported_count += 1
    
    # CSVの最後に統計行を追加
    writer.writerow([])
    writer.writerow(['--- 統計情報 ---'])
    writer.writerow(['出力件数', exported_count])
    writer.writerow(['出力日時', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
    
    return response

def stock_detail_view(request, stock_code):
    """個別銘柄詳細ビュー"""
    stock = get_object_or_404(Stock, code=stock_code)
    
    # 最新の指標データ
    latest_indicator = stock.indicators.order_by('-date').first()
    
    # 財務データ（過去5年）
    financials = stock.financials.order_by('-year')[:5]
    
    # 指標データの推移（過去30日）
    indicators_history = stock.indicators.order_by('-date')[:30]
    
    # 連続増益チェック
    is_consecutive_profit = StockDataFetcher.check_consecutive_profit_growth(stock, 5)
    
    context = {
        'stock': stock,
        'latest_indicator': latest_indicator,
        'financials': financials,
        'indicators_history': indicators_history,
        'is_consecutive_profit': is_consecutive_profit,
    }
    
    return render(request, 'stock/stock_detail.html', context)

def api_stock_search(request):
    """銘柄検索API（AJAX用）"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # 銘柄コードまたは企業名で検索
    stock = Stock.objects.filter(
        Q(code__icontains=query) | Q(name__icontains=query)
    )[:10]
    
    results = [
        {
            'code': stock.code,
            'name': stock.name,
            'market': stock.market,
        }
        for stock in stock
    ]
    
    return JsonResponse({'results': results})

def update_stock_data_view(request):
    """データ更新ビュー（管理者用）"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_indicators':
            # 指標データ更新（少数銘柄のみ）
            limit = int(request.POST.get('limit', 10))
            success_count = StockDataFetcher.batch_update_indicators(limit)
            messages.success(request, f'指標データを更新しました。成功: {success_count}件')
        
        elif action == 'update_stock_list':
            # 銘柄リスト更新
            try:
                created_count = StockDataFetcher.fetch_jpx_stock_list()
                messages.success(request, f'銘柄リストを更新しました。新規: {created_count}件')
            except Exception as e:
                messages.error(request, f'銘柄リスト更新に失敗: {str(e)}')
    
    # 現在の統計情報
    stats = {
        'total_stock': Stock.objects.count(),
        'total_indicators': Indicator.objects.count(),
        'total_financials': Financial.objects.count(),
        'latest_indicator_date': Indicator.objects.order_by('-date').first(),
    }
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'stock/admin_update.html', context)