from dotenv import load_dotenv
load_dotenv()

# Centralized LLM client for the entire application
# pip install -U langchain-openai
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.2)

if __name__ == "__main__":
    # Simple smoke test for the shared LLM client
    from langchain.schema import HumanMessage
    try:
        resp = llm([HumanMessage(content="Say hello in a sentence.")])
        print("✅ LLM responded:", resp.content)
    except Exception as e:
        print("❌ LLM invocation failed:", e)
