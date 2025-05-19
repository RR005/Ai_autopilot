import dspy
from dspy import Signature, InputField, OutputField

# Signature: what inputs and outputs the module takes
class AgentPlannerSignature(Signature):
    task = InputField()
    steps = OutputField(desc="Comma-separated list of agent steps: diagnostic, automation, writer")

# Configure the LLM globally
# You can set your OpenAI API key in the environment or via dspy.settings.configure
# Example: dspy.settings.configure(lm=dspy.LM("openai/gpt-3.5-turbo"))
dspy.settings.configure(lm=dspy.LM("openai/gpt-3.5-turbo"))

class DSPyCoordinatorAgent:
    """Agent that uses DSPy to plan workflow steps based on a task description."""
    def __init__(self):
        self.module = dspy.Predict(signature=AgentPlannerSignature)

    def execute(self, input: dict) -> dict:
        task = input.get("request", "")
        prediction = self.module(task=task)
        steps_str = getattr(prediction, "steps", "")
        steps = [s.strip() for s in steps_str.split(",") if s.strip()]
        return {
            "plan": {"steps": steps},
            "status": "waiting_approval" if input.get("require_approval", False) else "ready"
        }
