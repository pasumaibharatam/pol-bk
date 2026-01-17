# auth.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
MAX_BCRYPT_LENGTH = 72  # bcrypt limit

def hash_password(password: str) -> str:
    # truncate to 72 bytes
    password_bytes = password.encode("utf-8")[:MAX_BCRYPT_LENGTH]
    return pwd_context.hash(password_bytes)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode("utf-8")[:MAX_BCRYPT_LENGTH]
    return pwd_context.verify(plain_bytes, hashed_password)
