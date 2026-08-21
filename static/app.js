/* LLM Wiki - Frontend Application Logic */

document.addEventListener("DOMContentLoaded", () => {
    // Auto-resize chat textarea
    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
        chatInput.addEventListener("input", function() {
            this.style.height = "auto";
            this.style.height = (this.scrollHeight) + "px";
        });

        chatInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submitQuery();
            }
        });
    }

    // Drag and drop for upload
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    if (dropzone && fileInput) {
        dropzone.addEventListener("click", () => fileInput.click());

        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.remove("dragover");
            });
        });

        dropzone.addEventListener("drop", (e) => {
            const files = e.dataTransfer.files;
            if (files.length) {
                fileInput.files = files;
                handleFileUpload(files);
            }
        });

        fileInput.addEventListener("change", (e) => {
            if (fileInput.files.length) {
                handleFileUpload(fileInput.files);
            }
        });
    }
});

// Simple Markdown Formatter Helper
function renderMarkdown(text) {
    if (!text) return "";
    let html = text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="#" onclick="openWikiModal(\'$2\'); return false;" class="citation-tag">📄 $1</a>')
        .replace(/\n\n/g, '<br/><br/>');
    return html;
}

// Chat Functionality
async function submitQuery() {
    const input = document.getElementById("chat-input");
    const messagesContainer = document.getElementById("chat-messages");
    if (!input || !messagesContainer) return;

    const query = input.value.trim();
    if (!query) return;

    // Append User Message
    const userBubble = document.createElement("div");
    userBubble.className = "chat-bubble user";
    userBubble.innerHTML = `
        <div class="avatar user">Vous</div>
        <div class="bubble-content">${escapeHtml(query)}</div>
    `;
    messagesContainer.appendChild(userBubble);

    input.value = "";
    input.style.height = "auto";
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Append Assistant Loading Bubble
    const assistantBubble = document.createElement("div");
    assistantBubble.className = "chat-bubble assistant";
    assistantBubble.innerHTML = `
        <div class="avatar assistant">LLM</div>
        <div class="bubble-content">
            <div class="loading-spinner">🧠 Consultation et synthèse du Wiki en cours...</div>
        </div>
    `;
    messagesContainer.appendChild(assistantBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();

        if (data.error) {
            assistantBubble.querySelector(".bubble-content").innerHTML = `<span style="color: #ef4444;">❌ Erreur: ${escapeHtml(data.error)}</span>`;
        } else {
            let answerHtml = renderMarkdown(data.answer);

            // Render citations
            let citationsHtml = "";
            if (data.relevant_files && data.relevant_files.length) {
                citationsHtml = '<div class="citations-container"><strong style="font-size: 0.8rem; color: var(--text-muted);">Pages référencées :</strong> ';
                citationsHtml += data.relevant_files.map(f => `<a href="#" onclick="openWikiModal('${f}'); return false;" class="citation-tag">🔗 ${f}</a>`).join(" ");
                citationsHtml += '</div>';
            }

            // Save synthesis button
            const saveBtnHtml = `
                <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-color);">
                    <button onclick="saveCurrentSynthesis('${escapeQuotes(query)}', this)" class="btn btn-secondary btn-sm">
                        💾 Enregistrer cette synthèse dans le Wiki
                    </button>
                    <span class="save-status" style="margin-left: 10px; font-size: 0.8rem; color: #10b981;"></span>
                </div>
            `;

            assistantBubble.querySelector(".bubble-content").innerHTML = answerHtml + citationsHtml + saveBtnHtml;
            
            // Save answer dataset on element for synthesis filing
            assistantBubble.querySelector(".bubble-content").dataset.answerContent = data.answer;
        }
    } catch (err) {
        assistantBubble.querySelector(".bubble-content").innerHTML = `<span style="color: #ef4444;">❌ Erreur de connexion au serveur API.</span>`;
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// File Synthesis Back into Wiki
async function saveCurrentSynthesis(queryTitle, buttonEl) {
    const bubbleContent = buttonEl.closest(".bubble-content");
    const content = bubbleContent.dataset.answerContent || "";
    const statusSpan = bubbleContent.querySelector(".save-status");

    if (!content) return;

    buttonEl.disabled = true;
    buttonEl.innerText = "Enregistrement...";

    try {
        const response = await fetch("/api/save-synthesis", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: queryTitle, content: content })
        });
        const data = await response.json();

        if (data.success) {
            buttonEl.innerText = "✓ Enregistré";
            if (statusSpan) statusSpan.innerText = data.message;
        } else {
            buttonEl.disabled = false;
            buttonEl.innerText = "Réessayer";
            alert("Erreur lors de l'enregistrement : " + data.error);
        }
    } catch (e) {
        buttonEl.disabled = false;
        buttonEl.innerText = "Réessayer";
        alert("Erreur réseau : " + e);
    }
}

// File Upload Handler
async function handleFileUpload(files) {
    const statusDiv = document.getElementById("upload-status");
    if (!statusDiv) return;

    statusDiv.innerHTML = `<div style="color: var(--secondary);">Téléversement de ${files.length} fichier(s) en cours...</div>`;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (data.success) {
            let msg = `<div style="color: #10b981; font-weight: 600;">✓ Téléversement réussi (${data.saved_files.length} fichier(s) enregistrés dans /sources)</div>`;
            if (data.errors.length) {
                msg += `<div style="color: #ef4444;">${data.errors.join("<br>")}</div>`;
            }
            statusDiv.innerHTML = msg;
            reloadSourcesList();
        } else {
            statusDiv.innerHTML = `<div style="color: #ef4444;">❌ Erreur: ${data.error}</div>`;
        }
    } catch (e) {
        statusDiv.innerHTML = `<div style="color: #ef4444;">❌ Erreur réseau lors du téléversement.</div>`;
    }
}

// Trigger Ingestion from Web UI
async function triggerIngestion() {
    const resultDiv = document.getElementById("ingestion-result");
    const btn = document.getElementById("btn-ingest");
    if (!resultDiv || !btn) return;

    btn.disabled = true;
    btn.innerHTML = `⏳ Ingestion incrémentale en cours...`;
    resultDiv.innerHTML = `<div style="color: var(--secondary);">🧠 Le LLM analyse les nouveaux documents dans /sources et met à jour le wiki...</div>`;

    try {
        const response = await fetch("/api/ingest", { method: "POST" });
        const data = await response.json();

        if (data.success) {
            if (data.count > 0) {
                resultDiv.innerHTML = `
                    <div style="color: #10b981; font-weight: 600;">
                        ✅ Ingestion terminée ! ${data.count} source(s) traitée(s) :
                        <ul>${data.ingested_files.map(f => `<li>${f}</li>`).join("")}</ul>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `<div style="color: var(--text-muted);">ℹ️ Aucune nouvelle source ou modification détectée dans /sources.</div>`;
            }
        } else {
            resultDiv.innerHTML = `<div style="color: #ef4444;">❌ Erreur lors de l'ingestion: ${data.error}</div>`;
        }
    } catch (e) {
        resultDiv.innerHTML = `<div style="color: #ef4444;">❌ Erreur réseau pendant l'ingestion.</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `🚀 Démarrer l'ingestion incrémentale`;
    }
}

// Reload Sources list in Upload Page
async function reloadSourcesList() {
    const listEl = document.getElementById("sources-list");
    if (!listEl) return;

    try {
        const response = await fetch("/api/status");
        const data = await response.json();
        if (data.sources_list) {
            listEl.innerHTML = data.sources_list.map(s => `<li style="padding: 6px 0; border-bottom: 1px solid var(--border-color);">📄 ${s}</li>`).join("");
        }
    } catch (e) {}
}

// Admin Page Functions
async function runLintCheck() {
    const reportDiv = document.getElementById("lint-report");
    if (!reportDiv) return;

    reportDiv.innerHTML = `<div style="color: var(--secondary);">🔍 Audit de santé en cours par le LLM...</div>`;

    try {
        const response = await fetch("/api/lint", { method: "POST" });
        const data = await response.json();

        if (data.success) {
            reportDiv.innerHTML = renderMarkdown(data.report);
        } else {
            reportDiv.innerHTML = `<div style="color: #ef4444;">❌ Erreur: ${data.error}</div>`;
        }
    } catch (e) {
        reportDiv.innerHTML = `<div style="color: #ef4444;">❌ Erreur lors de l'audit.</div>`;
    }
}

async function triggerReset(hard = false) {
    const msg = hard 
        ? "⚠️ ATTENTION : Êtes-vous sûr de vouloir tout supprimer (Pages Wiki + Documents Sources) ?" 
        : "⚠️ Êtes-vous sûr de vouloir réinitialiser les pages et le log du Wiki ?";

    if (!confirm(msg)) return;

    try {
        const response = await fetch("/api/reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ hard: hard })
        });
        const data = await response.json();

        if (data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert("Erreur: " + data.error);
        }
    } catch (e) {
        alert("Erreur réseau: " + e);
    }
}

// Wiki Modal View
async function openWikiModal(filename) {
    try {
        const response = await fetch(`/api/wiki-page/${encodeURIComponent(filename)}`);
        const data = await response.json();

        if (data.content) {
            const modal = document.getElementById("wiki-modal");
            const modalTitle = document.getElementById("modal-title");
            const modalBody = document.getElementById("modal-body");

            if (modal && modalTitle && modalBody) {
                modalTitle.innerText = filename;
                modalBody.innerHTML = renderMarkdown(data.content);
                modal.style.display = "flex";
            }
        } else {
            alert("Impossible de charger la page : " + (data.error || "Non trouvée"));
        }
    } catch (e) {
        alert("Erreur lors de la lecture de la page : " + e);
    }
}

function closeWikiModal() {
    const modal = document.getElementById("wiki-modal");
    if (modal) modal.style.display = "none";
}

// Utilities
function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeQuotes(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}
