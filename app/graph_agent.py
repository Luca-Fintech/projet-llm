from neo4j import GraphDatabase
from typing import Dict, List, Optional


class GraphAgent:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "Caluboss18"):
        """
        Agent pour gérer le Knowledge Graph Neo4j.
        
        Args:
            uri: URI de connexion Neo4j
            user: Username
            password: Password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✓ Connecté à Neo4j")
    
    def close(self):
        """Ferme la connexion."""
        self.driver.close()
    
    def clear_database(self):
        """Efface toute la base de données (ATTENTION)."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Base de données effacée")
    
    def create_company_node(self, company_data: Dict) -> bool:
        """
        Crée un nœud Company dans le graph avec toutes ses données.
        
        Args:
            company_data: Dict avec les données de l'entreprise (depuis financial_data_agent)
        
        Returns:
            True si succès
        """
        print(f"\n📊 Création du nœud pour {company_data['name']}...")
        
        with self.driver.session() as session:
            # Créer le nœud Company
            query = """
            MERGE (c:Company {ticker: $ticker})
            SET c.name = $name,
                c.sector = $sector,
                c.industry = $industry,
                c.country = $country,
                c.employees = $employees,
                c.website = $website,
                c.description = $description,
                c.current_price = $current_price,
                c.market_cap = $market_cap,
                c.revenue = $revenue,
                c.revenue_growth = $revenue_growth,
                c.profit_margin = $profit_margin,
                c.operating_margin = $operating_margin,
                c.pe_ratio = $pe_ratio,
                c.debt_to_equity = $debt_to_equity,
                c.roe = $roe,
                c.updated_at = datetime()
            RETURN c
            """
            
            result = session.run(query, 
                ticker=company_data['ticker'],
                name=company_data['name'],
                sector=company_data['sector'],
                industry=company_data['industry'],
                country=company_data['country'],
                employees=company_data['employees'],
                website=company_data['website'],
                description=company_data['description'],
                current_price=company_data['current_price'],
                market_cap=company_data['market_cap'],
                revenue=company_data['revenue'],
                revenue_growth=company_data['revenue_growth'],
                profit_margin=company_data['profit_margin'],
                operating_margin=company_data['operating_margin'],
                pe_ratio=company_data['pe_ratio'],
                debt_to_equity=company_data['debt_to_equity'],
                roe=company_data['roe']
            )
            
            print(f"✓ Nœud créé pour {company_data['name']}")
            
            # Créer les relations avec Sector et Industry
            self._create_sector_relation(company_data['ticker'], company_data['sector'])
            self._create_industry_relation(company_data['ticker'], company_data['industry'])
            
            return True
    
    def add_10k_syntheses(self, ticker: str, syntheses: Dict):
        """
        Ajoute les synthèses 10-K à un nœud Company existant.
        
        Args:
            ticker: Le ticker de l'entreprise
            syntheses: Dict avec business_summary, risk_summary, mda_summary
        """
        with self.driver.session() as session:
            query = """
            MATCH (c:Company {ticker: $ticker})
            SET c.business_summary = $business,
                c.risk_summary = $risk,
                c.mda_summary = $mda,
                c.filing_updated_at = datetime()
            RETURN c
            """
            
            session.run(query,
                ticker=ticker,
                business=syntheses.get("business_summary"),
                risk=syntheses.get("risk_summary"),
                mda=syntheses.get("mda_summary")
            )
    
    def _create_sector_relation(self, ticker: str, sector: str):
        """Crée la relation Company -> Sector."""
        if not sector:
            return
        
        with self.driver.session() as session:
            query = """
            MATCH (c:Company {ticker: $ticker})
            MERGE (s:Sector {name: $sector})
            MERGE (c)-[:OPERATES_IN]->(s)
            """
            session.run(query, ticker=ticker, sector=sector)
            print(f"  ✓ Relation OPERATES_IN -> {sector}")
    
    def _create_industry_relation(self, ticker: str, industry: str):
        """Crée la relation Company -> Industry."""
        if not industry:
            return
        
        with self.driver.session() as session:
            query = """
            MATCH (c:Company {ticker: $ticker})
            MERGE (i:Industry {name: $industry})
            MERGE (c)-[:BELONGS_TO]->(i)
            """
            session.run(query, ticker=ticker, industry=industry)
            print(f"  ✓ Relation BELONGS_TO -> {industry}")
    
    def get_company(self, ticker: str) -> Optional[Dict]:
        """Récupère les données d'une entreprise depuis le graph."""
        with self.driver.session() as session:
            query = """
            MATCH (c:Company {ticker: $ticker})
            RETURN c
            """
            result = session.run(query, ticker=ticker)
            record = result.single()
            
            if record:
                return dict(record['c'])
            return None
    
    def get_all_companies(self) -> List[Dict]:
        """Récupère toutes les entreprises du graph."""
        with self.driver.session() as session:
            query = """
            MATCH (c:Company)
            RETURN c.ticker as ticker, c.name as name, c.sector as sector
            ORDER BY c.name
            """
            result = session.run(query)
            return [dict(record) for record in result]
    
    def get_companies_by_sector(self, sector: str) -> List[Dict]:
        """Récupère toutes les entreprises d'un secteur."""
        with self.driver.session() as session:
            query = """
            MATCH (c:Company)-[:OPERATES_IN]->(s:Sector {name: $sector})
            RETURN c.ticker as ticker, c.name as name, c.pe_ratio as pe_ratio, c.roe as roe
            ORDER BY c.name
            """
            result = session.run(query, sector=sector)
            return [dict(record) for record in result]