from datetime import datetime
from database import db
from auth import hash_password

admins_collection = db["admins"]

DEFAULT_ADMINS = [
    {"username": "adminX", "password": "admin123", "role": "superadmin"},
    {"username": "admin2", "password": "admin123", "role": "admin"},
    {"username": "admin3", "password": "admin123", "role": "admin"},
    {"username": "admin4", "password": "admin123", "role": "admin"},
    {"username": "admin5", "password": "admin123", "role": "admin"},
]

def create_default_admins():
    for admin in DEFAULT_ADMINS:
        if not admins_collection.find_one({"username": admin["username"]}):
            admins_collection.insert_one({
                "username": admin["username"],
                "password": hash_password(admin["password"]),
                "role": admin["role"],
                "active": True,
                "created_at": datetime.utcnow()
            })
