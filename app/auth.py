import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

load_dotenv()
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def _secret_key():
    key = os.getenv("SECRET_KEY")
    if not key or len(key) < 32:
        raise RuntimeError("SECRET_KEY must be set to a random value of at least 32 characters")
    return key

def make_token(username: str):
    payload = {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)

def require_admin(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not os.getenv("ADMIN_USERNAME") or username != os.getenv("ADMIN_USERNAME"):
            raise ValueError("invalid admin")
        return username
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin login talab qilinadi")
