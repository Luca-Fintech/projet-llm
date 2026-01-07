# app/entity_extraction_agent.py
"""
Agent d'extraction d'entités et de relations pour le Knowledge Graph.
Utilise Ollama LLM pour extraire entités et relations depuis le texte.
"""

import ollama
import json
import re
from typing import Dict, List, Optional


class EntityExtractionAgent:
    """Agent pour extraire entités et relations avec LLM."""

    def __init__(self, model: str = "llama3.2"):
        self.model = model
        print(f"✓ Entity Extraction Agent initialisé (modèle: {model})")

    def extract_entities(self, text: str, context: str = "") -> Dict:
        """
        Extrait les entités depuis un texte.

        Args:
            text: Le texte à analyser
            context: Contexte optionnel (ex: "financial document")

        Returns:
            Dict avec les entités extraites par type
        """
        # Limiter la taille du texte
        if len(text) > 8000:
            text = text[:8000] + "..."

        prompt = f"""You are an entity extraction system. Extract all named entities from the following text.

Categories to extract:
- PERSON: Names of people
- ORGANIZATION: Companies, institutions, agencies
- LOCATION: Cities, countries, addresses
- DATE: Dates and time periods
- MONEY: Monetary values
- PRODUCT: Products, services, technologies
- CONCEPT: Key concepts, topics, themes

Text:
{text}

Return a JSON object with this exact format (no other text):
{{
    "entities": [
        {{"name": "entity name", "type": "TYPE", "mentions": 1}},
        ...
    ]
}}

Only return valid JSON, no explanations."""

        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            result_text = response['response'].strip()

            # Extraire le JSON de la réponse
            entities = self._parse_json_response(result_text)

            print(f"  ✓ {len(entities.get('entities', []))} entités extraites")
            return entities

        except Exception as e:
            print(f"  ✗ Erreur extraction: {e}")
            return {"entities": [], "error": str(e)}

    def extract_relations(self, text: str, entities: List[Dict] = None) -> Dict:
        """
        Extrait les relations entre entités.

        Args:
            text: Le texte à analyser
            entities: Liste d'entités déjà extraites (optionnel)

        Returns:
            Dict avec les relations extraites
        """
        if len(text) > 8000:
            text = text[:8000] + "..."

        entity_hint = ""
        if entities:
            entity_names = [e.get("name", "") for e in entities[:20]]  # Max 20
            entity_hint = f"\nKnown entities: {', '.join(entity_names)}"

        prompt = f"""You are a relation extraction system. Extract relationships between entities in the text.
{entity_hint}

Text:
{text}

Common relation types:
- WORKS_FOR: Person works for Organization
- LOCATED_IN: Entity is located in Location
- OWNS: Entity owns another entity
- INVESTS_IN: Entity invests in another
- COMPETES_WITH: Organizations compete
- PARTNERS_WITH: Entities partner together
- PRODUCES: Organization produces Product
- RELATED_TO: General relationship

Return a JSON object with this exact format (no other text):
{{
    "relations": [
        {{"source": "Entity1", "relation": "RELATION_TYPE", "target": "Entity2"}},
        ...
    ]
}}

Only return valid JSON, no explanations."""

        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            result_text = response['response'].strip()

            relations = self._parse_json_response(result_text)

            print(f"  ✓ {len(relations.get('relations', []))} relations extraites")
            return relations

        except Exception as e:
            print(f"  ✗ Erreur extraction relations: {e}")
            return {"relations": [], "error": str(e)}

    def extract_all(self, text: str, source_name: str = "document") -> Dict:
        """
        Extraction complète: entités + relations.

        Args:
            text: Le texte à analyser
            source_name: Nom de la source pour les métadonnées

        Returns:
            Dict avec entités et relations
        """
        print(f"\n🔍 Extraction depuis: {source_name}")

        # Extraire les entités
        entities_result = self.extract_entities(text)
        entities = entities_result.get("entities", [])

        # Extraire les relations
        relations_result = self.extract_relations(text, entities)
        relations = relations_result.get("relations", [])

        return {
            "source": source_name,
            "entities": entities,
            "relations": relations,
            "stats": {
                "entity_count": len(entities),
                "relation_count": len(relations)
            }
        }

    def _parse_json_response(self, text: str) -> Dict:
        """Parse une réponse JSON potentiellement mal formée."""
        # Essayer de parser directement
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Chercher un bloc JSON dans la réponse
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: structure vide
        return {"entities": [], "relations": []}

    def batch_extract(self, documents: List[Dict]) -> List[Dict]:
        """
        Extraction en batch sur plusieurs documents.

        Args:
            documents: Liste de dicts avec 'text_content' et 'name'

        Returns:
            Liste des résultats d'extraction
        """
        results = []

        for doc in documents:
            text = doc.get("text_content", "")
            name = doc.get("source_info", {}).get("name", "document")

            if not text or len(text) < 50:
                continue

            result = self.extract_all(text, name)
            result["document"] = doc.get("source_info", {})
            results.append(result)

        print(f"\n✓ Extraction terminée pour {len(results)} documents")
        return results
