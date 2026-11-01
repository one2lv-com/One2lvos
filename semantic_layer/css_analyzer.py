#!/usr/bin/env python3
"""
CSS Analyzer
============

Extract semantic information from CSS files and convert to RDF triples.
"""

import re
import json
from typing import List, Dict, Tuple
from pathlib import Path


class CSSAnalyzer:
    """Analyze CSS files and extract semantic information"""

    def __init__(self, css_file: str):
        self.css_file = css_file
        with open(css_file, 'r', encoding='utf-8') as f:
            self.css_content = f.read()

        self.colors = []
        self.fonts = []
        self.components = []
        self.layouts = []

    def extract_colors(self) -> List[Dict]:
        """Extract color values from CSS"""
        # Find hex colors
        hex_pattern = r'#([0-9a-fA-F]{3,6})\b'
        hex_colors = set(re.findall(hex_pattern, self.css_content))

        # Find rgb/rgba colors
        rgb_pattern = r'rgba?\([^)]+\)'
        rgb_colors = set(re.findall(rgb_pattern, self.css_content))

        self.colors = []

        # Process hex colors
        for color in hex_colors:
            full_hex = f"#{color}"
            # Find where this color is used
            context = self._find_color_context(full_hex)
            self.colors.append({
                'hex': full_hex,
                'type': 'hex',
                'usage': context
            })

        # Process RGB colors
        for color in rgb_colors:
            self.colors.append({
                'value': color,
                'type': 'rgb',
                'usage': self._find_color_context(color)
            })

        return self.colors

    def _find_color_context(self, color: str) -> List[str]:
        """Find CSS rules where a color is used"""
        contexts = []
        lines = self.css_content.split('\n')

        for i, line in enumerate(lines):
            if color in line:
                # Look backwards for the selector
                for j in range(i, max(0, i - 20), -1):
                    if '{' in lines[j]:
                        # Find selector
                        selector_line = lines[j].split('{')[0].strip()
                        if selector_line:
                            contexts.append(selector_line)
                        break

        return contexts[:5]  # Limit to 5 contexts

    def extract_fonts(self) -> List[Dict]:
        """Extract font definitions and usage"""
        # Extract @font-face declarations
        fontface_pattern = r"@font-face\s*\{([^}]+)\}"
        fontfaces = re.findall(fontface_pattern, self.css_content, re.DOTALL)

        self.fonts = []

        for fontface in fontfaces:
            # Extract font-family
            family_match = re.search(r"font-family:\s*['\"]([^'\"]+)['\"]", fontface)
            # Extract src URLs
            src_matches = re.findall(r"url\(['\"]([^'\"]+)['\"]", fontface)

            if family_match:
                self.fonts.append({
                    'family': family_match.group(1),
                    'sources': src_matches,
                    'type': 'webfont'
                })

        # Extract font-family usage
        font_usage_pattern = r"font-family:\s*([^;]+)"
        font_usages = re.findall(font_usage_pattern, self.css_content)

        for usage in set(font_usages):
            if not any(f['family'] in usage for f in self.fonts):
                # System font
                fonts_list = [f.strip(' "\'') for f in usage.split(',')]
                self.fonts.append({
                    'family': fonts_list[0],
                    'fallbacks': fonts_list[1:],
                    'type': 'system'
                })

        return self.fonts

    def extract_components(self) -> List[Dict]:
        """Extract UI components based on CSS classes and IDs"""
        # Common UI component patterns
        component_patterns = {
            'navigation': [r'\.nav', r'#nav', r'\.menu'],
            'button': [r'\.btn', r'\.button', r'\.cta'],
            'form': [r'\.form', r'input', r'\.field'],
            'container': [r'\.box', r'\.container', r'\.wrapper'],
            'alert': [r'\.alert', r'\.warning', r'\.error', r'\.notice'],
            'tooltip': [r'\.tooltip', r'\.tip'],
            'modal': [r'\.modal', r'\.dialog', r'\.popup'],
            'card': [r'\.card', r'\.panel'],
            'header': [r'\.header', r'#header'],
            'footer': [r'\.footer', r'#footer'],
            'sidebar': [r'\.sidebar', r'\.side']
        }

        self.components = []

        for comp_type, patterns in component_patterns.items():
            for pattern in patterns:
                matches = re.finditer(
                    rf"({pattern}[^{{]*)\s*{{([^}}]+)}}",
                    self.css_content,
                    re.DOTALL
                )

                for match in matches:
                    selector = match.group(1).strip()
                    properties = match.group(2).strip()

                    # Extract key properties
                    bg_color = re.search(r'background(?:-color)?:\s*([^;]+)', properties)
                    color = re.search(r'(?<!background-)color:\s*([^;]+)', properties)

                    self.components.append({
                        'type': comp_type,
                        'selector': selector,
                        'background': bg_color.group(1).strip() if bg_color else None,
                        'color': color.group(1).strip() if color else None
                    })

        return self.components

    def extract_layouts(self) -> List[Dict]:
        """Extract layout patterns"""
        layout_patterns = [
            r'\.column', r'\.grid', r'\.flex',
            r'\.row', r'\.container', r'\.layout'
        ]

        self.layouts = []

        for pattern in layout_patterns:
            matches = re.finditer(
                rf"({pattern}[^{{]*)\s*{{([^}}]+)}}",
                self.css_content,
                re.DOTALL
            )

            for match in matches:
                selector = match.group(1).strip()
                properties = match.group(2).strip()

                # Check for layout properties
                has_float = 'float:' in properties
                has_flex = 'flex' in properties or 'display:flex' in properties
                has_grid = 'grid' in properties or 'display:grid' in properties
                has_position = 'position:' in properties

                if any([has_float, has_flex, has_grid, has_position]):
                    self.layouts.append({
                        'selector': selector,
                        'uses_float': has_float,
                        'uses_flex': has_flex,
                        'uses_grid': has_grid,
                        'uses_position': has_position
                    })

        return self.layouts

    def analyze_all(self) -> Dict:
        """Run all analysis"""
        return {
            'colors': self.extract_colors(),
            'fonts': self.extract_fonts(),
            'components': self.extract_components(),
            'layouts': self.extract_layouts()
        }

    def generate_report(self) -> str:
        """Generate a text report of the analysis"""
        analysis = self.analyze_all()

        report = []
        report.append("=" * 80)
        report.append("CSS ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")

        # Colors
        report.append(f"COLORS ({len(analysis['colors'])})")
        report.append("-" * 80)
        color_map = {}
        for color in analysis['colors'][:20]:  # Top 20 colors
            hex_val = color.get('hex', color.get('value'))
            usage = color.get('usage', [])
            report.append(f"  {hex_val}")
            if usage:
                report.append(f"    Used in: {', '.join(usage[:3])}")
            color_map[hex_val] = len(usage)
        report.append("")

        # Most used colors
        sorted_colors = sorted(color_map.items(), key=lambda x: x[1], reverse=True)
        report.append("Most Used Colors:")
        for color, count in sorted_colors[:10]:
            report.append(f"  {color} ({count} uses)")
        report.append("")

        # Fonts
        report.append(f"FONTS ({len(analysis['fonts'])})")
        report.append("-" * 80)
        for font in analysis['fonts'][:15]:
            report.append(f"  {font['family']} ({font['type']})")
            if font.get('sources'):
                report.append(f"    Sources: {len(font['sources'])}")
        report.append("")

        # Components
        report.append(f"UI COMPONENTS ({len(analysis['components'])})")
        report.append("-" * 80)
        comp_types = {}
        for comp in analysis['components']:
            comp_type = comp['type']
            comp_types[comp_type] = comp_types.get(comp_type, 0) + 1

        for comp_type, count in sorted(comp_types.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {comp_type}: {count} components")
        report.append("")

        # Layouts
        report.append(f"LAYOUTS ({len(analysis['layouts'])})")
        report.append("-" * 80)
        float_count = sum(1 for l in analysis['layouts'] if l['uses_float'])
        flex_count = sum(1 for l in analysis['layouts'] if l['uses_flex'])
        grid_count = sum(1 for l in analysis['layouts'] if l['uses_grid'])
        position_count = sum(1 for l in analysis['layouts'] if l['uses_position'])

        report.append(f"  Float layouts: {float_count}")
        report.append(f"  Flexbox layouts: {flex_count}")
        report.append(f"  Grid layouts: {grid_count}")
        report.append(f"  Positioned layouts: {position_count}")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def export_json(self, output_file: str):
        """Export analysis to JSON"""
        analysis = self.analyze_all()
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python css_analyzer.py <css_file>")
        sys.exit(1)

    css_file = sys.argv[1]

    print(f"Analyzing {css_file}...")
    analyzer = CSSAnalyzer(css_file)

    # Generate report
    report = analyzer.generate_report()
    print(report)

    # Export JSON
    json_file = css_file.replace('.css', '_analysis.json')
    analyzer.export_json(json_file)
    print(f"\nAnalysis exported to: {json_file}")
