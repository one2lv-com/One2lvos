# One2lvOS Semantic Layer

A comprehensive semantic web layer for One2lvOS that provides RDF/OWL ontology management, knowledge graph storage, and semantic querying capabilities.

## Architecture

```
semantic_layer/
├── ontologies/              # RDF/Turtle ontology files
│   ├── rdf-schema.ttl      # Base RDF vocabulary
│   └── one2lvos-ontology.ttl  # One2lvOS-specific ontology
├── knowledge_graph/         # Knowledge graph storage
├── tools/                   # Semantic tools
│   └── lumenis_ontology_tools.py  # Tools for Lumenis
├── skills/                  # Agent skills
│   └── semantic_skill.py   # Semantic skill for agents
├── rdf_parser.py           # RDF/Turtle parser
├── astra_semantic_bridge.py  # Astra DB integration
├── knowledge_graph_manager.py  # High-level KG manager
└── semantic_cli.py         # Command-line interface
```

## Features

### 1. RDF/OWL Ontology Management
- Parse RDF/Turtle format ontologies
- Support for classes, properties, and instances
- Prefix expansion and URI resolution
- Query triples by subject, predicate, or object

### 2. Knowledge Graph Storage
- Store semantic triples in Astra DB
- Vector embeddings for semantic search
- Efficient querying and retrieval
- Relationship traversal

### 3. Semantic Search
- Vector-based semantic similarity search
- Natural language queries
- Contextual entity retrieval

### 4. Lumenis Integration
- Tools for Lumenis to interact with ontologies
- Skills for autonomous ontology management
- Command handlers for semantic operations

## Ontology Overview

### One2lvOS Ontology Classes

```turtle
# Core Classes
one2lv:Agent        # Autonomous agents
one2lv:Memory       # Memory entries
one2lv:Skill        # Computational skills
one2lv:Tool         # Agent tools
one2lv:Reactor      # Reactor cores
one2lv:Layer        # Architectural layers
one2lv:Integration  # External integrations
one2lv:KnowledgeGraph  # Knowledge graph entities

# Key Properties
one2lv:hasSkill     # Agent possesses skill
one2lv:hasTool      # Agent has tool
one2lv:hasMemory    # Agent has memory
one2lv:atLayer      # Component at layer
one2lv:connectsTo   # Component connections
```

### Predefined Instances

- **Agents**: Lumenis, Aria
- **Layers**: L1_Memory, L2_Skills, L3_Integrations
- **Integrations**: NvidiaIntegration, DiscordIntegration, MatonIntegration

## Usage

### Command Line Interface

```bash
# Load ontologies into knowledge graph
python semantic_cli.py load

# Get statistics
python semantic_cli.py stats

# List all agents
python semantic_cli.py list agents

# Query an entity
python semantic_cli.py query Lumenis

# Visualize relationships
python semantic_cli.py visualize Lumenis

# Semantic search
python semantic_cli.py search "artificial intelligence agent"

# Add skill to agent
python semantic_cli.py add-skill Lumenis SemanticParsing

# Get relationships
python semantic_cli.py relationships Lumenis

# Export knowledge graph
python semantic_cli.py export knowledge_graph.json
```

### Python API

```python
from semantic_layer import KnowledgeGraphManager

# Initialize manager
manager = KnowledgeGraphManager()

# Load ontologies
results = manager.load_all_ontologies()

# Query entity
info = manager.query_entity("http://one2lv.com/ontology#Lumenis")

# Semantic search
results = manager.semantic_search("artificial intelligence", limit=10)

# Get agent skills
skills = manager.get_agent_skills("http://one2lv.com/ontology#Lumenis")

# Add skill to agent
manager.add_agent_skill(
    "http://one2lv.com/ontology#Lumenis",
    "http://one2lv.com/ontology#SemanticParsing"
)

# Get statistics
stats = manager.get_stats()
```

### Lumenis Tools

```python
from semantic_layer.tools import LumenisOntologyTools

tools = LumenisOntologyTools()

# Load ontologies
result = tools.load_ontologies()

# List agents
agents = tools.list_agents()

# Visualize entity
viz = tools.visualize_entity("Lumenis")

# Semantic search
results = tools.semantic_search("knowledge graph", limit=10)

# Add relationship
tools.add_relationship("Lumenis", "hasSkill", "SemanticWeb")
```

### Lumenis Skill

```python
from semantic_layer.skills import SemanticSkill

skill = SemanticSkill()

# Initialize knowledge graph
result = skill.execute("init")

# Query entity
info = skill.execute("query", entity="Lumenis")

# Semantic search
results = skill.execute("search", query="AI agent", limit=5)

# List agents
agents = skill.execute("list", type="agents")

# Add skill to agent
result = skill.execute("add", type="skill", agent="Lumenis", skill="NLP")
```

## Integration with Astra DB

The semantic layer uses Astra DB for persistent storage of the knowledge graph:

- **Collection**: `semantic_knowledge_graph`
- **Vector Dimension**: 384 (for embeddings)
- **Metric**: Cosine similarity
- **Storage**: Structured documents with vector embeddings

Each triple is stored as:
```json
{
  "_id": "unique_triple_id",
  "subject": "http://one2lv.com/ontology#Lumenis",
  "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
  "object": "http://one2lv.com/ontology#Agent",
  "object_type": "uri",
  "triple_text": "Lumenis is an Agent",
  "$vector": [0.1, 0.2, ...],
  "created_at": "2026-10-24T00:00:00",
  "metadata": {}
}
```

## Use Cases

### 1. Agent Self-Knowledge
Lumenis can query its own capabilities, skills, and relationships in the system.

### 2. Dynamic Skill Discovery
Agents can discover available skills and tools through semantic search.

### 3. System Understanding
Query the architectural layers and component relationships.

### 4. Integration Mapping
Understand which external services are integrated and how they connect.

### 5. Knowledge Evolution
As the system grows, the knowledge graph captures new entities and relationships.

## Advanced Features

### SPARQL-like Queries
```python
# Find all agents with a specific skill
results = manager.query_triples(
    predicate="http://one2lv.com/ontology#hasSkill",
    obj="http://one2lv.com/ontology#SemanticParsing"
)

# Find all components at a specific layer
results = manager.query_triples(
    predicate="http://one2lv.com/ontology#atLayer",
    obj="http://one2lv.com/ontology#L1_Memory"
)
```

### Relationship Traversal
```python
# Get all related entities
related = manager.bridge.get_related(
    "http://one2lv.com/ontology#Lumenis",
    depth=2
)
```

### Visualization
```python
# Generate text visualization
viz = manager.visualize_entity("http://one2lv.com/ontology#Lumenis")
print(viz)
```

Output:
```
Entity: http://one2lv.com/ontology#Lumenis
================================================================================

Outgoing relationships:
  - type → Agent
  - hasSkill → SemanticParsing
  - atLayer → L2_Skills

Incoming relationships:
  - Aria → connectsTo

Total relationships: 4
```

## Extending the Ontology

To add new classes, properties, or instances, edit `ontologies/one2lvos-ontology.ttl`:

```turtle
# Add new class
one2lv:NewClass a owl:Class ;
    rdfs:label "NewClass" ;
    rdfs:comment "Description of the new class" ;
    rdfs:subClassOf owl:Thing .

# Add new property
one2lv:newProperty a owl:ObjectProperty ;
    rdfs:label "newProperty" ;
    rdfs:comment "Description of the property" ;
    rdfs:domain one2lv:Agent ;
    rdfs:range one2lv:NewClass .

# Add new instance
one2lv:NewInstance a one2lv:NewClass ;
    rdfs:label "NewInstance" ;
    rdfs:comment "Description of the instance" .
```

Then reload the ontologies:
```bash
python semantic_cli.py load
```

## Future Enhancements

- [ ] NVIDIA NIM integration for embeddings
- [ ] Full SPARQL query support
- [ ] Ontology versioning and migration
- [ ] Graph visualization (GraphViz, D3.js)
- [ ] Reasoning engine (OWL inference)
- [ ] Federation with external knowledge bases
- [ ] Real-time event notifications
- [ ] Multi-agent collaborative ontology editing

## Requirements

```
astrapy>=1.0.0
requests>=2.28.0
```

Or use existing One2lvOS dependencies.

## License

Part of the One2lvOS project.

## Contact

For questions or issues, contact the One2lv team.
