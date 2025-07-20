// ctf_dashboard.js

const htbBoxes = [
    { name: "Lame", url: "https://app.hackthebox.com/machines/Lame" },
    { name: "Jerry", url: "https://app.hackthebox.com/machines/Jerry" },
    { name: "Blue", url: "https://app.hackthebox.com/machines/Blue" },
    { name: "Legacy", url: "https://app.hackthebox.com/machines/Legacy" },
    { name: "Optimum", url: "https://app.hackthebox.com/machines/Optimum" },
    { name: "Dancing", url: "https://app.hackthebox.com/machines/Dancing" },
    { name: "Bashed", url: "https://app.hackthebox.com/machines/Bashed" },
];

const banditLevels = 27;

function suggestHTBBox(completedBoxes) {
    const remaining = htbBoxes.filter(box => !completedBoxes.includes(box.name));
    if (remaining.length === 0) return { name: "All boxes completed!", url: "https://app.hackthebox.com/starting-point" };
    return remaining[Math.floor(Math.random() * remaining.length)];
}

function suggestBanditLevels(completedLevels) {
    const levelsLeft = [];
    for (let i = 0; i < banditLevels; i++) {
        if (!completedLevels.includes(i)) levelsLeft.push(i);
    }
    const todayLevels = levelsLeft.slice(0, 3);
    return todayLevels.map(lvl => ({
        level: lvl,
        url: `https://overthewire.org/wargames/bandit/bandit${lvl}.html`
    }));
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.suggest-btn').forEach(button => {
        button.addEventListener('click', () => {
            const topic = button.dataset.topic; 
            const outputDiv = document.getElementById(`${topic}-suggestion`); 

            if (!outputDiv) return;

            outputDiv.innerHTML = "<em>thinking...</em>";

            if (topic === 'htb') {
                fetch("/get_completed_htb")
                    .then(res => res.json())
                    .then(data => {
                        const suggestion = suggestHTBBox(data.completed || []);
                        outputDiv.innerHTML = `<a href="${suggestion.url}" target="_blank">💡 ${suggestion.name}</a>`;
                    }).catch(err => {
                        outputDiv.innerHTML = "Error fetching suggestion.";
                    });
            } else if (topic === 'bandit') {
                fetch("/get_completed_bandit")
                    .then(res => res.json())
                    .then(data => {
                        const suggestions = suggestBanditLevels(data.completed || []);
                        if (suggestions.length === 0) {
                             outputDiv.innerHTML = "All levels completed!";
                             return;
                        }
                        let listHtml = "<ul>";
                        suggestions.forEach(item => {
                            listHtml += `<li><a href='${item.url}' target='_blank'>Level ${item.level}</a></li>`;
                        });
                        listHtml += "</ul>";
                        outputDiv.innerHTML = listHtml;
                    }).catch(err => {
                        outputDiv.innerHTML = "Error fetching suggestion.";
                    });
            } else if (topic === 'python') {
                // Get the level from the button that was clicked
                const level = button.dataset.level;

                // Fetch a suggestion from the backend, now with the level
                fetch("/next_suggestion", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    // Add the level to the request body
                    body: JSON.stringify({ topic: 'python', level: level })
                })
                .then(res => res.json())
                .then(data => {
                    outputDiv.innerHTML = `💡 ${data.suggestion}`;
                }).catch(err => {
                    outputDiv.innerHTML = "Error fetching suggestion.";
                    console.error("Error:", err);
                });
            }
        });
    });
});