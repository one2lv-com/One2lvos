#!/usr/bin/env python3
"""
Semantic Skill for Lumenis
===========================

A skill that enables Lumenis to work with semantic web and knowledge graphs.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.lumenis_ontology_tools import LumenisOntologyTools


class SemanticSkill:
    """
    Semantic web skill for Lumenis.
    Provides access to ontology and knowledge graph operations.
    """

    def __init__(self):
        self.tools = LumenisOntologyTools()
        self.name = "semantic"
        self.description = "Semantic web and knowledge graph operations"

    def execute(self, action: str, **kwargs):
        """
        Execute a semantic action.

        Actions:
            - init: Initialize knowledge graph with ontologies
            - query: Query an entity
            - search: Semantic search
            - list: List agents or skills
            - add: Add relationships or skills
            - stats: Get knowledge graph statistics
        """

        if action == "init":
            return self.tools.load_ontologies()

        elif action == "query":
            entity = kwargs.get("entity")
            if entity:
                return self.tools.query_entity(entity)
            return {"error": "Missing entity parameter"}

        elif action == "search":
            query = kwargs.get("query")
            limit = kwargs.get("limit", 10)
            if query:
                return self.tools.semantic_search(query, limit)
            return {"error": "Missing query parameter"}

        elif action == "list":
            list_type = kwargs.get("type", "agents")
            if list_type == "agents":
                return self.tools.list_agents()
            elif list_type == "skills":
                return self.tools.list_skills()
            return {"error": f"Unknown list type: {list_type}"}

        elif action == "add":
            add_type = kwargs.get("type")

            if add_type == "skill":
                agent = kwargs.get("agent")
                skill = kwargs.get("skill")
                if agent and skill:
                    return self.tools.add_skill_to_agent(agent, skill)
                return {"error": "Missing agent or skill parameter"}

            elif add_type == "relationship":
                subject = kwargs.get("subject")
                predicate = kwargs.get("predicate")
                obj = kwargs.get("object")
                if subject and predicate and obj:
                    return self.tools.add_relationship(subject, predicate, obj)
                return {"error": "Missing relationship parameters"}

            return {"error": f"Unknown add type: {add_type}"}

        elif action == "stats":
            return self.tools.get_ontology_stats()

        elif action == "visualize":
            entity = kwargs.get("entity")
            if entity:
                viz = self.tools.visualize_entity(entity)
                return {"visualization": viz}
            return {"error": "Missing entity parameter"}

        elif action == "relationships":
            entity = kwargs.get("entity")
            if entity:
                return self.tools.get_entity_relationships(entity)
            return {"error": "Missing entity parameter"}

        elif action == "export":
            output_file = kwargs.get("output", "knowledge_graph.json")
            return self.tools.export_knowledge_graph(output_file)

        else:
            return {"error": f"Unknown action: {action}"}


def test_skill():
    """Test the semantic skill"""
    skill = SemanticSkill()

    print("=" * 80)
    print(f"Testing {skill.name.upper()} SKILL")
    print("=" * 80)

    # Initialize
    print("\n1. Initialize knowledge graph...")
    result = skill.execute("init")
    print(result)

    # Stats
    print("\n2. Get statistics...")
    result = skill.execute("stats")
    print(result)

    # List agents
    print("\n3. List agents...")
    result = skill.execute("list", type="agents")
    print(f"Agents: {result}")

    # Query entity
    if result and len(result) > 0 and not str(result[0]).startswith("Error"):
        print(f"\n4. Query entity: {result[0]}")
        info = skill.execute("query", entity=result[0])
        print(info)

        print(f"\n5. Get relationships: {result[0]}")
        relationships = skill.execute("relationships", entity=result[0])
        print(relationships)

    # Semantic search
    print("\n6. Semantic search...")
    search_results = skill.execute("search", query="agent artificial intelligence", limit=5)
    print(search_results)


if __name__ == "__main__":
    test_skill()
