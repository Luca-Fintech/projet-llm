import yfinance as yf
from datetime import datetime
from typing import Dict


class FinancialDataAgent:
    def __init__(self):
        """Agent pour récupérer les données financières via yfinance."""
        pass
    
    def get_company_data(self, ticker: str) -> Dict:
        """
        Récupère les données financières complètes d'une entreprise.
        
        Args:
            ticker: Le ticker de l'entreprise (ex: META, AAPL)
        
        Returns:
            Dict avec les données structurées
        """
        print(f"\n📊 Récupération des données pour {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            data = {
                "ticker": ticker,
                "name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary"),
                "employees": info.get("fullTimeEmployees"),
                
                # Prix et valorisation
                "current_price": info.get("currentPrice"),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "52week_high": info.get("fiftyTwoWeekHigh"),
                "52week_low": info.get("fiftyTwoWeekLow"),
                "52week_change": info.get("52WeekChange"),
                
                # Revenus et profits
                "revenue": info.get("totalRevenue"),
                "revenue_growth": info.get("revenueGrowth"),
                "revenue_per_share": info.get("revenuePerShare"),
                "gross_profit": info.get("grossProfits"),
                "ebitda": info.get("ebitda"),
                "net_income": info.get("netIncomeToCommon"),
                "earnings_growth": info.get("earningsGrowth"),
                
                # Marges
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "gross_margin": info.get("grossMargins"),
                "ebitda_margin": info.get("ebitdaMargins"),
                
                # Ratios de valorisation
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "price_to_sales": info.get("priceToSalesTrailing12Months"),
                "ev_to_revenue": info.get("enterpriseToRevenue"),
                "ev_to_ebitda": info.get("enterpriseToEbitda"),
                
                # Dette et liquidité
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio"),
                
                # Rentabilité
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "roic": info.get("returnOnCapital"),
                
                # Dividendes
                "dividend_rate": info.get("dividendRate"),
                "dividend_yield": info.get("dividendYield"),
                "payout_ratio": info.get("payoutRatio"),
                
                # Cash flow
                "free_cash_flow": info.get("freeCashflow"),
                "operating_cash_flow": info.get("operatingCashflow"),
                
                # Volume et beta
                "volume": info.get("volume"),
                "avg_volume": info.get("averageVolume"),
                "beta": info.get("beta"),
                
                # Recommandations analystes
                "target_price": info.get("targetMeanPrice"),
                "recommendation": info.get("recommendationKey"),
                "number_of_analysts": info.get("numberOfAnalystOpinions"),
                
                "retrieved_at": datetime.now().isoformat()
            }
            
            print(f"✓ Données récupérées pour {data['name']}")
            return data
            
        except Exception as e:
            print(f"✗ Erreur: {e}")
            return {"ticker": ticker, "error": str(e)}
    
    def get_price_history(self, ticker: str, period: str = "1y") -> Dict:
        """
        Récupère l'historique des prix.
        
        Args:
            ticker: Le ticker
            period: Période (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
        
        Returns:
            Dict avec l'historique
        """
        print(f"\n📈 Historique des prix {ticker} ({period})...")
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if hist.empty:
                return {"ticker": ticker, "error": "No data"}
            
            # Statistiques sur la période
            stats = {
                "ticker": ticker,
                "period": period,
                "num_days": len(hist),
                "start_date": hist.index[0].isoformat(),
                "end_date": hist.index[-1].isoformat(),
                "start_price": float(hist['Close'].iloc[0]),
                "end_price": float(hist['Close'].iloc[-1]),
                "min_price": float(hist['Close'].min()),
                "max_price": float(hist['Close'].max()),
                "avg_price": float(hist['Close'].mean()),
                "total_return": ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100,
                "volatility": float(hist['Close'].pct_change().std() * 100),
                "avg_volume": float(hist['Volume'].mean()),
            }
            
            print(f"✓ {stats['num_days']} jours de données")
            print(f"  Return: {stats['total_return']:.2f}%")
            print(f"  Volatilité: {stats['volatility']:.2f}%")
            
            return stats
            
        except Exception as e:
            print(f"✗ Erreur: {e}")
            return {"ticker": ticker, "error": str(e)}


if __name__ == "__main__":
    agent = FinancialDataAgent()
    
    # Test avec Meta
    print("="*70)
    print("TEST: Analyse complète Meta")
    print("="*70)
    
    data = agent.get_company_data("META")
    
    