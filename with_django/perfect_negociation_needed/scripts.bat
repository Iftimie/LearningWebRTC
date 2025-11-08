@echo off
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

call .venv\Scripts\activate.bat
python manage.py runserver 0.0.0.0:10000