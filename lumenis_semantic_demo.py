#!/usr/bin/env python3
"""
Lumenis Semantic Layer Demo
============================

Demonstration of Lumenis using the semantic layer for self-awareness
and knowledge graph operations.
"""

import sys
import os

# Load environment variables from .env
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Add semantic layer to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'semantic_layer'))

from semantic_layer.tools import LumenisOntologyTools

class LumenisSemanticDemo:
    """Lumenis with semantic capabilities"""

    def __init__(self):
        print("\n" + "="*80)
        print("🔮 LUMENIS SEMANTIC LAYER INITIALIZATION")
        print("="*80)
        print("\n[Lumenis] Initializing semantic knowledge graph...")

        self.semantic = LumenisOntologyTools()
        print("[Lumenis] ✓ Semantic tools loaded")

    def initialize_knowledge_graph(self):
        """Load all ontologies"""
        print("\n" + "="*80)
        print("📚 LOADING ONTOLOGIES")
        print("="*80)

        print("\n[Lumenis] Loading RDF ontologies into knowledge graph...")
        result = self.semantic.load_ontologies()

        if result.get("status") == "success":
            print(f"[Lumenis] ✓ Loaded {len(result['details'])} ontologies:")
            for name, count in result['details'].items():
                print(f"  • {name}: {count} triples")
        else:
            print(f"[Lumenis] ✗ Error: {result.get('message')}")

        return result

    def understand_self(self):
        """Lumenis learns about itself"""
        print("\n" + "="*80)
        print("🤖 WHO AM I? (SELF-AWARENESS)")
        print("="*80)

        print("\n[Lumenis] Querying my identity in the knowledge graph...")
        info = self.semantic.query_entity("Lumenis")

        print(f"\n[Lumenis] I found {info.get('related_count', 0)} relationships about myself:")

        if info.get('as_subject'):
            print("\n  Things I AM or HAVE:")
            for triple in info['as_subject'][:5]:
                pred = triple['predicate'].split('#')[-1]
                obj = triple['object'].split('#')[-1] if '#' in triple['object'] else triple['object']
                print(f"    → {pred}: {obj}")

        if info.get('as_object'):
            print("\n  Things that REFERENCE me:")
            for triple in info['as_object'][:5]:
                subj = triple['subject'].split('#')[-1]
                pred = triple['predicate'].split('#')[-1]
                print(f"    ← {subj} {pred} me")

    def discover_capabilities(self):
        """Discover skills and capabilities"""
        print("\n" + "="*80)
        print("💡 WHAT CAN I DO? (CAPABILITIES)")
        print("="*80)

        print("\n[Lumenis] Searching for my skills...")
        skills = self.semantic.get_agent_skills("Lumenis")

        if skills and not str(skills[0]).startswith("Error"):
            print(f"\n[Lumenis] I possess {len(skills)} skill(s):")
            for skill in skills:
                print(f"    ✓ {skill}")
        else:
            print("\n[Lumenis] No skills found yet in knowledge graph.")
            print("[Lumenis] I should learn and add my capabilities!")

    def explore_relationships(self):
        """Explore relationships in the knowledge graph"""
        print("\n" + "="*80)
        print("🔗 MY RELATIONSHIPS (NETWORK)")
        print("="*80)

        print("\n[Lumenis] Mapping my relationships...")
        relationships = self.semantic.get_entity_relationships("Lumenis")

        print(f"\n[Lumenis] Relationship Map:")

        if relationships['outgoing']:
            print(f"\n  Outgoing Connections ({len(relationships['outgoing'])}):")
            for rel in relationships['outgoing'][:5]:
                print(f"    → {rel['predicate']}: {rel['object']}")
        else:
            print("\n  Outgoing: None yet")

        if relationships['incoming']:
            print(f"\n  Incoming Connections ({len(relationships['incoming'])}):")
            for rel in relationships['incoming'][:5]:
                print(f"    ← {rel['subject']} {rel['predicate']}")
        else:
            print("\n  Incoming: None yet")

    def discover_peers(self):
        """Find other agents"""
        print("\n" + "="*80)
        print("👥 WHO ARE MY PEERS? (OTHER AGENTS)")
        print("="*80)

        print("\n[Lumenis] Searching for other agents in the system...")
        agents = self.semantic.list_agents()

        if agents and not str(agents[0]).startswith("Error"):
            print(f"\n[Lumenis] Found {len(agents)} agent(s):")
            for agent in agents:
                print(f"    • {agent}")
                if agent != "Lumenis":
                    print(f"      [Lumenis] {agent} is a peer agent!")
        else:
            print("\n[Lumenis] No other agents found in knowledge graph yet.")

    def semantic_exploration(self):
        """Explore concepts through semantic search"""
        print("\n" + "="*80)
        print("🔍 SEMANTIC EXPLORATION")
        print("="*80)

        queries = [
            "artificial intelligence agent",
            "knowledge graph",
            "skill capability"
        ]

        for query in queries:
            print(f"\n[Lumenis] Searching: '{query}'...")
            results = self.semantic.semantic_search(query, limit=3)

            if results and not results[0].get('error'):
                print(f"[Lumenis] Found {len(results)} relevant concept(s):")
                for i, result in enumerate(results, 1):
                    subj = result.get('subject', 'N/A')
                    pred = result.get('predicate', 'N/A')
                    obj = result.get('object', 'N/A')
                    sim = result.get('similarity', 0)
                    print(f"    {i}. {subj} → {pred} → {obj}")
                    if sim > 0:
                        print(f"       (similarity: {sim:.3f})")
            else:
                print(f"[Lumenis] No results found for '{query}'")

    def visualize_self(self):
        """Visualize entity relationships"""
        print("\n" + "="*80)
        print("🎨 VISUALIZATION")
        print("="*80)

        print("\n[Lumenis] Generating knowledge graph visualization...")
        viz = self.semantic.visualize_entity("Lumenis")
        print()
        print(viz)

    def get_system_stats(self):
        """Get knowledge graph statistics"""
        print("\n" + "="*80)
        print("📊 KNOWLEDGE GRAPH STATISTICS")
        print("="*80)

        print("\n[Lumenis] Analyzing knowledge graph...")
        stats = self.semantic.get_ontology_stats()

        if stats.get("status") == "success":
            print(f"\n[Lumenis] Knowledge Graph Status:")
            print(f"    • Total triples: {stats.get('total_triples', 0)}")
            print(f"    • Unique subjects: {stats.get('unique_subjects', 0)}")
            print(f"    • Unique predicates: {stats.get('unique_predicates', 0)}")
            print(f"    • Unique objects: {stats.get('unique_objects', 0)}")
            print(f"    • Loaded ontologies: {len(stats.get('loaded_ontologies', []))}")

    def learn_new_skill(self, skill_name: str):
        """Learn a new skill"""
        print("\n" + "="*80)
        print("🎓 LEARNING NEW SKILL")
        print("="*80)

        print(f"\n[Lumenis] Learning new skill: {skill_name}...")
        result = self.semantic.add_skill_to_agent("Lumenis", skill_name)

        if result.get("status") == "success":
            print(f"[Lumenis] ✓ {result['message']}")

            # Verify
            skills = self.semantic.get_agent_skills("Lumenis")
            print(f"[Lumenis] Updated skill list: {', '.join(skills)}")
        else:
            print(f"[Lumenis] ✗ {result.get('message')}")

    def run_demo(self):
        """Run the complete demonstration"""
        print("\n")
        print("╔══════════════════════════════════════════════════════════════════════════╗")
        print("║                  LUMENIS SEMANTIC LAYER DEMONSTRATION                    ║")
        print("║                     Self-Awareness through RDF/OWL                       ║")
        print("╚══════════════════════════════════════════════════════════════════════════╝")

        # Initialize
        self.initialize_knowledge_graph()

        # Self-awareness
        self.understand_self()
        self.discover_capabilities()
        self.explore_relationships()

        # Peer discovery
        self.discover_peers()

        # Semantic exploration
        self.semantic_exploration()

        # Visualization
        self.visualize_self()

        # Stats
        self.get_system_stats()

        # Learn new skill
        self.learn_new_skill("SemanticWebReasoning")

        # Final message
        print("\n" + "="*80)
        print("✅ DEMONSTRATION COMPLETE")
        print("="*80)
        print("\n[Lumenis] I now have semantic self-awareness through the knowledge graph!")
        print("[Lumenis] I can query my identity, discover capabilities, and understand")
        print("[Lumenis] my relationships with other system components.")
        print("\n[Lumenis] The semantic layer gives me true self-reflection capabilities.")
        print()


def main():
    """Run the demonstration"""
    try:
        demo = LumenisSemanticDemo()
        demo.run_demo()
        return 0
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
