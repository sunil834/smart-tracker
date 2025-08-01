// static/tracker.js

// Utility to map topic to input IDs
const topicToId = {
    "Python": "python-task",
    "Hack The Box": "htb-task",
    "Linux & Shell": "otw-task"
};

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    const calendarEl = document.getElementById('calendar');
    const currentDateEl = document.getElementById('current-date');
    const notesEl = document.getElementById('notes');
    const saveBtn = document.getElementById('save-log-btn');
    const statusMsgEl = document.getElementById('status-message');
    const streakBadgeEl = document.getElementById('streak-badge');

    let selectedDate = new Date().toISOString().slice(0, 10);
    currentDateEl.textContent = selectedDate;

    // Initialize Calendar
    flatpickr(calendarEl, {
        dateFormat: "Y-m-d",
        defaultDate: "today",
        onChange: function (selectedDates, dateStr) {
            selectedDate = dateStr;
            currentDateEl.textContent = dateStr;
            loadLogForDate(dateStr);
            // When calendar date changes, we might also want to reset checkboxes if it's not today.
            // However, the main daily reset logic happens on initial load for 'today'.
        }
    });

    loadLogForDate(selectedDate);
    loadStreak();
    // CALL THE NEW FUNCTION HERE TO RESET CHECKBOXES DAILY
    resetDailyCheckboxes(); //

    saveBtn.addEventListener('click', async () => {
        const taskSections = document.querySelectorAll('.task-section');
        const tasks = {};

        taskSections.forEach(section => {
            const topic = section.querySelector('.ai-button')?.dataset.topic || "";
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
            notes: notesEl.value,
            completed_tasks: tasks
        };

        statusMsgEl.textContent = 'Saving...';
        try {
            const res = await fetch('/save_log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(logData)
            });
            const result = await res.json();
            statusMsgEl.textContent = result.message;
            loadStreak();
        } catch (err) {
            console.error('Error:', err);
            statusMsgEl.textContent = 'Error saving log.';
        }
    });


    async function loadLogForDate(date) {
        try {
            const res = await fetch(`/load_log/${date}`);
            const result = await res.json();
            if (result.status === 'found') {
                const tasks = result.tasks || {};
                const taskSections = document.querySelectorAll('.task-section');

                taskSections.forEach(section => {
                    const topic = section.querySelector('.ai-button')?.dataset.topic || "";
                    const data = tasks[topic.toLowerCase()];
                    if (data) {
                        section.querySelector('.task-input').value = data.task || "";
                        section.querySelector('.completion-checkbox').checked = data.done || false;
                        section.querySelector('.extra-topic').value = data.extra || "";
                    } else {
                        // If no data found for this specific topic for the date, clear it.
                        section.querySelector('.task-input').value = "";
                        section.querySelector('.completion-checkbox').checked = false;
                        section.querySelector('.extra-topic').value = "";
                    }
                });

                notesEl.value = result.notes || "";
                statusMsgEl.textContent = 'Loaded saved log.';
            } else {
                // If no log found for the selected date, clear all fields
                const taskSections = document.querySelectorAll('.task-section');
                taskSections.forEach(section => {
                    section.querySelector('.task-input').value = "";
                    section.querySelector('.completion-checkbox').checked = false;
                    section.querySelector('.extra-topic').value = "";
                });
                notesEl.value = '';
                statusMsgEl.textContent = 'No log found for this date.';
            }
        } catch (err) {
            console.error(err);
            statusMsgEl.textContent = 'Failed to load log.';
        }
    }

    async function loadStreak() {
        try {
            const res = await fetch('/analytics_data');
            const data = await res.json();
            if (data.currentStreak >= 2) {
                streakBadgeEl.textContent = `⚡ Day ${data.currentStreak} Streak!`;
                streakBadgeEl.classList.remove('hidden');
            } else {
                streakBadgeEl.classList.add('hidden');
            }
        } catch (err) {
            console.error('Failed to fetch streak');
        }
    }

    // NEW FUNCTION: Reset checkboxes daily
    function resetDailyCheckboxes() {
        const today = new Date().toISOString().slice(0, 10); // Get today's date in YYYY-MM-DD format
        const lastResetDate = localStorage.getItem('last_daily_reset_date'); // Get the last date they were reset

        if (lastResetDate !== today) { // If it's a new day since the last reset
            const dailyTasks = document.querySelectorAll('.task-list input[type="checkbox"]'); // Select checkboxes in the Daily Routine
            dailyTasks.forEach(task => {
                task.checked = false; // Uncheck the task
                localStorage.removeItem(task.id); // Also clear its state from localStorage
            });
            localStorage.setItem('last_daily_reset_date', today); // Store today's date as the last reset date
        }
        // Load saved task states from localStorage (original logic, now runs AFTER potential reset)
        // This block is for the daily routine tasks (the 3 checkboxes at the top of tracker.html)
        document.querySelectorAll('.task-list input[type="checkbox"]').forEach(task => {
            const isChecked = localStorage.getItem(task.id) === 'true';
            task.checked = isChecked;
        });
    }

    // Handle all AI buttons
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

    // Handle all "What should I learn today?" buttons
    document.querySelectorAll('.suggest-today-button').forEach(button => {
        button.addEventListener('click', async () => {
            const section = button.closest('.task-section');
            const topic = button.dataset.topic;
            const input = section.querySelector('.task-input');
            const checkbox = section.querySelector('.completion-checkbox');

            // Reset input and checkbox for the specific section
            if (checkbox) checkbox.checked = false;
            if (input) input.value = ''; // Also clear the text input for the suggested task

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
            } catch (err) {
                alert('Could not suggest task for today.');
            }
        });
    });
});