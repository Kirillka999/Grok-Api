import os
from fastapi      import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse, ParseResult
from pydantic     import BaseModel
from core         import Grok
from uvicorn      import run


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    expected_api_key = os.getenv("PROXY_API_KEY")
    if expected_api_key and credentials.credentials != expected_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

class ConversationRequest(BaseModel):
    proxy: str | None = None
    message: str
    model: str = "grok-3-auto"
    extra_data: dict | None = None

def format_proxy(proxy: str) -> str:
    
    if not proxy.startswith(("http://", "https://")):
        proxy: str = "http://" + proxy
    
    try:
        parsed: ParseResult = urlparse(proxy)

        if parsed.scheme not in ("http", ""):
            raise ValueError("Not http scheme")

        if not parsed.hostname or not parsed.port:
            raise ValueError("No url and port")

        if parsed.username and parsed.password:
            return f"http://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
        
        else:
            return f"http://{parsed.hostname}:{parsed.port}"
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid proxy format: {str(e)}")

@app.post("/ask")
async def create_conversation(request: ConversationRequest, api_key: str = Depends(verify_api_key)):
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    proxy = format_proxy(request.proxy) if request.proxy else None
    
    try:
        answer: dict = Grok(request.model, proxy).start_convo(request.message, request.extra_data)

        return {
            "status": "success",
            **answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    run("api_server:app", host="0.0.0.0", port=6969)