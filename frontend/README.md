# QRShield Frontend Scaffold

The app uses Django templates with Tailwind utility classes and `backend/static/scanner/css/styles.css` for the mockup-specific glass, glow, and dashboard styling.

For a production Tailwind build instead of the CDN:

```bash
cd frontend
npm install
npm run build:css
```

Then include `scanner/css/tailwind.css` in `backend/templates/base.html` and remove the Tailwind CDN script.
