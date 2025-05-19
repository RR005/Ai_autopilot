import json
from typing import Dict
from dotenv import load_dotenv
from langchain.schema import HumanMessage
from app.agents.base_llm import llm

# Ensure environment variables are loaded (e.g., OPENAI_API_KEY)
load_dotenv()

class DiagnosticAgent:
    """
    Specialist agent that diagnoses IT issues by analyzing the request
    and returning structured root-cause information.
    """
    def __init__(self):
        self.llm = llm

    def execute(self, input: Dict) -> Dict:
        """
        Args:
            input: { 'task': str }

        Returns:
            { 'root_cause': str,
              'evidence': List[str],
              'recommended_actions': List[{'action': str, 'confidence': float}] }
        """
        task = input.get("task", "").strip()
        prompt = [
            HumanMessage(
                content=(
                    "You are an IT diagnostic expert. "
                    f"Given the request: \"{task}\", return a JSON object with keys:\n"
                    "- 'root_cause': brief description of the probable cause,\n"
                    "- 'evidence': list of observations supporting the cause,\n"
                    "- 'recommended_actions': list of objects { 'action': str, 'confidence': float }"  
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
    agent = DiagnosticAgent()
    sample = {"task": "Diagnose memory leak on server X causing high CPU."}
    result = agent.execute(sample)
    print(json.dumps(result, indent=2))
