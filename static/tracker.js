// static/tracker.js

// Utility to map topic to input IDs
const topicToId = {
    "Python": "python-task",
    "Hack The Box": "htb-task",
    "Linux & Shell": "otw-task"
};

// Toggle Completion Container Visuals
window.toggleCompletion = function(container) {
    const checkbox = container.querySelector('input[type="checkbox"]');
    // Prevent double-toggling if the user clicked the checkbox directly
    if (event.target !== checkbox) {
        checkbox.checked = !checkbox.checked;
    }
    
    if (checkbox.checked) {
        container.classList.add('checked');
    } else {
        container.classList.remove('checked');
    }
};

// Main Initialization
document.addEventListener('DOMContentLoaded', () => {
    // --- Auto-grow functionality ---
    function adjustAllHeights() {
        setTimeout(() => {
            document.querySelectorAll('.auto-grow').forEach(el => {
                el.style.height = '5px'; // Force drastic shrink
                el.style.height = (el.scrollHeight) + 'px';
            });
        }, 50); // Increased delay to ensure text is rendered
    }

    function initAutoGrow() {
        document.querySelectorAll('.auto-grow').forEach(textarea => {
            textarea.addEventListener('input', function() {
                // Inline adjustment for typing (faster response)
                this.style.height = '5px';
                this.style.height = (this.scrollHeight) + 'px';
            });
        });
        adjustAllHeights();
    }
    
    // Sync completion containers on load
    document.querySelectorAll('.completion-container').forEach(container => {
        const checkbox = container.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked) container.classList.add('checked');
        
        // Listen for direct checkbox changes (e.g. from loadLogForDate)
        if (checkbox) {
            checkbox.addEventListener('change', () => {
                 if (checkbox.checked) container.classList.add('checked');
                 else container.classList.remove('checked');
            });
        }
    });

    const calendarEl = document.getElementById('calendar');
    const currentDateEl = document.getElementById('current-date');
    const notesEl = document.getElementById('notes');
    const saveBtn = document.getElementById('save-log-btn');
    const statusMsgEl = document.getElementById('status-message');
    const streakBadgeEl = document.getElementById('streak-badge');
    
    let selectedDate = new Date().toISOString().slice(0, 10);
    currentDateEl.textContent = selectedDate;

    // Initialize Auto Grow
    initAutoGrow();
    // Final safety resize
    window.addEventListener('load', adjustAllHeights);
    setTimeout(adjustAllHeights, 200);

    // --- Daily Quote Logic ---
    const quotes = [
        "Small steps, big impact.",
        "Hack the planet! 🌍",
        "Consistency is key.",
        "Learn. Break. Fix. Repeat.",
        "Today is a good day to code.",
        "Debug your mind.",
        "Progress > Perfection.",
        "Keep pushing forward.",
        "Stay curious.",
        "One line at a time.",
        "Evolve or expire.",
        "Code is your craft.",
        "Master the fundamentals.",
        "Focus on the process.",
        "Bugs are just lessons.",
        "Your only limit is you.",
        "Think like a hacker.",
        "Fuel your ambition.",
        "Persistence pays off.",
        "Keep the fire burning."
    ];
    const quoteEl = document.getElementById('daily-quote');
    if (quoteEl) {
        quoteEl.textContent = quotes[Math.floor(Math.random() * quotes.length)];
    }

    // Initialize Calendar
    if (calendarEl) {
        flatpickr(calendarEl, {
            dateFormat: "Y-m-d",
            defaultDate: "today",
            onChange: function (selectedDates, dateStr) {
                selectedDate = dateStr;
                currentDateEl.textContent = dateStr;
                loadLogForDate(dateStr);
            }
        });
    }

    loadLogForDate(selectedDate);
    loadStreak();
    
    // Reset daily checkboxes (Legacy logic)
    resetDailyCheckboxes(); 

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const taskSections = document.querySelectorAll('.task-section');
            const tasks = {};

            taskSections.forEach(section => {
                const topicBtn = section.querySelector('.ai-button');
                const topic = topicBtn?.dataset.topic || "";
                
                const input = section.querySelector('.task-input')?.value || "";
                const done = section.querySelector('.completion-checkbox')?.checked || false;
                const extra = section.querySelector('.extra-topic')?.value || "";

                if (topic) {
                    tasks[topic.toLowerCase()] = {
                        task: input,
                        done: done,
                        extra: extra
                    };
                }
            });

            const logData = {
                date: selectedDate,
                notes: notesEl ? notesEl.value : "",
                completed_tasks: tasks
            };

            if (statusMsgEl) statusMsgEl.textContent = 'Saving...';
            try {
                const res = await fetch('/save_log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(logData)
                });
                const result = await res.json();
                if (statusMsgEl) statusMsgEl.textContent = result.message;
                loadStreak();
            } catch (err) {
                console.error('Error:', err);
                if (statusMsgEl) statusMsgEl.textContent = 'Error saving log.';
            }
        });
    }

    async function loadLogForDate(date) {
        try {
            const res = await fetch(`/load_log/${date}`);
            // If it's a 404/500 from server structure, throw to catch
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            
            const result = await res.json();
            
            if (result.status === 'found') {
                const tasks = result.tasks || {};
                const taskSections = document.querySelectorAll('.task-section');

                taskSections.forEach(section => {
                    const topicBtn = section.querySelector('.ai-button');
                    if (!topicBtn) return; // Guard clause
                    
                    const topic = topicBtn.dataset.topic || "";
                    if (!topic) return;

                    const data = tasks[topic.toLowerCase()];
                    const inputEl = section.querySelector('.task-input');
                    const checkboxEl = section.querySelector('.completion-checkbox');
                    const extraEl = section.querySelector('.extra-topic');

                    if (data) {
                        if (inputEl) inputEl.value = data.task || "";
                        if (checkboxEl) {
                            checkboxEl.checked = data.done || false;
                            // Trigger change event to update visual container
                            checkboxEl.dispatchEvent(new Event('change'));
                        }
                        if (extraEl) extraEl.value = data.extra || "";
                    } else {
                        // Clear fields if this specific topic has no data in the found log
                        if (inputEl) inputEl.value = "";
                        if (checkboxEl) {
                            checkboxEl.checked = false;
                            checkboxEl.dispatchEvent(new Event('change'));
                        }
                        if (extraEl) extraEl.value = "";
                    }
                });

                if (notesEl) notesEl.value = result.notes || "";
                if (statusMsgEl) statusMsgEl.textContent = 'Loaded saved log.';
            } else {
                // Status is 'not found' -> New Day
                clearAllFields();
                if (statusMsgEl) statusMsgEl.textContent = 'Ready for a new day. 🚀';
            }
        } catch (err) {
            console.error('Log load error:', err);
            if (err.message.includes('404') || err instanceof SyntaxError) {
                 if (statusMsgEl) statusMsgEl.textContent = 'Ready for a new day. 🚀';
            } else {
                 if (statusMsgEl) statusMsgEl.textContent = 'Error loading log.';
            }
            // Even on error, ensure we have a clean state if it was a fetch failure
            // But maybe don't clear fields if it was just a network glitch? 
            // For safety, let's keep current fields if it wasn't a 404.
        } finally {
            // Always resize
            adjustAllHeights();
        }
    }
    
    function clearAllFields() {
        document.querySelectorAll('.task-section').forEach(section => {
            const inputEl = section.querySelector('.task-input');
            const checkboxEl = section.querySelector('.completion-checkbox');
            const extraEl = section.querySelector('.extra-topic');
            
            if (inputEl) inputEl.value = "";
            if (checkboxEl) {
                checkboxEl.checked = false;
                checkboxEl.dispatchEvent(new Event('change'));
            }
            if (extraEl) extraEl.value = "";
        });
        if (notesEl) notesEl.value = '';
    }

    async function loadStreak() {
        try {
            const res = await fetch('/analytics_data');
            const data = await res.json();
            if (streakBadgeEl) {
                if (data.currentStreak > 0) {
                    streakBadgeEl.innerHTML = `🔥 ${data.currentStreak} Day Streak`;
                    streakBadgeEl.classList.remove('hidden');
                } else {
                    streakBadgeEl.classList.add('hidden');
                }
            }
        } catch (err) {
            console.error('Failed to fetch streak');
        }
    }

    function resetDailyCheckboxes() {
        const today = new Date().toISOString().slice(0, 10);
        const lastResetDate = localStorage.getItem('last_daily_reset_date');

        if (lastResetDate !== today) {
            const dailyTasks = document.querySelectorAll('.task-list input[type="checkbox"]');
            dailyTasks.forEach(task => {
                task.checked = false;
                localStorage.removeItem(task.id);
            });
            localStorage.setItem('last_daily_reset_date', today);
        }
        document.querySelectorAll('.task-list input[type="checkbox"]').forEach(task => {
            const isChecked = localStorage.getItem(task.id) === 'true';
            task.checked = isChecked;
        });
    }

    // Handle AI buttons
    document.querySelectorAll('.ai-button').forEach(button => {
        button.addEventListener('click', async () => {
            const section = button.closest('.task-section');
            const input = section.querySelector('.task-input');
            const topic = button.dataset.topic;
            const learning = input.value;

            if (!learning) return alert('Please enter what you did first.');

            try {
                const res = await fetch('/get_suggestion', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic, learning })
                });
                const result = await res.json();
                section.querySelector('#ai-suggestion-text')?.remove();
                const p = document.createElement('p');
                p.id = 'ai-suggestion-text';
                p.textContent = result.suggestion;
                section.appendChild(p);
            } catch (err) {
                alert('Could not fetch AI suggestion.');
            }
        });
    });

    // Handle "What should I learn today?"
    document.querySelectorAll('.suggest-today-button').forEach(button => {
        button.addEventListener('click', async () => {
            const section = button.closest('.task-section');
            const topic = button.dataset.topic;
            const input = section.querySelector('.task-input');
            const checkbox = section.querySelector('.completion-checkbox');

            if (checkbox) {
                checkbox.checked = false;
                checkbox.dispatchEvent(new Event('change'));
            }
            if (input) input.value = '';

            try {
                const res = await fetch('/next_suggestion', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic })
                });
                const result = await res.json();

                section.querySelector('#ai-suggestion-text')?.remove();
                const p = document.createElement('p');
                p.id = 'ai-suggestion-text';
                p.textContent = `💡 Suggested: ${result.suggestion}`;
                section.appendChild(p);
                
                if (input) {
                    input.style.height = 'auto';
                    input.style.height = (input.scrollHeight) + 'px';
                }
            } catch (err) {
                alert('Could not suggest task for today.');
            }
        });
    });
});