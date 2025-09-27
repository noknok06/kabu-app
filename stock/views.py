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
from .forms import StockScreeningForm  # ← 修正: stockcreeningForm → StockScreeningForm
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
    """株式スクリーニングビュー（拡張版）"""
    form = StockScreeningForm(request.GET)
    results = []
    total_count = 0
    execution_time = 0
    
    if request.GET:
        start_time = datetime.now()
        
        # 最新の指標データを持つ銘柄を取得
        queryset = Stock.objects.prefetch_related(
            Prefetch(
                'indicators',
                queryset=Indicator.objects.order_by('-date')[:1],
                to_attr='latest_indicator'
            ),
            Prefetch(
                'financials',
                queryset=Financial.objects.order_by('-year')[:10],  # 成長率計算のため多めに取得
                to_attr='recent_financials'
            )
        ).filter(
            indicators__isnull=False
        ).distinct()
        
        # フィルタリング条件を適用
        if form.is_valid():
            # 基本指標条件
            per_min = form.cleaned_data.get('per_min')
            per_max = form.cleaned_data.get('per_max')
            pbr_min = form.cleaned_data.get('pbr_min')
            pbr_max = form.cleaned_data.get('pbr_max')
            dividend_yield_min = form.cleaned_data.get('dividend_yield_min')
            dividend_yield_max = form.cleaned_data.get('dividend_yield_max')
            
            # 株価条件
            price_min = form.cleaned_data.get('price_min')
            price_max = form.cleaned_data.get('price_max')
            
            # 成長性条件
            consecutive_profit_years = form.cleaned_data.get('consecutive_profit_years')
            revenue_growth_min = form.cleaned_data.get('revenue_growth_min')
            revenue_growth_max = form.cleaned_data.get('revenue_growth_max')
            profit_growth_min = form.cleaned_data.get('profit_growth_min')
            profit_growth_max = form.cleaned_data.get('profit_growth_max')
            
            # 財務健全性条件
            profit_margin_min = form.cleaned_data.get('profit_margin_min')
            
            # 市場・業種条件
            market = form.cleaned_data.get('market')
            sector = form.cleaned_data.get('sector')
            
            # 表示設定
            sort_by = form.cleaned_data.get('sort_by') or 'code'
            
            # 結果を格納するリスト
            filtered_stocks = []
            
            for stock in queryset:
                # 最新の指標データ取得
                if not stock.latest_indicator:
                    continue
                
                indicator = stock.latest_indicator[0]
                
                # === 基本指標条件チェック ===
                # PER条件
                if per_min and (indicator.per is None or indicator.per < per_min):
                    continue
                if per_max and (indicator.per is None or indicator.per > per_max):
                    continue
                
                # PBR条件
                if pbr_min and (indicator.pbr is None or indicator.pbr < pbr_min):
                    continue
                if pbr_max and (indicator.pbr is None or indicator.pbr > pbr_max):
                    continue
                
                # 配当利回り条件
                if dividend_yield_min and (indicator.dividend_yield is None or indicator.dividend_yield < dividend_yield_min):
                    continue
                if dividend_yield_max and (indicator.dividend_yield is None or indicator.dividend_yield > dividend_yield_max):
                    continue
                
                # === 株価条件チェック ===
                if price_min and (indicator.price is None or indicator.price < price_min):
                    continue
                if price_max and (indicator.price is None or indicator.price > price_max):
                    continue
                
                # === 市場・業種条件チェック ===
                if market and market.lower() not in (stock.market or '').lower():
                    continue
                if sector and sector.lower() not in (stock.sector or '').lower():
                    continue
                
                # === 財務データ分析 ===
                financials = stock.recent_financials
                
                # 純利益率計算
                profit_margin = None
                if financials and len(financials) > 0:
                    latest_financial = financials[0]
                    if latest_financial.revenue and latest_financial.net_income and latest_financial.revenue > 0:
                        profit_margin = (float(latest_financial.net_income) / float(latest_financial.revenue)) * 100
                
                # 純利益率条件チェック
                if profit_margin_min and (profit_margin is None or profit_margin < profit_margin_min):
                    continue
                
                # 成長率計算
                revenue_growth = None
                profit_growth = None
                
                if len(financials) >= 2:
                    current = financials[0]
                    previous = financials[1]
                    
                    # 売上高成長率
                    if current.revenue and previous.revenue and previous.revenue > 0:
                        revenue_growth = ((float(current.revenue) - float(previous.revenue)) / float(previous.revenue)) * 100
                    
                    # 純利益成長率
                    if current.net_income and previous.net_income and previous.net_income > 0:
                        profit_growth = ((float(current.net_income) - float(previous.net_income)) / float(previous.net_income)) * 100
                
                # 成長率条件チェック
                if revenue_growth_min and (revenue_growth is None or revenue_growth < revenue_growth_min):
                    continue
                if revenue_growth_max and (revenue_growth is None or revenue_growth > revenue_growth_max):
                    continue
                if profit_growth_min and (profit_growth is None or profit_growth < profit_growth_min):
                    continue
                if profit_growth_max and (profit_growth is None or profit_growth > profit_growth_max):
                    continue
                
                # === 連続増益条件チェック ===
                is_consecutive_profit = False
                if consecutive_profit_years:
                    is_consecutive_profit = StockDataFetcher.check_consecutive_profit_growth(
                        stock, consecutive_profit_years
                    )
                    if not is_consecutive_profit:
                        continue
                else:
                    # 表示用に5年連続増益かどうかを計算
                    is_consecutive_profit = StockDataFetcher.check_consecutive_profit_growth(stock, 5)
                
                # === 条件をクリアした銘柄を追加 ===
                stock_data = {
                    'stock': stock,
                    'indicator': indicator,
                    'is_consecutive_profit': is_consecutive_profit,
                    'financial_years': len(financials),
                    'profit_margin': profit_margin,
                    'revenue_growth': revenue_growth,
                    'profit_growth': profit_growth,
                }
                
                # ソート用の値を事前計算
                if sort_by == 'per':
                    stock_data['sort_value'] = indicator.per or 999999
                elif sort_by == '-per':
                    stock_data['sort_value'] = -(indicator.per or 0)
                elif sort_by == 'pbr':
                    stock_data['sort_value'] = indicator.pbr or 999999
                elif sort_by == '-pbr':
                    stock_data['sort_value'] = -(indicator.pbr or 0)
                elif sort_by == 'dividend_yield':
                    stock_data['sort_value'] = indicator.dividend_yield or 0
                elif sort_by == '-dividend_yield':
                    stock_data['sort_value'] = -(indicator.dividend_yield or 0)
                elif sort_by == 'price':
                    stock_data['sort_value'] = indicator.price or 999999
                elif sort_by == '-price':
                    stock_data['sort_value'] = -(indicator.price or 0)
                elif sort_by == 'profit_margin':
                    stock_data['sort_value'] = profit_margin or -999
                elif sort_by == '-profit_margin':
                    stock_data['sort_value'] = -(profit_margin or -999)
                elif sort_by == 'consecutive_profit_years':
                    stock_data['sort_value'] = -(1 if is_consecutive_profit else 0)
                else:  # code
                    stock_data['sort_value'] = stock.code
                
                filtered_stocks.append(stock_data)
            
            # ソート処理
            filtered_stocks.sort(key=lambda x: x['sort_value'])
            
            results = filtered_stocks
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
    """スクリーニング結果をCSV出力（拡張版）"""
    # screening_viewと同じロジックでデータを取得
    form = StockScreeningForm(request.GET)
    
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
        '銘柄コード', '企業名', '市場区分', '業種',
        'PER', 'PBR', '配当利回り(%)', '株価(円)',
        '純利益率(%)', '売上高成長率(%)', '純利益成長率(%)',
        '連続増益', '財務データ年数', '指標取得日'
    ])
    
    # screening_viewのロジックを再利用
    queryset = Stock.objects.prefetch_related(
        Prefetch(
            'indicators',
            queryset=Indicator.objects.order_by('-date')[:1],
            to_attr='latest_indicator'
        ),
        Prefetch(
            'financials',
            queryset=Financial.objects.order_by('-year')[:10],
            to_attr='recent_financials'
        )
    ).filter(indicators__isnull=False).distinct()
    
    # フォームから条件取得
    per_min = form.cleaned_data.get('per_min')
    per_max = form.cleaned_data.get('per_max')
    pbr_min = form.cleaned_data.get('pbr_min')
    pbr_max = form.cleaned_data.get('pbr_max')
    dividend_yield_min = form.cleaned_data.get('dividend_yield_min')
    dividend_yield_max = form.cleaned_data.get('dividend_yield_max')
    price_min = form.cleaned_data.get('price_min')
    price_max = form.cleaned_data.get('price_max')
    consecutive_profit_years = form.cleaned_data.get('consecutive_profit_years')
    revenue_growth_min = form.cleaned_data.get('revenue_growth_min')
    revenue_growth_max = form.cleaned_data.get('revenue_growth_max')
    profit_growth_min = form.cleaned_data.get('profit_growth_min')
    profit_growth_max = form.cleaned_data.get('profit_growth_max')
    profit_margin_min = form.cleaned_data.get('profit_margin_min')
    market = form.cleaned_data.get('market')
    sector = form.cleaned_data.get('sector')
    
    exported_count = 0
    
    for stock in queryset:
        if not stock.latest_indicator:
            continue
            
        indicator = stock.latest_indicator[0]
        financials = stock.recent_financials
        
        # 基本指標フィルタリング
        if per_min and (indicator.per is None or indicator.per < per_min):
            continue
        if per_max and (indicator.per is None or indicator.per > per_max):
            continue
        if pbr_min and (indicator.pbr is None or indicator.pbr < pbr_min):
            continue
        if pbr_max and (indicator.pbr is None or indicator.pbr > pbr_max):
            continue
        if dividend_yield_min and (indicator.dividend_yield is None or indicator.dividend_yield < dividend_yield_min):
            continue
        if dividend_yield_max and (indicator.dividend_yield is None or indicator.dividend_yield > dividend_yield_max):
            continue
        if price_min and (indicator.price is None or indicator.price < price_min):
            continue
        if price_max and (indicator.price is None or indicator.price > price_max):
            continue
        
        # 市場・業種フィルタリング
        if market and market.lower() not in (stock.market or '').lower():
            continue
        if sector and sector.lower() not in (stock.sector or '').lower():
            continue
        
        # 財務データ計算
        profit_margin = None
        revenue_growth = None
        profit_growth = None
        
        if financials and len(financials) > 0:
            latest_financial = financials[0]
            
            # 純利益率計算
            if latest_financial.revenue and latest_financial.net_income and latest_financial.revenue > 0:
                profit_margin = (float(latest_financial.net_income) / float(latest_financial.revenue)) * 100
            
            # 成長率計算
            if len(financials) >= 2:
                previous_financial = financials[1]
                
                # 売上高成長率
                if latest_financial.revenue and previous_financial.revenue and previous_financial.revenue > 0:
                    revenue_growth = ((float(latest_financial.revenue) - float(previous_financial.revenue)) / float(previous_financial.revenue)) * 100
                
                # 純利益成長率
                if latest_financial.net_income and previous_financial.net_income and previous_financial.net_income > 0:
                    profit_growth = ((float(latest_financial.net_income) - float(previous_financial.net_income)) / float(previous_financial.net_income)) * 100
        
        # 財務データフィルタリング
        if profit_margin_min and (profit_margin is None or profit_margin < profit_margin_min):
            continue
        if revenue_growth_min and (revenue_growth is None or revenue_growth < revenue_growth_min):
            continue
        if revenue_growth_max and (revenue_growth is None or revenue_growth > revenue_growth_max):
            continue
        if profit_growth_min and (profit_growth is None or profit_growth < profit_growth_min):
            continue
        if profit_growth_max and (profit_growth is None or profit_growth > profit_growth_max):
            continue
        
        # 連続増益チェック
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
            stock.sector or '-',
            f"{indicator.per:.1f}" if indicator.per else '-',
            f"{indicator.pbr:.2f}" if indicator.pbr else '-',
            f"{indicator.dividend_yield:.2f}" if indicator.dividend_yield else '-',
            f"{indicator.price:.0f}" if indicator.price else '-',
            f"{profit_margin:.1f}" if profit_margin else '-',
            f"{revenue_growth:.1f}" if revenue_growth else '-',
            f"{profit_growth:.1f}" if profit_growth else '-',
            f"{consecutive_profit_years}年連続" if is_consecutive_profit and consecutive_profit_years else ('5年連続' if is_consecutive_profit else '-'),
            len(financials),
            indicator.date.strftime('%Y-%m-%d')
        ])
        exported_count += 1
    
    # CSVの最後に統計行を追加
    writer.writerow([])
    writer.writerow(['--- 統計情報 ---'])
    writer.writerow(['出力件数', exported_count])
    writer.writerow(['検索条件', form.get_search_summary() if form.is_valid() else '無効な条件'])
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
    
    # チャート用データの準備
    chart_data = {
        'financial_years': [],
        'revenues': [],
        'net_incomes': [],
        'indicator_dates': [],
        'prices': []
    }
    
    # 財務データをチャート用に変換
    if financials:
        for financial in reversed(list(financials)):  # 古い順に並び替え
            chart_data['financial_years'].append(str(financial.year))
            chart_data['revenues'].append(float(financial.revenue) if financial.revenue else 0)
            chart_data['net_incomes'].append(float(financial.net_income) if financial.net_income else 0)
    
    # 株価データをチャート用に変換
    if indicators_history:
        for indicator in reversed(list(indicators_history)):  # 古い順に並び替え
            chart_data['indicator_dates'].append(indicator.date.strftime('%Y-%m-%d'))
            chart_data['prices'].append(float(indicator.price) if indicator.price else 0)
    
    # 財務分析データ
    financial_analysis = {'growth_rates': []}
    if len(financials) > 1:
        financials_list = list(financials)
        for i, financial in enumerate(financials_list[:-1]):
            prev_financial = financials[i + 1]
            
            # 売上高成長率
            revenue_growth = None
            if financial.revenue and prev_financial.revenue and prev_financial.revenue != 0:
                revenue_growth = ((financial.revenue - prev_financial.revenue) / prev_financial.revenue) * 100
            
            # 純利益成長率
            profit_growth = None
            if financial.net_income and prev_financial.net_income and prev_financial.net_income != 0:
                profit_growth = ((financial.net_income - prev_financial.net_income) / prev_financial.net_income) * 100
            
            financial_analysis['growth_rates'].append({
                'year': financial.year,
                'revenue_growth': revenue_growth,
                'profit_growth': profit_growth
            })
    
    context = {
        'stock': stock,
        'latest_indicator': latest_indicator,
        'financials': financials,
        'indicators_history': indicators_history,
        'is_consecutive_profit': is_consecutive_profit,
        'chart_data': chart_data,
        'financial_analysis': financial_analysis,
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