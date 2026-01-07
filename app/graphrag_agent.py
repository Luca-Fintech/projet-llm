# app/graphrag_agent.py
"""
Agent GraphRAG - Fusion Graph Traversal + Vector Retrieval + LLM.
C'est le coeur du système de Question-Answering avec citations.
"""

import ollama
from typing import Dict, List, Optional
from neo4j import GraphDatabase


class GraphRAGAgent:
    """
    Agent de Question-Answering combinant:
    - Recherche vectorielle (ChromaDB)
    - Traversée de graphe (Neo4j)
    - Synthèse LLM (Ollama)
    """

    def __init__(
        self,
        vector_store,
        graph_uri: str = "bolt://localhost:7687",
        graph_user: str = "neo4j",
        graph_password: str = "Caluboss18",
        llm_model: str = "llama3.2"
    ):
        """
        Initialise l'agent GraphRAG.

        Args:
            vector_store: Instance de VectorStoreAgent
            graph_uri: URI Neo4j
            graph_user: User Neo4j
            graph_password: Password Neo4j
            llm_model: Modèle Ollama à utiliser
        """
        self.vector_store = vector_store
        self.llm_model = llm_model

        # Connexion Neo4j
        try:
            self.driver = GraphDatabase.driver(
                graph_uri, auth=(graph_user, graph_password)
            )
            print("✓ GraphRAG Agent connecté à Neo4j")
        except Exception as e:
            print(f"⚠ Connexion Neo4j échouée: {e}")
            self.driver = None

        print(f"✓ GraphRAG Agent initialisé (LLM: {llm_model})")

    def answer(
        self,
        question: str,
        n_vector_results: int = 5,
        include_graph: bool = True
    ) -> Dict:
        """
        Répond à une question en combinant graph + vector + LLM.

        Args:
            question: La question de l'utilisateur
            n_vector_results: Nombre de résultats vectoriels
            include_graph: Inclure les données du graphe

        Returns:
            Dict avec réponse, citations, et chemins du graphe
        """
        print(f"\n🤖 GraphRAG Query: '{question}'")

        # 1. Recherche vectorielle
        vector_context = self._vector_search(question, n_vector_results)

        # 2. Recherche dans le graphe
        graph_context = []
        graph_paths = []
        if include_graph and self.driver:
            graph_context, graph_paths = self._graph_search(question)

        # 3. Construire le contexte complet
        full_context = self._build_context(vector_context, graph_context)

        # 4. Générer la réponse avec LLM
        answer, citations = self._generate_answer(question, full_context, vector_context)

        return {
            "question": question,
            "answer": answer,
            "citations": citations,
            "graph_paths": graph_paths,
            "sources": {
                "vector_results": len(vector_context),
                "graph_entities": len(graph_context)
            }
        }

    def _vector_search(self, query: str, n_results: int) -> List[Dict]:
        """Recherche vectorielle dans ChromaDB."""
        print("  📊 Recherche vectorielle...")

        try:
            results = self.vector_store.search(query=query, n_results=n_results)

            contexts = []
            for i, (doc, meta, dist) in enumerate(zip(
                results.get("documents", []),
                results.get("metadatas", []),
                results.get("distances", [])
            )):
                contexts.append({
                    "content": doc[:2000] if doc else "",  # Limiter la taille
                    "metadata": meta,
                    "relevance": 1 - dist if dist else 0,  # Convertir distance en score
                    "source_type": "vector"
                })

            print(f"    ✓ {len(contexts)} documents trouvés")
            return contexts

        except Exception as e:
            print(f"    ✗ Erreur vector search: {e}")
            return []

    def _graph_search(self, query: str) -> tuple:
        """Recherche dans le Knowledge Graph Neo4j."""
        print("  🔗 Recherche dans le graphe...")

        entities = []
        paths = []

        if not self.driver:
            return entities, paths

        try:
            with self.driver.session() as session:
                # Recherche par mots-clés dans les entreprises
                keywords = self._extract_keywords(query)

                for keyword in keywords[:5]:  # Max 5 keywords
                    # Chercher les entreprises correspondantes
                    result = session.run("""
                        MATCH (c:Company)
                        WHERE toLower(c.name) CONTAINS toLower($keyword)
                           OR toLower(c.ticker) CONTAINS toLower($keyword)
                           OR toLower(c.sector) CONTAINS toLower($keyword)
                           OR toLower(c.industry) CONTAINS toLower($keyword)
                        RETURN c
                        LIMIT 3
                    """, keyword=keyword)

                    for record in result:
                        company = dict(record['c'])
                        entities.append({
                            "type": "Company",
                            "data": company,
                            "source_type": "graph"
                        })

                # Chercher les relations (paths)
                if entities:
                    ticker = entities[0].get("data", {}).get("ticker")
                    if ticker:
                        path_result = session.run("""
                            MATCH path = (c:Company {ticker: $ticker})-[r]->(target)
                            RETURN type(r) as relation, labels(target)[0] as target_type,
                                   target.name as target_name
                            LIMIT 10
                        """, ticker=ticker)

                        for record in path_result:
                            paths.append({
                                "source": ticker,
                                "relation": record["relation"],
                                "target_type": record["target_type"],
                                "target": record["target_name"]
                            })

            print(f"    ✓ {len(entities)} entités, {len(paths)} relations")
            return entities, paths

        except Exception as e:
            print(f"    ✗ Erreur graph search: {e}")
            return [], []

    def _extract_keywords(self, query: str) -> List[str]:
        """Extrait les mots-clés importants d'une requête."""
        # Mots à ignorer
        stopwords = {
            'what', 'who', 'where', 'when', 'why', 'how', 'is', 'are', 'was',
            'were', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'about', 'tell', 'me', 'show',
            'give', 'explain', 'describe', 'company', 'companies', 'stock',
            'quel', 'quelle', 'quels', 'quelles', 'est', 'sont', 'le', 'la',
            'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais', 'dans',
            'sur', 'pour', 'avec', 'par', 'entreprise', 'entreprises'
        }

        words = query.lower().replace('?', '').replace(',', '').split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        return keywords

    def _build_context(
        self,
        vector_context: List[Dict],
        graph_context: List[Dict]
    ) -> str:
        """Construit le contexte pour le LLM."""
        parts = []

        # Contexte vectoriel
        if vector_context:
            parts.append("=== DOCUMENT CONTEXT ===")
            for i, ctx in enumerate(vector_context, 1):
                meta = ctx.get("metadata", {})
                source = meta.get("ticker", meta.get("section", "unknown"))
                parts.append(f"\n[Source {i}: {source}]")
                parts.append(ctx.get("content", "")[:1500])

        # Contexte du graphe
        if graph_context:
            parts.append("\n\n=== KNOWLEDGE GRAPH CONTEXT ===")
            for entity in graph_context[:5]:  # Max 5 entités
                data = entity.get("data", {})
                if entity.get("type") == "Company":
                    parts.append(f"\nCompany: {data.get('name', 'N/A')}")
                    parts.append(f"  Ticker: {data.get('ticker', 'N/A')}")
                    parts.append(f"  Sector: {data.get('sector', 'N/A')}")
                    parts.append(f"  Industry: {data.get('industry', 'N/A')}")
                    if data.get('description'):
                        parts.append(f"  Description: {data.get('description', '')[:500]}")
                    if data.get('market_cap'):
                        parts.append(f"  Market Cap: ${data.get('market_cap', 0):,.0f}")
                    if data.get('revenue'):
                        parts.append(f"  Revenue: ${data.get('revenue', 0):,.0f}")

        return "\n".join(parts)

    def _generate_answer(
        self,
        question: str,
        context: str,
        vector_results: List[Dict]
    ) -> tuple:
        """Génère la réponse avec le LLM."""
        print("  🧠 Génération de la réponse...")

        if not context.strip():
            return "I don't have enough information to answer this question. Please ingest some documents first.", []

        prompt = f"""You are a helpful assistant answering questions based on the provided context.
Use ONLY the information from the context below to answer. If the context doesn't contain
enough information, say so clearly.

CONTEXT:
{context[:6000]}

QUESTION: {question}

Instructions:
1. Answer the question directly and concisely
2. Reference specific sources when possible (e.g., "According to [Source 1]...")
3. If multiple sources agree, mention that
4. If you're uncertain, express that uncertainty
5. Keep the answer focused and relevant

ANSWER:"""

        try:
            response = ollama.generate(model=self.llm_model, prompt=prompt)
            answer = response['response'].strip()

            # Extraire les citations depuis les résultats vectoriels
            citations = []
            for ctx in vector_results:
                meta = ctx.get("metadata", {})
                if meta:
                    citation = {
                        "source": meta.get("ticker", "Unknown"),
                        "section": meta.get("section", "document"),
                        "url": meta.get("url", ""),
                        "relevance": round(ctx.get("relevance", 0), 3)
                    }
                    citations.append(citation)

            print(f"    ✓ Réponse générée ({len(answer)} chars)")
            return answer, citations

        except Exception as e:
            print(f"    ✗ Erreur LLM: {e}")
            return f"Error generating answer: {e}", []

    def add_entities_to_graph(self, extraction_results: List[Dict]) -> Dict:
        """
        Ajoute les entités et relations extraites au Knowledge Graph.

        Args:
            extraction_results: Résultats de EntityExtractionAgent.batch_extract()

        Returns:
            Stats d'ajout
        """
        if not self.driver:
            return {"error": "Neo4j non connecté"}

        added_entities = 0
        added_relations = 0

        with self.driver.session() as session:
            for result in extraction_results:
                source = result.get("source", "unknown")

                # Ajouter les entités
                for entity in result.get("entities", []):
                    entity_type = entity.get("type", "Entity")
                    entity_name = entity.get("name", "")

                    if not entity_name:
                        continue

                    try:
                        session.run(f"""
                            MERGE (e:{entity_type} {{name: $name}})
                            SET e.source = $source,
                                e.updated_at = datetime()
                        """, name=entity_name, source=source)
                        added_entities += 1
                    except Exception:
                        pass  # Ignorer les erreurs de type de noeud

                # Ajouter les relations
                for rel in result.get("relations", []):
                    source_name = rel.get("source", "")
                    target_name = rel.get("target", "")
                    relation_type = rel.get("relation", "RELATED_TO")

                    if not source_name or not target_name:
                        continue

                    # Sanitize relation type
                    relation_type = relation_type.upper().replace(" ", "_")

                    try:
                        session.run(f"""
                            MATCH (s {{name: $source}})
                            MATCH (t {{name: $target}})
                            MERGE (s)-[r:{relation_type}]->(t)
                            SET r.updated_at = datetime()
                        """, source=source_name, target=target_name)
                        added_relations += 1
                    except Exception:
                        pass

        print(f"✓ Graph enrichi: {added_entities} entités, {added_relations} relations")
        return {
            "entities_added": added_entities,
            "relations_added": added_relations
        }

    def close(self):
        """Ferme la connexion Neo4j."""
        if self.driver:
            self.driver.close()
