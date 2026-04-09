from langchain_core.messages import HumanMessage
from graph import app

def chat():
    print(f"Agent ready. Type 'exit' to quit.\n")
    history = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break

        history.append(HumanMessage(content=user_input))
        result = app.invoke({"messages": history})

        # Append full history for multi-turn memory
        history = result["messages"]
        
        last = history[-1]
        print(f"\nAgent: {last.content}\n")

if __name__ == "__main__":
    chat()