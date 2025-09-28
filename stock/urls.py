# stock/urls.py - 比較機能追加版
from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    # ダッシュボード
    path('', views.dashboard_view, name='dashboard'),
    
    # スクリーニング
    path('screening/', views.screening_view, name='screening'),
    
    # 銘柄比較機能
    path('comparison/', views.comparison_view, name='comparison'),
    path('comparison/export/csv/', views.comparison_export_csv, name='comparison_export_csv'),
    path('comparison/export/pdf/', views.comparison_export_pdf, name='comparison_export_pdf'),
    
    # 個別銘柄詳細
    path('stock/<str:stock_code>/', views.stock_detail_view, name='stock_detail'),
    
    # CSV出力
    path('export/csv/', views.export_csv, name='export_csv'),
    
    # API エンドポイント
    path('api/search/', views.api_stock_search, name='api_search'),
    path('api/top-performers/', views.api_top_performers, name='api_top_performers'),
    path('api/market-news/', views.api_market_news, name='api_market_news'),
    path('api/sector-performance/', views.api_sector_performance, name='api_sector_performance'),
    path('api/market-data/', views.api_market_data, name='api_market_data'),
    path('api/watchlist/add/', views.api_watchlist_add, name='api_watchlist_add'),
    path('api/watchlist/create/', views.api_watchlist_create, name='api_watchlist_create'),
]