# app/source_discovery_agent.py
"""
Agent de découverte et ingestion de sources multiples.
Supporte: PDF, CSV, Markdown, HTML, TXT, JSON
"""

import os
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup


class SourceDiscoveryAgent:
    """Agent pour découvrir et ingérer des sources de données variées."""

    SUPPORTED_EXTENSIONS = {
        '.pdf': 'pdf',
        '.csv': 'csv',
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.html': 'html',
        '.htm': 'html',
        '.txt': 'text',
        '.json': 'json'
    }

    def __init__(self):
        print("✓ Source Discovery Agent initialisé")

    def discover_sources(self, path: str) -> List[Dict]:
        """
        Découvre toutes les sources dans un répertoire.

        Args:
            path: Chemin du répertoire à scanner

        Returns:
            Liste des sources découvertes avec métadonnées
        """
        sources = []
        path = Path(path)

        if not path.exists():
            return {"error": f"Chemin non trouvé: {path}"}

        if path.is_file():
            source = self._analyze_file(path)
            if source:
                sources.append(source)
        else:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    source = self._analyze_file(file_path)
                    if source:
                        sources.append(source)

        print(f"✓ {len(sources)} sources découvertes")
        return sources

    def _analyze_file(self, file_path: Path) -> Optional[Dict]:
        """Analyse un fichier et retourne ses métadonnées."""
        ext = file_path.suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            return None

        return {
            "path": str(file_path.absolute()),
            "name": file_path.name,
            "type": self.SUPPORTED_EXTENSIONS[ext],
            "size": file_path.stat().st_size,
            "extension": ext
        }

    def ingest_source(self, source: Dict) -> Dict:
        """
        Ingère une source et normalise son contenu.

        Args:
            source: Dict avec path et type

        Returns:
            Dict avec le contenu normalisé
        """
        file_type = source.get("type")
        file_path = source.get("path")

        print(f"  📄 Ingestion: {source.get('name')} ({file_type})")

        try:
            if file_type == "csv":
                return self._ingest_csv(file_path)
            elif file_type == "markdown":
                return self._ingest_markdown(file_path)
            elif file_type == "html":
                return self._ingest_html(file_path)
            elif file_type == "text":
                return self._ingest_text(file_path)
            elif file_type == "json":
                return self._ingest_json(file_path)
            elif file_type == "pdf":
                return self._ingest_pdf(file_path)
            else:
                return {"error": f"Type non supporté: {file_type}"}
        except Exception as e:
            return {"error": str(e)}

    def _ingest_csv(self, file_path: str) -> Dict:
        """Ingère un fichier CSV."""
        rows = []
        text_content = []

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            for row in reader:
                rows.append(row)
                # Convertir la ligne en texte pour le RAG
                text_content.append(" | ".join([f"{k}: {v}" for k, v in row.items() if v]))

        return {
            "type": "csv",
            "path": file_path,
            "headers": headers,
            "row_count": len(rows),
            "data": rows,
            "text_content": "\n".join(text_content)  # Pour embeddings
        }

    def _ingest_markdown(self, file_path: str) -> Dict:
        """Ingère un fichier Markdown."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extraire les sections (headers)
        sections = []
        current_section = {"title": "Introduction", "content": ""}

        for line in content.split('\n'):
            if line.startswith('#'):
                if current_section["content"].strip():
                    sections.append(current_section)
                # Nouveau header
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                current_section = {"title": title, "level": level, "content": ""}
            else:
                current_section["content"] += line + "\n"

        if current_section["content"].strip():
            sections.append(current_section)

        return {
            "type": "markdown",
            "path": file_path,
            "sections": sections,
            "text_content": content
        }

    def _ingest_html(self, file_path: str) -> Dict:
        """Ingère un fichier HTML."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')

        # Supprimer scripts et styles
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Extraire le texte
        text = soup.get_text(separator='\n', strip=True)

        # Extraire le titre
        title = soup.title.string if soup.title else "Sans titre"

        return {
            "type": "html",
            "path": file_path,
            "title": title,
            "text_content": text
        }

    def _ingest_text(self, file_path: str) -> Dict:
        """Ingère un fichier texte."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        return {
            "type": "text",
            "path": file_path,
            "text_content": content
        }

    def _ingest_json(self, file_path: str) -> Dict:
        """Ingère un fichier JSON."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)

        # Convertir en texte pour les embeddings
        text_content = self._json_to_text(data)

        return {
            "type": "json",
            "path": file_path,
            "data": data,
            "text_content": text_content
        }

    def _json_to_text(self, data, prefix="") -> str:
        """Convertit un JSON en texte lisible."""
        lines = []

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._json_to_text(value, prefix + "  "))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}[{i}]:")
                    lines.append(self._json_to_text(item, prefix + "  "))
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)

    def _ingest_pdf(self, file_path: str) -> Dict:
        """
        Ingère un fichier PDF.
        Note: Nécessite PyPDF2 ou pdfplumber (optionnel).
        Fallback simple si non disponible.
        """
        try:
            # Essayer avec PyPDF2
            import PyPDF2

            text_content = []
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_content.append(page.extract_text() or "")

            return {
                "type": "pdf",
                "path": file_path,
                "page_count": len(text_content),
                "text_content": "\n\n".join(text_content)
            }
        except ImportError:
            # PyPDF2 non installé - retourner info basique
            return {
                "type": "pdf",
                "path": file_path,
                "text_content": f"[PDF file: {file_path} - Install PyPDF2 for text extraction]",
                "warning": "PyPDF2 non installé. Exécuter: poetry add pypdf2"
            }

    def ingest_all(self, path: str) -> List[Dict]:
        """
        Découvre et ingère toutes les sources d'un répertoire.

        Args:
            path: Chemin du répertoire

        Returns:
            Liste des contenus ingérés
        """
        sources = self.discover_sources(path)

        if isinstance(sources, dict) and "error" in sources:
            return [sources]

        results = []
        for source in sources:
            content = self.ingest_source(source)
            content["source_info"] = source
            results.append(content)

        print(f"\n✓ {len(results)} sources ingérées")
        return results
