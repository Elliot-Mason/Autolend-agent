# AutoLend Agent - Remote API Setup

## Quick Start

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Start the API Server
```powershell
python api.py
```

The API will be available at:
- **API**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

### 3. Test the API (in another terminal)
```powershell
# Option A: Interactive client
python client.py

# Option B: Quick test
python client.py --test

# Option C: Using curl
curl -X POST "http://localhost:8000/chat" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"What is your name?\",\"session_id\":\"test\"}"
```

## API Endpoints

### `POST /chat`
Send a message to the agent.

**Request:**
```json
{
  "message": "Can I get an auto loan?",
  "session_id": "user_123"
}
```

**Response:**
```json
{
  "response": "Of course! I'd be happy to help you explore...",
  "session_id": "user_123"
}
```

### `GET /health`
Check API health and model status.

**Response:**
```json
{
  "status": "healthy",
  "model": "llama3.2"
}
```

### `POST /reset`
Clear session history.

**Query Parameters:**
- `session_id` (string): Session to reset (default: "default")

### `GET /sessions`
List all active sessions.

## Remote Access

### Option 1: Local Network
Use your machine's IP address:
```powershell
ipconfig
# Use the IPv4 Address from your network adapter
# Example: http://192.168.1.100:8000
```

### Option 2: Ngrok (Secure Tunneling)
```powershell
# Install ngrok: https://ngrok.com
ngrok http 8000
# Generates a public URL: https://xxxx-xx-xxx-xxx-xx.ngrok-free.app
```

### Option 3: Docker (Production)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "api.py"]
```

Build and run:
```powershell
docker build -t autolend-agent .
docker run -p 8000:8000 autolend-agent
```

## Security Considerations

⚠️ **Current Setup (Development Only)**

For production:
1. **Authentication**: Add API keys or OAuth
2. **CORS**: Restrict to specific domains (change `allow_origins=["*"]`)
3. **HTTPS**: Use SSL/TLS certificates
4. **Rate Limiting**: Add request throttling
5. **Session Storage**: Use Redis or database instead of in-memory storage
6. **Environment Variables**: Store sensitive config in `.env` file

Example with environment variables:
```python
from dotenv import load_dotenv
import os

load_dotenv()
API_PORT = int(os.getenv("API_PORT", 8000))
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")
```

## Troubleshooting

**"Cannot connect to API"**
- Ensure `api.py` is running
- Check if port 8000 is in use: `netstat -ano | findstr :8000`

**"Connection refused"**
- Verify Ollama is running: `ollama serve` in another terminal
- Check `OLLAMA_BASE_URL` in `config.py`

**"Module not found"**
- Reinstall dependencies: `pip install -r requirements.txt`

**Performance Issues**
- Scale to multiple workers:
  ```powershell
  uvicorn api:api --workers 4 --host 0.0.0.0 --port 8000
  ```
