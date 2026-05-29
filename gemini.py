# gemini.py

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

REQUEST_TIMEOUT_SECONDS = 8
_generation_executor = ThreadPoolExecutor(max_workers=4)


def configure_api():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Graceful fallback if key is missing
        print("Warning: GEMINI_API_KEY not found.")
        return False
    genai.configure(api_key=api_key)
    return True


def _generate_content_with_timeout(model, prompt, fallback_message):
    future = _generation_executor.submit(model.generate_content, prompt)
    try:
        response = future.result(timeout=REQUEST_TIMEOUT_SECONDS)
        return response.text.strip() if response and response.text else fallback_message
    except FuturesTimeoutError:
        future.cancel()
        print(f"Gemini request timed out after {REQUEST_TIMEOUT_SECONDS} seconds.")
        return fallback_message
    except Exception as exc:
        print("Gemini request failed:", exc)
        return fallback_message


def get_ai_suggestion(topic, previous_learning, history):
    if not configure_api():
        return "API Key missing."

    model = genai.GenerativeModel("models/gemini-flash-latest")
    recent = " -> ".join(history) if history else "None yet"

    prompt = f"""
    You are an expert cybersecurity and programming mentor.
    Topic: {topic}
    
    The student has previously done: {recent}
    Most recently, they learned/did: '{previous_learning}'.
    
    Based on this, suggest the SINGLE next logical step or a deeper dive into the recent topic.
    Keep it actionable and specific. 
    Limit response to one sentence. No intro text.
    """

    return _generate_content_with_timeout(
        model,
        prompt,
        "Could not generate suggestion. Please try again in a moment.",
    )


def get_next_step(topic, history, level="Basic"):
    if not configure_api():
        return "API Key missing."

    model = genai.GenerativeModel("models/gemini-flash-latest")
    recent = " -> ".join(history) if history else "None yet"

    # Context specific to the track
    context = ""
    if "python" in topic.lower():
        context = "Focus on Python programming, automation, and scripting for security."
    elif "hack" in topic.lower() or "ctf" in topic.lower():
        context = "Focus on Capture The Flag strategies, penetration testing methodologies, and tools (nmap, burpsuite, etc)."
    elif "linux" in topic.lower() or "shell" in topic.lower():
        context = "Focus on Linux command line, bash scripting, file permissions, and system administration."

    prompt = f"""
    As a technical mentor, suggest a learning task for a student.
    
    **Topic:** {topic} ({context})
    **Student's History:** {recent}
    **Target Difficulty:** {level}

    **Instructions:**
    1. Suggest a **new, specific, actionable task** that has NOT been done before based on the history.
    2. The task must match the '{level}' difficulty.
    3. The response must be a SINGLE sentence only. No intro or extra text.
    
    Suggest the next task now.
    """

    suggestion = _generate_content_with_timeout(
        model,
        prompt,
        "AI is busy. Please try again in a moment!",
    )
    return suggestion or "AI is busy. Please try again in a moment!"
