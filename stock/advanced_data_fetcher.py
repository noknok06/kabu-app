# stock/advanced_data_fetcher.py - プロフェッショナル版
import yfinance as yf
import pandas as pd
import numpy as np
from decimal import Decimal, InvalidOperation
from .models import Stock, Financial, AdvancedIndicator, TechnicalIndicator
from datetime import datetime, timedelta
import logging
import requests
import json
import time
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

class AdvancedDataFetcher:
    """高度指標データ収集クラス（プロフェッショナル版）"""
    
    @staticmethod
    def safe_decimal_convert(value):
        """安全にDecimal型に変換"""
        if value is None:
            return None
        
        # pandas/numpy NaN値のチェック
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        
        # numpy NaN値のチェック
        try:
            if isinstance(value, (int, float)) and np.isnan(value):
                return None
        except (TypeError, ValueError):
            pass
        
        # 文字列で'nan'の場合
        if isinstance(value, str) and value.lower() in ['nan', 'null', '', 'none']:
            return None
        
        # 無限大の値をチェック
        try:
            if isinstance(value, (int, float)) and (np.isinf(value) or abs(value) > 1e15):
                return None
        except (TypeError, ValueError):
            pass
        
        try:
            decimal_value = Decimal(str(value))
            # 異常に大きな値や小さな値をフィルタ
            if abs(decimal_value) > Decimal('1e15'):
                return None
            return decimal_value
        except (InvalidOperation, ValueError, TypeError, OverflowError):
            return None
    
    @staticmethod
    def fetch_comprehensive_data(stock_code):
        """包括的データ取得（高度指標 + テクニカル + アナリスト予想）"""
        try:
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            
            # 基本情報と財務データ取得
            info = ticker.info
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            # 価格履歴取得（テクニカル分析用）
            hist = ticker.history(period="1y")
            
            results = {}
            
            # 1. 高度財務指標の計算
            advanced_indicators = AdvancedDataFetcher.calculate_advanced_financial_ratios(
                info, financials, balance_sheet, cashflow
            )
            if advanced_indicators:
                results['advanced_indicators'] = advanced_indicators
            
            # 2. テクニカル指標の計算
            if not hist.empty:
                technical_indicators = AdvancedDataFetcher.calculate_technical_indicators(hist)
                if technical_indicators:
                    results['technical_indicators'] = technical_indicators
            
            # 3. リスク指標の計算
            risk_metrics = AdvancedDataFetcher.calculate_risk_metrics(hist, info)
            if risk_metrics:
                results['risk_metrics'] = risk_metrics
            
            # 4. 成長率の計算
            growth_metrics = AdvancedDataFetcher.calculate_growth_metrics(financials)
            if growth_metrics:
                results['growth_metrics'] = growth_metrics
            
            # データベース保存
            success = AdvancedDataFetcher.save_comprehensive_data(stock_code, results)
            
            if success:
                logger.info(f"包括的データ取得成功: {stock_code}")
                return True
            else:
                logger.warning(f"包括的データ保存失敗: {stock_code}")
                return False
                
        except Exception as e:
            logger.error(f"包括的データ取得エラー {stock_code}: {e}")
            return False
    
    @staticmethod
    def calculate_advanced_financial_ratios(info, financials, balance_sheet, cashflow):
        """高度財務指標の計算"""
        ratios = {}
        
        try:
            if financials.empty or balance_sheet.empty:
                return ratios
            
            latest_year = financials.columns[0]
            
            # === 収益性指標 ===
            
            # ROE計算（改良版）
            net_income = AdvancedDataFetcher.get_financial_value(financials, latest_year, [
                'Net Income', 'Net Income Common Stockholders'
            ])
            shareholders_equity = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Total Stockholder Equity', 'Stockholders Equity'
            ])
            
            if net_income and shareholders_equity and shareholders_equity > 0:
                roe = (net_income / shareholders_equity) * 100
                ratios['roe'] = float(roe)
            
            # ROA計算
            total_assets = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Total Assets', 'Total Assets'
            ])
            
            if net_income and total_assets and total_assets > 0:
                roa = (net_income / total_assets) * 100
                ratios['roa'] = float(roa)
            
            # ROIC計算（投下資本利益率）
            operating_income = AdvancedDataFetcher.get_financial_value(financials, latest_year, [
                'Operating Income', 'EBIT'
            ])
            
            if operating_income and shareholders_equity and total_assets:
                tax_rate = 0.3  # 日本の実効税率（概算）
                nopat = operating_income * (1 - tax_rate)
                
                total_debt = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                    'Total Debt', 'Net Debt', 'Long Term Debt'
                ]) or 0
                
                invested_capital = shareholders_equity + total_debt
                if invested_capital > 0:
                    roic = (nopat / invested_capital) * 100
                    ratios['roic'] = float(roic)
            
            # === 利益率指標 ===
            
            revenue = AdvancedDataFetcher.get_financial_value(financials, latest_year, [
                'Total Revenue', 'Revenue'
            ])
            
            if revenue and revenue > 0:
                # 営業利益率
                if operating_income:
                    operating_margin = (operating_income / revenue) * 100
                    ratios['operating_margin'] = float(operating_margin)
                
                # 純利益率
                if net_income:
                    net_margin = (net_income / revenue) * 100
                    ratios['net_margin'] = float(net_margin)
                
                # 売上総利益率
                gross_profit = AdvancedDataFetcher.get_financial_value(financials, latest_year, [
                    'Gross Profit'
                ])
                if gross_profit:
                    gross_margin = (gross_profit / revenue) * 100
                    ratios['gross_margin'] = float(gross_margin)
            
            # === バリュエーション指標（高度） ===
            
            # PEGレシオ計算
            pe_ratio = info.get('trailingPE')
            if pe_ratio and revenue:
                # 簡易的な成長率計算（実際はより詳細な計算が必要）
                growth_rate = AdvancedDataFetcher.estimate_growth_rate(financials, 'revenue')
                if growth_rate and growth_rate > 0:
                    peg_ratio = pe_ratio / growth_rate
                    ratios['peg_ratio'] = float(peg_ratio)
            
            # EV/EBITDA計算
            market_cap = info.get('marketCap')
            if market_cap and operating_income:
                total_debt = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                    'Total Debt', 'Net Debt'
                ]) or 0
                total_cash = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                    'Cash And Cash Equivalents', 'Cash'
                ]) or 0
                
                enterprise_value = market_cap + total_debt - total_cash
                
                # EBITDAの計算（Operating Income + 減価償却費）
                depreciation = AdvancedDataFetcher.get_cashflow_value(cashflow, latest_year, [
                    'Depreciation And Amortization'
                ]) or 0
                
                ebitda = operating_income + abs(depreciation)  # 減価償却費は通常負の値
                
                if ebitda > 0:
                    ev_ebitda = enterprise_value / ebitda
                    ratios['ev_ebitda'] = float(ev_ebitda)
            
            # === 安全性指標 ===
            
            # 自己資本比率
            if shareholders_equity and total_assets and total_assets > 0:
                equity_ratio = (shareholders_equity / total_assets) * 100
                ratios['equity_ratio'] = float(equity_ratio)
            
            # 流動比率
            current_assets = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Current Assets'
            ])
            current_liabilities = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Current Liabilities'
            ])
            
            if current_assets and current_liabilities and current_liabilities > 0:
                current_ratio = current_assets / current_liabilities
                ratios['current_ratio'] = float(current_ratio)
            
            # 当座比率
            cash_and_equivalents = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Cash And Cash Equivalents'
            ]) or 0
            
            accounts_receivable = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Accounts Receivable', 'Net Receivables'
            ]) or 0
            
            quick_assets = cash_and_equivalents + accounts_receivable
            if current_liabilities and current_liabilities > 0:
                quick_ratio = quick_assets / current_liabilities
                ratios['quick_ratio'] = float(quick_ratio)
            
            # D/Eレシオ
            total_debt = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Total Debt', 'Net Debt'
            ])
            
            if total_debt and shareholders_equity and shareholders_equity > 0:
                debt_equity_ratio = total_debt / shareholders_equity
                ratios['debt_equity_ratio'] = float(debt_equity_ratio)
            
            # インタレストカバレッジ
            interest_expense = AdvancedDataFetcher.get_financial_value(financials, latest_year, [
                'Interest Expense'
            ])
            
            if operating_income and interest_expense and interest_expense > 0:
                interest_coverage = operating_income / interest_expense
                ratios['interest_coverage'] = float(interest_coverage)
            
            # === 効率性指標 ===
            
            # 総資産回転率
            if revenue and total_assets and total_assets > 0:
                asset_turnover = revenue / total_assets
                ratios['asset_turnover'] = float(asset_turnover)
            
            # 棚卸回転率
            inventory = AdvancedDataFetcher.get_balance_value(balance_sheet, latest_year, [
                'Inventory'
            ])
            cost_of_revenue = AdvancedDataFetcher.get_financial_value(financials, latest_year, [
                'Cost Of Revenue'
            ])
            
            if cost_of_revenue and inventory and inventory > 0:
                inventory_turnover = cost_of_revenue / inventory
                ratios['inventory_turnover'] = float(inventory_turnover)
            
            # 売掛金回転率
            if revenue and accounts_receivable and accounts_receivable > 0:
                receivables_turnover = revenue / accounts_receivable
                ratios['receivables_turnover'] = float(receivables_turnover)
            
        except Exception as e:
            logger.error(f"高度財務指標計算エラー: {e}")
        
        return ratios
    
    @staticmethod
    def calculate_technical_indicators(price_data):
        """テクニカル指標計算"""
        indicators = {}
        
        try:
            prices = price_data['Close']
            volumes = price_data['Volume']
            highs = price_data['High']
            lows = price_data['Low']
            
            # 移動平均線
            indicators['ma_5'] = float(prices.rolling(5).mean().iloc[-1])
            indicators['ma_25'] = float(prices.rolling(25).mean().iloc[-1])
            indicators['ma_75'] = float(prices.rolling(75).mean().iloc[-1])
            
            if len(prices) >= 200:
                indicators['ma_200'] = float(prices.rolling(200).mean().iloc[-1])
            
            # RSI計算
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi'] = float(rsi.iloc[-1])
            
            # MACD計算
            exp1 = prices.ewm(span=12).mean()
            exp2 = prices.ewm(span=26).mean()
            macd = exp1 - exp2
            macd_signal = macd.ewm(span=9).mean()
            indicators['macd'] = float(macd.iloc[-1])
            indicators['macd_signal'] = float(macd_signal.iloc[-1])
            
            # ストキャスティクス
            low_14 = lows.rolling(14).min()
            high_14 = highs.rolling(14).max()
            k_percent = 100 * ((prices - low_14) / (high_14 - low_14))
            indicators['stochastic_k'] = float(k_percent.iloc[-1])
            
            # ボリンジャーバンド
            sma_20 = prices.rolling(20).mean()
            std_20 = prices.rolling(20).std()
            indicators['bb_upper'] = float(sma_20.iloc[-1] + (std_20.iloc[-1] * 2))
            indicators['bb_middle'] = float(sma_20.iloc[-1])
            indicators['bb_lower'] = float(sma_20.iloc[-1] - (std_20.iloc[-1] * 2))
            
            # ボラティリティ
            returns = prices.pct_change().dropna()
            volatility = returns.rolling(30).std() * np.sqrt(252)  # 年率換算
            indicators['volatility'] = float(volatility.iloc[-1])
            
            # モメンタム
            indicators['momentum_1d'] = float(((prices.iloc[-1] - prices.iloc[-2]) / prices.iloc[-2]) * 100)
            indicators['momentum_5d'] = float(((prices.iloc[-1] - prices.iloc[-6]) / prices.iloc[-6]) * 100)
            indicators['momentum_20d'] = float(((prices.iloc[-1] - prices.iloc[-21]) / prices.iloc[-21]) * 100)
            
            # トレンド判定
            ma_5 = indicators.get('ma_5')
            ma_25 = indicators.get('ma_25')
            ma_75 = indicators.get('ma_75')
            
            if ma_5 and ma_25 and ma_75:
                if ma_5 > ma_25 > ma_75:
                    indicators['trend'] = '強い上昇トレンド'
                elif ma_5 > ma_25:
                    indicators['trend'] = '上昇トレンド'
                elif ma_5 < ma_25 < ma_75:
                    indicators['trend'] = '強い下降トレンド'
                elif ma_5 < ma_25:
                    indicators['trend'] = '下降トレンド'
                else:
                    indicators['trend'] = 'レンジ'
            
            # サポート・レジスタンス（簡易版）
            recent_prices = prices.tail(20)
            indicators['support_level'] = float(recent_prices.min())
            indicators['resistance_level'] = float(recent_prices.max())
            
        except Exception as e:
            logger.error(f"テクニカル指標計算エラー: {e}")
        
        return indicators
    
    @staticmethod
    def calculate_risk_metrics(price_data, info):
        """リスク指標計算"""
        risk_metrics = {}
        
        try:
            if price_data.empty:
                return risk_metrics
            
            prices = price_data['Close']
            returns = prices.pct_change().dropna()
            
            # VaR（Value at Risk）計算
            var_95 = np.percentile(returns, 5) * 100  # 5%VaR
            var_99 = np.percentile(returns, 1) * 100  # 1%VaR
            
            risk_metrics['var_95'] = float(var_95)
            risk_metrics['var_99'] = float(var_99)
            
            # 最大ドローダウン
            peak = prices.expanding().max()
            drawdown = (prices - peak) / peak
            max_drawdown = drawdown.min() * 100
            
            risk_metrics['max_drawdown'] = float(max_drawdown)
            
            # シャープレシオ（簡易版）
            risk_free_rate = 0.001  # 日本の無リスク金利（概算）
            excess_returns = returns - risk_free_rate/252
            if returns.std() > 0:
                sharpe_ratio = (excess_returns.mean() / returns.std()) * np.sqrt(252)
                risk_metrics['sharpe_ratio'] = float(sharpe_ratio)
            
            # ベータ値（市場との相関、簡易版）
            # 実際の実装では日経平均やTOPIXとの相関を計算
            risk_metrics['beta'] = 1.0  # プレースホルダー
            
        except Exception as e:
            logger.error(f"リスク指標計算エラー: {e}")
        
        return risk_metrics
    
    @staticmethod
    def calculate_growth_metrics(financials):
        """成長率指標計算"""
        growth_metrics = {}
        
        try:
            if financials.empty or len(financials.columns) < 3:
                return growth_metrics
            
            years = sorted(financials.columns, reverse=True)  # 新しい順
            
            # 1年成長率
            if len(years) >= 2:
                current_year = years[0]
                previous_year = years[1]
                
                # 売上高成長率
                revenue_current = AdvancedDataFetcher.get_financial_value(financials, current_year, ['Total Revenue'])
                revenue_previous = AdvancedDataFetcher.get_financial_value(financials, previous_year, ['Total Revenue'])
                
                if revenue_current and revenue_previous and revenue_previous > 0:
                    revenue_growth = ((revenue_current - revenue_previous) / revenue_previous) * 100
                    growth_metrics['revenue_growth_1y'] = float(revenue_growth)
                
                # 営業利益成長率
                operating_current = AdvancedDataFetcher.get_financial_value(financials, current_year, ['Operating Income'])
                operating_previous = AdvancedDataFetcher.get_financial_value(financials, previous_year, ['Operating Income'])
                
                if operating_current and operating_previous and operating_previous > 0:
                    operating_growth = ((operating_current - operating_previous) / operating_previous) * 100
                    growth_metrics['operating_growth_1y'] = float(operating_growth)
                
                # 純利益成長率
                net_current = AdvancedDataFetcher.get_financial_value(financials, current_year, ['Net Income'])
                net_previous = AdvancedDataFetcher.get_financial_value(financials, previous_year, ['Net Income'])
                
                if net_current and net_previous and net_previous > 0:
                    net_growth = ((net_current - net_previous) / net_previous) * 100
                    growth_metrics['net_growth_1y'] = float(net_growth)
            
            # 3年CAGR
            if len(years) >= 4:  # 3年間の成長率には4年分のデータが必要
                start_year = years[3]
                end_year = years[0]
                
                # 売上高CAGR
                revenue_start = AdvancedDataFetcher.get_financial_value(financials, start_year, ['Total Revenue'])
                revenue_end = AdvancedDataFetcher.get_financial_value(financials, end_year, ['Total Revenue'])
                
                if revenue_start and revenue_end and revenue_start > 0:
                    revenue_cagr = (pow(revenue_end / revenue_start, 1/3) - 1) * 100
                    growth_metrics['revenue_cagr_3y'] = float(revenue_cagr)
                
                # 営業利益CAGR
                operating_start = AdvancedDataFetcher.get_financial_value(financials, start_year, ['Operating Income'])
                operating_end = AdvancedDataFetcher.get_financial_value(financials, end_year, ['Operating Income'])
                
                if operating_start and operating_end and operating_start > 0:
                    operating_cagr = (pow(operating_end / operating_start, 1/3) - 1) * 100
                    growth_metrics['operating_cagr_3y'] = float(operating_cagr)
                
                # 純利益CAGR
                net_start = AdvancedDataFetcher.get_financial_value(financials, start_year, ['Net Income'])
                net_end = AdvancedDataFetcher.get_financial_value(financials, end_year, ['Net Income'])
                
                if net_start and net_end and net_start > 0:
                    net_cagr = (pow(net_end / net_start, 1/3) - 1) * 100
                    growth_metrics['net_cagr_3y'] = float(net_cagr)
            
        except Exception as e:
            logger.error(f"成長率指標計算エラー: {e}")
        
        return growth_metrics
    
    @staticmethod
    def get_financial_value(financials, year, keys):
        """財務データから値を取得"""
        for key in keys:
            if key in financials.index:
                value = financials.loc[key, year]
                if pd.notna(value):
                    return float(value)
        return None
    
    @staticmethod
    def get_balance_value(balance_sheet, year, keys):
        """貸借対照表から値を取得"""
        for key in keys:
            if key in balance_sheet.index:
                value = balance_sheet.loc[key, year]
                if pd.notna(value):
                    return float(value)
        return None
    
    @staticmethod
    def get_cashflow_value(cashflow, year, keys):
        """キャッシュフローから値を取得"""
        for key in keys:
            if key in cashflow.index:
                value = cashflow.loc[key, year]
                if pd.notna(value):
                    return float(value)
        return None
    
    @staticmethod
    def estimate_growth_rate(financials, metric_type):
        """成長率推定"""
        if financials.empty or len(financials.columns) < 3:
            return None
        
        try:
            years = sorted(financials.columns, reverse=True)
            
            if metric_type == 'revenue':
                values = []
                for year in years[:3]:  # 最新3年
                    value = AdvancedDataFetcher.get_financial_value(financials, year, ['Total Revenue'])
                    if value:
                        values.append(value)
                
                if len(values) >= 2:
                    # 単純な成長率計算
                    growth = ((values[0] - values[-1]) / values[-1]) * 100 / (len(values) - 1)
                    return growth
            
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def save_comprehensive_data(stock_code, data):
        """包括的データの保存"""
        try:
            stock = Stock.objects.get(code=stock_code)
            today = timezone.now().date()
            
            # 高度指標の保存
            if 'advanced_indicators' in data:
                advanced_data = data['advanced_indicators']
                growth_data = data.get('growth_metrics', {})
                
                # 成長率データをマージ
                advanced_data.update(growth_data)
                
                # Decimal変換とバリデーション
                validated_data = {}
                for key, value in advanced_data.items():
                    if value is not None:
                        converted_value = AdvancedDataFetcher.safe_decimal_convert(value)
                        if converted_value is not None:
                            validated_data[key] = converted_value
                
                if validated_data:
                    AdvancedIndicator.objects.update_or_create(
                        stock=stock,
                        date=today,
                        defaults=validated_data
                    )
            
            # テクニカル指標の保存
            if 'technical_indicators' in data:
                technical_data = data['technical_indicators']
                
                # Decimal変換とバリデーション
                validated_technical = {}
                for key, value in technical_data.items():
                    if value is not None and key != 'trend':  # trendは文字列
                        converted_value = AdvancedDataFetcher.safe_decimal_convert(value)
                        if converted_value is not None:
                            validated_technical[key] = converted_value
                    elif key == 'trend':
                        validated_technical[key] = str(value)
                
                if validated_technical:
                    TechnicalIndicator.objects.update_or_create(
                        stock=stock,
                        date=today,
                        defaults=validated_technical
                    )
            
            return True
            
        except Stock.DoesNotExist:
            logger.error(f"銘柄が見つかりません: {stock_code}")
            return False
        except Exception as e:
            logger.error(f"包括的データ保存エラー {stock_code}: {e}")
            return False
    
    @staticmethod
    def fetch_analyst_estimates(stock_code):
        """アナリスト予想データ取得（外部API使用）"""
        try:
            # 実際の実装では、Bloomberg API、Thomson Reuters、
            # または日本の証券会社APIを使用
            # ここではサンプル実装
            
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            
            # Yahoo Financeからアナリスト情報取得（限定的）
            info = ticker.info
            
            analyst_data = {}
            
            # 目標株価
            target_high = info.get('targetHighPrice')
            target_mean = info.get('targetMeanPrice')
            target_low = info.get('targetLowPrice')
            
            if target_mean:
                analyst_data['target_price_avg'] = float(target_mean)
            if target_high:
                analyst_data['target_price_high'] = float(target_high)
            if target_low:
                analyst_data['target_price_low'] = float(target_low)
            
            # レーティング
            recommendation = info.get('recommendationKey')
            if recommendation:
                # 簡易的なレーティング変換
                rating_map = {
                    'strong_buy': (5, 0, 0),
                    'buy': (3, 2, 0),
                    'hold': (1, 3, 1),
                    'sell': (0, 2, 3),
                    'strong_sell': (0, 0, 5)
                }
                
                if recommendation in rating_map:
                    buy, hold, sell = rating_map[recommendation]
                    analyst_data['rating_buy'] = buy
                    analyst_data['rating_hold'] = hold
                    analyst_data['rating_sell'] = sell
            
            # データベース保存
            if analyst_data:
                AdvancedDataFetcher.save_analyst_estimates(stock_code, analyst_data)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"アナリスト予想取得エラー {stock_code}: {e}")
            return False
    
    @staticmethod
    def save_analyst_estimates(stock_code, analyst_data):
        """アナリスト予想データ保存"""
        try:
            from .models import AnalystEstimate
            
            stock = Stock.objects.get(code=stock_code)
            current_year = datetime.now().year
            
            AnalystEstimate.objects.update_or_create(
                stock=stock,
                target_year=current_year,
                defaults=analyst_data
            )
            
            logger.info(f"アナリスト予想保存成功: {stock_code}")
            return True
            
        except Exception as e:
            logger.error(f"アナリスト予想保存エラー {stock_code}: {e}")
            return False
    
    @staticmethod
    def batch_update_comprehensive_data(stock_codes=None, limit=20):
        """包括的データの一括更新"""
        try:
            if stock_codes:
                target_stocks = Stock.objects.filter(code__in=stock_codes)
            else:
                target_stocks = Stock.objects.filter(is_active=True)[:limit]
            
            success_count = 0
            total_count = len(target_stocks)
            
            for i, stock in enumerate(target_stocks, 1):
                logger.info(f"包括的データ更新: {i}/{total_count} - {stock.code}")
                
                try:
                    # 高度指標とテクニカル指標の更新
                    if AdvancedDataFetcher.fetch_comprehensive_data(stock.code):
                        success_count += 1
                    
                    # アナリスト予想の更新（オプション）
                    AdvancedDataFetcher.fetch_analyst_estimates(stock.code)
                    
                    # APIレート制限対策
                    time.sleep(1.5)
                    
                except Exception as e:
                    logger.error(f"銘柄処理エラー {stock.code}: {e}")
                    continue
            
            logger.info(f"包括的データ更新完了: {success_count}/{total_count}")
            return success_count
            
        except Exception as e:
            logger.error(f"一括更新エラー: {e}")
            return 0