# platform_for_it_teams
платформа помогает лидерам команд и менеджменту проводить циклы диагностики, фиксировать проблемы, согласовывать изменения и отслеживать движение от текущего состояния к целевому.

## Локальный запуск

База по умолчанию — PostgreSQL, не SQLite.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
sudo pg_ctlcluster 16 main start
sudo -u postgres psql -c "CREATE ROLE platform LOGIN PASSWORD 'platform' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE platform OWNER platform;"
cd platform
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Проверка процесса: `curl -sS -D - http://127.0.0.1:8000/health/ -o /tmp/health-body.txt`

Учётную запись для входа создаёт `manage.py createsuperuser` (поля: логин, имя, пароль).
