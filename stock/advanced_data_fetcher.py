# stock/advanced_data_fetcher.py (修正版)
import yfinance as yf
import pandas as pd
import numpy as np
from decimal import Decimal, InvalidOperation
from .models import Stock, Financial
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AdvancedDataFetcher:
    """高度指標データ収集クラス（修正版）"""
    
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
    def fetch_advanced_indicators(stock_code):
        """高度指標の取得・計算（修正版）"""
        try:
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            
            # 基本情報と財務データ取得
            info = ticker.info
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            # 計算結果格納
            advanced_data = {}
            
            # === 1. Yahoo Finance info から直接取得可能な指標 ===
            advanced_data.update(AdvancedDataFetcher.extract_from_info(info))
            
            # === 2. 財務諸表から計算する指標 ===
            financial_ratios = AdvancedDataFetcher.calculate_financial_ratios(
                financials, balance_sheet, cashflow
            )
            advanced_data.update(financial_ratios)
            
            # === 3. 市場データから計算する指標 ===
            market_ratios = AdvancedDataFetcher.calculate_market_ratios(
                ticker, info, financials
            )
            advanced_data.update(market_ratios)
            
            # デバッグ: 取得されたデータを確認
            logger.info(f"取得データ {stock_code}: {list(advanced_data.keys())}")
            
            # データベース保存
            success = AdvancedDataFetcher.save_advanced_indicators(
                stock_code, advanced_data
            )
            
            if success:
                logger.info(f"高度指標取得成功: {stock_code}")
                return True
            else:
                logger.warning(f"高度指標保存失敗: {stock_code}")
                return False
                
        except Exception as e:
            logger.error(f"高度指標取得エラー {stock_code}: {e}")
            return False
    
    @staticmethod
    def extract_from_info(info):
        """Yahoo Finance info から指標抽出（フィールド名修正版）"""
        data = {}
        
        try:
            # ROE (Return on Equity)
            roe = info.get('returnOnEquity')
            if roe is not None:
                data['roe'] = float(roe) * 100  # パーセント表示
            
            # ROA (Return on Assets)
            roa = info.get('returnOnAssets')
            if roa is not None:
                data['roa'] = float(roa) * 100
            
            # 負債比率関連
            debt_to_equity = info.get('debtToEquity')
            if debt_to_equity is not None:
                data['debt_equity_ratio'] = float(debt_to_equity)
            
            # 流動比率
            current_ratio = info.get('currentRatio')
            if current_ratio is not None:
                data['current_ratio'] = float(current_ratio)
            
            # 自己資本比率（計算で求める場合もある）
            # info から直接取得できない場合は、財務諸表から計算
            
            # 総資産回転率
            asset_turnover = info.get('assetTurnover')
            if asset_turnover is not None:
                data['asset_turnover'] = float(asset_turnover)
            
            # PSR（Price to Sales Ratio）
            price_to_sales = info.get('priceToSalesTrailing12Months')
            if price_to_sales is not None:
                data['psr'] = float(price_to_sales)
            
            logger.info(f"info抽出完了: {len(data)}項目")
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Info抽出エラー: {e}")
        
        return data
    
    @staticmethod
    def calculate_financial_ratios(financials, balance_sheet, cashflow):
        """財務諸表から比率計算（修正版）"""
        ratios = {}
        
        try:
            if financials.empty or balance_sheet.empty:
                logger.info("財務諸表データが空です")
                return ratios
            
            # 最新年度のデータを取得
            latest_year = financials.columns[0]
            logger.info(f"最新年度: {latest_year}")
            
            # === 収益性指標 ===
            # ROIC (Return on Invested Capital)
            roic = AdvancedDataFetcher.calculate_roic(
                financials, balance_sheet, latest_year
            )
            if roic is not None:
                ratios['roic'] = roic
            
            # === 効率性指標 ===
            # 棚卸回転率
            inventory_turnover = AdvancedDataFetcher.calculate_inventory_turnover(
                financials, balance_sheet, latest_year
            )
            if inventory_turnover is not None:
                ratios['inventory_turnover'] = inventory_turnover
            
            # === 安全性指標 ===
            # 自己資本比率
            equity_ratio = AdvancedDataFetcher.calculate_equity_ratio(
                balance_sheet, latest_year
            )
            if equity_ratio is not None:
                ratios['equity_ratio'] = equity_ratio
            
            logger.info(f"財務比率計算完了: {len(ratios)}項目")
                
        except Exception as e:
            logger.warning(f"財務比率計算エラー: {e}")
        
        return ratios
    
    @staticmethod
    def calculate_market_ratios(ticker, info, financials):
        """市場関連指標の計算"""
        ratios = {}
        
        try:
            market_cap = info.get('marketCap')
            
            if not financials.empty and market_cap:
                latest_year = financials.columns[0]
                
                # PSR (Price to Sales Ratio) - infoで取得できない場合の計算
                if 'psr' not in ratios:  # infoで取得できなかった場合
                    revenue = None
                    for revenue_key in ['Total Revenue', 'Revenue', 'totalRevenue']:
                        if revenue_key in financials.index:
                            revenue = financials.loc[revenue_key, latest_year]
                            break
                    
                    if revenue and not pd.isna(revenue) and revenue > 0:
                        psr = market_cap / revenue
                        ratios['psr'] = float(psr)
                
                # EV/EBITDA
                ev_ebitda = AdvancedDataFetcher.calculate_ev_ebitda(
                    ticker, info, financials, latest_year
                )
                if ev_ebitda is not None:
                    ratios['ev_ebitda'] = ev_ebitda
            
            logger.info(f"市場比率計算完了: {len(ratios)}項目")
            
        except Exception as e:
            logger.warning(f"市場比率計算エラー: {e}")
        
        return ratios
    
    @staticmethod
    def calculate_roic(financials, balance_sheet, year):
        """ROIC計算"""
        try:
            # Operating Income を探す
            operating_income = None
            for key in ['Operating Income', 'EBIT', 'operatingIncome']:
                if key in financials.index:
                    operating_income = financials.loc[key, year]
                    break
            
            if operating_income is None or pd.isna(operating_income):
                return None
            
            tax_rate = 0.3  # 日本の法人税率（概算）
            nopat = operating_income * (1 - tax_rate)
            
            # Invested Capital
            total_equity = None
            for key in ['Total Stockholder Equity', 'Total Equity', 'totalStockholderEquity']:
                if key in balance_sheet.index:
                    total_equity = balance_sheet.loc[key, year]
                    break
            
            if total_equity is None or pd.isna(total_equity):
                return None
            
            invested_capital = total_equity
            
            # Total Debt を加算（もしあれば）
            total_debt = None
            for key in ['Total Debt', 'Net Debt', 'totalDebt']:
                if key in balance_sheet.index:
                    total_debt = balance_sheet.loc[key, year]
                    break
            
            if total_debt and not pd.isna(total_debt):
                invested_capital += total_debt
            
            if invested_capital > 0:
                roic = (nopat / invested_capital) * 100
                return float(roic)
            
        except Exception as e:
            logger.warning(f"ROIC計算エラー: {e}")
        
        return None
    
    @staticmethod
    def calculate_inventory_turnover(financials, balance_sheet, year):
        """棚卸回転率計算"""
        try:
            # 売上原価
            cogs = None
            for key in ['Cost Of Revenue', 'Cost of Revenue', 'costOfRevenue']:
                if key in financials.index:
                    cogs = financials.loc[key, year]
                    break
            
            # 棚卸資産
            inventory = None
            for key in ['Inventory', 'inventory']:
                if key in balance_sheet.index:
                    inventory = balance_sheet.loc[key, year]
                    break
            
            if cogs and inventory and not pd.isna(cogs) and not pd.isna(inventory) and inventory > 0:
                turnover = cogs / inventory
                return float(turnover)
            
        except Exception as e:
            logger.warning(f"棚卸回転率計算エラー: {e}")
        
        return None
    
    @staticmethod
    def calculate_equity_ratio(balance_sheet, year):
        """自己資本比率計算"""
        try:
            # Total Stockholder Equity
            total_equity = None
            for key in ['Total Stockholder Equity', 'Total Equity', 'totalStockholderEquity']:
                if key in balance_sheet.index:
                    total_equity = balance_sheet.loc[key, year]
                    break
            
            # Total Assets
            total_assets = None
            for key in ['Total Assets', 'totalAssets']:
                if key in balance_sheet.index:
                    total_assets = balance_sheet.loc[key, year]
                    break
            
            if (total_equity and total_assets and 
                not pd.isna(total_equity) and not pd.isna(total_assets) and 
                total_assets > 0):
                equity_ratio = (total_equity / total_assets) * 100
                return float(equity_ratio)
            
        except Exception as e:
            logger.warning(f"自己資本比率計算エラー: {e}")
        
        return None
    
    @staticmethod
    def calculate_ev_ebitda(ticker, info, financials, year):
        """EV/EBITDA計算"""
        try:
            # Enterprise Value
            market_cap = info.get('marketCap')
            total_debt = info.get('totalDebt', 0) or 0
            total_cash = info.get('totalCash', 0) or 0
            
            if market_cap:
                enterprise_value = market_cap + total_debt - total_cash
            else:
                return None
            
            # EBITDA
            ebitda = None
            for key in ['EBITDA', 'ebitda']:
                if key in financials.index:
                    ebitda = financials.loc[key, year]
                    break
            
            if ebitda is None or pd.isna(ebitda):
                # EBITDAがない場合は営業利益から推定
                operating_income = None
                for key in ['Operating Income', 'EBIT', 'operatingIncome']:
                    if key in financials.index:
                        operating_income = financials.loc[key, year]
                        break
                
                if operating_income and not pd.isna(operating_income):
                    # 簡易的にEBITDAとして使用（減価償却費は無視）
                    ebitda = operating_income
                else:
                    return None
            
            if ebitda > 0:
                ev_ebitda = enterprise_value / ebitda
                return float(ev_ebitda)
            
        except Exception as e:
            logger.warning(f"EV/EBITDA計算エラー: {e}")
        
        return None
    
    @staticmethod
    def save_advanced_indicators(stock_code, data):
        """高度指標の保存（フィールドチェック付き）"""
        try:
            # AdvancedIndicatorモデルを動的に取得
            from .models import AdvancedIndicator
            
            # モデルの有効フィールドを取得
            valid_fields = set(field.name for field in AdvancedIndicator._meta.get_fields())
            valid_fields.update(['stock', 'date', 'created_at', 'updated_at'])  # リレーションフィールドも追加
            
            logger.info(f"有効フィールド: {valid_fields}")
            
            stock = Stock.objects.get(code=stock_code)
            today = datetime.now().date()
            
            # 有効なフィールドのみをフィルタリング
            filtered_data = {}
            for key, value in data.items():
                if key in valid_fields and value is not None:
                    try:
                        # 異常値のチェック
                        if isinstance(value, (int, float)) and abs(value) > 1e15:
                            logger.warning(f"異常値スキップ {key}: {value}")
                            continue
                        
                        converted_value = AdvancedDataFetcher.safe_decimal_convert(value)
                        if converted_value is not None:
                            filtered_data[key] = converted_value
                        else:
                            logger.warning(f"変換失敗 {key}: {value}")
                    except Exception as e:
                        logger.warning(f"フィールド処理エラー {key}: {e}")
                        continue
                else:
                    if key not in valid_fields:
                        logger.warning(f"無効フィールドスキップ: {key}")
            
            if not filtered_data:
                logger.warning(f"保存可能なデータがありません: {stock_code}")
                return False
            
            logger.info(f"保存データ {stock_code}: {list(filtered_data.keys())}")
            
            # 既存データの更新または新規作成
            advanced_indicator, created = AdvancedIndicator.objects.update_or_create(
                stock=stock,
                date=today,
                defaults=filtered_data
            )
            
            action = "新規作成" if created else "更新"
            logger.info(f"高度指標{action}: {stock_code} - {len(filtered_data)}項目")
            
            return True
            
        except ImportError:
            logger.error("AdvancedIndicatorモデルが見つかりません")
            return False
        except Stock.DoesNotExist:
            logger.error(f"銘柄が見つかりません: {stock_code}")
            return False
        except Exception as e:
            logger.error(f"高度指標保存エラー {stock_code}: {e}")
            return False

# テスト用関数
def test_single_stock(stock_code='7203'):
    """単一銘柄での動作テスト"""
    print(f"=== {stock_code} テスト開始 ===")
    
    try:
        import yfinance as yf
        
        # 1. 基本接続テスト
        symbol = f"{stock_code}.T"
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        print(f"企業名: {info.get('longName', 'N/A')}")
        print(f"セクター: {info.get('sector', 'N/A')}")
        
        # 2. 取得可能な指標確認
        indicators = {}
        
        # ROE
        roe = info.get('returnOnEquity')
        if roe:
            indicators['ROE'] = f"{float(roe)*100:.2f}%"
        
        # ROA
        roa = info.get('returnOnAssets')
        if roa:
            indicators['ROA'] = f"{float(roa)*100:.2f}%"
        
        # PER
        pe = info.get('trailingPE')
        if pe:
            indicators['PER'] = f"{float(pe):.2f}"
        
        # PBR
        pb = info.get('priceToBook')
        if pb:
            indicators['PBR'] = f"{float(pb):.2f}"
        
        print("\n取得可能な指標:")
        for key, value in indicators.items():
            print(f"  {key}: {value}")
        
        # 3. 財務諸表確認
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet
        
        print(f"\n財務諸表サイズ: {financials.shape if not financials.empty else '0x0'}")
        print(f"貸借対照表サイズ: {balance_sheet.shape if not balance_sheet.empty else '0x0'}")
        
        if not financials.empty:
            print(f"最新年度: {financials.columns[0]}")
            print("財務諸表項目（最初の10項目）:")
            for i, item in enumerate(financials.index[:10]):
                print(f"  {item}")
        
        return True
        
    except Exception as e:
        print(f"テストエラー: {e}")
        return False

if __name__ == "__main__":
    test_single_stock('7203')