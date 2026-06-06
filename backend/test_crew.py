from crewai import Agent, Task, Crew, Process
from llm_utils import get_llm

agent = Agent(
    role="Technical Reviewer",
    goal="Analyze projects",
    backstory="Senior Software Architect",
    llm=get_llm(),
    verbose=False
)

task = Task(
    description="""
Analyze FoodShare.

Give:
1. Technical Score
2. Strengths
3. Weaknesses
""",
    expected_output="Technical evaluation report",
    agent=agent
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    process=Process.sequential,
    verbose=False
)

result = crew.kickoff()

print("\nRESULT:")
print(result)