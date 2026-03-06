// WebSocket real-time notifications for CivicFix

// API configuration is defined in auth.js and available as window.API_BASE_URL
// No need to redeclare it here

class WebSocketManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.init();
    }

    init() {
        // Socket.IO disabled - using HTTP polling instead
        console.log('WebSocket disabled - using HTTP polling for real-time updates');
        // this.loadSocketIO().then(() => {
        //     this.connect();
        // }).catch(error => {
        //     console.error('Failed to load Socket.IO:', error);
        // });
    }

    loadSocketIO() {
        return new Promise((resolve, reject) => {
            if (window.io) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdn.socket.io/4.7.2/socket.io.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    connect() {
        try {
            // Prevent multiple connections from the same tab
            if (this.socket && this.socket.connected) {
                console.log('WebSocket already connected');
                return;
            }

            this.socket = io(API_BASE_URL, {
                transports: ['polling'],  // Use polling only - more reliable on production
                timeout: 20000,
                forceNew: false, // Allow connection reuse
                query: {
                    tabId: Date.now() + Math.random() // Unique tab identifier
                }
            });

            this.setupEventListeners();
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.scheduleReconnect();
        }
    }

    setupEventListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to CivicFix real-time updates');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;

            // Join appropriate rooms based on user status
            this.joinUserRooms();
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from real-time updates');
            this.isConnected = false;
            this.scheduleReconnect();
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.isConnected = false;
            this.scheduleReconnect();
        });

        // Real-time event handlers
        this.socket.on('status_update', (data) => {
            this.handleStatusUpdate(data);
        });

        this.socket.on('admin_update', (data) => {
            this.handleAdminUpdate(data);
        });

        // Fired whenever a new issue is created
        this.socket.on('new_issue', (data) => {
            this.handleNewIssue(data);
        });

        this.socket.on('vote_update', (data) => {
            this.handleVoteUpdate(data);
        });

        this.socket.on('joined_room', (data) => {
            console.log(`Joined room: ${data.room}`);
        });
    }

    joinUserRooms() {
        // Citizen side: join user-specific room if authManager exists
        if (window.authManager && typeof authManager.isAuthenticated === 'function' && authManager.isAuthenticated()) {
            if (authManager.currentUser && authManager.currentUser.id) {
                this.socket.emit('join_user_room', {
                    user_id: authManager.currentUser.id
                });
            }
        }

        // Admin side: join admin room if admin_token is present (admin dashboard)
        const hasAdminToken = !!localStorage.getItem('admin_token');
        if (hasAdminToken) {
            this.socket.emit('join_admin_room', {
                is_admin: true
            });
        } else if (window.authManager) {
            // Fallback for Supabase-based admin detection (if used on citizen UI)
            this.checkAdminStatus().then(isAdmin => {
                if (isAdmin) {
                    this.socket.emit('join_admin_room', {
                        is_admin: true
                    });
                }
            });
        }
    }

    async checkAdminStatus() {
        try {
            if (!window.authManager || typeof authManager.getAuthHeaders !== 'function') {
                return false;
            }

            const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
                headers: authManager.getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.user && data.user.is_admin;
            }
            return false;
        } catch (error) {
            console.error('Error checking admin status:', error);
            return false;
        }
    }

    handleStatusUpdate(data) {
        console.log('Status update received:', data);

        const issueId = data.issue_id || (data.issue && data.issue.id);
        const rawStatus = data.new_status || (data.issue && data.issue.status);
        const statusText = rawStatus || '';
        const statusClass = statusText.toString().toLowerCase().replace(/\s+/g, '-');

        // 1) Update any issue cards currently rendered (citizen side)
        if (issueId) {
            const cards = document.querySelectorAll(`.issue-card[data-issue-id="${issueId}"]`);
            cards.forEach(card => {
                const statusEl = card.querySelector('.status-value');
                if (statusEl) {
                    statusEl.textContent = statusText || statusEl.textContent;
                    statusEl.className = `status-value ${statusClass}`.trim();
                    // Brief highlight so user notices the change
                    statusEl.style.transition = 'background-color 0.3s ease';
                    statusEl.style.backgroundColor = '#c6f6d5';
                    setTimeout(() => { statusEl.style.backgroundColor = ''; }, 600);
                }
            });
        }
        
        // 2) Show notification to user
        if (data.message) {
            this.showRealtimeNotification(data.message, 'success');
        }
        
        // 3) Optionally refresh issue lists on main feed to keep pagination & counts accurate
        if (window.location.pathname === '/index.html' || window.location.pathname === '/') {
            if (window.app && typeof window.app.loadIssues === 'function') {
                window.app.loadIssues(window.app.currentPage || 1);
            }
        }
        
        // 4) Update notifications count/display
        this.updateNotificationDisplay();
    }

    handleAdminUpdate(data) {
        console.log('Admin update received:', data);
        
        // Determine if this client is an admin
        const hasAdminToken = !!localStorage.getItem('admin_token');
        if (!hasAdminToken) return; // Ignore admin updates on citizen-only clients

        this.showRealtimeNotification(data.message, 'info');
        
        // Update admin dashboard if on admin dashboard page
        if (window.location.pathname.includes('admin-dashboard')) {
            if (window.adminDashboard && typeof window.adminDashboard.loadIssues === 'function') {
                // Reload issues; loadIssues will also refresh statistics
                window.adminDashboard.loadIssues(true);
            }
        }
    }

    handleNewIssue(data) {
        console.log('New issue event received:', data);

        const message = data.message || (data.issue ? `New issue reported: ${data.issue.title}` : 'New issue reported');
        this.showRealtimeNotification(message, 'info');

        // Citizen main feed: reload issues so the new one appears
        if (window.location.pathname === '/index.html' || window.location.pathname === '/') {
            if (window.app && typeof window.app.loadIssues === 'function') {
                const page = window.app.currentPage || 1;
                window.app.loadIssues(page);
            }
        }

        // Admin dashboard: refresh list & statistics if an admin is logged in
        const hasAdminToken = !!localStorage.getItem('admin_token');
        if (hasAdminToken && window.location.pathname.includes('admin-dashboard')) {
            if (window.adminDashboard && typeof window.adminDashboard.loadIssues === 'function') {
                window.adminDashboard.loadIssues(true);
            }
        }
    }

    handleVoteUpdate(data) {
        console.log('Vote update received:', data);
        
        // Update vote count in real-time for all users
        const voteButtons = document.querySelectorAll(`[onclick*="voteIssue(${data.issue_id})"]`);
        voteButtons.forEach(button => {
            // Update the vote count display
            button.innerHTML = `${data.vote_count}`;
        });
        
        // Smart notification: Only show to issue owner, not the voter
        if (window.authManager && authManager.currentUser && data.issue_id && data.issue_owner_id) {
            // Only show notification if current user is the issue owner
            if (authManager.currentUser.id === data.issue_owner_id) {
                this.showRealtimeNotification(`Your issue #${data.issue_id} received a vote!`, 'success', 4000);
            }
        }
    }

    showRealtimeNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `realtime-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${this.getNotificationIcon(type)}</span>
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Add styles if not already added
        this.addNotificationStyles();
        
        // Add to page
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Auto remove
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, duration);
    }

    getNotificationIcon(type) {
        return '';
    }

    addNotificationStyles() {
        if (document.getElementById('realtime-notification-styles')) {
            return;
        }

        const styles = document.createElement('style');
        styles.id = 'realtime-notification-styles';
        styles.textContent = `
            .realtime-notification {
                position: fixed;
                top: 24px;
                right: 24px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 16px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
                z-index: 10000;
                transform: translateX(450px) scale(0.95);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                max-width: 420px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                overflow: hidden;
            }
            
            .realtime-notification.success {
                background: linear-gradient(135deg, rgba(46, 204, 113, 0.1) 0%, rgba(39, 174, 96, 0.05) 100%);
                border-left: 4px solid #27ae60;
            }
            
            .realtime-notification.error {
                background: linear-gradient(135deg, rgba(231, 76, 60, 0.1) 0%, rgba(192, 57, 43, 0.05) 100%);
                border-left: 4px solid #e74c3c;
            }
            
            .realtime-notification.warning {
                background: linear-gradient(135deg, rgba(243, 156, 18, 0.1) 0%, rgba(230, 126, 34, 0.05) 100%);
                border-left: 4px solid #f39c12;
            }
            
            .realtime-notification.info {
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.05) 100%);
                border-left: 4px solid #667eea;
            }
            
            .realtime-notification.show {
                transform: translateX(0) scale(1);
            }
            
            .notification-content {
                display: flex;
                align-items: flex-start;
                padding: 1.5rem;
                gap: 1rem;
                position: relative;
            }
            
            .notification-icon {
                font-size: 1.5rem;
                flex-shrink: 0;
                margin-top: 0.1rem;
            }
            
            .notification-message {
                flex: 1;
                font-size: 0.95rem;
                color: #2d3748;
                line-height: 1.5;
                font-weight: 500;
            }
            
            .notification-close {
                background: rgba(0, 0, 0, 0.1);
                border: none;
                font-size: 1.1rem;
                cursor: pointer;
                color: #718096;
                flex-shrink: 0;
                padding: 0;
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.2s ease;
                position: absolute;
                top: 12px;
                right: 12px;
            }
            
            .notification-close:hover {
                background: rgba(0, 0, 0, 0.2);
                color: #2d3748;
                transform: scale(1.1);
            }
        `;
        
        document.head.appendChild(styles);
    }

    updateNotificationDisplay() {
        // Update notification badge/count if exists
        const notificationBadge = document.getElementById('notification-badge');
        if (notificationBadge && window.authManager && typeof authManager.isAuthenticated === 'function' && authManager.isAuthenticated()) {
            // Fetch latest notification count
            fetch(`${API_BASE_URL}/api/notifications`, {
                headers: authManager.getAuthHeaders()
            })
            .then(response => response.json())
            .then(data => {
                const unreadCount = data.notifications.filter(n => !n.is_read).length;
                if (unreadCount > 0) {
                    notificationBadge.textContent = unreadCount;
                    notificationBadge.style.display = 'inline';
                } else {
                    notificationBadge.style.display = 'none';
                }
            })
            .catch(error => console.error('Error fetching notifications:', error));
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        console.log(`Attempting to reconnect in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
            this.isConnected = false;
        }
    }

    // Public methods for manual room management
    joinUserRoom(userId) {
        if (this.socket && this.isConnected) {
            this.socket.emit('join_user_room', { user_id: userId });
        }
    }

    leaveUserRoom(userId) {
        if (this.socket && this.isConnected) {
            this.socket.emit('leave_user_room', { user_id: userId });
        }
    }

    joinAdminRoom() {
        if (this.socket && this.isConnected) {
            this.socket.emit('join_admin_room', { is_admin: true });
        }
    }

    leaveAdminRoom() {
        if (this.socket && this.isConnected) {
            this.socket.emit('leave_admin_room');
        }
    }
}

// Initialize WebSocket manager when page loads
let wsManager;

document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for auth to initialize
    setTimeout(() => {
        wsManager = new WebSocketManager();
        
        // Re-join rooms when auth state changes
        if (window.authManager && typeof authManager.updateUI === 'function') {
            const originalUpdateUI = authManager.updateUI;
            authManager.updateUI = function() {
                originalUpdateUI.call(this);
                if (wsManager && wsManager.isConnected) {
                    wsManager.joinUserRooms();
                }
            };
        }
    }, 2000);
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (wsManager) {
        wsManager.disconnect();
    }
});
