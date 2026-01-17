# database.py
from pymongo import MongoClient
import os
import urllib.parse
from datetime import datetime

from auth import hash_password
# ===================== MONGODB CONFIG =====================

USERNAME = "pasumaibharatam_db_user"
PASSWORD = urllib.parse.quote_plus("pasumai123")
CLUSTER = "pasumai.mrsonfr.mongodb.net"

MONGO_URL = f"mongodb+srv://{USERNAME}:{PASSWORD}@{CLUSTER}/?retryWrites=true&w=majority"

# ===================== CONNECTION =====================

client = MongoClient(MONGO_URL)
db = client["political_db"]
