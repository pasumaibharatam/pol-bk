import bcrypt

# Hash a password
def hash_password(password: str) -> str:
    # bcrypt requires bytes, so encode
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')  # store as string in DB

# Verify a password
def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
