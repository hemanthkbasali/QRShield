# QRShield Status Color Scheme

## Color Specifications

### SAFE Status
- **Text Color**: `#dcfce7` (Light Green)
- **Background**: `rgba(22, 101, 52, 0.52)` (Dark Green, 52% opacity)
- **Border**: `rgba(74, 222, 128, 0.82)` (Green, 82% opacity)
- **Classes**: `.risk-safe`, `.status-option-badge-safe`, `.status-filter-option-safe`
- **Badge Label**: "Safe"

### WARNING Status
- **Text Color**: `#fef3c7` (Light Amber)
- **Background**: `rgba(146, 64, 14, 0.54)` (Dark Amber, 54% opacity)
- **Border**: `rgba(251, 191, 36, 0.84)` (Amber, 84% opacity)
- **Classes**: `.risk-warning`, `.status-option-badge-warning`, `.status-filter-option-warning`
- **Badge Label**: "Warning"

### MALICIOUS Status
- **Text Color**: `#fecdd3` (Light Red)
- **Background**: `rgba(127, 29, 29, 0.56)` (Dark Red, 56% opacity)
- **Border**: `rgba(251, 113, 133, 0.86)` (Red, 86% opacity)
- **Classes**: `.risk-malicious`, `.status-option-badge-malicious`, `.status-filter-option-malicious`
- **Badge Label**: "Malicious"

### INVALID Status
- **Text Color**: `#f3f4f6` (Light Gray)
- **Background**: `rgba(75, 85, 99, 0.60)` (Dark Gray, 60% opacity)
- **Border**: `rgba(209, 213, 219, 0.60)` (Gray, 60% opacity)
- **Classes**: `.risk-invalid`, `.status-option-badge-invalid`, `.status-filter-option-invalid`
- **Badge Label**: "Invalid"

## Dropdown Menu Styling

### Container (.custom-select)
- Position: relative
- Z-index when closed: 4
- Z-index when open: 9999
- Width: 100%

### Menu (.custom-select-menu)
- Position: absolute
- Z-index: 9999
- Max-height: 20rem
- Overflow-y: auto
- Glassmorphic background with backdrop blur (20px)
- Border: 1px solid rgba(139, 92, 246, 0.48)

### Options (.custom-select-option)
- Min-height: 2.15rem
- Gap between options: 0.35rem
- Hover background: rgba(139, 92, 246, 0.28)
- Selected background: linear-gradient(90deg, rgba(139, 92, 246, 0.62), rgba(233, 64, 130, 0.28))

## Dropdown Overflow Fix

- `.table-panel { overflow: visible; }` - Allows dropdown to escape parent container
- `.history-filters { z-index: 1; }` - Prevents z-index interference
- All dropdown options should be visible when menu is open

## Rendered Dropdown Options

1. **All** (Filter by Status) - Neutral styling
   - Color: #f0f4f8
   - Background: rgba(255, 255, 255, 0.09)
   - Border: rgba(213, 186, 255, 0.36)

2. **Safe** - Green styling
   - Color: #dcfce7
   - Background: rgba(22, 101, 52, 0.52)
   - Border: rgba(74, 222, 128, 0.82)

3. **Warning** - Amber styling
   - Color: #fef3c7
   - Background: rgba(146, 64, 14, 0.54)
   - Border: rgba(251, 191, 36, 0.84)

4. **Malicious** - Red styling
   - Color: #fecdd3
   - Background: rgba(127, 29, 29, 0.56)
   - Border: rgba(251, 113, 133, 0.86)

5. **Invalid** - Gray styling
   - Color: #f3f4f6
   - Background: rgba(75, 85, 99, 0.60)
   - Border: rgba(209, 213, 219, 0.60)

## Pages Using Status Badges

- **Scanner**: result.html - Shows risk_badge component
- **Dashboard**: dashboard.html - Recent scans widget uses risk_badge component
- **Scan History**: history.html - Table displays risk_badge component
- **Security Analytics**: threat_intel.html - Recent threats displays status_label text
- **Reports**: reports.html - Table displays risk_badge component
