import sys
sys.path.insert(0, ".")
from crewai import LLM, Agent, Task, Crew
from config import OLLAMA_HOST

llm = LLM(
    model="ollama/qwen2.5:3b",
    base_url=OLLAMA_HOST,
    temperature=0.1,
    max_tokens=200,
    config={"num_ctx": 8192}
)

agent = Agent(
    role="Test Agent",
    goal="Say hello",
    backstory="A test agent",
    llm=llm,
    verbose=True
)

task = Task(
    description="Say hello",
    expected_output="A hello message",
    agent=agent
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True
)

try:
    res = crew.kickoff()
    print("RESULT:", res)
except Exception:
    import traceback
    traceback.print_exc()
