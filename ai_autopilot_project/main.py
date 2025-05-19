# ai_autopilot_project/app/main.py

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import json
import asyncio
from fastapi_mcp import FastApiMCP
from app.workflow.coordinator_graph import coordinator_graph
#from app.agents.coordinator_agent import CoordinatorAgent
from app.agents.coordinator_agent import DSPyCoordinatorAgent

# import nest_asyncio
# nest_asyncio.apply()

app = FastAPI(
    title="AI Autopilot Service",
    version="1.0",
    debug=True,                   # ⇐ turn on full tracebacks
)


class ExecuteRequest(BaseModel):
    prompt: str                  # renamed from `request`
    require_approval: bool = False


class ExecuteResponse(BaseModel):
    task_id: str
    status: str
    plan: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    plan: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None

class PruneRequest(BaseModel):
    task: str
    diagnosis: Dict[str, Any]
    script_code: str


# simple in‑memory task store
TASK_STORE: Dict[str, Dict[str, Any]] = {}


@app.post("/api/v1/execute", response_model=ExecuteResponse)
async def execute_task(payload: ExecuteRequest):
    """
    Starts a new task.  
    - If require_approval=true: generates a plan and waits.  
    - Otherwise: runs the full coordinator_graph immediately.
    """
    task_id = str(uuid.uuid4())
    TASK_STORE[task_id] = {"prompt": payload.prompt, "status": "pending"}

    # ── Approval flow ─────────────────────────────
    if payload.require_approval:
        try:
            agent_resp = DSPyCoordinatorAgent().execute({
                "request": payload.prompt,
                "require_approval": True
            })
            plan = agent_resp.get("plan")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Plan generation failed: {e}"
            )

        TASK_STORE[task_id] = {
            "prompt": payload.prompt,
            "status": "waiting_approval",
            "plan": plan
        }
        return ExecuteResponse(
            task_id=task_id,
            status="waiting_approval",
            plan=plan
        )

    # ── Full execution flow ───────────────────────
    initial_state = {
        "input": payload.prompt,
        "require_approval": False,
        # "steps": [],
        # "diagnosis": None,
        # "script": None,
        # "email": None,
        # "summary": None,
        # "sop": None,
    }
    try:
        result_state = coordinator_graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {e}"
        )

    TASK_STORE[task_id] = {
        "prompt": payload.prompt,
        "status": "completed",
        **result_state
    }
    return ExecuteResponse(
        task_id=task_id,
        status="completed",
        result=result_state
    )


@app.post("/api/v1/plans/{task_id}/approve", response_model=TaskStatusResponse)
async def approve_plan(task_id: str):
    task = TASK_STORE.get(task_id)
    if not task or task.get("status") != "waiting_approval":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not awaiting approval"
        )

    try:
        # re‑run the full graph now that it’s approved
        initial_state = {
            "input": task["prompt"],
            "require_approval": False,
            # "steps": [],
            # "diagnosis": None,
            # "script": None,
            # "email": None,
            # "summary": None,
            # "sop": None,
        }
        result_state = coordinator_graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {e}"
        )

    task.update(result_state)
    task["status"] = "completed"
    return TaskStatusResponse(
        task_id=task_id,
        status="completed",
        plan=task.get("plan"),
        result=result_state
    )


@app.post("/api/v1/plans/{task_id}/reject", response_model=TaskStatusResponse)
async def reject_plan(task_id: str):
    task = TASK_STORE.get(task_id)
    if not task or task.get("status") != "waiting_approval":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not awaiting approval"
        )
    task["status"] = "rejected"
    return TaskStatusResponse(
        task_id=task_id,
        status="rejected",
        plan=task.get("plan")
    )


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # only expose the result‐fields that exist
    result = {
        k: task[k]
        for k in ("diagnosis", "script", "email", "summary", "sop")
        if k in task
    } or None

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        plan=task.get("plan"),
        result=result
    )



# mcp = FastMCP.from_fastapi(app=app)  

# @mcp.tool()
# async def prune_context(
#     task: str,
#     diagnosis: dict,
#     script_code: str,
#     ctx: Context
# ) -> str:
#     ctx.info("Pruning context for task")
#     chunks = []
#     if diagnosis:
#         chunks.append("Diagnosis: " + json.dumps(diagnosis))
#     if script_code:
#         chunks.append("Script:\n" + script_code)
#     response = await ctx.llm(
#         messages=[
#             {"role": "system",  "content": "Select the most relevant context chunks."},
#             {"role": "user",    "content": "\n\n".join(chunks)},
#         ],
#         max_tokens=400
#     )
#     return response.content.strip()

