# stock/admin.py
from django.contrib import admin
from .models import Stock, Financial, Indicator

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'market', 'sector', 'created_at']
    list_filter = ['market', 'sector']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['code']

@admin.register(Financial)
class FinancialAdmin(admin.ModelAdmin):
    list_display = ['stock', 'year', 'revenue', 'net_income', 'eps']
    list_filter = ['year']
    search_fields = ['stock__code', 'stock__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-year', 'stock__code']

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ['stock', 'date', 'per', 'pbr', 'dividend_yield', 'price']
    list_filter = ['date']
    search_fields = ['stock__code', 'stock__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date', 'stock__code']
