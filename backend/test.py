from llm_utils import get_llm

llm = get_llm()

response = llm.invoke(
    "Give a technical score between 0 and 100. Keep answer under 20 words."
)

print(response)