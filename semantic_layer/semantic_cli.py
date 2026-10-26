#!/usr/bin/env python3
"""
Semantic Layer CLI
==================

Command-line interface for managing the One2lvOS semantic layer.
"""

import sys
import argparse
from tools.lumenis_ontology_tools import LumenisOntologyTools


def main():
    parser = argparse.ArgumentParser(
        description="One2lvOS Semantic Layer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load all ontologies
  %(prog)s load

  # Get statistics
  %(prog)s stats

  # List all agents
  %(prog)s list agents

  # Query an entity
  %(prog)s query Lumenis

  # Visualize an entity
  %(prog)s visualize Lumenis

  # Semantic search
  %(prog)s search "artificial intelligence agent"

  # Add a skill to an agent
  %(prog)s add-skill Lumenis SemanticParsing

  # Get entity relationships
  %(prog)s relationships Lumenis

  # Export knowledge graph
  %(prog)s export knowledge_graph.json
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Load command
    subparsers.add_parser("load", help="Load all ontologies into knowledge graph")

    # Stats command
    subparsers.add_parser("stats", help="Get knowledge graph statistics")

    # List command
    list_parser = subparsers.add_parser("list", help="List entities")
    list_parser.add_argument("type", choices=["agents", "skills"], help="Type of entities to list")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query an entity")
    query_parser.add_argument("entity", help="Entity name to query")

    # Visualize command
    viz_parser = subparsers.add_parser("visualize", help="Visualize an entity")
    viz_parser.add_argument("entity", help="Entity name to visualize")

    # Search command
    search_parser = subparsers.add_parser("search", help="Semantic search")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Result limit")

    # Relationships command
    rel_parser = subparsers.add_parser("relationships", help="Get entity relationships")
    rel_parser.add_argument("entity", help="Entity name")

    # Add skill command
    add_skill_parser = subparsers.add_parser("add-skill", help="Add skill to agent")
    add_skill_parser.add_argument("agent", help="Agent name")
    add_skill_parser.add_argument("skill", help="Skill name")

    # Add relationship command
    add_rel_parser = subparsers.add_parser("add-relationship", help="Add a relationship")
    add_rel_parser.add_argument("subject", help="Subject entity")
    add_rel_parser.add_argument("predicate", help="Predicate")
    add_rel_parser.add_argument("object", help="Object entity")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export knowledge graph")
    export_parser.add_argument("output", help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize tools
    tools = LumenisOntologyTools()

    # Execute command
    if args.command == "load":
        result = tools.load_ontologies()
        print_result(result)

    elif args.command == "stats":
        result = tools.get_ontology_stats()
        print_result(result)

    elif args.command == "list":
        if args.type == "agents":
            result = tools.list_agents()
        else:
            result = tools.list_skills()
        print("Found entities:")
        for entity in result:
            print(f"  - {entity}")

    elif args.command == "query":
        result = tools.query_entity(args.entity)
        print_result(result)

    elif args.command == "visualize":
        result = tools.visualize_entity(args.entity)
        print(result)

    elif args.command == "search":
        results = tools.semantic_search(args.query, args.limit)
        print(f"Search results for: '{args.query}'")
        print("=" * 80)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.get('subject', 'N/A')} → {result.get('predicate', 'N/A')} → {result.get('object', 'N/A')}")
            if 'similarity' in result:
                print(f"   Similarity: {result['similarity']:.4f}")

    elif args.command == "relationships":
        result = tools.get_entity_relationships(args.entity)
        print_result(result)

    elif args.command == "add-skill":
        result = tools.add_skill_to_agent(args.agent, args.skill)
        print_result(result)

    elif args.command == "add-relationship":
        result = tools.add_relationship(args.subject, args.predicate, args.object)
        print_result(result)

    elif args.command == "export":
        result = tools.export_knowledge_graph(args.output)
        print_result(result)


def print_result(result):
    """Pretty print a result dictionary"""
    import json
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
