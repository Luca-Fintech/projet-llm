# app/vector_store_agent.py

from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict


class VectorStoreAgent:
    """Agent pour gérer le stockage et la recherche vectorielle."""
    
    def __init__(self, db_path: str = "./chroma_db"):
        """
        Initialise le vector store.
        
        Args:
            db_path: Chemin où ChromaDB stockera les données
        """
        print(f"\n📦 Initialisation Vector Store...")
        
        # Modèle d'embeddings (petit, rapide, gratuit)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print(f"  ✓ Modèle d'embeddings chargé (384 dimensions)")
        
        # ChromaDB client
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Collection pour les documents financiers
        self.collection = self.client.get_or_create_collection(
            name="financial_documents",
            metadata={"description": "10-K sections and financial documents"}
        )
        print(f"  ✓ Collection 'financial_documents' prête")
        print(f"  ✓ Documents actuels : {self.collection.count()}")
    
    def add_document(
        self, 
        ticker: str, 
        text: str, 
        metadata: Dict
    ):
        """
        Ajoute un document au vector store.
        
        Args:
            ticker: AAPL, META, etc.
            text: Le texte à stocker (section 10-K, news, etc.)
            metadata: Infos supplémentaires (section, date, url, etc.)
        """
        # Générer un ID unique
        doc_id = f"{ticker}_{metadata.get('section', 'doc')}_{metadata.get('year', '2024')}"
        
        print(f"\n  📄 Ajout document: {doc_id}")
        
        # Créer l'embedding
        embedding = self.embedding_model.encode(text).tolist()
        
        # Ajouter à ChromaDB
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "ticker": ticker,
                **metadata
            }]
        )
        
        print(f"    ✓ Embedding créé ({len(embedding)} dimensions)")
        print(f"    ✓ Stocké dans ChromaDB")
    
    def add_10k_sections(self, ticker: str, sections_data: Dict):
        """
        Ajoute toutes les sections d'un 10-K.
        
        Args:
            ticker: AAPL
            sections_data: Output de SECParserAgent.get_10k_sections()
        """
        if "error" in sections_data:
            print(f"  ✗ Erreur : {sections_data['error']}")
            return
        
        sections = sections_data.get("sections", {})
        filing_url = sections_data.get("filing_url")
        
        for section_name, text in sections.items():
            if text and text != "Erreur extraction" and text != "Section non trouvée":
                self.add_document(
                    ticker=ticker,
                    text=text,
                    metadata={
                        "section": section_name,
                        "source": "10-K",
                        "url": filing_url,
                        "year": "2024"  # Tu peux extraire l'année du filing
                    }
                )
        
        print(f"\n  ✓ {len(sections)} sections ajoutées pour {ticker}")
    
    def search(
        self, 
        query: str, 
        n_results: int = 5,
        ticker_filter: str = None
    ) -> Dict:
        """
        Recherche sémantique dans les documents.
        
        Args:
            query: "What are Meta's main risks?"
            n_results: Nombre de résultats à retourner
            ticker_filter: Filtrer par ticker (optionnel)
        
        Returns:
            Dict avec documents, metadatas, distances
        """
        print(f"\n🔍 Recherche : '{query}'")
        
        # Créer l'embedding de la question
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Construire le filtre
        where_filter = None
        if ticker_filter:
            where_filter = {"ticker": ticker_filter}
        
        # Rechercher
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )
        
        print(f"  ✓ {len(results['documents'][0])} résultats trouvés")
        
        return {
            "documents": results['documents'][0],
            "metadatas": results['metadatas'][0],
            "distances": results['distances'][0]
        }
    
    def get_stats(self) -> Dict:
        """Statistiques du vector store."""
        return {
            "total_documents": self.collection.count(),
            "collection_name": self.collection.name
        }


