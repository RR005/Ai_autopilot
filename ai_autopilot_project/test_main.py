import pytest
import shutil
from httpx import AsyncClient
from httpx import ASGITransport
from main import app, TASK_STORE
from app.agents.automation_agent import AutomationAgent

import asyncio
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import nest_asyncio
nest_asyncio.apply()

@pytest.mark.asyncio
async def test_happy_path():
    if not shutil.which("pwsh"):
        pytest.skip("pwsh not installed — skipping PowerShell test")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/execute", json={
            "prompt": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings.",
            "require_approval": False
        })
        
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "completed"
        assert "diagnosis" in data["result"]
        assert "script" in data["result"]


@pytest.mark.asyncio
async def test_approval_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/execute", json={
            "prompt": "Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands.",
            "require_approval": True
        })
        data = resp.json()
        
        assert resp.status_code == 200
        assert data["status"] == "waiting_approval"
        task_id = data["task_id"]

        approve = await ac.post(f"/api/v1/plans/{task_id}/approve")
        print("Approval Response Text:", approve.text)
        approve_data = approve.json()
        assert approve.status_code == 200
        assert approve_data["status"] == "completed"
        assert "result" in approve_data


@pytest.mark.asyncio
async def test_agent_retry(monkeypatch):
    def failing_execute(self, input):
        raise RuntimeError("Simulated AutomationAgent failure")

    monkeypatch.setattr(AutomationAgent, "execute", failing_execute)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/execute", json={
            "prompt": "Diagnose CPU usage and create PowerShell script",
            "require_approval": False
        })
        assert response.status_code == 500
        assert "Execution failed" in response.text


@pytest.mark.asyncio
async def test_script_compiles():
    if shutil.which("pwsh"):
        agent = AutomationAgent()
        result = agent.execute({"task": "Get system uptime", "language": "powershell"})
        assert result["lint_passed"] is True
    elif shutil.which("shellcheck"):
        agent = AutomationAgent()
        result = agent.execute({"task": "List running processes", "language": "bash"})
        assert result["lint_passed"] is True
    else:
        pytest.skip("Neither pwsh nor shellcheck is installed. Skipping lint test.")


@pytest.mark.asyncio
async def test_task_status():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/v1/execute", json={
            "prompt": "Diagnose memory issue and summarize findings in email",
            "require_approval": False
        })
        data = resp.json()
        task_id = data["task_id"]

        status_resp = await ac.get(f"/api/v1/tasks/{task_id}")
        status_data = status_resp.json()
        assert status_resp.status_code == 200
        assert status_data["status"] == "completed"
        assert "diagnosis" in status_data["result"]
