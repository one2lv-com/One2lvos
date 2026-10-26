#!/usr/bin/env python3
"""
Lumenis Design System
=====================

Design system for Lumenis UI based on extracted CSS patterns.
Integrates with semantic layer for ontology-driven UI generation.
"""

import json
from typing import Dict, List
from dataclasses import dataclass, asdict


@dataclass
class ColorPalette:
    """Color palette definition"""
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    error: str
    warning: str
    success: str
    info: str


@dataclass
class Typography:
    """Typography system"""
    primary_font: str
    secondary_font: str
    monospace_font: str
    base_size: str
    scale_ratio: float


@dataclass
class Spacing:
    """Spacing system"""
    xs: str
    sm: str
    md: str
    lg: str
    xl: str


@dataclass
class Component:
    """UI Component definition"""
    name: str
    type: str
    css_class: str
    background: str
    color: str
    properties: Dict


class LumenisDesignSystem:
    """
    Design system for Lumenis inspired by DynDNS patterns
    but adapted for AI agent interfaces.
    """

    def __init__(self):
        # Color palette inspired by DynDNS but modernized
        self.colors = ColorPalette(
            primary="#00A3FF",      # Bright blue for primary actions
            secondary="#6B7280",    # Neutral gray
            accent="#FFE36F",       # Yellow accent from DynDNS
            background="#FFFFFF",   # Clean white
            text="#1F2937",         # Dark gray text
            error="#DC2626",        # Red for errors
            warning="#FFFDBD",      # Light yellow from DynDNS
            success="#10B981",      # Green for success
            info="#FFF5D0"          # Light yellow info boxes from DynDNS
        )

        # Typography based on modern sans-serif
        self.typography = Typography(
            primary_font="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            secondary_font="'JetBrains Mono', 'Courier New', monospace",
            monospace_font="'JetBrains Mono', 'Courier New', monospace",
            base_size="16px",
            scale_ratio=1.25
        )

        # Spacing system (8px base)
        self.spacing = Spacing(
            xs="4px",
            sm="8px",
            md="16px",
            lg="24px",
            xl="32px"
        )

        # Component definitions
        self.components = self._define_components()

    def _define_components(self) -> List[Component]:
        """Define UI components"""
        return [
            Component(
                name="Primary Button",
                type="button",
                css_class=".lumenis-btn-primary",
                background=self.colors.primary,
                color="#FFFFFF",
                properties={
                    "padding": f"{self.spacing.sm} {self.spacing.md}",
                    "border-radius": "8px",
                    "font-weight": "600",
                    "border": "none",
                    "cursor": "pointer",
                    "transition": "all 0.2s"
                }
            ),
            Component(
                name="Secondary Button",
                type="button",
                css_class=".lumenis-btn-secondary",
                background="transparent",
                color=self.colors.primary,
                properties={
                    "padding": f"{self.spacing.sm} {self.spacing.md}",
                    "border-radius": "8px",
                    "font-weight": "600",
                    "border": f"2px solid {self.colors.primary}",
                    "cursor": "pointer"
                }
            ),
            Component(
                name="Navigation Bar",
                type="navigation",
                css_class=".lumenis-nav",
                background="#1F2937",
                color="#FFFFFF",
                properties={
                    "padding": f"{self.spacing.md} {self.spacing.lg}",
                    "display": "flex",
                    "align-items": "center",
                    "gap": self.spacing.lg
                }
            ),
            Component(
                name="Info Box",
                type="container",
                css_class=".lumenis-info-box",
                background=self.colors.info,
                color=self.colors.text,
                properties={
                    "padding": self.spacing.md,
                    "border-radius": "8px",
                    "border": f"1px solid {self.colors.accent}"
                }
            ),
            Component(
                name="Warning Banner",
                type="alert",
                css_class=".lumenis-warning",
                background=self.colors.warning,
                color=self.colors.text,
                properties={
                    "padding": self.spacing.md,
                    "border-radius": "8px",
                    "border": "1px solid #FFF925"
                }
            ),
            Component(
                name="Card",
                type="container",
                css_class=".lumenis-card",
                background=self.colors.background,
                color=self.colors.text,
                properties={
                    "padding": self.spacing.lg,
                    "border-radius": "12px",
                    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
                    "border": "1px solid #E5E7EB"
                }
            ),
            Component(
                name="Input Field",
                type="form",
                css_class=".lumenis-input",
                background=self.colors.background,
                color=self.colors.text,
                properties={
                    "padding": self.spacing.sm,
                    "border-radius": "6px",
                    "border": "1px solid #D1D5DB",
                    "font-size": self.typography.base_size
                }
            ),
            Component(
                name="Tooltip",
                type="overlay",
                css_class=".lumenis-tooltip",
                background="#1F2937",
                color="#FFFFFF",
                properties={
                    "padding": f"{self.spacing.xs} {self.spacing.sm}",
                    "border-radius": "4px",
                    "font-size": "14px",
                    "box-shadow": "0 2px 8px rgba(0, 0, 0, 0.15)"
                }
            ),
            Component(
                name="Semantic Search Box",
                type="search",
                css_class=".lumenis-semantic-search",
                background=self.colors.background,
                color=self.colors.text,
                properties={
                    "padding": self.spacing.md,
                    "border-radius": "12px",
                    "border": f"2px solid {self.colors.primary}",
                    "box-shadow": "0 2px 8px rgba(0, 163, 255, 0.1)"
                }
            )
        ]

    def generate_css(self) -> str:
        """Generate CSS from design system"""
        css = []

        # Add CSS reset
        css.append("/* Lumenis Design System - Generated from Semantic Layer */")
        css.append("")

        # Root variables
        css.append(":root {")
        css.append(f"  --color-primary: {self.colors.primary};")
        css.append(f"  --color-secondary: {self.colors.secondary};")
        css.append(f"  --color-accent: {self.colors.accent};")
        css.append(f"  --color-background: {self.colors.background};")
        css.append(f"  --color-text: {self.colors.text};")
        css.append(f"  --color-error: {self.colors.error};")
        css.append(f"  --color-warning: {self.colors.warning};")
        css.append(f"  --color-success: {self.colors.success};")
        css.append(f"  --color-info: {self.colors.info};")
        css.append("")
        css.append(f"  --font-primary: {self.typography.primary_font};")
        css.append(f"  --font-secondary: {self.typography.secondary_font};")
        css.append(f"  --font-mono: {self.typography.monospace_font};")
        css.append("")
        css.append(f"  --spacing-xs: {self.spacing.xs};")
        css.append(f"  --spacing-sm: {self.spacing.sm};")
        css.append(f"  --spacing-md: {self.spacing.md};")
        css.append(f"  --spacing-lg: {self.spacing.lg};")
        css.append(f"  --spacing-xl: {self.spacing.xl};")
        css.append("}")
        css.append("")

        # Base styles
        css.append("body {")
        css.append(f"  font-family: var(--font-primary);")
        css.append(f"  font-size: {self.typography.base_size};")
        css.append(f"  color: var(--color-text);")
        css.append(f"  background: var(--color-background);")
        css.append("  line-height: 1.6;")
        css.append("}")
        css.append("")

        # Component styles
        for component in self.components:
            css.append(f"{component.css_class} {{")
            css.append(f"  background: {component.background};")
            css.append(f"  color: {component.color};")

            for prop, value in component.properties.items():
                css.append(f"  {prop}: {value};")

            css.append("}")
            css.append("")

        return "\n".join(css)

    def export_to_json(self) -> Dict:
        """Export design system to JSON"""
        return {
            "colors": asdict(self.colors),
            "typography": asdict(self.typography),
            "spacing": asdict(self.spacing),
            "components": [asdict(comp) for comp in self.components]
        }

    def generate_documentation(self) -> str:
        """Generate Markdown documentation"""
        doc = []

        doc.append("# Lumenis Design System")
        doc.append("")
        doc.append("Design system for Lumenis AI agent interface, inspired by DynDNS patterns.")
        doc.append("")

        # Colors
        doc.append("## Color Palette")
        doc.append("")
        doc.append("| Name | Value | Usage |")
        doc.append("|------|-------|-------|")
        doc.append(f"| Primary | `{self.colors.primary}` | Primary actions, links |")
        doc.append(f"| Secondary | `{self.colors.secondary}` | Secondary actions |")
        doc.append(f"| Accent | `{self.colors.accent}` | Highlights, accents |")
        doc.append(f"| Background | `{self.colors.background}` | Page background |")
        doc.append(f"| Text | `{self.colors.text}` | Body text |")
        doc.append(f"| Error | `{self.colors.error}` | Error messages |")
        doc.append(f"| Warning | `{self.colors.warning}` | Warning messages |")
        doc.append(f"| Success | `{self.colors.success}` | Success messages |")
        doc.append(f"| Info | `{self.colors.info}` | Info boxes |")
        doc.append("")

        # Typography
        doc.append("## Typography")
        doc.append("")
        doc.append(f"- **Primary Font**: {self.typography.primary_font}")
        doc.append(f"- **Secondary Font**: {self.typography.secondary_font}")
        doc.append(f"- **Monospace**: {self.typography.monospace_font}")
        doc.append(f"- **Base Size**: {self.typography.base_size}")
        doc.append("")

        # Spacing
        doc.append("## Spacing")
        doc.append("")
        doc.append("| Size | Value |")
        doc.append("|------|-------|")
        doc.append(f"| XS | `{self.spacing.xs}` |")
        doc.append(f"| SM | `{self.spacing.sm}` |")
        doc.append(f"| MD | `{self.spacing.md}` |")
        doc.append(f"| LG | `{self.spacing.lg}` |")
        doc.append(f"| XL | `{self.spacing.xl}` |")
        doc.append("")

        # Components
        doc.append("## Components")
        doc.append("")
        for comp in self.components:
            doc.append(f"### {comp.name}")
            doc.append("")
            doc.append(f"**Type**: {comp.type}")
            doc.append("")
            doc.append(f"**CSS Class**: `{comp.css_class}`")
            doc.append("")
            doc.append("**Properties**:")
            doc.append("```css")
            doc.append(f"background: {comp.background};")
            doc.append(f"color: {comp.color};")
            for prop, value in comp.properties.items():
                doc.append(f"{prop}: {value};")
            doc.append("```")
            doc.append("")

        return "\n".join(doc)


if __name__ == "__main__":
    design_system = LumenisDesignSystem()

    # Generate CSS
    print("=" * 80)
    print("LUMENIS DESIGN SYSTEM")
    print("=" * 80)
    print()

    # Save CSS
    css = design_system.generate_css()
    with open("artifacts/lumenis-design-system.css", "w") as f:
        f.write(css)
    print("✓ CSS generated: artifacts/lumenis-design-system.css")

    # Save JSON
    json_data = design_system.export_to_json()
    with open("artifacts/lumenis-design-system.json", "w") as f:
        json.dump(json_data, f, indent=2)
    print("✓ JSON exported: artifacts/lumenis-design-system.json")

    # Save documentation
    docs = design_system.generate_documentation()
    with open("artifacts/LUMENIS_DESIGN_SYSTEM.md", "w") as f:
        f.write(docs)
    print("✓ Documentation: artifacts/LUMENIS_DESIGN_SYSTEM.md")

    print()
    print("Components:")
    for comp in design_system.components:
        print(f"  • {comp.name} ({comp.type})")

    print()
    print("Color Palette:")
    for name, value in asdict(design_system.colors).items():
        print(f"  • {name}: {value}")
