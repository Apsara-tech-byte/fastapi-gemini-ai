from typing import Dict, Optional
from .models import UserInDB
from .dependencies import get_password_hash, verify_password

fake_users_db: Dict[str, UserInDB] = {
    "testuser": UserInDB(
        username="testuser",
        full_name="John Doe",
        email="john@example.com",
        hashed_password=get_password_hash("secret"),
        disabled=False,
    ),
    "alice": UserInDB(
        username="alice",
        full_name="Alice Smith",
        email="alice@example.com",
        hashed_password=get_password_hash("wonderland"),
        disabled=False,
    ),
}


def get_user(username: str) -> Optional[UserInDB]:
    if username in fake_users_db:
        return fake_users_db[username]
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(username: str, password: str, email: Optional[str] = None, full_name: Optional[str] = None) -> Optional[UserInDB]:
    if username in fake_users_db:
        return None
    
    hashed_password = get_password_hash(password)
    user = UserInDB(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        disabled=False,
    )
    fake_users_db[username] = user
    return user