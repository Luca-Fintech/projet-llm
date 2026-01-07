import ollama
from typing import Dict


class LLMSynthesisAgent:
    """Agent pour synthétiser les sections 10-K avec Ollama."""
    
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        print(f"✓ LLM Synthesis Agent initialisé (modèle: {model})")
    
    def synthesize(self, sections_data: Dict) -> Dict:
        """
        Synthétise les sections parsées.
        
        Args:
            sections_data: Output de SECFilingAgent
        
        Returns:
            Dict avec les synthèses
        """
        if "error" in sections_data:
            return sections_data
        
        ticker = sections_data["ticker"]
        sections = sections_data["sections"]
        
        print(f"\n🤖 Synthèse LLM pour {ticker}...")
        
        result = {
            "ticker": ticker,
            "cik": sections_data.get("cik"),
            "filing_url": sections_data.get("filing_url"),
            "syntheses": {},
            "raw_sections": sections  # Garder le texte brut
        }
        
        # Synthétiser chaque section
        if "business" in sections and sections["business"] != "Erreur extraction":
            result["syntheses"]["business_summary"] = self._synthesize_business(
                sections["business"], ticker
            )
        
        if "risk" in sections and sections["risk"] != "Erreur extraction":
            result["syntheses"]["risk_summary"] = self._synthesize_risk(
                sections["risk"], ticker
            )
        
        if "mda" in sections and sections["mda"] != "Erreur extraction":
            result["syntheses"]["mda_summary"] = self._synthesize_mda(
                sections["mda"], ticker
            )
        
        return result
    
    def _synthesize_business(self, text: str, ticker: str) -> str:
        """Synthétise la section Business."""
        print(f"  🔄 Synthèse Business...")
        
        # Limiter la taille (Ollama context limit)
        if len(text) > 15000:
            text = text[:15000] + "..."
        
        prompt = f"""You are a financial analyst. Summarize the business description of {ticker} from their 10-K filing.

Extract and structure:
1. Main business activities and revenue streams
2. Key products/services
3. Target markets
4. Competitive position
5. Recent developments

Text:
{text}

Provide a clear, structured summary (200 words max):"""
        
        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            summary = response['response'].strip()
            print(f"  ✓ Business synthétisé ({len(summary)} chars)")
            return summary
        except Exception as e:
            print(f"  ✗ Erreur: {e}")
            return f"Erreur synthèse: {e}"
    
    def _synthesize_risk(self, text: str, ticker: str) -> str:
        """Synthétise les Risk Factors."""
        print(f"  🔄 Synthèse Risk Factors...")
        
        if len(text) > 15000:
            text = text[:15000] + "..."
        
        prompt = f"""You are a financial analyst. Summarize the TOP 5 most material risk factors for {ticker} from their 10-K.

Identify:
1. Market/industry risks
2. Operational risks
3. Financial risks
4. Regulatory risks
5. Strategic risks

Text:
{text}

Provide a numbered list of the 5 most critical risks (200 words max):"""
        
        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            summary = response['response'].strip()
            print(f"  ✓ Risk synthétisé ({len(summary)} chars)")
            return summary
        except Exception as e:
            print(f"  ✗ Erreur: {e}")
            return f"Erreur synthèse: {e}"
    
    def _synthesize_mda(self, text: str, ticker: str) -> str:
        """Synthétise la section MD&A."""
        print(f"  🔄 Synthèse MD&A...")
        
        if len(text) > 15000:
            text = text[:15000] + "..."
        
        prompt = f"""You are a financial analyst. Summarize the Management Discussion & Analysis for {ticker}.

Extract key insights on:
1. Financial performance trends
2. Revenue drivers
3. Profitability analysis
4. Liquidity and capital
5. Forward outlook

Text:
{text}

Provide a structured summary (200 words max):"""
        
        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            summary = response['response'].strip()
            print(f"  ✓ MD&A synthétisé ({len(summary)} chars)")
            return summary
        except Exception as e:
            print(f"  ✗ Erreur: {e}")
            return f"Erreur synthèse: {e}"


