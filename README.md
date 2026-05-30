# QRShield - QR Phishing Detection & Security Report Generator

QRShield is a full-stack Django Information & Network Security mini project for QR upload, QR decoding, URL phishing analysis, risk scoring, scan history, database-driven analytics, and downloadable PDF security reports.

## Stack

- Frontend: HTML, Tailwind CSS, JavaScript
- Backend: Django
- Database: MySQL via PyMySQL or SQLite for local demos
- QR and reports: OpenCV, pyzbar, Pillow, reportlab

## Features

- Login, registration, sessions, and profile/password settings
- Drag-and-drop QR image upload with preview
- QR decoding through pyzbar with OpenCV fallback
- Phishing heuristics for HTTPS, IP URLs, shorteners, suspicious keywords, random domains, special characters, fake login/payment lures, and redirect parameters
- Safe, Warning, and Malicious risk classification with score and explanation cards
- Scan history with search, filtering, pagination, timestamps, and report actions
- PDF reports containing QR image, extracted payload, risk score, threats, recommendations, and timestamp
- Dashboard and Security Analytics pages generated only from real scan records

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## MySQL

The default configuration expects MySQL. Update `.env` with your database credentials:

```env
QRSHIELD_DB_ENGINE=mysql
QRSHIELD_DB_NAME=qrshield
QRSHIELD_DB_USER=root
QRSHIELD_DB_PASSWORD=
QRSHIELD_DB_HOST=127.0.0.1
QRSHIELD_DB_PORT=3306
```

See `docs/MYSQL_SETUP.md` for a dedicated database user example.

For local demos without MySQL, set:

```env
QRSHIELD_DB_ENGINE=sqlite
```

## Notes

`pyzbar` may require the native ZBar shared library on your machine. QRShield also uses OpenCV's `QRCodeDetector` as a fallback so most demos keep working even when ZBar is missing.
