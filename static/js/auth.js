/**
 * Authentication JavaScript Module
 *
 * Handles user login, logout, session management, and authentication UI updates.
 */

const Auth = (function() {
    // Session token key
    const SESSION_TOKEN_KEY = 'ai_token_session';

    // Get current session token
    function getSessionToken() {
        return localStorage.getItem(SESSION_TOKEN_KEY);
    }

    // Set session token
    function setSessionToken(token) {
        localStorage.setItem(SESSION_TOKEN_KEY, token);
    }

    // Set session cookie for automatic authentication
    function setSessionCookie(token) {
        const expires = new Date();
        expires.setTime(expires.getTime() + 7 * 24 * 60 * 60 * 1000); // 7 days
        document.cookie = `session_token=${token};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
    }

    // Remove session token (logout)
    function removeSessionToken() {
        localStorage.removeItem(SESSION_TOKEN_KEY);
        // Also clear cookie
        document.cookie = 'session_token=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
    }

    // Check if user is authenticated
    function isAuthenticated() {
        const token = getSessionToken();
        return !!token;
    }

    // Get current user from session
    function getCurrentUser() {
        const userJson = sessionStorage.getItem('current_user');
        return userJson ? JSON.parse(userJson) : null;
    }

    // Set current user
    function setCurrentUser(user) {
        sessionStorage.setItem('current_user', JSON.stringify(user));
    }

    // Clear current user
    function clearCurrentUser() {
        sessionStorage.removeItem('current_user');
    }

    // API: Login user
    async function login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                }),
                credentials: 'include'  // Include cookies in request
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }

            // Store session token
            setSessionToken(data.session_token);

            // Set cookie for automatic authentication
            setSessionCookie(data.session_token);

            // Store user info
            setCurrentUser(data.user);

            return { success: true, user: data.user };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // API: Logout user
    async function logout() {
        const token = getSessionToken();
        if (token) {
            try {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token
                    },
                    credentials: 'include'
                });
            } catch (error) {
                console.error('Logout API error:', error);
            } finally {
                // Always clear local state
                removeSessionToken();
                clearCurrentUser();
            }
        } else {
            removeSessionToken();
            clearCurrentUser();
        }
    }

    // API: Get current user profile
    async function getProfile() {
        const token = getSessionToken();
        if (!token) {
            return { success: false, error: 'No session token' };
        }

        try {
            const response = await fetch('/api/auth/profile', {
                method: 'GET',
                headers: {
                    'Authorization': 'Bearer ' + token
                },
                credentials: 'include'
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get profile');
            }

            // Update stored user info
            setCurrentUser(data.user);
            return { success: true, user: data.user };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // Redirect to login page if not authenticated
    function requireAuth() {
        if (!isAuthenticated()) {
            window.location.href = '/login';
            return false;
        }
        return true;
    }

    // Check if current user is admin
    function isAdmin() {
        const user = getCurrentUser();
        return user && user.role === 'admin';
    }

    // Update navigation menu based on authentication and role
    function updateNavMenu() {
        const loginLink = document.getElementById('nav-login');
        const logoutLink = document.getElementById('nav-logout');
        const profileLink = document.getElementById('nav-profile');
        const dashboardLink = document.getElementById('nav-dashboard');
        const messagesLink = document.getElementById('nav-messages');
        const analysisLink = document.getElementById('nav-analysis');
        const managementLink = document.getElementById('nav-management');
        const workspaceLink = document.getElementById('nav-workspace');
        const reportLink = document.getElementById('nav-report');

        const user = getCurrentUser();

        if (isAuthenticated() && user) {
            // User is logged in
            if (loginLink) loginLink.style.display = 'none';
            if (profileLink) profileLink.style.display = 'inline-block';
            if (logoutLink) logoutLink.style.display = 'inline-block';
            if (profileLink) profileLink.textContent = user.username;

            // Show/hide menu items based on role
            if (dashboardLink) dashboardLink.style.display = 'block';
            if (messagesLink) messagesLink.style.display = 'block';

            if (analysisLink) {
                analysisLink.style.display = isAdmin() ? 'block' : 'none';
            }

            if (managementLink) {
                managementLink.style.display = isAdmin() ? 'block' : 'none';
            }

            if (workspaceLink) workspaceLink.style.display = isAdmin() ? 'none' : 'block';

            if (reportLink) reportLink.style.display = 'block';
        } else {
            // User is not logged in
            if (loginLink) loginLink.style.display = 'inline-block';
            if (logoutLink) logoutLink.style.display = 'none';
            if (profileLink) profileLink.style.display = 'none';

            // Hide protected menu items
            if (dashboardLink) dashboardLink.style.display = 'none';
            if (messagesLink) messagesLink.style.display = 'none';
            if (analysisLink) analysisLink.style.display = 'none';
            if (managementLink) managementLink.style.display = 'none';
            if (workspaceLink) workspaceLink.style.display = 'none';
            if (reportLink) reportLink.style.display = 'none';
        }
    }

    // Apply authentication check to page load
    function init() {
        // Check auth on page load
        if (window.location.pathname !== '/login') {
            updateNavMenu();
        }

        // Update menu when navigation links are clicked
        document.addEventListener('click', (e) => {
            if (e.target.closest('.nav-link')) {
                setTimeout(updateNavMenu, 100);
            }
        });
    }

    // Export public functions
    return {
        init,
        login,
        logout,
        getProfile,
        isAuthenticated,
        isAdmin,
        getCurrentUser,
        requireAuth,
        updateNavMenu
    };
})();

// Initialize auth when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    Auth.init();
});
