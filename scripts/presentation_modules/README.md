Presentation modules for the hackathon.

Files and presenters:

- frontend_module.py — frontend detection and samples. (Presenter 1)
- backend_module.py — backend / API / database signals. (Presenter 2)
- agents_module.py — agent/LLM systems and example agent task. (Presenter 3)
- integration_module.py — repository parsing, third-party integrations and repo stats. (Presenter 4)

How to run a syntax check:

python -m py_compile scripts/presentation_modules/*.py

Run the demo which imports all modules and prints sample outputs:

python scripts/presentation_modules/run_demo.py
