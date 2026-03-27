/* EventEngine — Auth helpers (loaded via <script> in every page) */

const AUTH_KEY = "ee_token";
const ROLE_KEY = "ee_role";
const NAME_KEY = "ee_name";
const EMAIL_KEY = "ee_email";

function saveAuth(token, role, name, email) {
    localStorage.setItem(AUTH_KEY, token);
    localStorage.setItem(ROLE_KEY, role);
    localStorage.setItem(NAME_KEY, name);
    if (email) localStorage.setItem(EMAIL_KEY, email);
}

function getToken() { return localStorage.getItem(AUTH_KEY); }
function getRole()  { return localStorage.getItem(ROLE_KEY); }
function getName()  { return localStorage.getItem(NAME_KEY); }
function getEmail() { return localStorage.getItem(EMAIL_KEY); }

function logout() {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem(NAME_KEY);
    localStorage.removeItem(EMAIL_KEY);
    window.location.href = "/frontend/login.html";
}

function checkAuth(requiredRole) {
    const token = getToken();
    const role  = getRole();
    if (!token || (requiredRole && role !== requiredRole)) {
        window.location.href = "/frontend/login.html";
        return false;
    }
    return true;
}

function authHeaders() {
    return {
        "Authorization": "Bearer " + getToken(),
        "Content-Type": "application/json"
    };
}
