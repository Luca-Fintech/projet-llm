import re
import unicodedata
from bs4 import BeautifulSoup as bs
import requests
from typing import Dict, Optional
from datetime import datetime
import json


class SECParserAgent:
    """
    Agent pour télécharger et parser les 10-K depuis la nouvelle API SEC.
    """
    
    def __init__(self):
        # IMPORTANT: SEC exige un User-Agent avec email
        self.headers = {
            'User-Agent': 'ESILV luca.rougemont@edu.devinci.fr',  # CHANGE ÇA
            'Accept-Encoding': 'gzip, deflate',
        }
        self.base_url = "https://data.sec.gov"
    
    def get_10k_sections(self, ticker: str, section: int = 0) -> Dict:
        """
        Télécharge et parse un 10-K.
        
        Args:
            ticker: AAPL, META, etc.
            section: 0=All, 1=Business, 2=Risk, 3=MD&A
        
        Returns:
            Dict avec les sections
        """
        print(f"\n📄 Téléchargement 10-K pour {ticker}...")
        
        # Étape 1: Trouver le CIK
        cik = self._get_cik(ticker)
        if not cik:
            return {"ticker": ticker, "error": "CIK non trouvé"}
        
        # Étape 2: Trouver le dernier 10-K
        filing_url = self._get_latest_10k(cik)
        if not filing_url:
            return {"ticker": ticker, "error": "10-K non trouvé"}
        
        # Étape 3: Parser les sections
        sections = self._parse_10k_filing(filing_url, section)
        
        return {
            "ticker": ticker,
            "cik": cik,
            "filing_url": filing_url,
            "sections": sections,
            "retrieved_at": datetime.now().isoformat()
        }
    
    def _get_cik(self, ticker: str) -> Optional[str]:
        """Récupère le CIK via l'API SEC."""
        try:
            # API des tickers SEC
            url = f"{self.base_url}/submissions/CIK{ticker.upper()}.json"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 404:
                # Essayer via le mapping ticker->CIK
                tickers_url = "https://www.sec.gov/files/company_tickers.json"
                tickers_response = requests.get(tickers_url, headers=self.headers)
                tickers_data = tickers_response.json()
                
                for entry in tickers_data.values():
                    if entry['ticker'].upper() == ticker.upper():
                        cik = str(entry['cik_str']).zfill(10)
                        print(f"✓ CIK trouvé: {cik}")
                        return cik
                
                return None
            
            data = response.json()
            cik = str(data['cik']).zfill(10)
            print(f"✓ CIK trouvé: {cik}")
            return cik
            
        except Exception as e:
            print(f"✗ Erreur CIK: {e}")
            return None
    
    def _get_latest_10k(self, cik: str) -> Optional[str]:
        """Récupère le dernier 10-K."""
        try:
            # API submissions
            url = f"{self.base_url}/submissions/CIK{cik}.json"
            response = requests.get(url, headers=self.headers)
            data = response.json()
            
            # Chercher le dernier 10-K
            recent = data['filings']['recent']
            
            for i, form in enumerate(recent['form']):
                if form == '10-K':
                    accession = recent['accessionNumber'][i].replace('-', '')
                    primary_doc = recent['primaryDocument'][i]
                    
                    # URL du document
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}"
                    print(f"✓ 10-K trouvé: {doc_url}")
                    return doc_url
            
            return None
            
        except Exception as e:
            print(f"✗ Erreur 10-K: {e}")
            return None
    
    def _parse_10k_filing(self, link: str, section: int) -> Dict:
        """Parse le 10-K (ton code original)."""
        if section not in [0, 1, 2, 3]:
            return {"error": "Section invalide"}
        
        try:
            text = self._get_text(link)
            sections = {}
            
            # Item 1: Business
            if section == 1 or section == 0:
                try:
                    item1_start = re.compile(r"item\s*[1][\.\;\:\-\_]*\s*\b", re.IGNORECASE)
                    item1_end = re.compile(r"item\s*1a[\.\;\:\-\_]\s*Risk|item\s*2[\.\,\;\:\-\_]\s*Prop", re.IGNORECASE)
                    sections["business"] = self._extract_text(text, item1_start, item1_end)
                    print(f"  ✓ Business: {len(sections['business'])} chars")
                except:
                    sections["business"] = "Erreur extraction"
            
            # Item 1A: Risk
            if section == 2 or section == 0:
                try:
                    item1a_start = re.compile(r"(?<!,\s)item\s*1a[\.\;\:\-\_]\s*Risk", re.IGNORECASE)
                    item1a_end = re.compile(r"item\s*2[\.\;\:\-\_]\s*Prop", re.IGNORECASE)
                    sections["risk"] = self._extract_text(text, item1a_start, item1a_end)
                    print(f"  ✓ Risk: {len(sections['risk'])} chars")
                except:
                    sections["risk"] = "Erreur extraction"
            
            # Item 7: MD&A
            if section == 3 or section == 0:
                try:
                    item7_start = re.compile(r"item\s*[7][\.\;\:\-\_]*\s*\bM", re.IGNORECASE)
                    item7_end = re.compile(r"item\s*7a[\.\;\:\-\_]\sQuanti|item\s*8[\.\,\;\:\-\_]\s*", re.IGNORECASE)
                    sections["mda"] = self._extract_text(text, item7_start, item7_end)
                    print(f"  ✓ MD&A: {len(sections['mda'])} chars")
                except:
                    sections["mda"] = "Erreur extraction"
            
            return sections
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_text(self, link: str) -> str:
        """Récupère le texte du 10-K."""
        page = requests.get(link, headers=self.headers)
        html = bs(page.content, "lxml")
        text = html.get_text()
        text = unicodedata.normalize("NFKD", text).encode('ascii', 'ignore').decode('utf8')
        text = text.split("\n")
        text = " ".join(text)
        return text
    
    def _extract_text(self, text: str, item_start, item_end) -> str:
        """Extrait une section."""
        starts = [i.start() for i in item_start.finditer(text)]
        ends = [i.start() for i in item_end.finditer(text)]
        
        positions = []
        for s in starts:
            for e in ends:
                if s < e:
                    positions.append([s, e])
                    break
        
        if not positions:
            return "Section non trouvée"
        
        # Prendre la plus longue
        best = max(positions, key=lambda p: p[1] - p[0])
        return text[best[0]:best[1]]


if __name__ == "__main__":
    agent = SECParserAgent()
    result = agent.get_10k_sections("AAPL", section=1)
    
    if "sections" in result:
        for name, content in result["sections"].items():
            print(f"\n{name}: {len(content)} chars")
            print(content[:500])