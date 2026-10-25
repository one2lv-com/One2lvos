# Lumenis Design System

Design system for Lumenis AI agent interface, inspired by DynDNS patterns.

## Color Palette

| Name | Value | Usage |
|------|-------|-------|
| Primary | `#00A3FF` | Primary actions, links |
| Secondary | `#6B7280` | Secondary actions |
| Accent | `#FFE36F` | Highlights, accents |
| Background | `#FFFFFF` | Page background |
| Text | `#1F2937` | Body text |
| Error | `#DC2626` | Error messages |
| Warning | `#FFFDBD` | Warning messages |
| Success | `#10B981` | Success messages |
| Info | `#FFF5D0` | Info boxes |

## Typography

- **Primary Font**: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
- **Secondary Font**: 'JetBrains Mono', 'Courier New', monospace
- **Monospace**: 'JetBrains Mono', 'Courier New', monospace
- **Base Size**: 16px

## Spacing

| Size | Value |
|------|-------|
| XS | `4px` |
| SM | `8px` |
| MD | `16px` |
| LG | `24px` |
| XL | `32px` |

## Components

### Primary Button

**Type**: button

**CSS Class**: `.lumenis-btn-primary`

**Properties**:
```css
background: #00A3FF;
color: #FFFFFF;
padding: 8px 16px;
border-radius: 8px;
font-weight: 600;
border: none;
cursor: pointer;
transition: all 0.2s;
```

### Secondary Button

**Type**: button

**CSS Class**: `.lumenis-btn-secondary`

**Properties**:
```css
background: transparent;
color: #00A3FF;
padding: 8px 16px;
border-radius: 8px;
font-weight: 600;
border: 2px solid #00A3FF;
cursor: pointer;
```

### Navigation Bar

**Type**: navigation

**CSS Class**: `.lumenis-nav`

**Properties**:
```css
background: #1F2937;
color: #FFFFFF;
padding: 16px 24px;
display: flex;
align-items: center;
gap: 24px;
```

### Info Box

**Type**: container

**CSS Class**: `.lumenis-info-box`

**Properties**:
```css
background: #FFF5D0;
color: #1F2937;
padding: 16px;
border-radius: 8px;
border: 1px solid #FFE36F;
```

### Warning Banner

**Type**: alert

**CSS Class**: `.lumenis-warning`

**Properties**:
```css
background: #FFFDBD;
color: #1F2937;
padding: 16px;
border-radius: 8px;
border: 1px solid #FFF925;
```

### Card

**Type**: container

**CSS Class**: `.lumenis-card`

**Properties**:
```css
background: #FFFFFF;
color: #1F2937;
padding: 24px;
border-radius: 12px;
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
border: 1px solid #E5E7EB;
```

### Input Field

**Type**: form

**CSS Class**: `.lumenis-input`

**Properties**:
```css
background: #FFFFFF;
color: #1F2937;
padding: 8px;
border-radius: 6px;
border: 1px solid #D1D5DB;
font-size: 16px;
```

### Tooltip

**Type**: overlay

**CSS Class**: `.lumenis-tooltip`

**Properties**:
```css
background: #1F2937;
color: #FFFFFF;
padding: 4px 8px;
border-radius: 4px;
font-size: 14px;
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
```

### Semantic Search Box

**Type**: search

**CSS Class**: `.lumenis-semantic-search`

**Properties**:
```css
background: #FFFFFF;
color: #1F2937;
padding: 16px;
border-radius: 12px;
border: 2px solid #00A3FF;
box-shadow: 0 2px 8px rgba(0, 163, 255, 0.1);
```
