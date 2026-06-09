// Universal API utilities for handling errors and responses
const API_BASE = location.origin.startsWith('http://localhost:5173') ? 'http://localhost:8000' : '';
const TOKEN_KEY = 'retail_jwt';

// Get authentication headers
function getAuthHeaders() {
    const token = localStorage.getItem(TOKEN_KEY);
    const headers = {
        'Content-Type': 'application/json'
    };
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }
    return headers;
}

// Safe API call with proper error handling
async function safeApiCall(url, options = {}) {
    try {
        // Ensure we have proper headers
        if (!options.headers) {
            options.headers = {};
        }
        
        // Add auth headers if not present
        if (!options.headers['Authorization'] && localStorage.getItem(TOKEN_KEY)) {
            options.headers['Authorization'] = 'Bearer ' + localStorage.getItem(TOKEN_KEY);
        }
        
        // Make the request
        const response = await fetch(API_BASE + url, options);
        
        // Check if response is ok
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Check content type
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response:', text.substring(0, 200));
            throw new Error('Server returned HTML instead of JSON. Check if backend is running correctly.');
        }
        
        // Parse JSON
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error('API Call Error:', error);
        
        // Return a standardized error response
        return {
            success: false,
            meta: {
                error: error.message || 'Network error occurred'
            },
            data: null
        };
    }
}

// Show user-friendly error messages
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="p-3 bg-red-50 border border-red-200 rounded-lg">
                <div class="flex items-center gap-2">
                    <span class="text-red-600">❌</span>
                    <span class="text-red-800 font-medium">Error</span>
                </div>
                <div class="text-sm text-red-700 mt-1">${message}</div>
            </div>
        `;
        element.classList.remove('hidden');
    }
}

// Show success messages
function showSuccess(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div class="flex items-center gap-2">
                    <span class="text-green-600">✅</span>
                    <span class="text-green-800 font-medium">Success</span>
                </div>
                <div class="text-sm text-green-700 mt-1">${message}</div>
            </div>
        `;
        element.classList.remove('hidden');
    }
}

// Check if user is authenticated
function isAuthenticated() {
    return !!localStorage.getItem(TOKEN_KEY);
}

// Redirect to login if not authenticated
function requireAuth() {
    if (!isAuthenticated()) {
        location.href = '/login.html';
        return false;
    }
    return true;
}

// Logout function
function logout() {
    localStorage.removeItem(TOKEN_KEY);
    location.href = '/login.html';
}

// Export for use in other scripts
window.apiUtils = {
    safeApiCall,
    getAuthHeaders,
    showError,
    showSuccess,
    isAuthenticated,
    requireAuth,
    logout,
    API_BASE,
    TOKEN_KEY
};
