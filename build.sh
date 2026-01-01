#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Cria o superusuário automaticamente se ele não existir
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'fgerke@gmail.com', 'Lulu,1502')
    print("Superuser created successfully!")
else:
    print("Superuser already exists.")
EOF