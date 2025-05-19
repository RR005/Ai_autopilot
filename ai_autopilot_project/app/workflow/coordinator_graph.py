from typing import TypedDict, List, Dict, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph
#from langgraph.graph import StateGraphBuilder

#from app.agents.coordinator_agent import CoordinatorAgent
from app.agents.diagnostic_agent import DiagnosticAgent
from app.agents.automation_agent import AutomationAgent
from app.agents.writer_agent import WriterAgent
from app.agents.coordinator_agent import DSPyCoordinatorAgent


# Load env vars for LLM API key
load_dotenv()

class AgentState(TypedDict):
    input: str
    steps: List[str]
    diagnosis: Optional[Dict]
    script: Optional[Dict]
    email: Optional[str]
    summary: Optional[str]
    sop: Optional[str]

# === Nodes ===

def coordinator_node(state: AgentState) -> AgentState:
    agent = DSPyCoordinatorAgent()
    plan = agent.execute({"request": state["input"], "require_approval": state.get("require_approval", False)})
    steps = plan.get("plan", {}).get("steps", [])
    if not steps or steps[-1] != "finish":
        steps.append("finish")
    return {
        "input": state["input"],
        "steps": steps,
        "diagnosis": None,
        "script": None,
        "email": None,
        "summary": None,
        "sop": None
    }


def diagnostic_node(state: AgentState) -> AgentState:
    agent = DiagnosticAgent()
    result = agent.execute({"task": state["input"]})
    new_state = state.copy()
    new_state["diagnosis"] = result
    return new_state


def automation_node(state: AgentState) -> AgentState:
    agent = AutomationAgent()
    result = agent.execute({"task": state["input"], "language": "powershell"})
    new_state = state.copy()
    new_state["script"] = result
    return new_state


def writer_node(state: AgentState) -> AgentState:
    agent = WriterAgent()
    result = agent.execute({
        "task": state["input"],
        "diagnosis": state.get("diagnosis") or {},
        "script": state.get("script") or {}
    })
    new_state = state.copy()
    new_state.update({
        "email": result.get("email"),
        "summary": result.get("summary"),
        "sop": result.get("sop")
    })
    return new_state

def finish_node(state: AgentState) -> AgentState:
    return state


def route(state: AgentState) -> Optional[str]:
    if state["steps"]:
        # Pop the next step to execute
        return state["steps"].pop(0)
    return None

# === Build the LangGraph ===
builder = StateGraph(AgentState)
#builder = StateGraphBuilder(AgentState)
builder.add_node("coordinator", coordinator_node)
builder.add_node("diagnostic", diagnostic_node)
builder.add_node("automation", automation_node)
builder.add_node("writer", writer_node)
builder.add_node("finish", finish_node)

builder.set_entry_point("coordinator")
for node in ["coordinator", "diagnostic", "automation", "writer"]:
    builder.add_conditional_edges(node, route)

builder.set_finish_point("finish")
#builder.set_finish_when_function(lambda state: not state["steps"])
coordinator_graph = builder.compile()

# === Test Invocation ===
if __name__ == "__main__":
    input_text = (
        "Diagnose disk issue, generate a PowerShell script to log disk usage, and write a summary email."
    )
    result = coordinator_graph.invoke({"input": input_text})
    print("\n=== Graph Output ===")
    for key, val in result.items():
        print(f"{key}: {val}\n")
