// Bolão Copa 2026 - Main JavaScript

// API Base URL
const API_BASE = '/api';

// Toast notification
function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toast-title');
    const toastMessage = document.getElementById('toast-message');
    
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    
    // Set color based on type
    toast.className = `toast bg-${type === 'danger' ? 'danger text-white' : type === 'success' ? 'success text-white' : 'light'}`;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Check authentication status
async function checkAuth() {
    const token = localStorage.getItem('token');
    const authButtons = document.getElementById('auth-buttons');
    const userMenu = document.getElementById('user-menu');
    const loginCard = document.getElementById('login-card');
    const userDashboard = document.getElementById('user-dashboard');
    
    if (token) {
        // Check if user is admin
        let isAdmin = false;
        let userName = 'Usuário';
        try {
            const response = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const user = await response.json();
                isAdmin = user.is_admin;
                userName = user.full_name || user.email;
                // Store for later use
                localStorage.setItem('user', JSON.stringify(user));
            }
        } catch (e) {}
        
        // Hide auth buttons, show user menu
        if (authButtons) authButtons.classList.add('d-none');
        if (userMenu) {
            userMenu.classList.remove('d-none');
            const adminLink = isAdmin ? `
                <li><a class="dropdown-item" href="/admin"><i class="bi bi-shield-lock me-2"></i>Admin</a></li>
                <li><hr class="dropdown-divider"></li>
            ` : '';
            
            userMenu.innerHTML = `
                <div class="dropdown">
                    <a class="btn btn-outline-light dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-person-circle me-1"></i>${userName}
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><a class="dropdown-item" href="/dashboard"><i class="bi bi-speedometer2 me-2"></i>Dashboard</a></li>
                        <li><a class="dropdown-item" href="/perfil"><i class="bi bi-person me-2"></i>Meu Perfil</a></li>
                        <li><a class="dropdown-item" href="/palpites"><i class="bi bi-pencil-square me-2"></i>Fazer Palpites</a></li>
                        ${adminLink}
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item text-danger" href="#" onclick="logout()"><i class="bi bi-box-arrow-right me-2"></i>Sair</a></li>
                    </ul>
                </div>
            `;
        }
        
        // Update home page cards
        if (loginCard) loginCard.style.display = 'none';
        if (userDashboard) {
            userDashboard.style.display = 'block';
            loadUserInfo();
        }
    } else {
        // User is not logged in - show auth buttons
        if (authButtons) authButtons.classList.remove('d-none');
        if (userMenu) userMenu.classList.add('d-none');
    }
}

// Load user info for dashboard card
async function loadUserInfo() {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    try {
        const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const user = await response.json();
            document.getElementById('user-name').textContent = user.full_name;
        }
        
        // Load dashboard stats
        const dashResponse = await fetch('/api/users/dashboard', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (dashResponse.ok) {
            const data = await dashResponse.json();
            document.getElementById('user-points').textContent = data.total_points;
            document.getElementById('user-position').textContent = data.general_position || '-';
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// Logout
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

// Load home page data
async function loadHomeData() {
    try {
        // Load live matches
        const liveResponse = await fetch('/api/matches/live');
        if (liveResponse.ok) {
            const liveMatches = await liveResponse.json();
            const liveSection = document.getElementById('live-matches-section');
            const liveContainer = document.getElementById('live-matches');
            
            if (liveMatches.length > 0 && liveSection && liveContainer) {
                liveSection.style.display = 'block';
                liveContainer.innerHTML = liveMatches.map(m => `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <span class="badge bg-danger live-badge me-2">AO VIVO</span>
                            <strong>${m.team_a} ${m.score_a || 0} x ${m.score_b || 0} ${m.team_b}</strong>
                        </div>
                        <small>${m.city}</small>
                    </div>
                `).join('');
            }
        }
        
        // Load today's matches
        const todayResponse = await fetch('/api/matches/today');
        if (todayResponse.ok) {
            const todayMatches = await todayResponse.json();
            const todayContainer = document.getElementById('today-matches');
            
            if (todayContainer) {
                todayContainer.innerHTML = todayMatches.map(m => `
                    <div class="d-flex justify-content-between align-items-center mb-2 p-2 bg-light rounded">
                        <div>
                            <strong>${m.team_a} x ${m.team_b}</strong>
                            <small class="d-block text-muted">${m.brasilia_time} - ${m.city}</small>
                        </div>
                        <span class="badge ${m.status === 'finished' ? 'bg-success' : 'bg-primary'}">
                            ${m.status === 'finished' ? 'Encerrado' : m.brasilia_time}
                        </span>
                    </div>
                `).join('') || '<p class="text-muted">Nenhum jogo hoje</p>';
            }
        }
        
        // Load upcoming matches
        const upcomingResponse = await fetch('/api/matches/?status=scheduled');
        if (upcomingResponse.ok) {
            const upcomingMatches = await upcomingResponse.json();
            const upcomingContainer = document.getElementById('upcoming-matches');
            
            if (upcomingContainer) {
                const next5 = upcomingMatches.slice(0, 5);
                upcomingContainer.innerHTML = next5.map(m => `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <small class="text-muted">${formatDateBR(m.match_date)}</small>
                            <div>${m.team_a} x ${m.team_b}</div>
                        </div>
                        <small>${m.brasilia_time}</small>
                    </div>
                `).join('') || '<p class="text-muted">Nenhum jogo agendado</p>';
            }
        }
        
        // Load ranking
        const rankingResponse = await fetch('/api/rankings/general');
        if (rankingResponse.ok) {
            const ranking = await rankingResponse.json();
            const rankingTable = document.getElementById('ranking-table');
            
            if (rankingTable) {
                const tbody = rankingTable.querySelector('tbody');
                const top10 = ranking.slice(0, 10);
                
                tbody.innerHTML = top10.map((r, i) => `
                    <tr>
                        <td>${i + 1}º</td>
                        <td>${r.user_name || r.user?.full_name || 'Jogador'}</td>
                        <td class="fw-bold">${r.total_points}</td>
                    </tr>
                `).join('') || '<tr><td colspan="3" class="text-center">Ranking em breve</td></tr>';
            }
        }
    } catch (error) {
        console.error('Error loading home data:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Check auth status and update menu
    await checkAuth();
    
    // Login form handler
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('username', document.getElementById('login-email').value);
            formData.append('password', document.getElementById('login-password').value);
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    localStorage.setItem('token', data.access_token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    
                    // Redirect to intended page or dashboard
                    const urlParams = new URLSearchParams(window.location.search);
                    const redirect = urlParams.get('redirect') || '/dashboard';
                    window.location.href = redirect;
                } else {
                    showToast('Erro', data.detail || 'Email ou senha incorretos', 'danger');
                }
            } catch (error) {
                showToast('Erro', 'Erro de conexão', 'danger');
            }
        });
    }
});

// Format date (UTC → Brasília)
function formatDate(dateString) {
    const iso = dateString.includes('Z') ? dateString : dateString + 'Z';
    return new Date(iso).toLocaleString('pt-BR', {
        timeZone: 'America/Sao_Paulo',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}
