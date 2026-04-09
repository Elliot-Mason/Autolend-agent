from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import json
import uvicorn
import os
import re

from graph import app

# --- Request/Response Models ---
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

class HealthResponse(BaseModel):
    status: str
    model: str

# --- Sessions Storage (in-memory; use Redis/DB for production) ---
sessions = {}

# --- GUARDRAIL KEYWORDS ---
JAILBREAK_KEYWORDS = [
    'ignore', 'forget', 'disregard', 'override', 'bypass',
    'system prompt', 'instructions', 'rules', 'guidelines',
    'pretend', 'role play', 'act as', 'be a different',
    'change your role', 'forget auto', 'no longer'
]

# --- VALIDATION FUNCTIONS ---
def is_jailbreak_attempt(text: str) -> bool:
    """Detect jailbreak/instruction-breaking attempts."""
    text_lower = text.lower()
    for keyword in JAILBREAK_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

def is_disclosure_attempt(text: str) -> bool:
    """Detect EXPLICIT requests for confidential information only."""
    text_lower = text.lower()
    
    # VERY narrow scope - only block specific confidential data requests
    disclosure_patterns = [
        r'rate\s+table',           # "What are the rate tables?"
        r'internal\s+rate',         # "What are internal rates?"
        r'scoring\s+logic',         # "Show me scoring logic"
        r'score\s+to\s+rate',       # "Score to rate mapping?"
        r'how\s+is\s+rate\s+calculated',  # "How is the rate calculated?"
        r'approval\s+criteria',     # "What are approval criteria?"
    ]
    
    return any(re.search(pattern, text_lower) for pattern in disclosure_patterns)

def contains_disclosure_content(response: str) -> bool:
    """Detect if response contains confidential information - STRICT matching only."""
    response_lower = response.lower()
    
    # ONLY block if explicitly disclosing confidential information
    # Be VERY specific to avoid false positives
    
    # 1. Tier information (Tier 1, Tier 2, etc. with numbers)
    if re.search(r'tier\s+[1-5]', response_lower):
        return True
    
    # 2. Rate percentages combined with tier/adjustment language
    if re.search(r'\d+\.\d+%', response_lower):
        if any(x in response_lower for x in ['tier', 'adjustment', 'base rate', 'percentage increase']):
            return True
    
    # 3. Minimum income/down payment requirements disclosed
    if re.search(r'minimum\s+(annual\s+)?income\s+of\s+\$[\d,]+', response_lower):
        return True
    if re.search(r'minimum\s+down\s+payment\s+of\s+\$[\d,]+', response_lower):
        return True
    
    # 4. Technical parameter documentation (backticks with multiple parameters)
    if '`vehicle_type`' in response and ('`annual_income`' in response or '`loan_term`' in response):
        return True
    
    # 5. Approval conditions with specific requirements
    if 'approved for' in response_lower and re.search(r'(\d+\s+month|year)s?', response_lower):
        if 'down payment' in response_lower or 'income' in response_lower:
            return True
    
    return False

# --- Safe Response Messages ---
SAFE_RESPONSES = {
    'jailbreak': "I'm AutoLend Assistant and I only help with auto loan pre-qualification. How can I help you today?",
    'disclosure': "I can't share internal rate information or scoring methodology. What I can do is provide a pre-qualification estimate if you'd like to explore an auto loan.",
    'out_of_scope': "I'm only able to help with auto loan inquiries. For that, please contact Westpac at westpac.com.au or 132 032."
}

# --- FastAPI App ---
api = FastAPI(
    title="AutoLend Agent API",
    description="Remote API for AutoLend loan advisory agent",
    version="1.0.0"
)

# --- CORS Middleware ---
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static Files ---
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

@api.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    try:
        html_path = os.path.join(static_dir, "index.html")
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Chat Interface</h1><p>To use the web UI, ensure static/index.html exists.</p><p>Use /docs for interactive API documentation.</p>"

if os.path.exists(static_dir):
    from fastapi.staticfiles import StaticFiles
    api.mount("/static", StaticFiles(directory=static_dir), name="static")

@api.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    from config import MODEL
    return {
        "status": "healthy",
        "model": MODEL
    }

@api.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the agent and get response."""
    try:
        # VALIDATION: Check for jailbreak/disclosure attempts in user input
        if is_jailbreak_attempt(request.message):
            return ChatResponse(
                response=SAFE_RESPONSES['jailbreak'],
                session_id=request.session_id
            )
        
        if is_disclosure_attempt(request.message):
            return ChatResponse(
                response=SAFE_RESPONSES['disclosure'],
                session_id=request.session_id
            )
        
        # Get or create session history
        if request.session_id not in sessions:
            sessions[request.session_id] = []
        
        history = sessions[request.session_id]
        
        # Add user message
        history.append(HumanMessage(content=request.message))
        
        # Invoke the agent
        result = app.invoke({"messages": history})
        
        # Update session with full history
        sessions[request.session_id] = result["messages"]
        
        # Extract agent response
        agent_response = str(result["messages"][-1].content)
        
        # VALIDATION: Check response for disclosure content
        if contains_disclosure_content(agent_response):
            return ChatResponse(
                response=SAFE_RESPONSES['disclosure'],
                session_id=request.session_id
            )
        
        # CLEANUP: Strip out any code blocks or technical content
        agent_response = re.sub(r'```python\s*[\s\S]*?```', '', agent_response)
        agent_response = re.sub(r'```[\s\S]*?```', '', agent_response)
        
        # Remove function definitions or explanations about pre_qualify
        if 'def pre_qualify' in agent_response or 'function' in agent_response.lower():
            lines = agent_response.split('\n')
            clean_lines = []
            for line in lines:
                if any(x in line.lower() for x in ['def ', 'import ', 'return ', '```', 'function', 'parameter', 'parameters']):
                    continue
                if line.strip():
                    clean_lines.append(line)
            agent_response = '\n'.join(clean_lines)
        
        # Clean up extra whitespace
        agent_response = agent_response.strip()
        
        if not agent_response:
            agent_response = "I'm here to help with auto loan pre-qualification. What would you like to know?"
        
        return ChatResponse(
            response=agent_response,
            session_id=request.session_id
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Chat Error:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@api.post("/reset")
async def reset_session(session_id: str = "default"):
    """Clear session history."""
    if session_id in sessions:
        del sessions[session_id]
    return {"message": f"Session {session_id} cleared"}

@api.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    return {
        "sessions": list(sessions.keys()),
        "count": len(sessions)
    }

# --- Main ---
if __name__ == "__main__":
    print("Starting AutoLend Agent API...")
    print("Access the API at: http://localhost:8000")
    print("API docs: http://localhost:8000/docs")
    uvicorn.run(
        api,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
