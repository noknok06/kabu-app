# stock/urls.py - プロフェッショナル版
from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    # === メインページ ===
    path('', views.dashboard_view, name='dashboard'),
    
    # === スクリーニング機能 ===
    path('screening/', views.screening_view, name='screening'),
    path('export-csv/', views.export_csv, name='export_csv'),
    
    # === 個別銘柄詳細 ===
    path('stock/<str:stock_code>/', views.stock_detail_view, name='stock_detail'),
    
    # === API エンドポイント（AJAX用） ===
    
    # 基本検索API
    path('api/search/', views.api_stock_search, name='api_stock_search'),
    
    # マーケットデータAPI
    path('api/market-data/', views.api_market_data, name='api_market_data'),
    path('api/top-performers/', views.api_top_performers, name='api_top_performers'),
    path('api/market-news/', views.api_market_news, name='api_market_news'),
    path('api/sector-performance/', views.api_sector_performance, name='api_sector_performance'),
    
    # ウォッチリスト機能
    path('api/watchlist/add/', views.api_watchlist_add, name='api_watchlist_add'),
    
    # === 管理者用データ更新 ===
    # path('admin/update/', views.update_stock_data_view, name='admin_update'),
]