# tracker_memory.py
import os
import json

MEMORY_FILE = "tracker_memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=4)

def update_topic_history(topic, new_entry):
    topic = topic.lower().strip()
    memory = load_memory()
    if topic not in memory:
        memory[topic] = []
    if new_entry and new_entry not in memory[topic]:
        memory[topic].append(new_entry.strip())
        save_memory(memory)

def get_recent_progress(topic, count=3):
    topic = topic.lower().strip()
    memory = load_memory()
    return memory.get(topic, [])[-count:]

def get_all_history(topic):
    topic = topic.lower().strip()
    memory = load_memory()
    return memory.get(topic, [])
