import json
from typing import Dict
from dotenv import load_dotenv
from langchain.schema import HumanMessage
from app.agents.base_llm import llm
import asyncio
from fastapi.testclient import TestClient
import importlib
#from app.main import app   # this is your FastAPI instance

from app.utils.server import mcp

import nest_asyncio
nest_asyncio.apply()
from fastmcp import Client


load_dotenv()

# async def _sync_call_prune(task: str, diagnosis: dict, script_code: str) -> str:
#         # each invocation gets its own connected client
#         async with Client(mcp) as client:
#             out = await client.call_tool(
#                 "prune_context",
#                 {
#                     "task":        task,
#                     "diagnosis":   diagnosis,
#                     "script_code": script_code
#                 }
#             )
#             return out[0]

#         loop = asyncio.new_event_loop()
#         try:
#             return loop.run_until_complete(_call())
#         finally:
#             loop.close()

# app/agents/writer_agent.py




# def _sync_call_prune(task: str, diagnosis: dict, script_code: str) -> str:
#     """
#     Synchronously invoke the prune_context MCP tool
#     on a fresh asyncio loop, avoiding nested loops.
#     """
#     async def _call():
#         async with Client(mcp) as client:
#             out = await client.call_tool(
#                 "prune_context",
#                 {
#                     "task": task,
#                     "diagnosis": diagnosis,
#                     "script_code": script_code
#                 }
#             )
#             return out[0]

#     loop = asyncio.new_event_loop()
#     # Windows-only: ensure self-pipe exists so close() won’t error
#     if hasattr(loop, "_setup_self_pipe"):
#         try:
#             loop._setup_self_pipe()
#         except Exception:
#             pass

#     try:
#         return loop.run_until_complete(_call())
#     finally:
#         loop.close()

class WriterAgent:
    """
    Specialist agent that composes an email update, executive summary,
    and SOP documentation from diagnostic and script context.
    """
    def __init__(self):
        self.llm = llm


    def execute(self, input: Dict) -> Dict:
        """
        Args:
            input: {
                'task': str,
                'diagnosis': dict,
                'script': dict
            }

        Returns:
            {
                'email': str,
                'summary': str,
                'sop': str
            }
        """
        task = input.get("task", "")
        diagnosis = input.get("diagnosis", {})
        script_code = input.get("script", {}).get("code", "")

        #pruned_context = _sync_call_prune(task, diagnosis, script_code)

        prompt = [
            HumanMessage(
                content=(
                    # "You are a technical writer for IT operations. "
                    # "Based on the following pruned context, generate JSON with keys: "
                    # "'email', 'summary', and 'sop'.\n\n"
                    # f"{pruned_context}\n\nTask: {task}"
                    "Generate JSON with keys: 'email', 'summary', and 'sop'."
                    "You are a technical writer for IT operations. Given the IT task, "
                    "the diagnostic findings, and the remediation script, compose the following:"
                    "\n1. A professional email to management summarizing the plan and next steps."
                    "\n2. A concise executive summary paragraph."
                    "\n3. An SOP-style technical documentation outlining the performed steps."
                    f"\n\nTask: {task}"
                    f"\nDiagnostic: {diagnosis}"
                    f"\nScript:\n{script_code}"
                    "\n\nRespond only in JSON with keys 'email', 'summary', and 'sop'."
                )
            )
        ]

        try:
            response = self.llm(prompt)
        except Exception as e:
            raise RuntimeError(f"LLM invocation failed: {e}")

        content = response.content.strip()
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse JSON from LLM response: {content}")

        return result

if __name__ == "__main__":
    # Ad-hoc smoke test
    agent = WriterAgent()
    sample = {
        "task": "Reset password for user jdoe on server X",
        "diagnosis": {
            "root_cause": "Account lockout due to multiple failed logins",
            "evidence": ["Detected 5 failed login attempts"],
            "recommended_actions": [{"action": "Unlock account and reset password", "confidence": 0.95}]
        },
        "script": {"code": "Unlock-ADAccount -Identity jdoe"}
    }
    result = agent.execute(sample)
    print(json.dumps(result, indent=2))
