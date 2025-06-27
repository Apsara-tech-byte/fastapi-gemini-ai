import os
from datetime import timedelta
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from .ai.gemini import Gemini
from .auth.dependencies import get_user_identifier, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from .auth.throttling import apply_rate_limit
from .auth.models import Token, UserCreate, UserLogin, User
from .auth.user_db import authenticate_user, create_user, get_user


# --- App Initialization ---
app = FastAPI()


# --- AI Configuration ---
def load_system_prompt():
    try:
        with open("src/prompts/system_prompt.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return None


system_prompt = load_system_prompt()
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

ai_platform = Gemini(api_key=gemini_api_key, system_prompt=system_prompt)


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str


# --- API Endpoints ---
@app.post("/register", response_model=User)
async def register(user_data: UserCreate):
    existing_user = get_user(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    user = create_user(
        username=user_data.username,
        password=user_data.password,
        email=user_data.email,
        full_name=user_data.full_name
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create user"
        )
    
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled
    )


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    user = authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
async def read_users_me(user_id: str = Depends(get_user_identifier)):
    if user_id == "global_unauthenticated_user":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user_id: str = Depends(get_user_identifier)):
    apply_rate_limit(user_id)
    response_text = ai_platform.chat(request.prompt)
    return ChatResponse(response=response_text)


@app.get("/")
async def root():
    return {"message": "API is running"}
