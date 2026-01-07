# Multi-Agent GraphRAG Builder

Application full-stack pour construire un pipeline GraphRAG (Graph Retrieval Augmented Generation) avec extraction d'entites, construction de Knowledge Graph, et Question-Answering intelligent.

## Fonctionnalites

### 1. Decouverte et Ingestion de Sources
- **Formats supportes**: PDF, CSV, Markdown, HTML, JSON, TXT
- Scan automatique de repertoires
- Normalisation du contenu

### 2. Extraction d'Entites et Relations (NER)
- Extraction automatique via LLM (Ollama)
- Types d'entites: PERSON, ORGANIZATION, LOCATION, DATE, MONEY, PRODUCT, CONCEPT
- Detection de relations entre entites

### 3. Construction du Knowledge Graph
- Stockage dans Neo4j
- Noeuds: Companies, Sectors, Industries, Entites extraites
- Relations: OPERATES_IN, BELONGS_TO, WORKS_FOR, INVESTS_IN, etc.

### 4. Vector Store pour RAG classique
- ChromaDB pour le stockage vectoriel
- Embeddings avec all-MiniLM-L6-v2 (384 dimensions)
- Recherche semantique

### 5. GraphRAG QA Endpoint
- **Fusion** de:
  - Recherche vectorielle (documents similaires)
  - Traversee de graphe (relations entre entites)
  - Synthese LLM (reponse coherente)
- Citations des sources
- Chemins du graphe affiches

## Architecture

```
                    +-------------------+
                    |    Frontend       |
                    |    (React 19)     |
                    +--------+----------+
                             |
                             v
                    +-------------------+
                    |   Flask API       |
                    |   (Port 5000)     |
                    +--------+----------+
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
+------------------+ +---------------+ +------------------+
| Source Discovery | | Entity Extract| | GraphRAG Agent   |
| Agent            | | Agent (NER)   | | (QA Fusion)      |
+------------------+ +---------------+ +------------------+
          |                  |                  |
          v                  v                  v
+------------------+ +---------------+ +------------------+
| VectorStore      | | Neo4j Graph   | | Ollama LLM       |
| (ChromaDB)       | | Database      | | (llama3.2)       |
+------------------+ +---------------+ +------------------+
```

## Prerequis

- **Python 3.11+**
- **Node.js 18+**
- **Neo4j** (base de donnees graphe)
- **Ollama** avec le modele `llama3.2`

## Installation

### 1. Cloner et installer les dependances Python

```bash
cd investment-graphrag-analyzer
poetry install
```

### 2. Demarrer Neo4j

```bash
# Via Docker (recommande)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Caluboss18 \
  neo4j:latest

# Ou installer Neo4j Desktop
# https://neo4j.com/download/
```

### 3. Installer et demarrer Ollama

```bash
# Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Demarrer le service
ollama serve

# Telecharger le modele
ollama pull llama3.2
```

### 4. Installer les dependances frontend

```bash
cd ui/frontend
npm install
```

## Lancement

### Terminal 1 - Backend

```bash
cd investment-graphrag-analyzer
poetry run python app/api.py
```

Le serveur demarre sur http://localhost:5000

### Terminal 2 - Frontend

```bash
cd investment-graphrag-analyzer/ui/frontend
npm start
```

L'interface demarre sur http://localhost:3000

## Utilisation

### Mode 1: Analyse Financiere

1. Cliquer sur "Financial Analysis"
2. Entrer un nom d'entreprise ou ticker (ex: "Apple", "MSFT")
3. Visualiser les donnees financieres
4. Cliquer sur "Analyze 10-K" pour la synthese des rapports SEC

### Mode 2: Pipeline GraphRAG

1. Cliquer sur "GraphRAG Pipeline"
2. **Etape 1**: Entrer le chemin vers vos documents
   - Ex: `/Users/vous/documents/data`
3. Cliquer sur "Run Pipeline"
4. Attendre l'ingestion, extraction, et indexation
5. **Etape 2**: Poser des questions sur vos documents
   - Ex: "What are the main risks mentioned?"
   - Ex: "Who are the key people involved?"

## API Endpoints

### GraphRAG (Nouveaux)

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/qa` | Question-Answering GraphRAG |
| POST | `/api/pipeline` | Pipeline complet |
| POST | `/api/ingest` | Ingestion de sources |
| POST | `/api/extract-entities` | Extraction NER |
| GET | `/api/graph/stats` | Stats du Knowledge Graph |
| GET | `/api/health` | Health check |

### Finance (Existants)

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/analyze` | Analyse d'entreprise |
| POST | `/api/10k` | Analyse 10-K avec synthese |
| POST | `/api/search` | Recherche semantique |
| GET | `/api/companies` | Liste des entreprises |
| GET | `/api/sector/<name>` | Entreprises par secteur |

## Exemples d'appels API

### Pipeline complet

```bash
curl -X POST http://localhost:5000/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/documents",
    "use_case": "Analyze financial reports"
  }'
```

### Question-Answering

```bash
curl -X POST http://localhost:5000/api/qa \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Apple main risks?",
    "n_results": 5,
    "include_graph": true
  }'
```

### Reponse GraphRAG

```json
{
  "question": "What are Apple main risks?",
  "answer": "Based on the documents, Apple faces several key risks...",
  "citations": [
    {
      "source": "AAPL",
      "section": "risk",
      "url": "https://sec.gov/...",
      "relevance": 0.85
    }
  ],
  "graph_paths": [
    {
      "source": "AAPL",
      "relation": "OPERATES_IN",
      "target": "Technology"
    }
  ]
}
```

## Structure du Projet

```
investment-graphrag-analyzer/
├── app/
│   ├── api.py                    # API Flask principale
│   ├── source_discovery_agent.py # Decouverte de sources
│   ├── entity_extraction_agent.py# Extraction NER
│   ├── graphrag_agent.py         # GraphRAG QA
│   ├── vector_store_agent.py     # ChromaDB
│   ├── graph_agent.py            # Neo4j
│   ├── ticker_agent.py           # Resolution de tickers
│   ├── financial_data_agent.py   # Donnees yfinance
│   ├── sec_filing_agent.py       # Parser SEC 10-K
│   └── llm_synthesis_agent.py    # Synthese Ollama
├── ui/frontend/
│   ├── src/
│   │   ├── App.js                # Composant React principal
│   │   └── App.css               # Styles
│   └── package.json
├── data/
│   └── stocks_symbol.xlsx        # Base de tickers
├── chroma_db/                    # Vector store persistant
├── pyproject.toml                # Dependances Python
└── README.md
```

## Technologies

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.11, Flask |
| Frontend | React 19 |
| Vector DB | ChromaDB |
| Graph DB | Neo4j |
| LLM | Ollama (llama3.2) |
| Embeddings | all-MiniLM-L6-v2 |
| Finance API | yfinance |
| SEC Filings | sec-edgar-downloader |

## Conformite au Cahier des Charges

| Exigence | Status |
|----------|--------|
| 1. Discover & select sources | OK |
| 2. Ingest & normalize content | OK |
| 3. Extract entities & relations | OK |
| 4. Embed chunks to vector store | OK |
| 5. GraphRAG QA endpoint | OK |

## Auteur

Luca Rougemont - ESILV
