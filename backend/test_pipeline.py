# backend/test_pipeline.py

from crew.crew import run_evaluation

context = """
Project Name: FoodShare

Problem:
Restaurants waste food.

Solution:
AI platform connecting restaurants and NGOs.

Tech:
React
FastAPI
SQLite

Features:
Food listing
NGO matching
Volunteer tracking
"""

result = run_evaluation(context)

print("\n========== VERDICT ==========")
print(result["raw_verdict"])