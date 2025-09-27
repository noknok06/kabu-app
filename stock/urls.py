# stock/urls.py
from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    # メインページ
    path('', views.dashboard_view, name='dashboard'),
    
    # スクリーニング機能
    path('screening/', views.screening_view, name='screening'),
    path('export-csv/', views.export_csv, name='export_csv'),
    
    # 個別銘柄詳細
    path('stock/<str:stock_code>/', views.stock_detail_view, name='stock_detail'),
    
    # API エンドポイント（AJAX用）
    path('api/search/', views.api_stock_search, name='api_stock_search'),
    
    # 管理者用データ更新
    path('admin/update/', views.update_stock_data_view, name='admin_update'),
]