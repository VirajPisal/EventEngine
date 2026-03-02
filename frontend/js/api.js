/**
 * EventEngine API Client
 * Handles all API communication with the backend
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Generic API request handler
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const config = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || `API Error: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error(`API Request failed: ${endpoint}`, error);
        throw error;
    }
}

/**
 * Events API
 */
const EventsAPI = {
    // Get all events
    async getAll(skip = 0, limit = 100) {
        return apiRequest(`/api/events/?skip=${skip}&limit=${limit}`);
    },
    
    // Get single event
    async getById(eventId) {
        return apiRequest(`/api/events/${eventId}`);
    },
    
    // Create new event
    async create(eventData) {
        return apiRequest('/api/events/', {
            method: 'POST',
            body: JSON.stringify(eventData),
        });
    },
    
    // Transition event state
    async transition(eventId, transitionData) {
        return apiRequest(`/api/events/${eventId}/transition`, {
            method: 'POST',
            body: JSON.stringify(transitionData),
        });
    },
    
    // Get event participants
    async getParticipants(eventId) {
        return apiRequest(`/api/events/${eventId}/participants`);
    },
};

/**
 * Registrations API
 */
const RegistrationsAPI = {
    // Register participant
    async register(registrationData) {
        return apiRequest('/api/registrations/register', {
            method: 'POST',
            body: JSON.stringify(registrationData),
        });
    },
    
    // Get participant details
    async getParticipant(participantId) {
        return apiRequest(`/api/registrations/${participantId}`);
    },
    
    // Confirm participant
    async confirm(participantId) {
        return apiRequest('/api/registrations/confirm', {
            method: 'POST',
            body: JSON.stringify({ participant_id: participantId }),
        });
    },
};

/**
 * Attendance API
 */
const AttendanceAPI = {
    // Generate QR code
    async generateQR(participantId) {
        return apiRequest('/api/attendance/qr/generate', {
            method: 'POST',
            body: JSON.stringify({ participant_id: participantId }),
        });
    },
    
    // Validate QR code
    async validateQR(qrToken, checkInData = {}) {
        return apiRequest('/api/attendance/qr/validate', {
            method: 'POST',
            body: JSON.stringify({
                qr_token: qrToken,
                check_in_ip: checkInData.ip || '127.0.0.1',
                check_in_device: checkInData.device || 'Web Dashboard',
            }),
        });
    },
    
    // Generate OTP
    async generateOTP(participantId) {
        return apiRequest('/api/attendance/otp/generate', {
            method: 'POST',
            body: JSON.stringify({ participant_id: participantId }),
        });
    },
    
    // Validate OTP
    async validateOTP(participantId, otp) {
        return apiRequest('/api/attendance/otp/validate', {
            method: 'POST',
            body: JSON.stringify({
                participant_id: participantId,
                otp: otp,
            }),
        });
    },
    
    // Get event attendance
    async getEventAttendance(eventId) {
        return apiRequest(`/api/attendance/event/${eventId}`);
    },
    
    // Get attendance stats
    async getStats(eventId) {
        return apiRequest(`/api/attendance/event/${eventId}/stats`);
    },
};

/**
 * Analytics API
 */
const AnalyticsAPI = {
    // Calculate analytics
    async calculate(eventId) {
        return apiRequest('/api/analytics/calculate', {
            method: 'POST',
            body: JSON.stringify({ event_id: eventId }),
        });
    },
    
    // Get analytics
    async getAnalytics(eventId) {
        return apiRequest(`/api/analytics/event/${eventId}`);
    },
    
    // Generate insights
    async generateInsights(eventId) {
        return apiRequest('/api/analytics/insights/generate', {
            method: 'POST',
            body: JSON.stringify({ event_id: eventId }),
        });
    },
    
    // Get insights
    async getInsights(eventId) {
        return apiRequest(`/api/analytics/insights/${eventId}`);
    },
    
    // Get summary report
    async getReport(eventId) {
        return apiRequest(`/api/analytics/report/${eventId}`);
    },
    
    // Get dashboard stats
    async getDashboard(limit = 10) {
        return apiRequest(`/api/analytics/dashboard?limit=${limit}`);
    },
};

/**
 * Utility Functions
 */
const Utils = {
    // Format date/time
    formatDateTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    },
    
    // Format date only
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    },
    
    // Get state badge class
    getStateBadgeClass(state) {
        const stateMap = {
            'CREATED': 'badge-info',
            'REGISTRATION_OPEN': 'badge-success',
            'SCHEDULED': 'badge-primary',
            'ATTENDANCE_OPEN': 'badge-warning',
            'RUNNING': 'badge-warning',
            'COMPLETED': 'badge-success',
            'ANALYZING': 'badge-info',
            'REPORT_GENERATED': 'badge-success',
            'CANCELLED': 'badge-danger',
        };
        return stateMap[state] || 'badge-info';
    },
    
    // Get event type badge
    getEventTypeBadge(type) {
        const typeMap = {
            'ONLINE': '🌐 Online',
            'OFFLINE': '📍 Offline',
            'HYBRID': '🔄 Hybrid',
        };
        return typeMap[type] || type;
    },
    
    // Show loading spinner
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading...</p>
                </div>
            `;
        }
    },
    
    // Show error message
    showError(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="alert alert-error">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }
    },
    
    // Show success message
    showSuccess(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="alert alert-success">
                    <strong>Success:</strong> ${message}
                </div>
            `;
        }
    },
    
    // Show toast notification
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type}`;
        toast.style.position = 'fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.style.minWidth = '300px';
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    },
    
    // Open modal
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
        }
    },
    
    // Close modal
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
        }
    },
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        EventsAPI,
        RegistrationsAPI,
        AttendanceAPI,
        AnalyticsAPI,
        Utils,
    };
}
