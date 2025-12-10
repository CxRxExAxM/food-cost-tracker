# Food Cost Tracker - Design System

**Last Updated:** November 29, 2024  
**Design Philosophy:** Professional cyberpunk-influenced dark UI with sharp geometric lines, clear visual hierarchy, and terminal aesthetics

## Design Principles

1. **Visual Hierarchy First** - Clear importance through size, color, and spacing
2. **Data Density with Breathing Room** - Fit information efficiently without cramping
3. **Sharp & Geometric** - Clean angles, minimal rounding, grid-based layout
4. **Professional Dark** - Not pure black, comfortable for extended use
5. **Semantic Color** - Red (costs/danger), Yellow (warnings/edits), Green (success/profit)

## Color System

### Base Palette (Dark Mode)

```css
:root {
  /* Background Layers */
  --bg-primary: #1a1a1a;        /* Main background (VS Code Dark Modern) */
  --bg-secondary: #242424;      /* Cards, elevated surfaces */
  --bg-tertiary: #2d2d2d;       /* Hover states, subtle elevation */
  --bg-elevated: #323232;       /* Modals, dropdowns, highest elevation */
  
  /* Borders & Dividers */
  --border-subtle: #2d2d2d;     /* Very subtle dividers */
  --border-default: #3d3d3d;    /* Default borders */
  --border-strong: #4d4d4d;     /* Focused/active borders */
  
  /* Text Hierarchy */
  --text-primary: #e6e6e6;      /* Main content */
  --text-secondary: #a3a3a3;    /* Supporting text */
  --text-tertiary: #6b6b6b;     /* Disabled, placeholders */
  --text-inverse: #1a1a1a;      /* Text on colored backgrounds */
  
  /* Semantic Colors - Muted Professional */
  --color-red: #d13438;         /* Costs, errors, alerts */
  --color-red-dim: #8a2226;     /* Subtle red backgrounds */
  --color-red-bright: #ff4d4f;  /* Bright accents */
  
  --color-yellow: #d4a72c;      /* Warnings, edits, pending */
  --color-yellow-dim: #8a6e1c;  /* Subtle yellow backgrounds */
  --color-yellow-bright: #fadb14; /* Bright accents */
  
  --color-green: #2d8653;       /* Success, profit, active */
  --color-green-dim: #1d5737;   /* Subtle green backgrounds */
  --color-green-bright: #52c41a; /* Bright accents */
  
  /* Neutral Accents */
  --color-blue: #3b82f6;        /* Links, info (limited use) */
  --color-purple: #8b5cf6;      /* Special states (limited use) */
  
  /* Functional Colors */
  --color-focus: #d4a72c;       /* Focus rings */
  --color-selection: rgba(212, 167, 44, 0.2); /* Text selection */
}
```

### Color Usage Guidelines

**Red - Financial Costs & Alerts**
- Cost values, expenses
- Error states
- Delete actions
- Alert badges
- High food cost percentages

**Yellow - Warnings & Edits**
- Warning states
- Edit mode indicators
- Pending actions
- Moderate food cost percentages
- In-progress states

**Green - Success & Profit**
- Success messages
- Profit indicators
- Completed states
- Low food cost percentages
- Active/enabled states

**When to Use Bright vs. Dim:**
- **Bright:** Primary actions, important alerts, data highlights
- **Base:** Standard semantic use (badges, icons, borders)
- **Dim:** Subtle backgrounds, hover states, low-priority indicators

## Typography

### Font Stack

```css
:root {
  /* Primary Font - Geometric Sans */
  --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  
  /* Alternative: Use Space Grotesk for more geometric feel */
  /* --font-primary: 'Space Grotesk', sans-serif; */
  
  /* Monospace - Data & Numbers */
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  
  /* Font Weights */
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}

/* Import Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Alternative Geometric Option */
/* @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap'); */
```

### Typography Scale

```css
:root {
  /* Font Sizes - Modular Scale (1.25 ratio) */
  --text-xs: 0.75rem;     /* 12px - Captions, labels */
  --text-sm: 0.875rem;    /* 14px - Small text, table data */
  --text-base: 1rem;      /* 16px - Body text */
  --text-lg: 1.125rem;    /* 18px - Emphasized text */
  --text-xl: 1.25rem;     /* 20px - Small headings */
  --text-2xl: 1.5rem;     /* 24px - Card titles */
  --text-3xl: 1.875rem;   /* 30px - Section headers */
  --text-4xl: 2.25rem;    /* 36px - Page titles */
  
  /* Line Heights */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;
  
  /* Letter Spacing */
  --tracking-tight: -0.02em;
  --tracking-normal: 0;
  --tracking-wide: 0.02em;
}
```

### Typography Classes

```css
/* Headings */
.heading-1 {
  font-family: var(--font-primary);
  font-size: var(--text-4xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
  color: var(--text-primary);
}

.heading-2 {
  font-family: var(--font-primary);
  font-size: var(--text-3xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
  color: var(--text-primary);
}

.heading-3 {
  font-family: var(--font-primary);
  font-size: var(--text-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--leading-tight);
  color: var(--text-primary);
}

/* Body Text */
.body-primary {
  font-family: var(--font-primary);
  font-size: var(--text-base);
  font-weight: var(--font-weight-regular);
  line-height: var(--leading-normal);
  color: var(--text-primary);
}

.body-secondary {
  font-family: var(--font-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-weight-regular);
  line-height: var(--leading-normal);
  color: var(--text-secondary);
}

/* Monospace - For Data */
.text-mono {
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
  letter-spacing: var(--tracking-normal);
}

/* Data/Numbers - Always monospace */
.data-value,
.price,
.quantity,
.percentage {
  font-family: var(--font-mono);
  font-weight: var(--font-weight-semibold);
  font-variant-numeric: tabular-nums; /* Align numbers in tables */
}

/* Labels */
.label {
  font-family: var(--font-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--text-tertiary);
}
```

## Spacing System

```css
:root {
  /* Spacing Scale - Based on 4px grid */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
  --space-20: 5rem;     /* 80px */
  
  /* Component Spacing */
  --spacing-component-xs: var(--space-2);
  --spacing-component-sm: var(--space-3);
  --spacing-component-md: var(--space-4);
  --spacing-component-lg: var(--space-6);
  --spacing-component-xl: var(--space-8);
}
```

## Border Radius (Minimal)

```css
:root {
  /* Sharp, minimal rounding */
  --radius-none: 0;
  --radius-sm: 2px;      /* Subtle softening */
  --radius-md: 4px;      /* Default for most elements */
  --radius-lg: 6px;      /* Cards, modals */
  --radius-full: 9999px; /* Pills, badges (use sparingly) */
}
```

## Shadows & Elevation

```css
:root {
  /* Subtle shadows for dark mode */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 
               0 2px 4px -1px rgba(0, 0, 0, 0.2);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 
               0 4px 6px -2px rgba(0, 0, 0, 0.2);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 
               0 10px 10px -5px rgba(0, 0, 0, 0.2);
  
  /* Colored shadows for accents */
  --shadow-red: 0 0 0 3px rgba(209, 52, 56, 0.1);
  --shadow-yellow: 0 0 0 3px rgba(212, 167, 44, 0.1);
  --shadow-green: 0 0 0 3px rgba(45, 134, 83, 0.1);
}
```

## Component Styles

### Buttons

```css
/* Base Button */
.btn {
  font-family: var(--font-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-weight-medium);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

/* Primary Button */
.btn-primary {
  background: var(--color-green);
  color: var(--text-inverse);
  border-color: var(--color-green);
}

.btn-primary:hover {
  background: var(--color-green-bright);
  border-color: var(--color-green-bright);
}

/* Secondary Button */
.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border-color: var(--border-default);
}

.btn-secondary:hover {
  background: var(--bg-elevated);
  border-color: var(--border-strong);
}

/* Danger Button */
.btn-danger {
  background: var(--color-red-dim);
  color: var(--text-primary);
  border-color: var(--color-red);
}

.btn-danger:hover {
  background: var(--color-red);
  color: var(--text-inverse);
}

/* Ghost Button */
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: transparent;
}

.btn-ghost:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

/* Icon Button */
.btn-icon {
  padding: var(--space-2);
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

### Inputs

```css
/* Base Input */
.input {
  font-family: var(--font-primary);
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  outline: none;
  transition: all 0.15s ease;
}

.input:hover {
  border-color: var(--border-strong);
}

.input:focus {
  border-color: var(--color-focus);
  box-shadow: var(--shadow-yellow);
}

.input::placeholder {
  color: var(--text-tertiary);
}

/* Input for numbers/data */
.input-data {
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
}

/* Input with error */
.input-error {
  border-color: var(--color-red);
}

.input-error:focus {
  border-color: var(--color-red);
  box-shadow: var(--shadow-red);
}
```

### Cards

```css
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  transition: all 0.2s ease;
}

.card:hover {
  border-color: var(--border-default);
}

/* Card with sharp emphasis */
.card-sharp {
  border-left: 2px solid var(--border-strong);
}

.card-sharp.accent-red {
  border-left-color: var(--color-red);
}

.card-sharp.accent-yellow {
  border-left-color: var(--color-yellow);
}

.card-sharp.accent-green {
  border-left-color: var(--color-green);
}

/* Interactive card */
.card-interactive {
  cursor: pointer;
}

.card-interactive:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
```

### Tables

```css
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.table thead {
  border-bottom: 1px solid var(--border-default);
}

.table th {
  font-family: var(--font-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--text-tertiary);
  text-align: left;
  padding: var(--space-3) var(--space-4);
}

.table td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
}

.table tbody tr:hover {
  background: var(--bg-tertiary);
}

/* Monospace for data cells */
.table td.data-cell {
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
  font-variant-numeric: tabular-nums;
}

/* Striped rows (alternative) */
.table-striped tbody tr:nth-child(even) {
  background: var(--bg-tertiary);
}
```

### Badges

```css
.badge {
  font-family: var(--font-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-weight-semibold);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.badge-red {
  background: var(--color-red-dim);
  color: var(--color-red-bright);
}

.badge-yellow {
  background: var(--color-yellow-dim);
  color: var(--color-yellow-bright);
}

.badge-green {
  background: var(--color-green-dim);
  color: var(--color-green-bright);
}

.badge-neutral {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}
```

### Dividers

```css
.divider {
  height: 1px;
  background: var(--border-subtle);
  border: none;
}

.divider-strong {
  background: var(--border-default);
}

/* Vertical divider */
.divider-vertical {
  width: 1px;
  height: auto;
  background: var(--border-subtle);
}
```

## Layout Patterns

### Container

```css
.container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}

.container-narrow {
  max-width: 1024px;
}

.container-wide {
  max-width: 1920px;
}
```

### Grid System

```css
.grid {
  display: grid;
  gap: var(--space-6);
}

.grid-2 {
  grid-template-columns: repeat(2, 1fr);
}

.grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.grid-4 {
  grid-template-columns: repeat(4, 1fr);
}

/* Responsive grid */
.grid-auto {
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}
```

### Flex Utilities

```css
.flex {
  display: flex;
}

.flex-col {
  flex-direction: column;
}

.items-center {
  align-items: center;
}

.justify-between {
  justify-content: space-between;
}

.gap-2 {
  gap: var(--space-2);
}

.gap-4 {
  gap: var(--space-4);
}

.gap-6 {
  gap: var(--space-6);
}
```

## Icons

**Recommended Icon Library:** Lucide React (geometric, clean, matches aesthetic)

```bash
npm install lucide-react
```

**Icon Sizing:**
```css
.icon-xs {
  width: 12px;
  height: 12px;
}

.icon-sm {
  width: 16px;
  height: 16px;
}

.icon-md {
  width: 20px;
  height: 20px;
}

.icon-lg {
  width: 24px;
  height: 24px;
}
```

**Usage in React:**
```jsx
import { DollarSign, AlertTriangle, CheckCircle } from 'lucide-react';

// Colored icons based on context
<DollarSign className="icon-md" style={{ color: 'var(--color-red)' }} />
<AlertTriangle className="icon-md" style={{ color: 'var(--color-yellow)' }} />
<CheckCircle className="icon-md" style={{ color: 'var(--color-green)' }} />
```

## Animation & Transitions

```css
:root {
  /* Transition Speeds */
  --transition-fast: 0.1s;
  --transition-base: 0.15s;
  --transition-slow: 0.2s;
  --transition-slower: 0.3s;
  
  /* Easing */
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
}

/* Hover transitions */
.transition-base {
  transition: all var(--transition-base) var(--ease-in-out);
}

/* Loading skeleton */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.skeleton {
  background: var(--bg-tertiary);
  animation: pulse 2s var(--ease-in-out) infinite;
  border-radius: var(--radius-md);
}
```

## Focus States (Accessibility)

```css
/* Keyboard focus ring */
*:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

/* Remove default outline */
*:focus {
  outline: none;
}

/* Skip to content link */
.skip-to-content {
  position: absolute;
  top: -100%;
  left: 0;
  background: var(--bg-elevated);
  color: var(--text-primary);
  padding: var(--space-3) var(--space-4);
  z-index: 9999;
}

.skip-to-content:focus {
  top: 0;
}
```

## Semantic Color Application Examples

### Recipe Cost Display
```jsx
// High cost (>40%) = Red
// Medium cost (30-40%) = Yellow  
// Low cost (<30%) = Green

const getCostColor = (percentage) => {
  if (percentage > 40) return 'var(--color-red)';
  if (percentage > 30) return 'var(--color-yellow)';
  return 'var(--color-green)';
};

<span style={{ color: getCostColor(costPercent) }}>
  {costPercent}%
</span>
```

### Status Indicators
```jsx
// Success/Active = Green
<div className="badge badge-green">Active</div>

// Warning/Pending = Yellow
<div className="badge badge-yellow">Pending Review</div>

// Error/High Cost = Red
<div className="badge badge-red">Over Budget</div>
```

## Implementation Notes

### Global Styles Setup
```css
/* globals.css */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-primary);
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: var(--leading-normal);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

::selection {
  background: var(--color-selection);
  color: var(--text-primary);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: var(--radius-md);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--border-strong);
}
```

### Tailwind Alternative
If using Tailwind CSS, configure theme to match:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#1a1a1a',
        secondary: '#242424',
        // ... map all CSS variables
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'sm': '2px',
        'md': '4px',
        'lg': '6px',
      }
    }
  }
}
```

## Quick Reference: Linear.com Style Patterns

**What makes Linear feel "Linear":**
1. **Subtle borders** - Most borders are very low contrast
2. **Smart hover states** - Elements lift/highlight on interaction
3. **Consistent spacing** - Everything on a grid
4. **Monospace for data** - All numbers use monospace
5. **Minimal color** - Mostly grayscale, color for meaning only
6. **Sharp corners** - 4-6px max radius
7. **Fast interactions** - 150ms transitions everywhere
8. **Dense but breathable** - Information-rich without cramping

**What to avoid:**
- Heavy drop shadows
- Bright gradients
- Excessive rounding (>8px)
- Emoji-style icons (use Lucide instead)
- Saturated colors for decoration
- Long transitions (>300ms)

## Migration Strategy

**Phase 1: Setup**
1. Add CSS variables to root stylesheet
2. Import Google Fonts (Inter + JetBrains Mono)
3. Update global body styles

**Phase 2: Components**
1. Update buttons first (most visible)
2. Migrate cards and tables
3. Update forms and inputs
4. Replace icons with Lucide

**Phase 3: Polish**
1. Add transitions
2. Refine spacing
3. Test accessibility (focus states, contrast)
4. Mobile responsive adjustments

**Phase 4: Details**
1. Custom scrollbars
2. Loading states
3. Empty states
4. Error states

---

## Next Steps with Claude Code

1. Copy this file to `/docs/DESIGN_SYSTEM.md`
2. Reference when building components
3. Use CSS variables consistently
4. Test dark mode contrast ratios (aim for WCAG AA minimum)

**Questions for implementation:**
- Prefer vanilla CSS, CSS Modules, or Tailwind?
- Any specific components to redesign first?
- Need help converting existing components?
