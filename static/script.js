let currentChatNumber = null;
let conversationsCache = [];
let adminsCache = [];
let masterAdminsCache = [];

document.addEventListener("DOMContentLoaded", () => {
    fetchLogs();
    fetchAdmins();
    fetchEnv();
    
    const messageInput = document.getElementById("messageInput");
    messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });
    
    // Paste Image Logic
    messageInput.addEventListener("paste", (e) => {
        const items = e.clipboardData.items;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf("image") !== -1) {
                const blob = items[i].getAsFile();
                if (blob) sendMediaFile(blob);
            }
        }
    });

    document.getElementById("searchInput").addEventListener("input", (e) => {
        filterChats(e.target.value);
    });

    // Emoji Picker Setup
    const emojiBtn = document.getElementById("emojiBtn");
    const emojiPickerContainer = document.getElementById("emojiPickerContainer");
    
    emojiBtn.addEventListener('click', () => {
        emojiPickerContainer.style.display = emojiPickerContainer.style.display === 'none' ? 'block' : 'none';
    });
    
    document.querySelector('emoji-picker').addEventListener('emoji-click', event => {
        messageInput.value += event.detail.unicode;
        emojiPickerContainer.style.display = 'none';
        messageInput.focus();
    });

    // Attach File Setup
    const attachBtn = document.getElementById("attachBtn");
    const mediaInput = document.getElementById("mediaInput");
    
    attachBtn.addEventListener('click', () => {
        mediaInput.click();
    });
    
    mediaInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            for (let i = 0; i < e.target.files.length; i++) {
                sendMediaFile(e.target.files[i]);
            }
            mediaInput.value = ""; // Reset
        }
    });
});

async function fetchLogs() {
    try {
        const response = await fetch('/api/dashboard/logs');
        const data = await response.json();
        conversationsCache = data.conversations;
        renderChatList(conversationsCache);
    } catch (e) {
        console.error("Erro ao buscar logs", e);
    }
}

function renderChatList(conversations) {
    const list = document.getElementById("chatList");
    list.innerHTML = "";
    
    conversations.forEach(conv => {
        const div = document.createElement("div");
        div.className = "chat-item";
        if (currentChatNumber === conv.id) div.classList.add("active");
        
        let lastMsg = "Nenhuma mensagem";
        if (conv.messages.length > 0) {
            lastMsg = conv.messages[conv.messages.length - 1].text;
        }

        div.innerHTML = `
            <img src="https://ui-avatars.com/api/?name=${conv.id}&background=random" class="avatar">
            <div class="chat-item-info">
                <div class="chat-item-title">${conv.id}</div>
                <div class="chat-item-preview">${lastMsg}</div>
            </div>
        `;
        div.onclick = () => openChat(conv.id);
        list.appendChild(div);
    });
}

function filterChats(query) {
    if (!query) {
        renderChatList(conversationsCache);
        return;
    }
    const filtered = conversationsCache.filter(c => c.id.includes(query));
    renderChatList(filtered);
}

function openChat(number) {
    currentChatNumber = number;
    document.getElementById("emptyChat").style.display = "none";
    document.getElementById("mainChat").style.display = "flex";
    
    document.getElementById("currentChatName").innerText = number;
    document.getElementById("currentChatAvatar").src = `https://ui-avatars.com/api/?name=${number}&background=random`;
    
    const conv = conversationsCache.find(c => c.id === number);
    const messagesContainer = document.getElementById("chatMessages");
    messagesContainer.innerHTML = "";
    
    if (conv) {
        conv.messages.forEach(msg => {
            const msgDiv = document.createElement("div");
            msgDiv.className = `message ${msg.fromMe ? 'out' : 'in'}`;
            
            const time = new Date(msg.timestamp * 1000);
            const timeStr = time.getHours().toString().padStart(2, '0') + ':' + time.getMinutes().toString().padStart(2, '0');
            
            let contentHtml = msg.text;
            if (msg.type && msg.type.startsWith("media_")) {
                if (msg.type === "media_image") {
                    contentHtml = `<img src="${msg.text}" style="max-width: 100%; border-radius: 8px;">`;
                } else if (msg.type === "media_video") {
                    contentHtml = `<video src="${msg.text}" controls style="max-width: 100%; border-radius: 8px;"></video>`;
                } else if (msg.type === "media_audio") {
                    contentHtml = `<audio src="${msg.text}" controls style="max-width: 100%;"></audio>`;
                } else {
                    contentHtml = `<a href="${msg.text}" target="_blank" style="color: #60a5fa;"><i class="fas fa-file"></i> Ver Arquivo</a>`;
                }
            }

            msgDiv.innerHTML = `
                ${contentHtml}
                <span class="message-time">${timeStr}</span>
            `;
            messagesContainer.appendChild(msgDiv);
        });
    }
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Atualiza a seleção visual
    document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
    renderChatList(conversationsCache); // Re-render to show active
}

function toggleNewChat() {
    const container = document.getElementById("newChatContainer");
    container.style.display = container.style.display === "none" ? "flex" : "none";
}

function startNewChat() {
    const num = document.getElementById("newChatInput").value.trim();
    if (num) {
        // Se já existir na lista, abre. Senão, cria uma estrutura vazia localmente
        if (!conversationsCache.find(c => c.id === num)) {
            conversationsCache.unshift({id: num, name: num, messages: [], last_timestamp: Date.now()/1000});
            renderChatList(conversationsCache);
        }
        openChat(num);
        document.getElementById("newChatInput").value = "";
        toggleNewChat();
    }
}

async function sendMessage() {
    if (!currentChatNumber) return;
    
    const input = document.getElementById("messageInput");
    const text = input.value.trim();
    
    if (!text) return;
    
    try {
        const response = await fetch('/api/dashboard/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ number: currentChatNumber, text: text })
        });
        
        if (response.ok) {
            input.value = "";
            // Add locally to UI
            let conv = conversationsCache.find(c => c.id === currentChatNumber);
            if(conv) {
                conv.messages.push({
                    text: text,
                    fromMe: true,
                    timestamp: Date.now() / 1000
                });
                openChat(currentChatNumber);
            }
        } else {
            alert("Erro ao enviar mensagem!");
        }
    } catch (e) {
        console.error(e);
        alert("Erro de conexão!");
    }
}

async function sendMediaFile(file) {
    if (!currentChatNumber) {
        alert("Selecione um contato primeiro.");
        return;
    }
    
    const formData = new FormData();
    formData.append("number", currentChatNumber);
    formData.append("file", file);
    
    try {
        const response = await fetch('/api/dashboard/send_media', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Add locally to UI
            let conv = conversationsCache.find(c => c.id === currentChatNumber);
            if(conv) {
                let mType = "media_unknown";
                if(file.type.startsWith("image/")) mType = "media_image";
                else if(file.type.startsWith("video/")) mType = "media_video";
                else if(file.type.startsWith("audio/")) mType = "media_audio";
                else mType = "media_document";
                
                conv.messages.push({
                    text: `/media/${data.file}`,
                    fromMe: true,
                    timestamp: Date.now() / 1000,
                    type: mType
                });
                openChat(currentChatNumber);
            }
        } else {
            alert("Erro ao enviar arquivo!");
        }
    } catch(e) {
        console.error(e);
        alert("Erro de conexão ao enviar mídia.");
    }
}

// ================= ADMIN PANEL =================
function toggleAdminPanel() {
    const panel = document.getElementById("adminPanel");
    panel.classList.toggle("active");
}

async function fetchAdmins() {
    try {
        const res = await fetch('/api/dashboard/admins');
        const data = await res.json();
        adminsCache = data.admins;
        masterAdminsCache = data.master_admins || [];
        renderAdmins();
        renderMasterAdmins();
    } catch(e) { console.error(e); }
}

function renderMasterAdmins() {
    const list = document.getElementById("masterAdminList");
    list.innerHTML = "";
    
    masterAdminsCache.forEach((admin) => {
        const div = document.createElement("div");
        div.className = "admin-badge";
        div.innerHTML = `
            <span>${admin}</span>
            <i class="fas fa-trash remove-btn" onclick="removeMasterAdmin('${admin}')"></i>
        `;
        list.appendChild(div);
    });
}

function renderAdmins() {
    const list = document.getElementById("adminList");
    list.innerHTML = "";
    
    adminsCache.forEach((admin) => {
        const div = document.createElement("div");
        div.className = "admin-badge";
        div.innerHTML = `
            <span>${admin}</span>
            <i class="fas fa-trash remove-btn" onclick="removeAdmin('${admin}')"></i>
        `;
        list.appendChild(div);
    });
}

async function updateAdminsAPI() {
    try {
        await fetch('/api/dashboard/admins', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ admins: adminsCache, master_admins: masterAdminsCache })
        });
    } catch(e) { alert("Erro ao salvar admins"); }
}

function addMasterAdmin() {
    const input = document.getElementById("newMasterAdminInput");
    const num = input.value.trim();
    if (num && !masterAdminsCache.includes(num)) {
        masterAdminsCache.push(num);
        input.value = "";
        renderMasterAdmins();
        updateAdminsAPI();
    }
}

function removeMasterAdmin(num) {
    if (confirm(`Remover ${num} dos MASTER administradores?`)) {
        masterAdminsCache = masterAdminsCache.filter(a => a !== num);
        renderMasterAdmins();
        updateAdminsAPI();
    }
}

function addAdmin() {
    const input = document.getElementById("newAdminInput");
    const num = input.value.trim();
    if (num && !adminsCache.includes(num)) {
        adminsCache.push(num);
        input.value = "";
        renderAdmins();
        updateAdminsAPI();
    }
}

function removeAdmin(num) {
    if (confirm(`Remover ${num} dos administradores padrão?`)) {
        adminsCache = adminsCache.filter(a => a !== num);
        renderAdmins();
        updateAdminsAPI();
    }
}

// ================= ENV EDITOR =================
async function fetchEnv() {
    try {
        const res = await fetch('/api/dashboard/env');
        const data = await res.json();
        document.getElementById("envEditor").value = data.env_content;
    } catch(e) { console.error(e); }
}

async function saveEnv() {
    const content = document.getElementById("envEditor").value;
    try {
        const res = await fetch('/api/dashboard/env', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ env_content: content })
        });
        if (res.ok) {
            alert("Credenciais salvas com sucesso! (Reinicie o main.py para aplicar tudo)");
        } else {
            alert("Erro ao salvar credenciais.");
        }
    } catch(e) {
        alert("Erro de conexão.");
    }
}
