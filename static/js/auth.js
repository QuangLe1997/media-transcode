/**
 * Authentication utilities for the Media Transcode Service
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication status
    checkAuth();

    // Setup logout handler
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
});

/**
 * Check if user is authenticated and update UI
 */
function checkAuth() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    const navLogin = document.getElementById('nav-login');
    const navRegister = document.getElementById('nav-register');
    const navUser = document.getElementById('nav-user');
    const navJobs = document.getElementById('nav-jobs');
    const navConfigs = document.getElementById('nav-configs');
    const username = document.getElementById('username');

    if (token) {
        // User is logged in
        if (navLogin) navLogin.style.display = 'none';
        if (navRegister) navRegister.style.display = 'none';
        if (navUser) {
            navUser.style.display = '';
            if (username) username.textContent = user.username || 'User';
        }
        if (navJobs) navJobs.style.display = '';
        if (navConfigs) navConfigs.style.display = '';

        // Validate token
        validateToken(token);
    } else {
        // User is not logged in
        if (navLogin) navLogin.style.display = '';
        if (navRegister) navRegister.style.display = '';
        if (navUser) navUser.style.display = 'none';
        if (navJobs) navJobs.style.display = 'none';
        if (navConfigs) navConfigs.style.display = 'none';

        // Redirect if on a protected page
        const protectedPaths = ['/jobs', '/configs', '/profile'];
        const currentPath = window.location.pathname;

        for (const path of protectedPaths) {
            if (currentPath.startsWith(path)) {
                window.location.href = '/login';
                break;
            }
        }
    }
}

/**
 * Validate token with the server
 */
function validateToken(token) {
    fetch('/api/auth/profile', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Token validation failed');
        }
        return response.json();
    })
    .then(data => {
        // Update user data if needed
        const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
        if (JSON.stringify(currentUser) !== JSON.stringify(data)) {
            localStorage.setItem('user', JSON.stringify(data));

            // Update username in navbar
            const username = document.getElementById('username');
            if (username) username.textContent = data.username || 'User';
        }
    })
    .catch(error => {
        console.error('Token validation error:', error);
        // Token is invalid, logout user
        logout();
    });
}

/**
 * Logout user
 */
function logout() {
    // Make API request (optional)
    const token = localStorage.getItem('token');
    if (token) {
        fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .catch(error => {
            console.error('Logout error:', error);
        });
    }

    // Clear local storage
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    // Redirect to login page
    window.location.href = '/login';
}

/**
 * Get authorization header
 */
function getAuthHeader() {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}