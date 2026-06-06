# backend/test_direct_llm.py

from llm_utils import get_llm

llm = get_llm()

response = llm.invoke("""
Analyze FoodShare.

Give:
1. Technical Score
2. Strengths
3. Weaknesses
""")

print(response)