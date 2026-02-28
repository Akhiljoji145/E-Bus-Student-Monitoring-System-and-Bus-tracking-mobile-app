#!/bin/bash
# Path to your backend directory
cd /home/akhiljoji/mobile_app/backend

# Activate the virtual environment. Ensure the path matches your actual pythonanywhere virtualenv.
# Usually, pythonanywhere environments are in ~/.virtualenvs/
source ~/.virtualenvs/my-virtualenv/bin/activate 

# Run the django management command
python manage.py notify_unboarded_students
