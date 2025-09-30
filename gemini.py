# gemini.py (Modified)

import os
import google.generativeai as genai
from dotenv import load_dotenv
# No longer imports from tracker_memory

load_dotenv()

def configure_api():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found.")
    genai.configure(api_key=api_key)

# The function now accepts 'history' as an argument
def get_ai_suggestion(topic, previous_learning, history):
    configure_api()
    model = genai.GenerativeModel('models/gemini-flash-latest')
    recent = " -> ".join(history) if history else "None yet"
    prompt = f"""
    You are a cybersecurity mentor. Topic: {topic}.
    Previously done: {recent}
    Most recently learned: '{previous_learning}'.
    Suggest the next logical task in a single actionable sentence, no intro text.
    """
    try:
        response = model.generate_content(prompt)
        # The responsibility of updating history is now in app.py
        return response.text.strip()
    except Exception as e:
        print("Error:", e)
        return "Could not generate."

# The function now accepts 'history' as an argument
def get_next_step(topic, history, level="Basic"):
    configure_api()
    # You might need to adjust the model name based on availability
    model = genai.GenerativeModel('gemini-1.5-flash') 
    recent = " -> ".join(history) if history else "None yet"
    prompt = f"""
    As a Python mentor, provide a learning task for a student.

    **Student's History for '{topic}':**
    {recent}

    **Instructions:**
    1.  Suggest a **new, specific, actionable task** that has NOT been done before.
    2.  The task must match the requested difficulty level: **{level}**.
    3.  The response must be a single sentence only. No intro or extra text.

    **Difficulty Level Guide:**
    - **Basic:** Core concepts like variables, loops, conditionals, simple data structures (lists, dicts).
    - **Intermediate:** Functions, OOP basics (classes), file I/O, simple modules (like `random` or `datetime`).
    - **Advanced:** Advanced OOP (inheritance, decorators), list comprehensions, generators, working with APIs (`requests`).
    - **Pro:** Data structures & algorithms (trees, graphs), concurrency, metaprogramming, performance optimization.
    - **Scripting:** Practical automation tasks involving file system operations (`os`, `shutil`), web scraping (`BeautifulSoup`), or data manipulation (`csv`).

    Suggest the next task now.
    """

    seen = set(history)
    max_attempts = 5

    for _ in range(max_attempts):
        try:
            response = model.generate_content(prompt)
            suggestion = response.text.strip()
            if suggestion and suggestion not in seen:
                # The responsibility of updating history is now in app.py
                return suggestion
        except Exception as e:
            print("Error generating next step:", e)
            break


    return "AI is busy. Please try again in a moment!"
