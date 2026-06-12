from agents.forge_agent import create_forge_agent
from crewai import Task

agent = create_forge_agent()

task = Task(
    description="Analyze a food donation platform and provide strengths and weaknesses.",
    expected_output="Technical analysis report",
    agent=agent
)

print("TASK CREATED SUCCESSFULLY")
