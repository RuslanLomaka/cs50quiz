document.addEventListener('DOMContentLoaded', () => {
    // Navigation buttons
    document.querySelector('#inbox').addEventListener('click', (e) => {
        e.target.blur();
        showMailbox('inbox', true);
    });
    document.querySelector('#sent').addEventListener('click', (e) => {
        e.target.blur();
        showMailbox('sent', true);
    });
    document.querySelector('#archived').addEventListener('click', (e) => {
        e.target.blur();
        showMailbox('archived', true);
    });
    document.querySelector('#compose').addEventListener('click', (e) => {
        e.target.blur();
        newMessage(true);
    });

    // Compose form submit
    document.querySelector('#compose-form').addEventListener('submit', sendMessage);

    // Browser back/forward navigation
    window.onpopstate = (event) => {
        if (event.state) {
            if (event.state.view === 'mailbox') {
                showMailbox(event.state.name, false);
            } else if (event.state.view === 'compose') {
                newMessage(false);
            } else if (event.state.view === 'detail') {
                viewMessage(event.state.id, event.state.folder, false);
            }
        } else {
            showMailbox('inbox', false);
        }
    };

    // Initial load: respect URL hash
    loadInitialView();
});

/* ===== Handle initial view from URL hash ===== */
function loadInitialView() {
    const hash = location.hash;

    if (hash === '#compose') {
        newMessage(false);
    } else if (hash === '#sent') {
        showMailbox('sent', false);
    } else if (hash === '#archived') {
        showMailbox('archived', false);
    } else if (hash.startsWith('#inbox')) {
        showMailbox('inbox', false);
    } else {
        // default if no hash
        showMailbox('inbox', true);
    }
}

/* ===== Compose a new message ===== */
function newMessage(push = false) {
    toggleView('compose');
    setActiveNav('compose');

    // Reset form fields
    document.querySelector('#compose-recipients').value = '';
    document.querySelector('#compose-subject').value = '';
    document.querySelector('#compose-body').value = '';

    if (push) {
        history.pushState({ view: 'compose' }, '', '#compose');
    }
}

/* ===== Show mailbox (Inbox, Sent, Archived) ===== */
async function showMailbox(name, push = false) {
    toggleView('list');
    setActiveNav(name);

    const listView = document.querySelector('#emails-view');
    listView.innerHTML = `<h3>${name[0].toUpperCase() + name.slice(1)}</h3>`;

    // Backend expects "archive" instead of "archived"
    const apiName = (name === 'archived') ? 'archive' : name;
    const resp = await fetch(`/emails/${apiName}`);
    const msgs = await resp.json();

    if (msgs.length === 0) {
        listView.innerHTML += `<p class="empty-msg">Nothing here yet.</p>`;
    } else {
        msgs.forEach(msg => {
            const row = document.createElement('div');
            row.classList.add('email-row', msg.read ? 'read' : 'unread');

            const toStr = Array.isArray(msg.recipients) ? msg.recipients.join(', ') : msg.recipients;
            const senderOrTo = name === 'sent' ? toStr : msg.sender;

            row.innerHTML = `
                <span class="email-meta"><strong>${senderOrTo}</strong> — ${msg.subject} — ${msg.timestamp}</span>
                <span class="email-actions">
                    ${name !== 'sent'
                ? `<button class="archive-btn">${msg.archived ? 'Unarchive' : 'Archive'}</button>`
                : ''}
                    ${name !== 'sent'
                ? `<button class="read-btn">${msg.read ? 'Mark Unread' : 'Mark Read'}</button>`
                : ''}
                </span>
            `;

            const archBtn = row.querySelector('.archive-btn');
            if (archBtn) {
                archBtn.addEventListener('click', async (ev) => {
                    ev.stopPropagation();
                    row.classList.add('fade-out');
                    row.addEventListener('animationend', async () => {
                        await updateArchive(msg.id, !msg.archived);
                        // SPEC: After archiving/unarchiving, load Inbox
                        showMailbox('inbox', true);
                    }, { once: true });
                });
            }

            const readBtn = row.querySelector('.read-btn');
            if (readBtn) {
                readBtn.addEventListener('click', async (ev) => {
                    ev.stopPropagation();
                    await updateRead(msg.id, !msg.read);
                    showMailbox(name, false);
                });
            }

            row.addEventListener('click', (ev) => {
                if (ev.target.closest('button')) return;
                viewMessage(msg.id, name, true);
            });

            listView.appendChild(row);
        });
    }

    if (push) {
        history.pushState({ view: 'mailbox', name }, '', `#${name}`);
    }
}

/* ===== Send a new message ===== */
async function sendMessage(ev) {
    ev.preventDefault();

    const to = document.querySelector('#compose-recipients').value.trim();
    const subj = document.querySelector('#compose-subject').value.trim();
    const body = document.querySelector('#compose-body').value.trim();

    if (!to) {
        alert("Recipient cannot be empty.");
        return;
    }

    const resp = await fetch('/emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipients: to, subject: subj, body })
    });

    const info = await resp.json();
    if (info.error) {
        alert(info.error);
        return;
    }
    showMailbox('sent', true);
}

/* ===== View a single email ===== */
async function viewMessage(id, folder, push = false) {
    const resp = await fetch(`/emails/${id}`);
    const mail = await resp.json();

    if (!mail.read) {
        await fetch(`/emails/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ read: true })
        });
    }

    toggleView('detail');
    setActiveNav(null);

    const detail = document.querySelector('#email-view');
    detail.innerHTML = `
        <h3>${mail.subject}</h3>
        <p><strong>From:</strong> ${mail.sender}</p>
        <p><strong>To:</strong> ${Array.isArray(mail.recipients) ? mail.recipients.join(', ') : mail.recipients}</p>
        <p><strong>Timestamp:</strong> ${mail.timestamp}</p>
        <button class="reply-btn">Reply</button>
        <hr>
        <pre class="email-body">${mail.body}</pre>
    `;

    const replyBtn = detail.querySelector('.reply-btn');
    replyBtn.addEventListener('click', () => {
        newMessage(true);
        document.querySelector('#compose-recipients').value = mail.sender;

        let subj = mail.subject;
        if (!subj.startsWith("Re:")) subj = "Re: " + subj;
        document.querySelector('#compose-subject').value = subj;

        const bodyField = document.querySelector('#compose-body');
        bodyField.value =
            `On ${mail.timestamp}, ${mail.sender} wrote:\n${mail.body}\n___\n`;
        bodyField.focus(); // autofocus when replying
    });

    if (push) {
        history.pushState({ view: 'detail', id, folder }, '', `#${folder}/${id}`);
    }
}

/* ===== Helpers ===== */
function toggleView(which) {
    document.querySelector('#emails-view').style.display = (which === 'list') ? 'block' : 'none';
    document.querySelector('#compose-view').style.display = (which === 'compose') ? 'block' : 'none';
    document.querySelector('#email-view').style.display = (which === 'detail') ? 'block' : 'none';
}

function setActiveNav(activeId) {
    document.querySelectorAll('#inbox, #sent, #archived, #compose').forEach(btn => {
        btn.classList.remove('active');
    });
    if (activeId) {
        const el = document.querySelector(`#${activeId}`);
        if (el) el.classList.add('active');
    }
}

async function updateArchive(id, state) {
    await fetch(`/emails/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archived: state })
    });
}

async function updateRead(id, state) {
    await fetch(`/emails/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read: state })
    });
}
