#!/usr/bin/env python3
"""
Test Script for Semantic Layer
===============================

Comprehensive test of the One2lvOS semantic layer components.
"""

import sys
import os

# Load environment variables from .env file
env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value


def test_rdf_parser():
    """Test RDF parser"""
    print("\n" + "=" * 80)
    print("TEST 1: RDF Parser")
    print("=" * 80)

    try:
        from rdf_parser import RDFParser

        parser = RDFParser()

        # Parse RDF schema
        print("\nParsing rdf-schema.ttl...")
        triples = parser.parse_file("rdf-schema.ttl")
        print(f"✓ Parsed {len(triples)} triples")

        classes = parser.get_classes()
        print(f"✓ Found {len(classes)} classes")

        properties = parser.get_properties()
        print(f"✓ Found {len(properties)} properties")

        # Parse One2lvOS ontology
        print("\nParsing one2lvos-ontology.ttl...")
        parser2 = RDFParser()
        triples2 = parser2.parse_file("one2lvos-ontology.ttl")
        print(f"✓ Parsed {len(triples2)} triples")

        classes2 = parser2.get_classes()
        print(f"✓ Found {len(classes2)} classes")
        print(f"  Classes: {', '.join([c.split('#')[-1] for c in classes2[:5]])}")

        instances = parser2.get_instances()
        print(f"✓ Found {len(instances)} instances")
        print(f"  Instances: {', '.join([i.split('#')[-1] for i in instances[:5]])}")

        return True
    except Exception as e:
        print(f"✗ RDF Parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_astra_bridge():
    """Test Astra DB bridge"""
    print("\n" + "=" * 80)
    print("TEST 2: Astra DB Semantic Bridge")
    print("=" * 80)

    try:
        from astra_semantic_bridge import AstraSemanticBridge
        from rdf_parser import Triple

        print("\nInitializing Astra DB bridge...")
        bridge = AstraSemanticBridge()
        print("✓ Bridge initialized")

        # Create test triple
        test_triple = Triple(
            subject="http://one2lv.com/ontology#TestEntity",
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            object="http://one2lv.com/ontology#Agent",
            object_type="uri"
        )

        print("\nStoring test triple...")
        success = bridge.store_triple(test_triple)
        print(f"{'✓' if success else '✗'} Triple storage: {success}")

        print("\nQuerying test triple...")
        results = bridge.query_triples(subject="http://one2lv.com/ontology#TestEntity")
        print(f"✓ Found {len(results)} results")

        print("\nSemantic search test...")
        results = bridge.semantic_search("agent artificial intelligence", limit=5)
        print(f"✓ Semantic search returned {len(results)} results")

        return True
    except Exception as e:
        print(f"✗ Astra Bridge test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_knowledge_graph_manager():
    """Test knowledge graph manager"""
    print("\n" + "=" * 80)
    print("TEST 3: Knowledge Graph Manager")
    print("=" * 80)

    try:
        from knowledge_graph_manager import KnowledgeGraphManager

        print("\nInitializing knowledge graph manager...")
        manager = KnowledgeGraphManager()
        print("✓ Manager initialized")

        print("\nLoading ontologies...")
        results = manager.load_all_ontologies()
        print(f"✓ Loaded {len(results)} ontologies")
        for name, count in results.items():
            print(f"  - {name}: {count} triples")

        print("\nGetting statistics...")
        stats = manager.get_stats()
        print(f"✓ Total triples: {stats['total_triples']}")
        print(f"✓ Unique subjects: {stats['unique_subjects']}")
        print(f"✓ Unique predicates: {stats['unique_predicates']}")

        print("\nListing agents...")
        agents = manager.get_all_agents()
        print(f"✓ Found {len(agents)} agents")
        if agents:
            print(f"  Agents: {', '.join([a.split('#')[-1] for a in agents])}")

        if agents:
            print(f"\nVisualizing agent: {agents[0].split('#')[-1]}")
            viz = manager.visualize_entity(agents[0])
            print(viz)

        return True
    except Exception as e:
        print(f"✗ Knowledge Graph Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_lumenis_tools():
    """Test Lumenis ontology tools"""
    print("\n" + "=" * 80)
    print("TEST 4: Lumenis Ontology Tools")
    print("=" * 80)

    try:
        from tools.lumenis_ontology_tools import LumenisOntologyTools

        print("\nInitializing Lumenis tools...")
        tools = LumenisOntologyTools()
        print("✓ Tools initialized")

        print("\nGetting stats...")
        stats = tools.get_ontology_stats()
        if stats.get("status") == "success":
            print(f"✓ Stats retrieved")
            print(f"  Total triples: {stats.get('total_triples', 0)}")
        else:
            print(f"✗ Stats retrieval failed")

        print("\nListing agents...")
        agents = tools.list_agents()
        if agents and not str(agents[0]).startswith("Error"):
            print(f"✓ Found agents: {', '.join(agents)}")
        else:
            print(f"! No agents found yet (this is OK if ontologies not loaded)")

        print("\nSemantic search...")
        results = tools.semantic_search("artificial intelligence", limit=3)
        print(f"✓ Search returned {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            print(f"  {i}. {r.get('subject', 'N/A')} → {r.get('predicate', 'N/A')} → {r.get('object', 'N/A')}")

        return True
    except Exception as e:
        print(f"✗ Lumenis Tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_semantic_skill():
    """Test semantic skill"""
    print("\n" + "=" * 80)
    print("TEST 5: Semantic Skill")
    print("=" * 80)

    try:
        from skills.semantic_skill import SemanticSkill

        print("\nInitializing semantic skill...")
        skill = SemanticSkill()
        print(f"✓ Skill initialized: {skill.name}")

        print("\nTesting skill actions...")

        # Stats
        result = skill.execute("stats")
        print(f"✓ Stats action executed: {result.get('status', 'unknown')}")

        # List agents
        result = skill.execute("list", type="agents")
        print(f"✓ List action executed: {type(result).__name__}")

        # Search
        result = skill.execute("search", query="agent", limit=3)
        print(f"✓ Search action executed: {len(result)} results")

        return True
    except Exception as e:
        print(f"✗ Semantic Skill test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("ONE2LVOS SEMANTIC LAYER - COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    tests = [
        ("RDF Parser", test_rdf_parser),
        ("Astra DB Bridge", test_astra_bridge),
        ("Knowledge Graph Manager", test_knowledge_graph_manager),
        ("Lumenis Tools", test_lumenis_tools),
        ("Semantic Skill", test_semantic_skill),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")

    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
