"""
One2lvOS Semantic Layer
=======================

A semantic web layer for One2lvOS that provides:
- RDF/OWL ontology management
- Knowledge graph storage in Astra DB
- SPARQL querying capabilities
- Lumenis ontology tools

Architecture:
- ontologies/ - RDF schemas and One2lvOS ontology
- knowledge_graph/ - Knowledge graph management
- tools/ - Semantic web tools
- skills/ - Skills for Lumenis to use
"""

__version__ = "1.0.0"
__author__ = "One2lv"

from .rdf_parser import RDFParser, Triple
from .astra_semantic_bridge import AstraSemanticBridge
from .knowledge_graph_manager import KnowledgeGraphManager

__all__ = [
    "RDFParser",
    "Triple",
    "AstraSemanticBridge",
    "KnowledgeGraphManager",
]
