// static/tracker.js

window.toggleCompletion = function (container, event) {
    const checkbox = container.querySelector('input[type="checkbox"]');
    const section = container.closest('.task-section');

    if (event && event.target !== checkbox) {
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

document.addEventListener('DOMContentLoaded', () => {
    const calendarEl = document.getElementById('calendar');
    const currentDateEl = document.getElementById('current-date');
    const notesEl = document.getElementById('notes');
    const saveBtn = document.getElementById('save-log-btn');
    const statusMsgEl = document.getElementById('status-message');
    const streakBadgeEl = document.getElementById('streak-badge');
    const dailyLogEl = document.getElementById('daily-log');
    const workspaceGridEl = document.querySelector('.workspace-grid');
    const aiSuggestionBox = document.getElementById('ai-suggestion-box');
    const aiSuggestionText = document.getElementById('ai-suggestion-text');
    const createTopicBtn = document.getElementById('create-topic-btn');
    const isAuthenticated = document.body.dataset.authenticated === 'true';

    const autosaveStateByDate = new Map();
    let selectedDate = new Date().toISOString().slice(0, 10);
    let isHydratingLog = false;

    if (currentDateEl) currentDateEl.textContent = selectedDate;

    function setStatusMessage(message, state = '') {
        if (!statusMsgEl) return;
        statusMsgEl.textContent = message;
        if (state) {
            statusMsgEl.dataset.state = state;
        } else {
            delete statusMsgEl.dataset.state;
        }
    }

    function adjustAllHeights() {
        setTimeout(() => {
            document.querySelectorAll('.auto-grow').forEach((el) => {
                el.style.height = '5px';
                el.style.height = `${el.scrollHeight}px`;
            });
        }, 50);
    }

    function initAutoGrow() {
        document.querySelectorAll('.auto-grow').forEach((textarea) => {
            textarea.addEventListener('input', function () {
                this.style.height = '5px';
                this.style.height = `${this.scrollHeight}px`;
            });
        });
        adjustAllHeights();
    }

    function setSkeletonState(isLoading) {
        if (!workspaceGridEl) return;

        workspaceGridEl.classList.toggle('is-skeleton-loading', isLoading);

        const controls = workspaceGridEl.querySelectorAll(
            '#calendar, #new-topic-name, #notes, .task-input, .extra-topic, .completion-checkbox, #create-topic-btn, .ai-button, .suggest-today-button, .delete-topic-button, #save-log-btn'
        );

        controls.forEach((control) => {
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
        const tasks = {};
        const taskSections = document.querySelectorAll('.task-section');

        taskSections.forEach((section) => {
            const topic = section.dataset.topicName || section.querySelector('.ai-button')?.dataset.topic || '';
            const input = section.querySelector('.task-input')?.value || '';
            const done = section.querySelector('.completion-checkbox')?.checked || false;
            const extra = section.querySelector('.extra-topic')?.value || '';

            if (topic) {
                tasks[topic] = { task: input, done, extra };
            }
        });

        return {
            date,
            notes: notesEl ? notesEl.value : '',
            completed_tasks: tasks,
        };
    }

    async function saveLogDraft(date, showLoginPrompt = false) {
        if (!isAuthenticated) {
            if (showLoginPrompt) {
                alert('Please login first.');
            } else {
                setStatusMessage('Please login first.');
            }
            return;
        }

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

    function escapeHtml(text) {
        return String(text ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderEmptyDailyLog(message = 'Add a topic for the selected date.') {
        if (!dailyLogEl) return;
        dailyLogEl.innerHTML = `
            <div id="daily-log-empty" class="empty-state glass-panel">
                <p class="panel-kicker">No topics for this day yet</p>
                <h3>${escapeHtml(message)}</h3>
                <p class="muted">Use the topic field in the sidebar to add what you worked on today, or switch the calendar to view a different day.</p>
            </div>
        `;
    }

    function createTopicCard(topicName, data = {}) {
        const taskText = typeof data.task === 'string' ? data.task : '';
        const extraText = typeof data.extra === 'string' ? data.extra : '';
        const done = Boolean(data.done);
        const safeTopic = escapeHtml(topicName);

        const card = document.createElement('article');
        card.className = 'task-section topic-card';
        card.dataset.topicName = topicName;
        card.innerHTML = `
            <div class="task-head">
                <div>
                    <p class="panel-kicker">Topic</p>
                    <h3 class="task-title">${safeTopic}</h3>
                </div>
                <div class="completion-container" onclick="toggleCompletion(this, event)">
                    <input type="checkbox" class="completion-checkbox" aria-label="Mark ${safeTopic} task complete">
                    <span class="completion-pill">Complete</span>
                </div>
            </div>
            <textarea class="task-input theme-input auto-grow" placeholder="What ${safeTopic} did you practice?" rows="1">${escapeHtml(taskText)}</textarea>
            <div class="task-actions">
                <button class="ai-button" data-topic="${safeTopic}">Get AI suggestion</button>
                <button class="suggest-today-button" data-topic="${safeTopic}">What should I learn today?</button>
                <button type="button" class="delete-topic-button">Remove topic</button>
            </div>
            <textarea class="extra-topic theme-input mt-2 auto-grow" placeholder="Extra topic learned? (optional)" rows="1">${escapeHtml(extraText)}</textarea>
        `;

        const checkbox = card.querySelector('.completion-checkbox');
        const completion = card.querySelector('.completion-container');
        if (checkbox) checkbox.checked = done;
        if (completion) completion.classList.toggle('checked', done);
        card.classList.toggle('completed', done);
        return card;
    }

    function renderDailyLog(tasks = {}) {
        if (!dailyLogEl) return;

        const entries = Object.entries(tasks || {});
        dailyLogEl.innerHTML = '';

        if (!entries.length) {
            renderEmptyDailyLog();
            return;
        }

        entries.forEach(([topicName, data]) => {
            dailyLogEl.appendChild(createTopicCard(topicName, data || {}));
        });
    }

    function bindAutosaveListeners() {
        if (notesEl && !notesEl.dataset.autosaveBound) {
            notesEl.addEventListener('input', () => {
                if (isHydratingLog) return;
                scheduleAutosave(selectedDate);
            });
            notesEl.dataset.autosaveBound = 'true';
        }

        if (dailyLogEl && !dailyLogEl.dataset.autosaveBound) {
            dailyLogEl.addEventListener('input', (event) => {
                if (isHydratingLog) return;
                if (event.target.matches('.task-input, .extra-topic')) {
                    scheduleAutosave(selectedDate);
                }
            });

            dailyLogEl.addEventListener('change', (event) => {
                if (isHydratingLog) return;
                if (event.target.matches('.completion-checkbox')) {
                    scheduleAutosave(selectedDate);
                }
            });

            dailyLogEl.addEventListener('click', async (event) => {
                const removeButton = event.target.closest('.delete-topic-button');
                if (removeButton) {
                    const section = removeButton.closest('.task-section');
                    if (section) {
                        section.remove();
                        if (!dailyLogEl.querySelector('.task-section')) {
                            renderEmptyDailyLog();
                        }
                        setStatusMessage('Topic removed from this day.', 'saved');
                        scheduleAutosave(selectedDate);
                    }
                    return;
                }

                const aiButton = event.target.closest('.ai-button');
                if (aiButton) {
                    const section = aiButton.closest('.task-section');
                    const input = section?.querySelector('.task-input');
                    const topic = aiButton.dataset.topic;
                    const learning = input?.value || '';

                    if (!learning) return alert('Please enter what you did first.');

                    try {
                        setAISuggestionMessage('Generating AI response...');
                        const jobId = await submitAIJob('/get_suggestion', { topic, learning });
                        const suggestion = await pollAIJob(jobId, '');
                        setAISuggestionMessage(suggestion);
                    } catch (err) {
                        alert('Could not fetch AI suggestion.');
                    }
                    return;
                }

                const suggestButton = event.target.closest('.suggest-today-button');
                if (suggestButton) {
                    const section = suggestButton.closest('.task-section');
                    const topic = suggestButton.dataset.topic;
                    const input = section?.querySelector('.task-input');
                    const checkbox = section?.querySelector('.completion-checkbox');

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
                            input.style.height = `${input.scrollHeight}px`;
                        }
                    } catch (err) {
                        alert('Could not suggest task for today.');
                    }
                }
            });

            dailyLogEl.dataset.autosaveBound = 'true';
        }
    }

    async function loadLogForDate(date) {
        isHydratingLog = true;
        setSkeletonState(true);
        try {
            const res = await fetch(`/load_log/${date}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const result = await res.json();

            if (result.status === 'found') {
                renderDailyLog(result.tasks || {});
                if (notesEl) notesEl.value = result.notes || '';
                setStatusMessage('Loaded saved log.');
            } else {
                renderDailyLog({});
                if (notesEl) notesEl.value = '';
                setStatusMessage('Ready for a new day. 🚀');
            }
        } catch (err) {
            console.error('Log load error:', err);
            if (String(err.message).includes('404') || err instanceof SyntaxError) {
                renderDailyLog({});
                if (notesEl) notesEl.value = '';
                setStatusMessage('Ready for a new day. 🚀');
            } else {
                setStatusMessage('Error loading log.');
            }
        } finally {
            isHydratingLog = false;
            setSkeletonState(false);
            adjustAllHeights();
        }
    }

    function getNextMilestone(streak) {
        const milestones = [
            { at: 3, name: 'Seedling' },
            { at: 7, name: 'On Fire' },
            { at: 15, name: 'Momentum' },
            { at: 30, name: 'Moonshot' },
            { at: 60, name: 'Champion' },
            { at: 90, name: 'Quarter' },
            { at: 180, name: 'Half Year' },
            { at: 270, name: '3 Quarters' },
            { at: 365, name: 'Legend' },
        ];
        const found = milestones.find((milestone) => streak < milestone.at);
        return found ? { ...found, daysLeft: found.at - streak } : null;
    }

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
            body: JSON.stringify(payload),
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
            await new Promise((resolve) => setTimeout(resolve, 1200));
        }

        throw new Error('AI request timed out. Please try again.');
    }

    function loadStreak() {
        fetch('/analytics_data')
            .then((response) => response.json())
            .then((data) => {
                const n = data.currentStreak || 0;
                const emoji = data.badge_emoji || '';
                const name = data.badge_name || '';
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

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            await saveLogDraft(selectedDate, true);
            loadStreak();
        });
    }

    if (createTopicBtn) {
        createTopicBtn.addEventListener('click', async () => {
            const nameEl = document.getElementById('new-topic-name');
            if (!nameEl) return;

            const name = nameEl.value.trim();
            if (!name) return alert('Please enter a topic name.');
            if (!dailyLogEl) return;

            const duplicate = Array.from(dailyLogEl.querySelectorAll('.task-title')).some((titleEl) => {
                return titleEl.textContent.trim().toLowerCase() === name.toLowerCase();
            });

            if (duplicate) {
                alert('This topic already exists for the selected day.');
                return;
            }

            const emptyState = dailyLogEl.querySelector('#daily-log-empty');
            if (emptyState) emptyState.remove();

            const card = createTopicCard(name, {});
            dailyLogEl.appendChild(card);
            nameEl.value = '';
            setStatusMessage(`Added ${name} for this day.`, 'saved');
            bindAutosaveListeners();
            await saveLogDraft(selectedDate);
            adjustAllHeights();

            const taskInput = card.querySelector('.task-input');
            if (taskInput) taskInput.focus();
        });
    }

    if (calendarEl) {
        flatpickr(calendarEl, {
            dateFormat: 'Y-m-d',
            defaultDate: 'today',
            onChange: function (_, dateStr) {
                selectedDate = dateStr;
                if (currentDateEl) currentDateEl.textContent = dateStr;
                loadLogForDate(dateStr);
            },
        });
    }

    const quotes = [
        'Read docs. Trust evidence.',
        'Think in systems, not hacks.',
        'Complexity is earned, not added.',
        'Write less code, solve more problems.',
        'Clarity is a superpower.',
        'Precision over noise.',
        'Own your fundamentals.',
        'Momentum loves consistency.',
        'Start ugly, finish strong.',
        'The keyboard rewards patience.',
        'Hard things become habits.',
        'Build evidence, not excuses.',
        'Every bug teaches architecture.',
        'Use friction as feedback.',
        'Discipline is compounding interest.',
        'You are one session away from progress.',
        'Mastery lives in repetition.',
        'Slow is smooth, smooth is fast.',
        'Optimize after understanding.',
        'Question assumptions early.',
    ];
    const quoteEl = document.getElementById('daily-quote');
    if (quoteEl) {
        quoteEl.textContent = quotes[Math.floor(Math.random() * quotes.length)];
    }

    loadLogForDate(selectedDate);
    loadStreak();
    bindAutosaveListeners();
    initAutoGrow();
    window.addEventListener('load', adjustAllHeights);
    setTimeout(adjustAllHeights, 200);
});
