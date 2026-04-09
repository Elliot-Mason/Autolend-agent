import requests
import json
import sys

# Configuration
API_URL = "http://localhost:8000"
SESSION_ID = "user_session_1"

def test_health():
    """Test API health."""
    print("🏥 Testing API health...")
    response = requests.get(f"{API_URL}/health")
    print(f"Response: {response.json()}\n")

def chat(message: str, session_id: str = SESSION_ID):
    """Send a message to the agent."""
    print(f"📤 Sending: {message}")
    response = requests.post(
        f"{API_URL}/chat",
        json={"message": message, "session_id": session_id}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"📥 Agent: {result['response']}\n")
        return result["response"]
    else:
        print(f"❌ Error: {response.json()}\n")
        return None

def list_sessions():
    """List active sessions."""
    response = requests.get(f"{API_URL}/sessions")
    print(f"Sessions: {response.json()}\n")

def reset_session(session_id: str = SESSION_ID):
    """Clear session history."""
    response = requests.post(f"{API_URL}/reset", params={"session_id": session_id})
    print(f"Reset response: {response.json()}\n")

def interactive_chat(session_id: str = SESSION_ID):
    """Interactive chat loop."""
    print("🤖 AutoLend Agent - Remote Client")
    print("Type 'exit' to quit, 'reset' to clear history, 'health' to check status\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            elif user_input.lower() == "exit":
                print("👋 Goodbye!")
                break
            elif user_input.lower() == "reset":
                reset_session(session_id)
                continue
            elif user_input.lower() == "health":
                test_health()
                continue
            else:
                chat(user_input, session_id)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to API. Is the server running?")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running quick tests...\n")
        test_health()
        chat("What auto loans do you offer?")
        list_sessions()
    else:
        interactive_chat()
