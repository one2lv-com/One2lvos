"""
RDF Parser and Ontology Manager
================================

Parses RDF/Turtle files and manages semantic triples.
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Triple:
    """Represents an RDF triple (subject, predicate, object)"""
    subject: str
    predicate: str
    object: str
    object_type: str = "uri"  # uri, literal, or blank_node

    def __repr__(self):
        return f"<{self.subject}> <{self.predicate}> <{self.object}>"


class RDFParser:
    """
    Parser for RDF/Turtle format ontologies.
    Handles prefix expansion and triple extraction.
    """

    def __init__(self, ontology_dir: Optional[str] = None):
        if ontology_dir is None:
            ontology_dir = os.path.join(
                os.path.dirname(__file__),
                "ontologies"
            )
        self.ontology_dir = Path(ontology_dir)
        self.prefixes: Dict[str, str] = {}
        self.triples: List[Triple] = []

    def parse_file(self, filename: str) -> List[Triple]:
        """Parse an RDF/Turtle file and extract triples"""
        filepath = self.ontology_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Ontology file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        return self.parse_turtle(content)

    def parse_turtle(self, content: str) -> List[Triple]:
        """Parse Turtle format RDF content"""
        self.prefixes = {}
        self.triples = []

        # Remove comments
        lines = []
        for line in content.split('\n'):
            # Remove comments
            if '#' in line:
                comment_pos = line.find('#')
                # Check if it's not part of a URI
                if comment_pos > 0 and line[comment_pos-1] not in ['<', ':']:
                    line = line[:comment_pos]
            lines.append(line)

        content = '\n'.join(lines)

        # Extract prefixes
        prefix_pattern = r'@prefix\s+(\w+):\s+<([^>]+)>\s+\.'
        for match in re.finditer(prefix_pattern, content):
            prefix, uri = match.groups()
            self.prefixes[prefix] = uri

        # Remove prefix declarations
        content = re.sub(prefix_pattern, '', content)

        # Extract triples (simplified parser)
        # This handles basic subject predicate object patterns
        triple_pattern = r'(<[^>]+>|[\w]+:[\w]+)\s+(<[^>]+>|[\w]+:[\w]+|a)\s+([^;.]+)'

        for match in re.finditer(triple_pattern, content):
            subject, predicate, obj_str = match.groups()

            # Handle 'a' as rdf:type
            if predicate == 'a':
                predicate = 'rdf:type'

            # Parse object (might be multi-line or have multiple values)
            objects = self._parse_object(obj_str.strip())

            for obj, obj_type in objects:
                triple = Triple(
                    subject=self._expand_uri(subject),
                    predicate=self._expand_uri(predicate),
                    object=self._expand_uri(obj) if obj_type == 'uri' else obj,
                    object_type=obj_type
                )
                self.triples.append(triple)

        return self.triples

    def _parse_object(self, obj_str: str) -> List[Tuple[str, str]]:
        """Parse object part of a triple (may contain multiple values)"""
        objects = []

        # Split by comma for multiple values
        parts = re.split(r'\s*,\s*', obj_str)

        for part in parts:
            part = part.strip()
            if not part or part in [';', '.']:
                continue

            # Literal string
            if part.startswith('"'):
                literal_match = re.match(r'"([^"]*)"', part)
                if literal_match:
                    objects.append((literal_match.group(1), 'literal'))
            # URI in angle brackets
            elif part.startswith('<') and part.endswith('>'):
                objects.append((part[1:-1], 'uri'))
            # Prefixed name
            elif ':' in part:
                objects.append((part, 'uri'))
            # Blank node
            elif part.startswith('_:'):
                objects.append((part, 'blank_node'))

        return objects if objects else [(obj_str, 'uri')]

    def _expand_uri(self, uri: str) -> str:
        """Expand a prefixed URI to full URI"""
        if uri.startswith('<') and uri.endswith('>'):
            return uri[1:-1]

        if ':' in uri:
            prefix, local = uri.split(':', 1)
            if prefix in self.prefixes:
                return self.prefixes[prefix] + local

        return uri

    def get_classes(self) -> List[str]:
        """Get all classes defined in the ontology"""
        classes = []
        for triple in self.triples:
            if triple.predicate.endswith('type') and \
               (triple.object.endswith('Class') or triple.object.endswith('owl#Class')):
                classes.append(triple.subject)
        return classes

    def get_properties(self) -> List[str]:
        """Get all properties defined in the ontology"""
        properties = []
        for triple in self.triples:
            if triple.predicate.endswith('type') and \
               'Property' in triple.object:
                properties.append(triple.subject)
        return properties

    def get_instances(self) -> List[str]:
        """Get all instances defined in the ontology"""
        instances = []
        classes = set(self.get_classes())

        for triple in self.triples:
            if triple.predicate.endswith('type') and triple.object in classes:
                instances.append(triple.subject)

        return instances

    def query_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None
    ) -> List[Triple]:
        """Query triples by subject, predicate, or object"""
        results = self.triples

        if subject:
            subject = self._expand_uri(subject)
            results = [t for t in results if t.subject == subject]

        if predicate:
            predicate = self._expand_uri(predicate)
            results = [t for t in results if t.predicate == predicate]

        if obj:
            obj = self._expand_uri(obj)
            results = [t for t in results if t.object == obj]

        return results

    def to_json(self) -> Dict:
        """Export ontology to JSON format"""
        return {
            "prefixes": self.prefixes,
            "triples": [
                {
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object,
                    "object_type": t.object_type
                }
                for t in self.triples
            ],
            "classes": self.get_classes(),
            "properties": self.get_properties(),
            "instances": self.get_instances()
        }


if __name__ == "__main__":
    # Test the parser
    parser = RDFParser()

    print("Parsing RDF Schema...")
    triples = parser.parse_file("rdf-schema.ttl")
    print(f"Found {len(triples)} triples")
    print(f"Classes: {len(parser.get_classes())}")
    print(f"Properties: {len(parser.get_properties())}")

    print("\nParsing One2lvOS Ontology...")
    parser2 = RDFParser()
    triples2 = parser2.parse_file("one2lvos-ontology.ttl")
    print(f"Found {len(triples2)} triples")
    print(f"Classes: {parser2.get_classes()}")
    print(f"Instances: {parser2.get_instances()}")
