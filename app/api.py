# app/api.py
"""
API Flask pour le Multi-Agent GraphRAG Builder.
Endpoints pour:
- Analyse d'entreprises
- Ingestion de sources (PDF, CSV, MD, HTML)
- Extraction d'entités
- GraphRAG QA (fusion graph + vector + LLM)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import math
import os
import tempfile
import shutil
from werkzeug.utils import secure_filename

from ticker_agent import TickerAgent
from financial_data_agent import FinancialDataAgent
from graph_agent import GraphAgent
from sec_filing_agent import SECParserAgent
from llm_synthesis_agent import LLMSynthesisAgent
from vector_store_agent import VectorStoreAgent
from source_discovery_agent import SourceDiscoveryAgent
from entity_extraction_agent import EntityExtractionAgent
from graphrag_agent import GraphRAGAgent

app = Flask(__name__)
CORS(app)

# ============================================
# Initialisation des agents
# ============================================
print("\n" + "=" * 50)
print("🚀 Initialisation des agents...")
print("=" * 50)

ticker_agent = TickerAgent()
financial_agent = FinancialDataAgent()
graph_agent = GraphAgent(password="Caluboss18")
sec_parser = SECParserAgent()
llm_synthesis = LLMSynthesisAgent()
vector_agent = VectorStoreAgent()
source_agent = SourceDiscoveryAgent()
entity_agent = EntityExtractionAgent()
graphrag_agent = GraphRAGAgent(vector_store=vector_agent, graph_password="Caluboss18")

print("=" * 50)
print("✓ Tous les agents sont prêts!")
print("=" * 50 + "\n")


# ============================================
# Utilitaires
# ============================================

def clean_nan(data):
    """Remplace récursivement tous les NaN par None."""
    if isinstance(data, dict):
        return {key: clean_nan(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_nan(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    else:
        return data


# ============================================
# ENDPOINTS EXISTANTS (Finance)
# ============================================

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Endpoint pour analyser une entreprise."""
    data = request.json
    query = data.get('query', '')

    if not query:
        return jsonify({"error": "No query provided"}), 400

    ticker_result = ticker_agent.find_ticker(query)

    if not ticker_result.get("validated"):
        return jsonify({"error": f"Unable to find ticker for '{query}'"}), 404

    ticker = ticker_result["ticker"]
    financial_data = financial_agent.get_company_data(ticker)

    if "error" in financial_data:
        return jsonify({"error": financial_data["error"]}), 500

    financial_data = clean_nan(financial_data)

    try:
        graph_agent.create_company_node(financial_data)
        print(f"✓ {ticker} ajouté au graph")
    except Exception as e:
        print(f"⚠ Erreur lors de l'ajout au graph: {e}")

    price_history = {
        "1mo": financial_agent.get_price_history(ticker, "1mo"),
        "6mo": financial_agent.get_price_history(ticker, "6mo"),
        "1y": financial_agent.get_price_history(ticker, "1y")
    }
    price_history = clean_nan(price_history)

    return jsonify({
        "ticker": ticker,
        "data": financial_data,
        "price_history": price_history
    })


@app.route('/api/10k', methods=['POST'])
def analyze_10k():
    """Endpoint pour analyser un 10-K avec synthèse LLM."""
    data = request.json
    ticker = data.get('ticker', '')
    section = data.get('section', 0)

    if not ticker:
        return jsonify({"error": "No ticker provided"}), 400

    sections_data = sec_parser.get_10k_sections(ticker, section)

    if "error" in sections_data:
        return jsonify({"error": sections_data["error"]}), 404

    result = llm_synthesis.synthesize(sections_data)

    try:
        graph_agent.add_10k_syntheses(ticker, result.get('syntheses', {}))
        print(f"✓ Synthèses 10-K ajoutées au graph pour {ticker}")
    except Exception as e:
        print(f"⚠ Erreur ajout synthèses au graph: {e}")

    try:
        vector_agent.add_10k_sections(ticker, sections_data)
        print(f"✓ 10-K de {ticker} ajouté au vector store")
    except Exception as e:
        print(f"⚠ Erreur ajout vector store: {e}")

    result = clean_nan(result)
    return jsonify(result)


@app.route('/api/10k/raw', methods=['POST'])
def get_raw_10k():
    """Endpoint pour récupérer les sections brutes."""
    data = request.json
    ticker = data.get('ticker', '')
    section = data.get('section', 0)

    if not ticker:
        return jsonify({"error": "No ticker provided"}), 400

    sections_data = sec_parser.get_10k_sections(ticker, section)
    sections_data = clean_nan(sections_data)
    return jsonify(sections_data)


@app.route('/api/search', methods=['POST'])
def semantic_search():
    """Recherche sémantique simple dans le vector store."""
    data = request.json
    query = data.get('query', '')
    ticker_filter = data.get('ticker', None)
    n_results = data.get('n_results', 5)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        results = vector_agent.search(
            query=query,
            n_results=n_results,
            ticker_filter=ticker_filter
        )
        results = clean_nan(results)
        return jsonify({"query": query, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/vector-store/stats', methods=['GET'])
def get_vector_store_stats():
    """Statistiques du vector store."""
    try:
        stats = vector_agent.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Liste toutes les entreprises du graph."""
    try:
        companies = graph_agent.get_all_companies()
        companies = clean_nan(companies)
        return jsonify({"companies": companies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sector/<sector_name>', methods=['GET'])
def get_sector_companies(sector_name):
    """Récupère les entreprises d'un secteur."""
    try:
        companies = graph_agent.get_companies_by_sector(sector_name)
        companies = clean_nan(companies)
        return jsonify({"sector": sector_name, "companies": companies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================
# NOUVEAUX ENDPOINTS - GraphRAG Pipeline
# ============================================

@app.route('/api/qa', methods=['POST'])
def graphrag_qa():
    """
    🌟 ENDPOINT PRINCIPAL: GraphRAG Question-Answering.
    Combine recherche vectorielle + traversée de graphe + LLM.

    Body:
        {
            "question": "What are Apple's main risks?",
            "n_results": 5,
            "include_graph": true
        }

    Returns:
        {
            "question": "...",
            "answer": "...",
            "citations": [...],
            "graph_paths": [...]
        }
    """
    data = request.json
    question = data.get('question', '')
    n_results = data.get('n_results', 5)
    include_graph = data.get('include_graph', True)

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        result = graphrag_agent.answer(
            question=question,
            n_vector_results=n_results,
            include_graph=include_graph
        )
        result = clean_nan(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ingest', methods=['POST'])
def ingest_sources():
    """
    Ingère des sources depuis un répertoire ou fichier.

    Body:
        {
            "path": "/path/to/documents",
            "extract_entities": true
        }

    Returns:
        {
            "sources_found": 5,
            "sources_ingested": 5,
            "documents_added": 10,
            "entities_extracted": 50
        }
    """
    data = request.json
    path = data.get('path', '')
    extract_entities = data.get('extract_entities', False)

    if not path:
        return jsonify({"error": "No path provided"}), 400

    if not os.path.exists(path):
        return jsonify({"error": f"Path not found: {path}"}), 404

    try:
        # Découvrir et ingérer les sources
        sources = source_agent.discover_sources(path)

        if isinstance(sources, dict) and "error" in sources:
            return jsonify(sources), 404

        ingested = []
        for source in sources:
            content = source_agent.ingest_source(source)
            if "error" not in content:
                content["source_info"] = source
                ingested.append(content)

                # Ajouter au vector store
                text = content.get("text_content", "")
                if text and len(text) > 50:
                    vector_agent.add_document(
                        ticker=source.get("name", "doc"),
                        text=text[:10000],  # Limiter la taille
                        metadata={
                            "section": source.get("type", "document"),
                            "source": "ingested",
                            "path": source.get("path", "")
                        }
                    )

        # Extraction d'entités optionnelle
        entities_count = 0
        if extract_entities and ingested:
            extractions = entity_agent.batch_extract(ingested)
            graphrag_agent.add_entities_to_graph(extractions)
            entities_count = sum(
                len(e.get("entities", [])) for e in extractions
            )

        return jsonify({
            "sources_found": len(sources),
            "sources_ingested": len(ingested),
            "entities_extracted": entities_count,
            "sources": [s.get("name") for s in sources]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/extract-entities', methods=['POST'])
def extract_entities():
    """
    Extrait les entités d'un texte donné.

    Body:
        {
            "text": "Apple Inc. is a technology company...",
            "add_to_graph": true
        }

    Returns:
        {
            "entities": [...],
            "relations": [...]
        }
    """
    data = request.json
    text = data.get('text', '')
    add_to_graph = data.get('add_to_graph', False)

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        result = entity_agent.extract_all(text, "api_request")

        if add_to_graph:
            graphrag_agent.add_entities_to_graph([result])

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pipeline', methods=['POST'])
def full_pipeline():
    """
    🚀 Pipeline complet: Ingest → Extract → Index → Ready for QA.

    Body:
        {
            "path": "/path/to/documents",
            "use_case": "Analyze company financials"
        }

    Returns:
        Stats complètes du pipeline
    """
    data = request.json
    path = data.get('path', '')
    use_case = data.get('use_case', 'general analysis')

    if not path:
        return jsonify({"error": "No path provided"}), 400

    if not os.path.exists(path):
        return jsonify({"error": f"Path not found: {path}"}), 404

    try:
        print(f"\n{'='*50}")
        print(f"🚀 Pipeline GraphRAG: {use_case}")
        print(f"📁 Source: {path}")
        print(f"{'='*50}")

        # Étape 1: Découvrir les sources
        print("\n📋 Étape 1: Découverte des sources...")
        sources = source_agent.discover_sources(path)

        if isinstance(sources, dict) and "error" in sources:
            return jsonify(sources), 404

        print(f"   ✓ {len(sources)} sources trouvées")

        # Étape 2: Ingérer et normaliser
        print("\n📥 Étape 2: Ingestion et normalisation...")
        ingested = []
        for source in sources:
            content = source_agent.ingest_source(source)
            if "error" not in content:
                content["source_info"] = source
                ingested.append(content)

        print(f"   ✓ {len(ingested)} sources ingérées")

        # Étape 3: Extraire entités et relations
        print("\n🔍 Étape 3: Extraction d'entités...")
        extractions = entity_agent.batch_extract(ingested)
        total_entities = sum(len(e.get("entities", [])) for e in extractions)
        total_relations = sum(len(e.get("relations", [])) for e in extractions)
        print(f"   ✓ {total_entities} entités, {total_relations} relations")

        # Étape 4: Construire le Knowledge Graph
        print("\n🔗 Étape 4: Construction du Knowledge Graph...")
        graph_stats = graphrag_agent.add_entities_to_graph(extractions)

        # Étape 5: Créer le Vector Store
        print("\n📊 Étape 5: Indexation vectorielle...")
        docs_added = 0
        for content in ingested:
            text = content.get("text_content", "")
            source_info = content.get("source_info", {})

            if text and len(text) > 50:
                vector_agent.add_document(
                    ticker=source_info.get("name", "doc"),
                    text=text[:10000],
                    metadata={
                        "section": source_info.get("type", "document"),
                        "source": "pipeline",
                        "path": source_info.get("path", "")
                    }
                )
                docs_added += 1

        print(f"   ✓ {docs_added} documents indexés")

        print(f"\n{'='*50}")
        print("✅ Pipeline terminé! Prêt pour GraphRAG QA")
        print(f"{'='*50}\n")

        return jsonify({
            "status": "success",
            "use_case": use_case,
            "pipeline_stats": {
                "sources_discovered": len(sources),
                "sources_ingested": len(ingested),
                "entities_extracted": total_entities,
                "relations_extracted": total_relations,
                "graph_entities_added": graph_stats.get("entities_added", 0),
                "graph_relations_added": graph_stats.get("relations_added", 0),
                "documents_indexed": docs_added
            },
            "ready_for_qa": True
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/graph/stats', methods=['GET'])
def get_graph_stats():
    """Statistiques du Knowledge Graph."""
    try:
        with graph_agent.driver.session() as session:
            # Compter les noeuds
            nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]

            # Compter les relations
            rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

            # Types de noeuds
            node_types = session.run("""
                MATCH (n) RETURN labels(n)[0] as type, count(*) as count
                ORDER BY count DESC
            """)

            types = [{"type": r["type"], "count": r["count"]} for r in node_types]

        return jsonify({
            "total_nodes": nodes,
            "total_relations": rels,
            "node_types": types
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérifie que tous les services sont opérationnels."""
    status = {
        "api": True,
        "vector_store": False,
        "graph_db": False,
        "llm": False
    }

    # Check Vector Store
    try:
        stats = vector_agent.get_stats()
        status["vector_store"] = True
        status["vector_store_docs"] = stats.get("total_documents", 0)
    except Exception:
        pass

    # Check Graph DB
    try:
        with graph_agent.driver.session() as session:
            session.run("RETURN 1")
        status["graph_db"] = True
    except Exception:
        pass

    # Check LLM
    try:
        import ollama
        ollama.generate(model="llama3.2", prompt="test", options={"num_predict": 1})
        status["llm"] = True
    except Exception:
        pass

    all_ok = all([status["api"], status["vector_store"], status["graph_db"], status["llm"]])

    return jsonify({
        "status": "healthy" if all_ok else "degraded",
        "services": status
    }), 200 if all_ok else 503


# ============================================
# UPLOAD DE FICHIERS
# ============================================

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'csv', 'md', 'markdown', 'html', 'htm', 'txt', 'json'}

# Créer le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """
    Upload de fichiers pour le pipeline GraphRAG.
    Accepte plusieurs fichiers via multipart/form-data.
    """
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist('files')
    use_case = request.form.get('use_case', 'Uploaded documents')

    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No files selected"}), 400

    # Créer un sous-dossier unique pour cet upload
    import uuid
    upload_id = str(uuid.uuid4())[:8]
    upload_path = os.path.join(UPLOAD_FOLDER, upload_id)
    os.makedirs(upload_path, exist_ok=True)

    saved_files = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(upload_path, filename)
            file.save(filepath)
            saved_files.append(filename)

    if not saved_files:
        shutil.rmtree(upload_path)
        return jsonify({"error": "No valid files uploaded"}), 400

    # Lancer le pipeline sur les fichiers uploadés
    try:
        print(f"\n{'='*50}")
        print(f"📤 Upload Pipeline: {use_case}")
        print(f"📁 {len(saved_files)} fichiers uploadés")
        print(f"{'='*50}")

        # Découvrir les sources
        sources = source_agent.discover_sources(upload_path)
        if isinstance(sources, dict) and "error" in sources:
            return jsonify(sources), 404

        # Ingérer
        ingested = []
        for source in sources:
            content = source_agent.ingest_source(source)
            if "error" not in content:
                content["source_info"] = source
                ingested.append(content)

        # Extraire entités
        extractions = entity_agent.batch_extract(ingested)
        total_entities = sum(len(e.get("entities", [])) for e in extractions)
        total_relations = sum(len(e.get("relations", [])) for e in extractions)

        # Ajouter au graphe
        graph_stats = graphrag_agent.add_entities_to_graph(extractions)

        # Indexer
        docs_added = 0
        for content in ingested:
            text = content.get("text_content", "")
            source_info = content.get("source_info", {})
            if text and len(text) > 50:
                vector_agent.add_document(
                    ticker=source_info.get("name", "doc"),
                    text=text[:10000],
                    metadata={
                        "section": source_info.get("type", "document"),
                        "source": "upload",
                        "path": source_info.get("path", "")
                    }
                )
                docs_added += 1

        print(f"✅ Pipeline terminé!")

        return jsonify({
            "status": "success",
            "upload_id": upload_id,
            "files_uploaded": saved_files,
            "pipeline_stats": {
                "sources_discovered": len(sources),
                "sources_ingested": len(ingested),
                "entities_extracted": total_entities,
                "relations_extracted": total_relations,
                "graph_entities_added": graph_stats.get("entities_added", 0),
                "graph_relations_added": graph_stats.get("relations_added", 0),
                "documents_indexed": docs_added
            },
            "ready_for_qa": True
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================
# VISUALISATION DU GRAPHE
# ============================================

@app.route('/api/graph/visualize', methods=['GET'])
def visualize_graph():
    """
    Retourne les données du graphe pour visualisation.
    Format compatible avec les librairies de visualisation (vis.js, d3, etc.)
    """
    limit = request.args.get('limit', 100, type=int)

    try:
        with graph_agent.driver.session() as session:
            # Récupérer les noeuds
            nodes_result = session.run("""
                MATCH (n)
                RETURN id(n) as id, labels(n)[0] as label,
                       coalesce(n.name, n.ticker, 'Unknown') as name,
                       properties(n) as properties
                LIMIT $limit
            """, limit=limit)

            nodes = []
            for record in nodes_result:
                node = {
                    "id": record["id"],
                    "label": record["name"],
                    "group": record["label"],
                    "properties": dict(record["properties"]) if record["properties"] else {}
                }
                nodes.append(node)

            # Récupérer les relations
            edges_result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN id(a) as source, id(b) as target, type(r) as label
                LIMIT $limit
            """, limit=limit * 2)

            edges = []
            for record in edges_result:
                edge = {
                    "from": record["source"],
                    "to": record["target"],
                    "label": record["label"],
                    "arrows": "to"
                }
                edges.append(edge)

        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🌐 GraphRAG API Server")
    print("=" * 50)
    print("\n📍 Endpoints disponibles:")
    print("   POST /api/qa          - GraphRAG Question-Answering")
    print("   POST /api/pipeline    - Pipeline complet")
    print("   POST /api/ingest      - Ingestion de sources")
    print("   POST /api/analyze     - Analyse d'entreprise")
    print("   POST /api/10k         - Analyse 10-K")
    print("   POST /api/search      - Recherche sémantique")
    print("   GET  /api/health      - Health check")
    print("   GET  /api/graph/stats - Stats du graphe")
    print("\n")

    app.run(debug=True, port=5000)
