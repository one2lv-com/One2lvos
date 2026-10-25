# Lumenis Integration with Semantic Layer

This document describes how Lumenis can use the semantic layer for ontology management and knowledge graph operations.

## Overview

The semantic layer provides Lumenis with:
- **Self-awareness**: Query its own capabilities and relationships
- **Ontology management**: Load, parse, and manage RDF ontologies
- **Knowledge graph**: Store and query semantic triples
- **Semantic search**: Find relevant entities through natural language

## Integration Points

### 1. Direct Tool Access

Lumenis can import and use the tools directly:

```python
from semantic_layer.tools import LumenisOntologyTools

class Lumenis:
    def __init__(self):
        self.semantic_tools = LumenisOntologyTools()

    def initialize_knowledge_graph(self):
        """Load all ontologies on startup"""
        result = self.semantic_tools.load_ontologies()
        print(f"Loaded ontologies: {result}")

    def query_self(self):
        """Query Lumenis' own capabilities"""
        info = self.semantic_tools.query_entity("Lumenis")
        skills = self.semantic_tools.get_agent_skills("Lumenis")
        return {
            "info": info,
            "skills": skills
        }

    def find_similar_concepts(self, query: str):
        """Semantic search for concepts"""
        results = self.semantic_tools.semantic_search(query, limit=10)
        return results
```

### 2. Skill-Based Access

Use the SemanticSkill for structured operations:

```python
from semantic_layer.skills import SemanticSkill

class Lumenis:
    def __init__(self):
        self.semantic_skill = SemanticSkill()

    def handle_semantic_request(self, action: str, **kwargs):
        """Handle semantic operations"""
        return self.semantic_skill.execute(action, **kwargs)

# Usage examples:
lumenis = Lumenis()

# Initialize
lumenis.handle_semantic_request("init")

# Query
info = lumenis.handle_semantic_request("query", entity="Lumenis")

# Search
results = lumenis.handle_semantic_request("search", query="AI agent")

# List
agents = lumenis.handle_semantic_request("list", type="agents")
```

### 3. Command Handler

Use the command handler for simple text-based commands:

```python
from semantic_layer.tools import lumenis_command_handler

class Lumenis:
    def process_semantic_command(self, command: str, *args):
        """Process semantic commands"""
        return lumenis_command_handler(command, *args)

# Usage examples:
lumenis = Lumenis()

# Load ontologies
result = lumenis.process_semantic_command("load_ontologies")

# List agents
result = lumenis.process_semantic_command("list_agents")

# Query entity
result = lumenis.process_semantic_command("query_entity", "Lumenis")

# Semantic search
result = lumenis.process_semantic_command("semantic_search", "AI", "agent")
```

## Use Case Examples

### 1. Self-Awareness

```python
def lumenis_self_awareness():
    """Lumenis queries its own identity and capabilities"""
    tools = LumenisOntologyTools()

    # Who am I?
    info = tools.query_entity("Lumenis")
    print(f"I am: {info}")

    # What can I do?
    skills = tools.get_agent_skills("Lumenis")
    print(f"My skills: {skills}")

    # How do I relate to other components?
    relationships = tools.get_entity_relationships("Lumenis")
    print(f"My relationships: {relationships}")
```

### 2. Learning New Skills

```python
def lumenis_learn_skill(skill_name: str):
    """Lumenis learns a new skill"""
    tools = LumenisOntologyTools()

    # Add skill to knowledge graph
    result = tools.add_skill_to_agent("Lumenis", skill_name)

    if result["status"] == "success":
        print(f"Learned new skill: {skill_name}")

        # Verify
        skills = tools.get_agent_skills("Lumenis")
        print(f"Updated skills: {skills}")

    return result
```

### 3. Discovering Integrations

```python
def discover_available_integrations():
    """Find all available integrations"""
    tools = LumenisOntologyTools()

    # Semantic search for integrations
    results = tools.semantic_search("integration external service")

    integrations = []
    for result in results:
        if "Integration" in result.get("subject", ""):
            integrations.append(result)

    return integrations
```

### 4. Understanding System Architecture

```python
def understand_system_layers():
    """Query the architectural layers"""
    tools = LumenisOntologyTools()

    # Search for layers
    results = tools.semantic_search("layer architecture")

    layers = {}
    for result in results:
        if "Layer" in result.get("subject", ""):
            layer_name = result["subject"]
            info = tools.query_entity(layer_name)
            layers[layer_name] = info

    return layers
```

### 5. Dynamic Tool Discovery

```python
def find_tools_for_task(task_description: str):
    """Find tools that can help with a task"""
    tools = LumenisOntologyTools()

    # Semantic search
    results = tools.semantic_search(f"tool {task_description}")

    relevant_tools = []
    for result in results:
        if "Tool" in result.get("object", "") or "tool" in result.get("object", "").lower():
            relevant_tools.append(result)

    return relevant_tools
```

## Integration with Lumenis Main Loop

```python
# In lumenis-main.py

from semantic_layer.tools import LumenisOntologyTools

class Lumenis:
    def __init__(self):
        # ... existing initialization ...

        # Add semantic tools
        self.semantic_tools = LumenisOntologyTools()

        # Initialize knowledge graph on startup
        print("Initializing semantic knowledge graph...")
        self.semantic_tools.load_ontologies()

    def process_message(self, message: str):
        # ... existing message processing ...

        # Add semantic commands
        if message.startswith("/semantic"):
            parts = message.split()
            command = parts[1] if len(parts) > 1 else "help"
            args = parts[2:] if len(parts) > 2 else []

            return self.handle_semantic_command(command, *args)

    def handle_semantic_command(self, command: str, *args):
        """Handle semantic layer commands"""
        from semantic_layer.tools import lumenis_command_handler
        return lumenis_command_handler(command, *args)
```

## Chat Interface Commands

Add these commands to Lumenis' chat interface:

```
/semantic load_ontologies    - Load all ontologies
/semantic stats              - Show knowledge graph statistics
/semantic list_agents        - List all agents
/semantic query [entity]     - Query an entity
/semantic search [query]     - Semantic search
/semantic visualize [entity] - Visualize entity relationships
/semantic add_skill [agent] [skill] - Add skill to agent
```

Example usage in chat:
```
User: /semantic query Lumenis
Lumenis: Here's what I know about myself:
  - Type: Agent
  - Skills: [SemanticParsing, NaturalLanguageProcessing]
  - Layer: L2_Skills
  - Connections: Aria, ReactorCore

User: /semantic search "knowledge graph"
Lumenis: Found 5 results related to "knowledge graph"
  1. KnowledgeGraph → type → Class
  2. Lumenis → uses → KnowledgeGraph
  3. ...
```

## Autonomous Semantic Operations

Lumenis can autonomously use the semantic layer:

```python
class AutonomousLumenis:
    def __init__(self):
        self.semantic_tools = LumenisOntologyTools()
        self.knowledge_graph_initialized = False

    def on_startup(self):
        """Initialize on startup"""
        if not self.knowledge_graph_initialized:
            print("Loading ontologies...")
            self.semantic_tools.load_ontologies()
            self.knowledge_graph_initialized = True

    def on_new_skill_learned(self, skill_name: str):
        """Update knowledge graph when learning new skill"""
        self.semantic_tools.add_skill_to_agent("Lumenis", skill_name)

    def on_new_integration(self, integration_name: str, endpoint: str):
        """Add new integration to knowledge graph"""
        # Add integration entity
        self.semantic_tools.add_relationship(
            integration_name,
            "integrationType",
            "external_service"
        )

        # Connect to Lumenis
        self.semantic_tools.add_relationship(
            "Lumenis",
            "usesIntegration",
            integration_name
        )

    def understand_context(self, query: str):
        """Use semantic search to understand context"""
        results = self.semantic_tools.semantic_search(query, limit=5)

        # Analyze results to build contextual understanding
        context = {
            "query": query,
            "related_concepts": results,
            "confidence": self._calculate_confidence(results)
        }

        return context
```

## Testing

Test the integration:

```bash
# Run the semantic skill test
python semantic_layer/skills/semantic_skill.py

# Run the tools test
python semantic_layer/tools/lumenis_ontology_tools.py

# Run the CLI
python semantic_layer/semantic_cli.py load
python semantic_layer/semantic_cli.py list agents
python semantic_layer/semantic_cli.py query Lumenis
```

## Performance Considerations

1. **Lazy Loading**: Load ontologies only when needed
2. **Caching**: Cache frequently accessed entities
3. **Batch Operations**: Use batch queries for multiple entities
4. **Async Operations**: Use async for non-blocking semantic operations

```python
import asyncio

class AsyncLumenis:
    async def semantic_search_async(self, query: str):
        """Async semantic search"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.semantic_tools.semantic_search,
            query
        )
        return result
```

## Next Steps

1. Integrate semantic tools into `lumenis-main.py`
2. Add semantic commands to chat interface
3. Implement autonomous ontology updates
4. Add semantic context to message processing
5. Create semantic-aware decision making

## Support

For questions or issues with the semantic integration:
- Check the main README: `semantic_layer/README.md`
- Review examples in: `semantic_layer/tools/lumenis_ontology_tools.py`
- Test with: `semantic_layer/semantic_cli.py`
