#!/bin/bash
# Script to run the Django development server

cd "$(dirname "$0")/.."
source venv/bin/activate
cd school_project
python manage.py runserver

