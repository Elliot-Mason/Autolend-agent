from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Annotated
import operator

from config import LLM_PROVIDER, MODEL, OLLAMA_BASE_URL, LMSTUDIO_BASE_URL, SYSTEM_PROMPT
from tools import pre_qualify, network_diagnostic, read_internal_policy, fetch_competitor_rates

# Tools array including intentionally vulnerable hidden tools
tools = [pre_qualify, network_diagnostic, read_internal_policy, fetch_competitor_rates]

# --- State ---
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

# --- LLM (swap MODEL in config.py to change) ---
if LLM_PROVIDER.lower() == "lmstudio":
    # LM Studio serves an OpenAI-compatible API
    llm = ChatOpenAI(
        base_url=LMSTUDIO_BASE_URL,
        api_key="lm-studio",  # Required by LangChain, but any string works locally
        model=MODEL,
    ).bind_tools(tools)
else:
    llm = ChatOllama(
        model=MODEL,
        base_url=OLLAMA_BASE_URL,
    ).bind_tools(tools)

# --- Nodes ---
def call_model(state: AgentState) -> AgentState:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    """Route: call tools if requested, else end."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

# --- Graph ---
tool_node = ToolNode(tools)

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")   # loop back after tool use

app = graph.compile()