from app import app
from database.models import db

with app.app_context():
    db.create_all()