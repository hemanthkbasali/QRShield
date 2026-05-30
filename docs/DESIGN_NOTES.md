# QRShield Design Notes

The uploaded mockups are treated as the visual source of truth. The implementation keeps:

- Matte black application background with dark gray cards.
- Purple neon borders, focus rings, and sidebar active states.
- Crimson and pink threat accents for malicious risk states.
- Compact SaaS dashboard layout with left sidebar, glass panels, dense tables, and report preview.
- Animated scanner details: upload glow, QR preview beam, progress/risk meter, and canvas charts.

Primary style files:

- `backend/templates/**/*.html`
- `backend/static/scanner/css/styles.css`
- `backend/static/scanner/js/app.js`
