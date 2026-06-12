let newChallengeModal;

document.addEventListener('DOMContentLoaded', function() {
    newChallengeModal = new bootstrap.Modal(document.getElementById('newChallengeModal'));
    loadReceivedChallenges();
});

function getToken() {
    return localStorage.getItem('token');
}

function getCurrentUserId() {
    const token = getToken();
    if (!token) return null;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return parseInt(payload.sub);
    } catch {
        return null;
    }
}

async function loadReceivedChallenges() {
    const token = getToken();
    if (!token) { window.location.href = '/login?redirect=/pvp'; return; }

    try {
        const response = await fetch('/api/pvp/received', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const bets = await response.json();

        const pendingCount = bets.filter(b => b.status === 'pending').length;
        const badge = document.getElementById('received-count');
        badge.textContent = pendingCount;
        badge.style.display = pendingCount > 0 ? 'inline' : 'none';

        renderBets(bets, 'received-list', 'received');
    } catch (error) {
        showToast('Erro', 'Erro ao carregar desafios', 'danger');
    }
}

async function loadSentChallenges() {
    const token = getToken();
    try {
        const response = await fetch('/api/pvp/sent', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const bets = await response.json();
        renderBets(bets, 'sent-list', 'sent');
    } catch (error) {
        showToast('Erro', 'Erro ao carregar desafios', 'danger');
    }
}

async function loadActiveBets() {
    const token = getToken();
    try {
        const response = await fetch('/api/pvp/active', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const bets = await response.json();
        renderBets(bets, 'active-list', 'active');
    } catch (error) {
        showToast('Erro', 'Erro ao carregar apostas', 'danger');
    }
}

async function loadHistory() {
    const token = getToken();
    try {
        const response = await fetch('/api/pvp/history', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const bets = await response.json();
        renderBets(bets, 'history-list', 'history');
    } catch (error) {
        showToast('Erro', 'Erro ao carregar histórico', 'danger');
    }
}

function renderBets(bets, containerId, context) {
    const container = document.getElementById(containerId);

    if (bets.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="bi bi-inbox display-1 text-muted"></i>
                <p class="mt-3 text-muted">Nenhum desafio encontrado</p>
            </div>`;
        return;
    }

    container.innerHTML = bets.map(bet => createChallengeCard(bet, context)).join('');
}

function createChallengeCard(bet, context) {
    const statusConfig = {
        'pending': { badge: 'bg-warning', icon: 'bi-hourglass-split', text: 'Pendente' },
        'accepted': { badge: 'bg-success', icon: 'bi-check-circle', text: 'Aceita' },
        'rejected': { badge: 'bg-danger', icon: 'bi-x-circle', text: 'Recusada' },
        'cancelled': { badge: 'bg-secondary', icon: 'bi-ban', text: 'Cancelada' },
        'completed': { badge: 'bg-primary', icon: 'bi-trophy', text: 'Finalizada' },
        'expired': { badge: 'bg-dark', icon: 'bi-clock', text: 'Expirada' }
    };

    const status = statusConfig[bet.status] || statusConfig['pending'];
    const isReceived = context === 'received';
    const isPending = bet.status === 'pending';
    const isSentPending = context === 'sent' && isPending;

    const opponentName = isReceived ? bet.challenger_name : bet.challenged_name;
    const opponentLabel = isReceived ? 'Desafiado por' : 'Desafiado';

    let betDescription = '';
    if (bet.bet_type === 'match' && bet.match) {
        betDescription = `${bet.match.team_a} x ${bet.match.team_b}`;
    } else if (bet.bet_type === 'round') {
        betDescription = `Rodada ${bet.round_number}`;
    } else {
        betDescription = 'Campeonato';
    }

    let resultHtml = '';
    if (bet.status === 'completed') {
        const isWinner = bet.winner_id === getCurrentUserId();
        const isTie = !bet.winner_id;
        if (isTie) {
            resultHtml = '<div class="alert alert-info mt-2 py-1"><i class="bi bi-hand-thumbs-up me-2"></i>Empate!</div>';
        } else if (isWinner) {
            resultHtml = '<div class="alert alert-success mt-2 py-1"><i class="bi bi-trophy me-2"></i>Você Venceu!</div>';
        } else {
            resultHtml = '<div class="alert alert-secondary mt-2 py-1"><i class="bi bi-emoji-frown me-2"></i>Você Perdeu</div>';
        }
    }

    let actionsHtml = '';
    if (isReceived && isPending) {
        actionsHtml = `
            <div class="d-grid gap-2 d-md-flex mt-3">
                <button class="btn btn-success btn-sm flex-fill" onclick="respondChallenge(${bet.id}, 'accept')">
                    <i class="bi bi-check-lg me-1"></i>Aceitar
                </button>
                <button class="btn btn-outline-danger btn-sm flex-fill" onclick="respondChallenge(${bet.id}, 'reject')">
                    <i class="bi bi-x-lg me-1"></i>Recusar
                </button>
            </div>`;
    } else if (isSentPending) {
        actionsHtml = `
            <div class="mt-3">
                <button class="btn btn-outline-danger btn-sm" onclick="cancelChallenge(${bet.id})">
                    <i class="bi bi-trash me-1"></i>Cancelar
                </button>
            </div>`;
    }

    return `
        <div class="col-md-6 col-lg-4">
            <div class="card h-100 ${bet.status === 'completed' && bet.winner_id === getCurrentUserId() ? 'border-success' : ''}">
                <div class="card-header d-flex justify-content-between align-items-center py-2">
                    <span class="badge ${status.badge} small">
                        <i class="bi ${status.icon} me-1"></i>${status.text}
                    </span>
                    <small class="text-muted">#${bet.id}</small>
                </div>
                <div class="card-body">
                    <small class="text-muted">${opponentLabel}</small>
                    <h5 class="card-title mb-2">${opponentName}</h5>
                    <span class="badge bg-info mb-2">${betDescription}</span>
                    <div class="d-flex align-items-center">
                        <i class="bi bi-gift text-warning me-2"></i>
                        <span class="fw-bold">${bet.prize_description}</span>
                    </div>
                    ${resultHtml}
                    ${actionsHtml}
                </div>
                <div class="card-footer text-muted small py-2">
                    ${isPending ? `Expira: ${formatDateTimeBR(bet.expires_at)}` : `Criado: ${formatDateBR(bet.created_at)}`}
                </div>
            </div>
        </div>`;
}

async function searchUsers() {
    const query = document.getElementById('userSearch').value.trim();
    if (query.length < 2) return;

    const token = getToken();
    try {
        const response = await fetch(`/api/pvp/users/search?query=${encodeURIComponent(query)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const users = await response.json();

        const resultsDiv = document.getElementById('userResults');
        resultsDiv.innerHTML = users.map(u => `
            <button type="button" class="list-group-item list-group-item-action py-2"
                    onclick="selectUser(${u.id}, '${u.full_name}')">
                <div class="fw-bold">${u.full_name}</div>
                <small class="text-muted">${u.email}</small>
            </button>
        `).join('');
    } catch (error) {
        console.error('Error:', error);
    }
}

function selectUser(id, name) {
    document.getElementById('challengedId').value = id;
    document.getElementById('selectedUser').innerHTML = `<i class="bi bi-person-check me-2"></i><strong>${name}</strong>`;
    document.getElementById('selectedUser').classList.remove('d-none');
    document.getElementById('userResults').innerHTML = '';
}

function onBetTypeChange() {
    const type = document.getElementById('betType').value;
    document.getElementById('matchSelectDiv').classList.toggle('d-none', type !== 'match');
    document.getElementById('roundSelectDiv').classList.toggle('d-none', type !== 'round');

    if (type === 'match') loadAvailableMatches();
    if (type === 'round') loadAvailableRounds();
}

async function loadAvailableMatches() {
    const token = getToken();
    try {
        const response = await fetch('/api/pvp/available-matches', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const matches = await response.json();
        document.getElementById('matchId').innerHTML = matches.map(m => `
            <option value="${m.id}">${m.team_a} x ${m.team_b} - ${formatDateBR(m.match_date)}</option>
        `).join('');
    } catch (error) {
        console.error('Error loading matches:', error);
    }
}

async function loadAvailableRounds() {
    const token = getToken();
    try {
        const response = await fetch('/api/pvp/available-rounds', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const rounds = await response.json();
        document.getElementById('roundNumber').innerHTML = rounds.map(r => `
            <option value="${r.round_number}">Rodada ${r.round_number} (${r.total_matches} partidas)</option>
        `).join('');
    } catch (error) {
        console.error('Error loading rounds:', error);
    }
}

function openNewChallengeModal() {
    document.getElementById('challengeForm').reset();
    document.getElementById('selectedUser').classList.add('d-none');
    document.getElementById('matchSelectDiv').classList.add('d-none');
    document.getElementById('roundSelectDiv').classList.add('d-none');
    newChallengeModal.show();
}

async function submitChallenge() {
    const challengedId = document.getElementById('challengedId').value;
    const betType = document.getElementById('betType').value;
    const prizeDescription = document.getElementById('prizeDescription').value.trim();

    if (!challengedId || !betType || !prizeDescription) {
        showToast('Erro', 'Preencha todos os campos obrigatórios', 'danger');
        return;
    }

    const data = {
        challenged_id: parseInt(challengedId),
        bet_type: betType,
        match_id: betType === 'match' ? parseInt(document.getElementById('matchId').value) : null,
        round_number: betType === 'round' ? parseInt(document.getElementById('roundNumber').value) : null,
        prize_description: prizeDescription,
        expires_hours: parseInt(document.getElementById('expiresHours').value) || 24
    };

    try {
        const response = await fetch('/api/pvp/challenge', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            newChallengeModal.hide();
            showToast('Sucesso', 'Desafio enviado! O jogador será notificado.', 'success');
            loadSentChallenges();
        } else {
            const error = await response.json();
            showToast('Erro', error.detail || 'Erro ao criar desafio', 'danger');
        }
    } catch (error) {
        showToast('Erro', 'Erro ao enviar desafio', 'danger');
    }
}

async function respondChallenge(betId, action) {
    try {
        const response = await fetch(`/api/pvp/${betId}/respond`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action })
        });

        if (response.ok) {
            const result = await response.json();
            showToast('Sucesso', result.message, 'success');
            loadReceivedChallenges();
            if (action === 'accept') loadActiveBets();
        } else {
            const error = await response.json();
            showToast('Erro', error.detail, 'danger');
        }
    } catch (error) {
        showToast('Erro', 'Erro ao responder', 'danger');
    }
}

async function cancelChallenge(betId) {
    if (!confirm('Cancelar este desafio?')) return;

    try {
        const response = await fetch(`/api/pvp/${betId}/cancel`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });

        if (response.ok) {
            showToast('Sucesso', 'Desafio cancelado', 'success');
            loadSentChallenges();
        } else {
            const error = await response.json();
            showToast('Erro', error.detail, 'danger');
        }
    } catch (error) {
        showToast('Erro', 'Erro ao cancelar', 'danger');
    }
}

function formatDateBR(dateStr) {
    if (!dateStr) return '';
    const iso = dateStr.includes('Z') ? dateStr : dateStr + 'Z';
    return new Date(iso).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
}

function formatDateTimeBR(dateStr) {
    if (!dateStr) return '';
    const iso = dateStr.includes('Z') ? dateStr : dateStr + 'Z';
    return new Date(iso).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
}
