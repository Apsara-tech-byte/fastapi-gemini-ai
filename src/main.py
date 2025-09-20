import os
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from .ai.gemini import Gemini
from .auth.dependencies import get_user_identifier
from .auth.throttling import apply_rate_limit

#all endpoints and logic here
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
    prompt: str #expect a JSON body like {'prompt':'...'}


class ChatResponse(BaseModel):
    response: str #return a JSON body like {'response':'...'}


# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse) #checks response resembles chat response structure
async def chat(request: ChatRequest, user_id: str = Depends(get_user_identifier)):
    apply_rate_limit(user_id)
    response_text = ai_platform.chat(request.prompt)
    return ChatResponse(response=response_text)


@app.get("/")
async def root():
    return {"message": "API is running"}
