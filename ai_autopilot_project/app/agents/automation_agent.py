import os
import tempfile
import subprocess
import json
from typing import Dict, Optional
from dotenv import load_dotenv
from langchain.schema import HumanMessage
from app.agents.base_llm import llm

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()


def sanitize_request(task: str) -> str:
    """
    Basic sanitization to remove unwanted characters or patterns.
    Extend this function with stricter rules as needed.
    """
    return task.replace('```', '').strip()


class AutomationAgent:
    """
    Specialist agent that generates, lints, and optionally executes scripts for IT tasks.
    """
    def __init__(self):
        # Use centralized LLM client
        self.llm = llm

    def execute(self, input: Dict) -> Dict:
        """
        Args:
            input: { 'task': str, 'language': 'powershell' | 'bash' }

        Returns:
            {
              'language': str,
              'code': str,
              'lint_passed': bool,
              'lint_errors': Optional[str],
              'output': Optional[Dict]
            }
        """
        raw_task = input.get("task", "").strip()
        task = sanitize_request(raw_task)
        language = input.get("language", "powershell").lower()

        # Build prompt for raw script only
        prompt = [
            HumanMessage(
                content=(
                    f"Generate a {language} script to accomplish the following IT task:\n"
                    f"{task}\n\n"
                    "Ensure the script is syntactically correct and production-safe."
                    " Respond **only** with the raw script, no explanations or markdown."
                )
            )
        ]

        # Invoke LLM
        try:
            response = self.llm(prompt)
        except Exception as e:
            raise RuntimeError(f"LLM invocation failed: {e}")

        code = response.content.strip()
        if code.startswith("```"):
            code = code.strip("`\n")

        # Write script to temp
        suffix = ".ps1" if language == "powershell" else ".sh"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        # Lint
        lint_passed = False
        lint_errors: Optional[str] = None
        if language == "powershell":
            lint_cmd = ["pwsh", "-NoProfile", "-Command", f"Invoke-ScriptAnalyzer -Path '{tmp_path}' -Severity Error"]
        else:
            lint_cmd = ["shellcheck", tmp_path]

        try:
            result = subprocess.run(lint_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                lint_passed = True
            else:
                lint_errors = result.stderr or result.stdout
        except Exception as e:
            lint_errors = str(e)

        # Execute dry-run
        output: Optional[Dict] = None
        if lint_passed:
            try:
                if language == "powershell":
                    exec_cmd = ["pwsh", "-NoProfile", "-Command", f"& '{tmp_path}'"]
                else:
                    exec_cmd = ["bash", tmp_path]
                exec_result = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=60)
                output = {"stdout": exec_result.stdout, "stderr": exec_result.stderr}
            except Exception as e:
                output = {"execution_error": str(e)}

        # Cleanup
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        return {
            "language": language,
            "code": code,
            "lint_passed": lint_passed,
            "lint_errors": lint_errors,
            "output": output,
        }


if __name__ == "__main__":
    # Ad-hoc smoke test
    agent = AutomationAgent()
    sample = {"task": "List all running processes on the local machine.", "language": "bash"}
    result = agent.execute(sample)
    print(json.dumps(result, indent=2))
