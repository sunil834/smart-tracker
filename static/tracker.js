// static/tracker.js

// No static topic-to-id mapping — topics are rendered dynamically now

// Toggle Completion Container Visuals
window.toggleCompletion = function(container) {
    const checkbox = container.querySelector('input[type="checkbox"]');
    const section = container.closest('.task-section');
    // Prevent double-toggling if the user clicked the checkbox directly
    if (event.target !== checkbox) {
        checkbox.checked = !checkbox.checked;
    }
    
    if (checkbox.checked) {
        container.classList.add('checked');
        if (section) section.classList.add('completed');
    } else {
        container.classList.remove('checked');
        if (section) section.classList.remove('completed');
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
                if (checkbox.checked) {
                    container.classList.add('checked');
                    container.closest('.task-section')?.classList.add('completed');
                } else {
                    container.classList.remove('checked');
                    container.closest('.task-section')?.classList.remove('completed');
                }
            });
        }
    });

    const calendarEl = document.getElementById('calendar');
    const currentDateEl = document.getElementById('current-date');
    const notesEl = document.getElementById('notes');
    const saveBtn = document.getElementById('save-log-btn');
    const statusMsgEl = document.getElementById('status-message');
    const streakBadgeEl = document.getElementById('streak-badge');
    const dailyLogEl = document.getElementById('daily-log');
    const workspaceGridEl = document.querySelector('.workspace-grid');
    const autosaveStateByDate = new Map();
    
    let selectedDate = new Date().toISOString().slice(0, 10);
    let isHydratingLog = false;
    currentDateEl.textContent = selectedDate;

    function setStatusMessage(message, state = '') {
        if (!statusMsgEl) return;
        statusMsgEl.textContent = message;
        if (state) {
            statusMsgEl.dataset.state = state;
        } else {
            delete statusMsgEl.dataset.state;
        }
    }

    function setSkeletonState(isLoading) {
        if (!workspaceGridEl) return;

        workspaceGridEl.classList.toggle('is-skeleton-loading', isLoading);

        const controls = workspaceGridEl.querySelectorAll(
            '#calendar, #new-topic-name, #notes, .task-input, .extra-topic, .completion-checkbox, #create-topic-btn, .ai-button, .suggest-today-button, #save-log-btn'
        );

        controls.forEach(control => {
            if ('disabled' in control) {
                control.disabled = isLoading;
            }
        });
    }

    function getAutosaveState(date) {
        if (!autosaveStateByDate.has(date)) {
            autosaveStateByDate.set(date, {
                timerId: null,
                inFlight: false,
                queued: false,
            });
        }
        return autosaveStateByDate.get(date);
    }

    function buildLogPayload(date) {
        const taskSections = document.querySelectorAll('.task-section');
        const tasks = {};

        taskSections.forEach(section => {
            const topicBtn = section.querySelector('.ai-button');
            const topic = topicBtn?.dataset.topic || section.dataset.topicName || '';

            const input = section.querySelector('.task-input')?.value || '';
            const done = section.querySelector('.completion-checkbox')?.checked || false;
            const extra = section.querySelector('.extra-topic')?.value || '';

            if (topic) {
                tasks[topic] = {
                    task: input,
                    done: done,
                    extra: extra,
                };
            }
        });

        return {
            date: date,
            notes: notesEl ? notesEl.value : '',
            completed_tasks: tasks,
        };
    }

    async function saveLogDraft(date) {
        const state = getAutosaveState(date);
        if (state.timerId) {
            clearTimeout(state.timerId);
            state.timerId = null;
        }

        if (state.inFlight) {
            state.queued = true;
            return;
        }

        state.inFlight = true;
        setStatusMessage('Saving...', 'saving');

        try {
            const res = await fetch(`/api/log/${date}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildLogPayload(date)),
            });

            const result = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(result.error || `HTTP ${res.status}`);
            }

            setStatusMessage('Saved just now', 'saved');
        } catch (err) {
            console.error('Error saving log:', err);
            setStatusMessage('Error saving log.', 'error');
        } finally {
            state.inFlight = false;
            if (state.queued) {
                state.queued = false;
                scheduleAutosave(date);
            }
        }
    }

    function scheduleAutosave(date) {
        const state = getAutosaveState(date);
        if (state.timerId) {
            clearTimeout(state.timerId);
        }
        state.timerId = setTimeout(() => {
            state.timerId = null;
            saveLogDraft(date);
        }, 800);
    }

    function bindAutosaveListeners() {
        document.querySelectorAll('.task-input, .extra-topic, #notes').forEach(field => {
            field.addEventListener('input', () => {
                if (isHydratingLog) return;
                scheduleAutosave(selectedDate);
            });
        });

        document.querySelectorAll('.completion-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                if (isHydratingLog) return;
                scheduleAutosave(selectedDate);
            });
        });
    }

    // Initialize Auto Grow
    initAutoGrow();
    // Final safety resize
    window.addEventListener('load', adjustAllHeights);
    setTimeout(adjustAllHeights, 200);

    // --- Daily Quote Logic ---
    const quotes = [
    "Read docs. Trust evidence.",
    "Think in systems, not hacks.",
    "Complexity is earned, not added.",
    "Write less code, solve more problems.",
    "Clarity is a superpower.",
    "Precision over noise.",
    "Own your fundamentals.",
    "Momentum loves consistency.",
    "Start ugly, finish strong.",
    "The keyboard rewards patience.",
    "Hard things become habits.",
    "Build evidence, not excuses.",
    "Every bug teaches architecture.",
    "Use friction as feedback.",
    "Discipline is compounding interest.",
    "You are one session away from progress.",
    "Mastery lives in repetition.",
    "Slow is smooth, smooth is fast.",
    "Optimize after understanding.",
    "Question assumptions early.",
    "Learning is a daily protocol.",
    "Guard your focus.",
    "Depth beats hype.",
    "Make the next action obvious.",
    "If it hurts, document it.",
    "Own your stack.",
    "Think in constraints.",
    "Do the boring things well.",
    "Aim for robust, not rushed.",
    "Consistency outlives intensity.",
    "Progress is logged, not guessed.",
    "Trust process over mood.",
    "Better questions, better code.",
    "Turn confusion into checklists.",
    "One focused hour beats four distracted.",
    "Learn deeply, execute calmly.",
    "Refine, don't randomize.",
    "Ship value every day.",
    "Simplicity scales.",

    "Trust is the first vulnerability.",
    "Humans are the real attack surface.",
    "Every system leaks somewhere.",
    "Control is a comforting illusion.",
    "Silence is operational security.",
    "Confidence hides weak engineering.",
    "Logs remember what people forget.",
    "Security begins where ego ends.",
    "Most exploits start with assumptions.",
    "The system behaves exactly as designed.",
    "Noise hides bad architecture.",
    "Automation exposes discipline.",
    "Good attackers study people first.",
    "Precision survives panic.",
    "Paranoia is pattern recognition.",
    "The cleanest exploit looks normal.",
    "People patch software, not behavior.",
    "Observation beats brute force.",
    "Obsession outlasts motivation.",
    "Assumptions are undocumented vulnerabilities.",

    "People always leave a backdoor.",
    "The world runs on code.",
    "Control is just an illusion.",
    "I don't trust systems. Or people.",
    "We're all living in someone else's script.",
    "The strongest firewall can't fix human nature.",
    "I don't hack machines. I hack assumptions.",
    "Hello, friend.",

    "Every system trusts something. That's where it breaks.",
    "Humans are the default vulnerability.",
    "Code never lies. People do.",
    "Security ends where assumptions begin.",
    "Most exploits start with trust.",
    "Firewalls block packets, not manipulation.",
    "The loudest people know the least.",
    "The system wasn't hacked. It behaved as designed."
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
    bindAutosaveListeners();
    
    // Reset daily checkboxes (Legacy logic)
    resetDailyCheckboxes(); 

    // AI suggestion box elements (global for page)
    const aiSuggestionBox = document.getElementById('ai-suggestion-box');
    const aiSuggestionText = document.getElementById('ai-suggestion-text');

    function setAISuggestionMessage(message) {
        if (aiSuggestionText) {
            aiSuggestionText.textContent = message;
        } else if (aiSuggestionBox) {
            let messageEl = aiSuggestionBox.querySelector('#ai-suggestion-text');
            if (!messageEl) {
                messageEl = document.createElement('p');
                messageEl.id = 'ai-suggestion-text';
                aiSuggestionBox.appendChild(messageEl);
            }
            messageEl.textContent = message;
        }
        if (aiSuggestionBox) {
            aiSuggestionBox.classList.remove('hidden');
        }
    }

    async function submitAIJob(endpoint, payload) {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (!res.ok) {
            throw new Error(result.error || 'Could not submit AI job.');
        }
        return result.job_id;
    }

    async function pollAIJob(jobId, messagePrefix, timeoutMs = 60000) {
        const startedAt = Date.now();
        while (Date.now() - startedAt < timeoutMs) {
            const res = await fetch(`/ai_job/${jobId}`);
            const result = await res.json();

            if (!res.ok) {
                throw new Error(result.error || 'Could not load AI job status.');
            }

            if (result.status === 'complete') {
                return `${messagePrefix}${result.suggestion || ''}`.trim();
            }

            if (result.status === 'failed') {
                throw new Error(result.error || 'AI job failed.');
            }

            setAISuggestionMessage('Generating AI response...');
            await new Promise(resolve => setTimeout(resolve, 1200));
        }

        throw new Error('AI request timed out. Please try again.');
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            await saveLogDraft(selectedDate);
            loadStreak();
        });
    }

    async function loadLogForDate(date) {
        isHydratingLog = true;
        setSkeletonState(true);
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

                    const data = tasks[topic];
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
                setStatusMessage('Loaded saved log.');
            } else {
                // Status is 'not found' -> New Day
                clearAllFields();
                setStatusMessage('Ready for a new day. 🚀');
            }
        } catch (err) {
            console.error('Log load error:', err);
            if (err.message.includes('404') || err instanceof SyntaxError) {
                 setStatusMessage('Ready for a new day. 🚀');
            } else {
                 setStatusMessage('Error loading log.');
            }
            // Even on error, ensure we have a clean state if it was a fetch failure
            // But maybe don't clear fields if it was just a network glitch? 
            // For safety, let's keep current fields if it wasn't a 404.
        } finally {
            isHydratingLog = false;
            setSkeletonState(false);
            // Always resize
            adjustAllHeights();
        }
    }
    
    function clearAllFields() {
        const previousHydrationState = isHydratingLog;
        isHydratingLog = true;

        try {
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
            // Hide and clear the AI suggestion box when resetting fields
            if (typeof aiSuggestionText !== 'undefined' && aiSuggestionText) aiSuggestionText.textContent = '';
            if (typeof aiSuggestionBox !== 'undefined' && aiSuggestionBox) aiSuggestionBox.classList.add('hidden');
        } finally {
            isHydratingLog = previousHydrationState;
        }
    }

    function getNextMilestone(streak) {
        const milestones = [
            {at: 3, name: 'Seedling'},
            {at: 7, name: 'On Fire'},
            {at: 15, name: 'Momentum'},
            {at: 30, name: 'Moonshot'},
            {at: 60, name: 'Champion'},
            {at: 90, name: 'Quarter'},
            {at: 180, name: 'Half Year'},
            {at: 270, name: '3 Quarters'},
            {at: 365, name: 'Legend'},
        ];
        const found = milestones.find(m => streak < m.at);
        return found ? { ...found, daysLeft: found.at - streak } : null;
    }

    function loadStreak() {
        fetch('/analytics_data')
            .then(r => r.json())
            .then(data => {
                const n = data.currentStreak || 0;
                const emoji = data.badge_emoji || '';
                const name  = data.badge_name  || '';
                const label = data.milestone_label;
                const tierText = name ? `${emoji} ${name}`.trim() : `${n} day${n !== 1 ? 's' : ''} streak`;
                const streakText = label ? `${tierText} · ${label}` : tierText;
                const next = getNextMilestone(n);

                const streakBadge = document.getElementById('streak-badge');
                if (streakBadge) {
                    const valueEl = streakBadge.querySelector('.streak-badge-value');
                    const metaEl = streakBadge.querySelector('.streak-badge-meta');
                    if (valueEl) {
                        valueEl.textContent = streakText;
                    } else {
                        streakBadge.textContent = streakText;
                    }
                    if (metaEl) {
                        metaEl.textContent = next ? `Next: ${next.name} in ${next.daysLeft} day${next.daysLeft !== 1 ? 's' : ''}` : 'Legend unlocked';
                    }
                    streakBadge.classList.remove('hidden');
                }

                const headerVal = document.getElementById('headerStreakValue');
                if (headerVal) headerVal.textContent = streakText;

                const subLabel = document.getElementById('streak-sublabel');
                if (subLabel) {
                    subLabel.textContent = next ? `Next: ${next.name} in ${next.daysLeft} day${next.daysLeft !== 1 ? 's' : ''}` : 'Max tier reached · Legend 🌟';
                }
            });
    }

    function resetDailyCheckboxes() {
        const today = new Date().toISOString().slice(0, 10);
        const lastResetDate = localStorage.getItem('last_daily_reset_date');

        if (lastResetDate !== today) {
            const dailyTasks = document.querySelectorAll('.completion-checkbox');
            dailyTasks.forEach(task => {
                task.checked = false;
                localStorage.removeItem(task.id);
            });
            localStorage.setItem('last_daily_reset_date', today);
        }
        document.querySelectorAll('.completion-checkbox').forEach(task => {
            const isChecked = localStorage.getItem(task.id) === 'true';
            task.checked = isChecked;
        });
    }

    // Create-topic handler (if the UI is present)
    const createTopicBtn = document.getElementById('create-topic-btn');
    if (createTopicBtn) {
        createTopicBtn.addEventListener('click', async () => {
            const nameEl = document.getElementById('new-topic-name');
            if (!nameEl) return;
            const name = nameEl.value.trim();
            if (!name) return alert('Please enter a topic name.');
            try {
                const res = await fetch('/topics', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name })
                });
                const data = await res.json();
                if (res.ok && data.status && (data.status === 'created' || data.status === 'exists')) {
                    // Reload to show the new topic
                    window.location.reload();
                } else {
                    alert('Could not create topic.');
                }
            } catch (err) {
                alert('Error creating topic.');
            }
        });
    }

    // Delete-topic handler (if dynamic topic cards are present)
    document.querySelectorAll('.delete-topic-button').forEach(button => {
        button.addEventListener('click', async () => {
            const topicId = button.dataset.topicId;
            const topicName = button.dataset.topicName || 'this topic';
            if (!topicId) return;

            const shouldDelete = confirm(`Delete "${topicName}"? This cannot be undone.`);
            if (!shouldDelete) return;

            button.disabled = true;
            const originalText = button.textContent;
            button.textContent = 'Deleting...';

            try {
                const res = await fetch(`/topics/${topicId}`, {
                    method: 'DELETE',
                });
                const data = await res.json().catch(() => ({}));

                if (!res.ok) {
                    throw new Error(data.error || 'Could not delete topic.');
                }

                const card = button.closest('.task-section');
                if (card) {
                    card.remove();
                }

                if (dailyLogEl && !dailyLogEl.querySelector('.task-section')) {
                    dailyLogEl.innerHTML = `
                        <div class="empty-state glass-panel">
                            <p class="panel-kicker">No topics yet</p>
                            <h3>Add your first topic to start logging</h3>
                            <p class="muted">Create a custom topic from the sidebar, then return here to capture your progress.</p>
                        </div>
                    `;
                }

                setStatusMessage('Topic deleted.', 'saved');
            } catch (err) {
                alert(err.message || 'Error deleting topic.');
                button.disabled = false;
                button.textContent = originalText;
            }
        });
    });

    // Handle AI buttons
    document.querySelectorAll('.ai-button').forEach(button => {
        button.addEventListener('click', async () => {
            const section = button.closest('.task-section');
            const input = section.querySelector('.task-input');
            const topic = button.dataset.topic;
            const learning = input.value;

            if (!learning) return alert('Please enter what you did first.');

            try {
                setAISuggestionMessage('Generating AI response...');
                const jobId = await submitAIJob('/get_suggestion', { topic, learning });
                const suggestion = await pollAIJob(jobId, '');
                setAISuggestionMessage(suggestion);
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

            if (input && input.value.trim()) {
                const shouldClear = confirm('This will clear your current draft for this topic. Continue?');
                if (!shouldClear) {
                    return;
                }
            }

            if (checkbox) {
                checkbox.checked = false;
                checkbox.dispatchEvent(new Event('change'));
            }
            if (input) input.value = '';

            try {
                setAISuggestionMessage('Generating AI response...');
                const jobId = await submitAIJob('/next_suggestion', { topic });
                const suggestion = await pollAIJob(jobId, '💡 Suggested: ');
                setAISuggestionMessage(suggestion);
                
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