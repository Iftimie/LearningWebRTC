init() {
    sudo apt-get install python3.8-venv
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r requirements.txt

    python manage.py makemigrations
    python manage.py migrate
    python manage.py createsuperuser
}

run() {
    source .venv/bin/activate
    python manage.py runserver 0.0.0.0:10000
}