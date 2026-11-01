"""
Lumenis Ontology Tools
======================

Tools for Lumenis to interact with the semantic layer and knowledge graph.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional

try:
    from semantic_layer.knowledge_graph_manager import KnowledgeGraphManager
    from semantic_layer.rdf_parser import Triple
except ImportError:
    try:
        from knowledge_graph_manager import KnowledgeGraphManager
        from rdf_parser import Triple
    except ImportError:
        import sys
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        from knowledge_graph_manager import KnowledgeGraphManager
        from rdf_parser import Triple


class LumenisOntologyTools:
    """
    High-level tools for Lumenis to work with ontologies and knowledge graphs.
    """

    def __init__(self):
        self.manager = KnowledgeGraphManager()

    # ========================================================================
    # ONTOLOGY MANAGEMENT
    # ========================================================================

    def load_ontologies(self) -> Dict[str, str]:
        """
        Load all ontologies into the knowledge graph.
        Returns a summary of loaded ontologies.
        """
        try:
            results = self.manager.load_all_ontologies()

            summary = {
                "status": "success",
                "message": f"Loaded {len(results)} ontologies",
                "details": results
            }

            return summary
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_ontology_stats(self) -> Dict:
        """Get statistics about the knowledge graph"""
        try:
            stats = self.manager.get_stats()
            stats["status"] = "success"
            return stats
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # ========================================================================
    # ENTITY QUERIES
    # ========================================================================

    def query_entity(self, entity_name: str) -> Dict:
        """
        Query information about an entity.
        Entity name can be short form (e.g., 'Lumenis') or full URI.
        """
        # Convert short name to URI if needed
        if not entity_name.startswith("http"):
            entity_uri = f"http://one2lv.com/ontology#{entity_name}"
        else:
            entity_uri = entity_name

        try:
            info = self.manager.query_entity(entity_uri)
            info["status"] = "success"
            return info
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def visualize_entity(self, entity_name: str) -> str:
        """
        Get a text visualization of an entity and its relationships.
        """
        if not entity_name.startswith("http"):
            entity_uri = f"http://one2lv.com/ontology#{entity_name}"
        else:
            entity_uri = entity_name

        try:
            return self.manager.visualize_entity(entity_uri)
        except Exception as e:
            return f"Error: {e}"

    # ========================================================================
    # AGENT OPERATIONS
    # ========================================================================

    def list_agents(self) -> List[str]:
        """Get all agents in the system"""
        try:
            agents = self.manager.get_all_agents()
            # Convert URIs to short names
            return [a.split('#')[-1] for a in agents]
        except Exception as e:
            return [f"Error: {e}"]

    def list_skills(self) -> List[str]:
        """Get all skills in the system"""
        try:
            skills = self.manager.get_all_skills()
            return [s.split('#')[-1] for s in skills]
        except Exception as e:
            return [f"Error: {e}"]

    def get_agent_skills(self, agent_name: str) -> List[str]:
        """Get skills possessed by an agent"""
        agent_uri = f"http://one2lv.com/ontology#{agent_name}"

        try:
            skills = self.manager.get_agent_skills(agent_uri)
            return [s.split('#')[-1] for s in skills]
        except Exception as e:
            return [f"Error: {e}"]

    def add_skill_to_agent(self, agent_name: str, skill_name: str) -> Dict:
        """Add a skill to an agent"""
        agent_uri = f"http://one2lv.com/ontology#{agent_name}"
        skill_uri = f"http://one2lv.com/ontology#{skill_name}"

        try:
            success = self.manager.add_agent_skill(agent_uri, skill_uri)
            return {
                "status": "success" if success else "failed",
                "message": f"{'Added' if success else 'Failed to add'} skill {skill_name} to agent {agent_name}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # ========================================================================
    # SEMANTIC SEARCH
    # ========================================================================

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Perform semantic search on the knowledge graph.
        Returns relevant triples based on the query.
        """
        try:
            results = self.manager.semantic_search(query, limit)

            # Simplify results
            simplified = []
            for result in results:
                simplified.append({
                    "subject": result["subject"].split('#')[-1],
                    "predicate": result["predicate"].split('#')[-1],
                    "object": result["object"].split('#')[-1] if '#' in result["object"] else result["object"],
                    "similarity": result.get("$similarity", 0)
                })

            return simplified
        except Exception as e:
            return [{"error": str(e)}]

    # ========================================================================
    # KNOWLEDGE GRAPH OPERATIONS
    # ========================================================================

    def get_entity_relationships(self, entity_name: str) -> Dict:
        """Get all relationships of an entity"""
        entity_uri = f"http://one2lv.com/ontology#{entity_name}"

        try:
            relationships = self.manager.get_entity_relationships(entity_uri)

            # Simplify URIs
            simplified = {
                "entity": entity_name,
                "outgoing": [
                    {
                        "predicate": r["predicate"].split('#')[-1],
                        "object": r["object"].split('#')[-1] if '#' in r["object"] else r["object"]
                    }
                    for r in relationships["outgoing"]
                ],
                "incoming": [
                    {
                        "subject": r["subject"].split('#')[-1],
                        "predicate": r["predicate"].split('#')[-1]
                    }
                    for r in relationships["incoming"]
                ]
            }

            return simplified
        except Exception as e:
            return {
                "error": str(e)
            }

    def add_relationship(
        self,
        subject_name: str,
        predicate_name: str,
        object_name: str
    ) -> Dict:
        """
        Add a new relationship to the knowledge graph.
        Creates a triple (subject, predicate, object).
        """
        subject_uri = f"http://one2lv.com/ontology#{subject_name}"
        predicate_uri = f"http://one2lv.com/ontology#{predicate_name}"
        object_uri = f"http://one2lv.com/ontology#{object_name}"

        triple = Triple(
            subject=subject_uri,
            predicate=predicate_uri,
            object=object_uri,
            object_type="uri"
        )

        try:
            success = self.manager.bridge.store_triple(triple)
            return {
                "status": "success" if success else "failed",
                "message": f"{'Added' if success else 'Failed to add'} relationship: {subject_name} → {predicate_name} → {object_name}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # ========================================================================
    # EXPORT OPERATIONS
    # ========================================================================

    def export_knowledge_graph(self, output_file: str = "knowledge_graph.json") -> Dict:
        """Export the entire knowledge graph to JSON"""
        try:
            self.manager.export_graph(output_file)
            return {
                "status": "success",
                "message": f"Exported knowledge graph to {output_file}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


def lumenis_command_handler(command: str, *args) -> str:
    """
    Command handler for Lumenis to interact with the ontology tools.

    Usage examples:
        lumenis_command_handler("load_ontologies")
        lumenis_command_handler("list_agents")
        lumenis_command_handler("query_entity", "Lumenis")
        lumenis_command_handler("semantic_search", "artificial intelligence agent")
    """
    tools = LumenisOntologyTools()

    if command == "load_ontologies":
        result = tools.load_ontologies()
        return str(result)

    elif command == "stats":
        result = tools.get_ontology_stats()
        return str(result)

    elif command == "list_agents":
        agents = tools.list_agents()
        return f"Agents: {', '.join(agents)}"

    elif command == "list_skills":
        skills = tools.list_skills()
        return f"Skills: {', '.join(skills)}"

    elif command == "query_entity" and len(args) > 0:
        info = tools.query_entity(args[0])
        return str(info)

    elif command == "visualize" and len(args) > 0:
        return tools.visualize_entity(args[0])

    elif command == "get_agent_skills" and len(args) > 0:
        skills = tools.get_agent_skills(args[0])
        return f"Skills of {args[0]}: {', '.join(skills)}"

    elif command == "semantic_search" and len(args) > 0:
        query = " ".join(args)
        results = tools.semantic_search(query)
        return str(results)

    elif command == "relationships" and len(args) > 0:
        relationships = tools.get_entity_relationships(args[0])
        return str(relationships)

    elif command == "add_skill" and len(args) >= 2:
        result = tools.add_skill_to_agent(args[0], args[1])
        return str(result)

    elif command == "add_relationship" and len(args) >= 3:
        result = tools.add_relationship(args[0], args[1], args[2])
        return str(result)

    elif command == "export" and len(args) > 0:
        result = tools.export_knowledge_graph(args[0])
        return str(result)

    else:
        return f"Unknown command: {command}"


if __name__ == "__main__":
    # Test the tools
    tools = LumenisOntologyTools()

    print("=" * 80)
    print("LUMENIS ONTOLOGY TOOLS - TEST")
    print("=" * 80)

    print("\n1. Loading ontologies...")
    result = tools.load_ontologies()
    print(result)

    print("\n2. Getting stats...")
    stats = tools.get_ontology_stats()
    print(stats)

    print("\n3. Listing agents...")
    agents = tools.list_agents()
    print(f"Agents: {agents}")

    if agents and agents[0] != "Error":
        print(f"\n4. Visualizing agent: {agents[0]}")
        viz = tools.visualize_entity(agents[0])
        print(viz)

    print("\n5. Semantic search...")
    results = tools.semantic_search("artificial intelligence")
    for r in results[:3]:
        print(f"  - {r}")
