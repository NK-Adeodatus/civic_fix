// Beautiful notification system for CivicFix
class NotificationManager {
    constructor() {
        this.notifications = [];
        this.container = null;
        this.init();
    }

    init() {
        // Create notification container
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            pointer-events: none;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type);
        this.container.appendChild(notification);
        this.notifications.push(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }

        return notification;
    }

    createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `beautiful-notification ${type}`;
        notification.style.cssText = `
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            margin-bottom: 16px;
            max-width: 420px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            overflow: hidden;
            transform: translateX(450px) scale(0.95);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: auto;
        `;

        // Add type-specific styling
        const typeStyles = {
            success: {
                background: 'linear-gradient(135deg, rgba(46, 204, 113, 0.1) 0%, rgba(39, 174, 96, 0.05) 100%)',
                borderLeft: '4px solid #27ae60',
                icon: ''
            },
            error: {
                background: 'linear-gradient(135deg, rgba(231, 76, 60, 0.1) 0%, rgba(192, 57, 43, 0.05) 100%)',
                borderLeft: '4px solid #e74c3c',
                icon: ''
            },
            warning: {
                background: 'linear-gradient(135deg, rgba(243, 156, 18, 0.1) 0%, rgba(230, 126, 34, 0.05) 100%)',
                borderLeft: '4px solid #f39c12',
                icon: ''
            },
            info: {
                background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.05) 100%)',
                borderLeft: '4px solid #667eea',
                icon: ''
            }
        };

        const style = typeStyles[type] || typeStyles.info;
        notification.style.background = style.background;
        notification.style.borderLeft = style.borderLeft;

        notification.innerHTML = `
            <div style="
                display: flex;
                align-items: flex-start;
                padding: 1.5rem;
                gap: 1rem;
                position: relative;
            ">
                <div style="
                    font-size: 1.5rem;
                    flex-shrink: 0;
                    margin-top: 0.1rem;
                ">${style.icon}</div>
                <div style="
                    flex: 1;
                    font-size: 0.95rem;
                    color: #2d3748;
                    line-height: 1.5;
                    font-weight: 500;
                ">${message}</div>
                <button class="notification-close" style="
                    background: rgba(0, 0, 0, 0.1);
                    border: none;
                    font-size: 1.1rem;
                    cursor: pointer;
                    color: #718096;
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
                ">×</button>
            </div>
        `;

        // Add close functionality
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => this.remove(notification));
        closeBtn.addEventListener('mouseenter', (e) => {
            e.target.style.background = 'rgba(0, 0, 0, 0.2)';
            e.target.style.color = '#2d3748';
            e.target.style.transform = 'scale(1.1)';
        });
        closeBtn.addEventListener('mouseleave', (e) => {
            e.target.style.background = 'rgba(0, 0, 0, 0.1)';
            e.target.style.color = '#718096';
            e.target.style.transform = 'scale(1)';
        });

        // Add show class for animation
        notification.addEventListener('animationend', function() {
            if (this.classList.contains('show')) {
                this.style.transform = 'translateX(0) scale(1)';
            }
        });

        return notification;
    }

    remove(notification) {
        if (!notification || !notification.parentNode) return;

        // Animate out
        notification.style.transform = 'translateX(450px) scale(0.95)';
        notification.style.opacity = '0';

        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            const index = this.notifications.indexOf(notification);
            if (index > -1) {
                this.notifications.splice(index, 1);
            }
        }, 400);
    }

    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 7000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }

    clear() {
        this.notifications.forEach(notification => this.remove(notification));
    }
}

// Create global instance
window.notifications = new NotificationManager();

// Backward compatibility with existing alert functions
window.showAlert = function(message, type = 'info') {
    window.notifications.show(message, type);
};

// Enhanced alert functions
window.showSuccess = function(message) {
    window.notifications.success(message);
};

window.showError = function(message) {
    window.notifications.error(message);
};

window.showWarning = function(message) {
    window.notifications.warning(message);
};

window.showInfo = function(message) {
    window.notifications.info(message);
};
