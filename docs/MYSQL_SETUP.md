# MySQL Setup

Create the database:

```sql
CREATE DATABASE qrshield CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'qrshield_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON qrshield.* TO 'qrshield_user'@'localhost';
FLUSH PRIVILEGES;
```

Configure `.env`:

```env
QRSHIELD_DB_ENGINE=mysql
QRSHIELD_DB_NAME=qrshield
QRSHIELD_DB_USER=qrshield_user
QRSHIELD_DB_PASSWORD=strong_password
QRSHIELD_DB_HOST=127.0.0.1
QRSHIELD_DB_PORT=3306
```

Run migrations from `backend/`:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

For classroom demos without a MySQL service, set `QRSHIELD_DB_ENGINE=sqlite`. The application code remains MySQL-ready.
