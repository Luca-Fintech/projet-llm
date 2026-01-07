import pandas as pd
import yfinance as yf
import ollama
from pathlib import Path
from difflib import get_close_matches


class TickerAgent:
    def __init__(self, stocks_file: str = "data/stocks_symbol.xlsx"):
        """
        Agent pour trouver le ticker d'une entreprise depuis une requête utilisateur.
        """
        self.stocks_file = Path(stocks_file)
        self.stocks_df = None
        self._load_stocks()
    
    def _load_stocks(self):
        """Charge la liste des stocks depuis le fichier Excel."""
        if not self.stocks_file.exists():
            raise FileNotFoundError(f"Fichier {self.stocks_file} introuvable")
        
        self.stocks_df = pd.read_excel(self.stocks_file)
        print(f"✓ Chargé {len(self.stocks_df)} stocks depuis {self.stocks_file}")
    
    def find_ticker(self, user_query: str, model: str = "llama3.2") -> dict:
        """
        Trouve le ticker depuis n'importe quelle requête utilisateur.
        
        Args:
            user_query: N'importe quoi (ex: "Please analyse for me Mastercard")
            model: Modèle Ollama
        
        Returns:
            dict avec ticker, name, validated
        """
        print(f"\n🔍 Requête utilisateur: {user_query}")
        
        # ÉTAPE 1: Extraire le nom de l'entreprise avec LLM
        company_name = self._extract_company_name(user_query, model)
        
        if not company_name or company_name.upper() == "UNKNOWN":
            return {
                "ticker": None,
                "name": None,
                "validated": False,
                "error": "Impossible d'identifier une entreprise dans la requête"
            }
        
        print(f"  📌 Entreprise identifiée: {company_name}")
        
        # ÉTAPE 2: Chercher le ticker dans Excel (fuzzy matching)
        ticker_candidate = self._search_in_excel(company_name)
        
        # ÉTAPE 3: Si pas trouvé, demander au LLM directement
        if not ticker_candidate:
            print(f"  ⚠ Pas trouvé dans Excel, demande au LLM...")
            ticker_candidate = self._llm_find_ticker(company_name, model)
        
        if not ticker_candidate:
            return {
                "ticker": None,
                "name": None,
                "validated": False,
                "error": f"Ticker introuvable pour '{company_name}'"
            }
        
        # ÉTAPE 4: Valider avec yfinance
        yf_info = self._verify_with_yfinance(ticker_candidate)
        
        if not yf_info:
            return {
                "ticker": ticker_candidate,
                "name": None,
                "validated": False,
                "error": "Ticker invalide sur yfinance"
            }
        
        return {
            "ticker": ticker_candidate,
            "name": yf_info.get("longName") or yf_info.get("shortName"),
            "validated": True
        }
    
    def _extract_company_name(self, user_query: str, model: str) -> str:
        """Extrait le nom de l'entreprise d'une requête libre."""
        
        prompt = f"""You are a financial assistant. Extract ONLY the company name from the user's query.

User query: "{user_query}"

Examples:
- "Please analyse for me Mastercard" → Mastercard
- "What do you think about Apple stock?" → Apple
- "Tell me about Microsoft" → Microsoft
- "I want to invest in Tesla" → Tesla
- "Meta earnings" → Meta
- "How is Amazon doing?" → Amazon
- "AAPL" → Apple

Instructions:
- Extract the company name (NOT the ticker)
- If you see a ticker (like AAPL), convert it to the company name (Apple)
- Return ONLY the company name, nothing else
- If no company is mentioned, return "UNKNOWN"

Company name:"""

        try:
            response = ollama.generate(model=model, prompt=prompt)
            company_name = response['response'].strip()
            
            # Nettoyer la réponse
            company_name = company_name.replace('"', '').replace("'", '').strip()
            
            return company_name if company_name else "UNKNOWN"
            
        except Exception as e:
            print(f"  ✗ Erreur LLM extraction: {e}")
            return "UNKNOWN"
    
    def _search_in_excel(self, company_name: str) -> str:
        """Recherche fuzzy dans le fichier Excel."""
        
        # Chercher dans la colonne 'Company Name' (nom des entreprises)
        if 'Company Name' not in self.stocks_df.columns:
            print(f"  ⚠ Colonne 'Company Name' introuvable")
            return None
        
        # Préparer les noms pour la recherche
        company_names_lower = self.stocks_df['Company Name'].str.lower().tolist()
        search_term = company_name.lower()
        
        # 1. Chercher correspondance exacte
        exact_matches = self.stocks_df[
            self.stocks_df['Company Name'].str.lower() == search_term
        ]
        
        if not exact_matches.empty:
            ticker = exact_matches.iloc[0]['Symbol']
            print(f"  ✓ Match exact dans Excel: {company_name} → {ticker}")
            return ticker
        
        # 2. Chercher correspondance partielle
        partial_matches = self.stocks_df[
            self.stocks_df['Company Name'].str.contains(search_term, case=False, na=False)
        ]
        
        if not partial_matches.empty:
            ticker = partial_matches.iloc[0]['Symbol']
            matched_name = partial_matches.iloc[0]['Company Name']
            print(f"  ✓ Match partiel dans Excel: {matched_name} → {ticker}")
            return ticker
        
        # 3. Fuzzy matching
        matches = get_close_matches(search_term, company_names_lower, n=1, cutoff=0.6)
        
        if matches:
            matched_name_lower = matches[0]
            matched_row = self.stocks_df[
                self.stocks_df['Company Name'].str.lower() == matched_name_lower
            ]
            
            if not matched_row.empty:
                ticker = matched_row.iloc[0]['Symbol']
                matched_name = matched_row.iloc[0]['Company Name']
                print(f"  ✓ Match fuzzy dans Excel: {matched_name} → {ticker}")
                return ticker
        
        print(f"  ✗ '{company_name}' non trouvé dans Excel")
        return None
    
    def _llm_find_ticker(self, company_name: str, model: str) -> str:
        """Demande au LLM de trouver le ticker (fallback)."""
        
        prompt = f"""You are a stock market expert. What is the US stock ticker symbol for: "{company_name}"?

Answer ONLY with the ticker symbol (1-5 capital letters like AAPL, MSFT, MA).
NO explanation, NO punctuation.
If you don't know, answer "UNKNOWN".

Ticker:"""

        try:
            response = ollama.generate(model=model, prompt=prompt)
            ticker = response['response'].strip().upper()
            
            # Nettoyer
            ticker = ''.join(c for c in ticker if c.isalpha())
            
            if ticker and ticker != "UNKNOWN":
                print(f"  ✓ LLM propose: {ticker}")
                return ticker
            else:
                return None
                
        except Exception as e:
            print(f"  ✗ Erreur LLM ticker: {e}")
            return None
    
    def _verify_with_yfinance(self, ticker: str) -> dict:
        """Vérifie que le ticker existe sur yfinance."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if info and ('longName' in info or 'shortName' in info):
                company_name = info.get('longName', info.get('shortName'))
                print(f"  ✓ yfinance confirme: {ticker} → {company_name} ✓ VALIDÉ")
                return info
            else:
                print(f"  ✗ Ticker {ticker} invalide sur yfinance")
                return None
                
        except Exception as e:
            print(f"  ✗ Erreur yfinance: {e}")
            return None


if __name__ == "__main__":
    agent = TickerAgent()
    
    # Tests
    queries = [
        "Please analyse for me Mastercard",
        "What about Apple?",
        "Tell me about MSFT",
        "I want to invest in Tesla",
        "Meta earnings report"
    ]
    
    for query in queries:
        print("\n" + "="*70)
        result = agent.find_ticker(query)
        print(f"Résultat: {result}")