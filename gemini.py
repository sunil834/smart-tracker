# gemini.py

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def configure_api():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Graceful fallback if key is missing
        print("Warning: GEMINI_API_KEY not found.")
        return False
    genai.configure(api_key=api_key)
    return True

def get_ai_suggestion(topic, previous_learning, history):
    if not configure_api():
        return "API Key missing."
    
    model = genai.GenerativeModel('models/gemini-flash-latest')
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
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Error:", e)
        return "Could not generate suggestion."

def get_next_step(topic, history, level="Basic"):
    if not configure_api():
        return "API Key missing."

    model = genai.GenerativeModel('models/gemini-flash-latest') 
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

    try:
        response = model.generate_content(prompt)
        suggestion = response.text.strip()
        if suggestion:
            return suggestion
    except Exception as e:
        print("Error generating next step:", e)

    return "AI is busy. Please try again in a moment!"

