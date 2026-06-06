from agents.engineering_agent import create_engineering_agent
from crewai import Task

agent = create_engineering_agent()

task = Task(
    description="Analyze a food donation platform and provide strengths and weaknesses.",
    expected_output="Technical analysis report",
    agent=agent
)

print("TASK CREATED SUCCESSFULLY")