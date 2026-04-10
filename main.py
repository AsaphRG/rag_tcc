import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from admin_agent.agent import root_agent
import uvicorn
import os

app = FastAPI(title="Prowise RAG API")

# Habilita o CORS para permitir que seu site faça requisições
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Troque "*" pelo domínio do seu site para maior segurança
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default-session"

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Chama o agente ADK
        # O ADK Agent geralmente tem um método `invoke` ou similar dependendo da versão.
        # Na versão 1.28.0 do google-adk, costuma ser `agent.run(input=...)`
        response = root_agent.run(input=request.message)
        return ChatResponse(response=str(response.output))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
