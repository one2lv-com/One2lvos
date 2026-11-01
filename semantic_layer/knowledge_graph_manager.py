"""
Knowledge Graph Manager
=======================

High-level manager for the One2lvOS semantic knowledge graph.
Integrates RDF parsing with Astra DB storage.
"""

import os
from typing import List, Dict, Optional
from pathlib import Path

try:
    from .rdf_parser import RDFParser, Triple
    from .astra_semantic_bridge import AstraSemanticBridge
except ImportError:
    from rdf_parser import RDFParser, Triple
    from astra_semantic_bridge import AstraSemanticBridge


class KnowledgeGraphManager:
    """
    Manages the One2lvOS knowledge graph.
    Provides high-level operations for ontology management.
    """

    def __init__(self, ontology_dir: Optional[str] = None):
        self.parser = RDFParser(ontology_dir)
        self.bridge = AstraSemanticBridge()
        self.loaded_ontologies: List[str] = []

    def load_ontology(self, filename: str) -> int:
        """
        Load an ontology file and store triples in Astra DB.
        Returns the number of triples stored.
        """
        print(f"Loading ontology: {filename}")

        # Parse the ontology
        triples = self.parser.parse_file(filename)
        print(f"Parsed {len(triples)} triples")

        # Store in Astra DB
        metadata = {
            "source": filename,
            "ontology": filename.replace('.ttl', '')
        }

        stored_count = self.bridge.store_triples(triples, metadata)
        print(f"Stored {stored_count} triples in Astra DB")

        self.loaded_ontologies.append(filename)
        return stored_count

    def load_all_ontologies(self) -> Dict[str, int]:
        """Load all ontologies in the ontologies directory"""
        ontology_dir = Path(self.parser.ontology_dir)
        results = {}

        for ontology_file in ontology_dir.glob("*.ttl"):
            filename = ontology_file.name
            count = self.load_ontology(filename)
            results[filename] = count

        return results

    def query_entity(self, entity_uri: str) -> Dict:
        """Get all information about an entity"""
        # Get triples where entity is subject
        as_subject = self.bridge.query_triples(subject=entity_uri)

        # Get triples where entity is object
        as_object = self.bridge.query_triples(obj=entity_uri)

        return {
            "uri": entity_uri,
            "as_subject": as_subject,
            "as_object": as_object,
            "related_count": len(as_subject) + len(as_object)
        }

    def get_entity_type(self, entity_uri: str) -> Optional[str]:
        """Get the rdf:type of an entity"""
        triples = self.bridge.query_triples(
            subject=entity_uri,
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        )

        if triples:
            return triples[0].get("object")
        return None

    def get_all_agents(self) -> List[str]:
        """Get all agents in the system"""
        agent_class = "http://one2lv.com/ontology#Agent"
        triples = self.bridge.query_triples(
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            obj=agent_class
        )

        return [t.get("subject") for t in triples]

    def get_all_skills(self) -> List[str]:
        """Get all skills in the system"""
        skill_class = "http://one2lv.com/ontology#Skill"
        triples = self.bridge.query_triples(
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            obj=skill_class
        )

        return [t.get("subject") for t in triples]

    def get_agent_skills(self, agent_uri: str) -> List[str]:
        """Get all skills possessed by an agent"""
        has_skill_predicate = "http://one2lv.com/ontology#hasSkill"
        triples = self.bridge.query_triples(
            subject=agent_uri,
            predicate=has_skill_predicate
        )

        return [t.get("object") for t in triples]

    def add_agent_skill(self, agent_uri: str, skill_uri: str) -> bool:
        """Add a skill to an agent"""
        triple = Triple(
            subject=agent_uri,
            predicate="http://one2lv.com/ontology#hasSkill",
            object=skill_uri,
            object_type="uri"
        )

        return self.bridge.store_triple(triple)

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Perform semantic search on the knowledge graph"""
        return self.bridge.semantic_search(query, limit)

    def get_entity_relationships(self, entity_uri: str) -> Dict:
        """Get all relationships of an entity"""
        related = self.bridge.get_related(entity_uri)

        relationships = {
            "outgoing": [],  # Entity as subject
            "incoming": []   # Entity as object
        }

        for triple in related:
            if triple["subject"] == entity_uri:
                relationships["outgoing"].append({
                    "predicate": triple["predicate"],
                    "object": triple["object"]
                })
            else:
                relationships["incoming"].append({
                    "subject": triple["subject"],
                    "predicate": triple["predicate"]
                })

        return relationships

    def export_graph(self, output_file: str):
        """Export the entire knowledge graph to JSON"""
        self.bridge.export_to_json(output_file)

    def get_stats(self) -> Dict:
        """Get statistics about the knowledge graph"""
        all_triples = self.bridge.query_triples(limit=10000)

        subjects = set(t["subject"] for t in all_triples)
        predicates = set(t["predicate"] for t in all_triples)
        objects = set(t["object"] for t in all_triples)

        return {
            "total_triples": len(all_triples),
            "unique_subjects": len(subjects),
            "unique_predicates": len(predicates),
            "unique_objects": len(objects),
            "loaded_ontologies": self.loaded_ontologies
        }

    def visualize_entity(self, entity_uri: str) -> str:
        """Generate a text visualization of an entity and its relationships"""
        info = self.query_entity(entity_uri)

        lines = [
            f"Entity: {entity_uri}",
            "=" * 80,
            ""
        ]

        if info["as_subject"]:
            lines.append("Outgoing relationships:")
            for triple in info["as_subject"]:
                pred = triple["predicate"].split('#')[-1]
                obj = triple["object"].split('#')[-1] if '#' in triple["object"] else triple["object"]
                lines.append(f"  - {pred} → {obj}")
            lines.append("")

        if info["as_object"]:
            lines.append("Incoming relationships:")
            for triple in info["as_object"]:
                subj = triple["subject"].split('#')[-1]
                pred = triple["predicate"].split('#')[-1]
                lines.append(f"  - {subj} → {pred}")
            lines.append("")

        lines.append(f"Total relationships: {info['related_count']}")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test the knowledge graph manager
    manager = KnowledgeGraphManager()

    print("Loading all ontologies...")
    results = manager.load_all_ontologies()
    print(f"Loaded ontologies: {results}")

    print("\nKnowledge graph stats:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\nGetting all agents...")
    agents = manager.get_all_agents()
    print(f"Found agents: {agents}")

    if agents:
        print(f"\nVisualizing {agents[0]}:")
        print(manager.visualize_entity(agents[0]))
