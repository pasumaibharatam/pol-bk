from database import db
from auth import hash_password

def create_default_admins():
    if db.admins.count_documents({}) > 0:
        return

    admins = [
        {"username": "superadmin", "password": hash_password("super123"), "role": "superadmin", "active": True},
        {"username": "admin1", "password": hash_password("admin123"), "role": "admin", "active": True},
        {"username": "admin2", "password": hash_password("admin123"), "role": "admin", "active": True},
        {"username": "admin3", "password": hash_password("admin123"), "role": "admin", "active": True},
        {"username": "admin4", "password": hash_password("admin123"), "role": "admin", "active": True}
    ]

    db.admins.insert_many(admins)
