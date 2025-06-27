import pytest
from fastapi.testclient import TestClient
from datetime import timedelta
import os
from unittest.mock import patch

os.environ["GEMINI_API_KEY"] = "fake-key-for-testing"

from src.main import app
from src.auth.dependencies import create_access_token, verify_token, get_password_hash, verify_password
from src.auth.user_db import authenticate_user, create_user, get_user


@pytest.fixture
def mock_ai_platform():
    with patch('src.main.ai_platform') as mock:
        mock.chat.return_value = "Mocked AI response"
        yield mock


client = TestClient(app)

@pytest.fixture
def client_with_mock_ai(mock_ai_platform):
    return TestClient(app)


class TestPasswordHashing:
    def test_password_hashing(self):
        password = "secret123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False


class TestJWTTokens:
    def test_create_and_verify_token(self):
        data = {"sub": "testuser"}
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)
        
        username = verify_token(token)
        assert username == "testuser"
    
    def test_create_token_with_expiration(self):
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        assert token is not None
        
        username = verify_token(token)
        assert username == "testuser"
    
    def test_verify_invalid_token(self):
        invalid_token = "invalid.token.here"
        username = verify_token(invalid_token)
        assert username is None


class TestUserDatabase:
    def test_get_existing_user(self):
        user = get_user("testuser")
        assert user is not None
        assert user.username == "testuser"
        assert user.full_name == "John Doe"
    
    def test_get_nonexistent_user(self):
        user = get_user("nonexistent")
        assert user is None
    
    def test_authenticate_user_success(self):
        user = authenticate_user("testuser", "secret")
        assert user is not None
        assert user.username == "testuser"
    
    def test_authenticate_user_wrong_password(self):
        user = authenticate_user("testuser", "wrong")
        assert user is None
    
    def test_authenticate_nonexistent_user(self):
        user = authenticate_user("nonexistent", "password")
        assert user is None


class TestAuthEndpoints:
    def test_register_new_user(self):
        user_data = {
            "username": "apiuser",
            "password": "apipassword",
            "email": "api@example.com",
            "full_name": "API User"
        }
        response = client.post("/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "apiuser"
        assert data["email"] == "api@example.com"
        assert data["full_name"] == "API User"
        assert data["disabled"] is False
    
    def test_register_duplicate_user(self):
        user_data = {
            "username": "testuser",
            "password": "password"
        }
        response = client.post("/register", json=user_data)
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]
    
    def test_login_success(self):
        user_data = {
            "username": "testuser",
            "password": "secret"
        }
        response = client.post("/login", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self):
        user_data = {
            "username": "testuser",
            "password": "wrong"
        }
        response = client.post("/login", json=user_data)
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_token_endpoint_success(self):
        form_data = {
            "username": "testuser",
            "password": "secret"
        }
        response = client.post("/token", data=form_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_get_current_user_authenticated(self):
        token = create_access_token({"sub": "testuser"})
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["full_name"] == "John Doe"
    
    def test_get_current_user_unauthenticated(self):
        response = client.get("/users/me")
        assert response.status_code == 401


class TestChatEndpointAuth:
    def test_chat_authenticated(self, client_with_mock_ai):
        token = create_access_token({"sub": "testuser"})
        headers = {"Authorization": f"Bearer {token}"}
        chat_data = {"prompt": "Hello, world!"}
        response = client_with_mock_ai.post("/chat", json=chat_data, headers=headers)
        assert response.status_code in [200, 429]
        if response.status_code == 200:
            assert response.json()["response"] == "Mocked AI response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])