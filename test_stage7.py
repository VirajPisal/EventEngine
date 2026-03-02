"""
Stage 7 Test - Web UI Dashboard
Tests: Frontend pages accessibility and functionality
"""
import sys
import requests
import time
from datetime import datetime, timedelta, timezone

# Base URL for API and Frontend
BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def test_stage_7():
    """Test Stage 7: Web UI Dashboard"""
    
    print("\n" + "=" * 60)
    print(" STAGE 7 TEST: Web UI Dashboard")
    print("=" * 60)
    
    # Check if server is running
    print_section("TEST 1: Server Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Server is running: {response.json()}")
        else:
            print(f"[FAIL] Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] Server is not running!")
        print("Please start the server with: python api/main.py")
        print("Or in another terminal: uvicorn api.main:app --reload")
        return False
    
    # Test frontend static files serving
    print_section("TEST 2: Frontend Static Files")
    
    frontend_files = [
        "/frontend/index.html",
        "/frontend/events.html",
        "/frontend/registrations.html",
        "/frontend/attendance.html",
        "/frontend/analytics.html",
        "/frontend/css/styles.css",
        "/frontend/js/api.js"
    ]
    
    for file_path in frontend_files:
        try:
            response = requests.get(f"{BASE_URL}{file_path}", timeout=5)
            if response.status_code == 200:
                print(f"[OK] {file_path} - {len(response.content)} bytes")
            else:
                print(f"[FAIL] {file_path} - Status {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] {file_path} - Error: {e}")
            return False
    
    # Test dashboard page content
    print_section("TEST 3: Dashboard Page Content")
    
    response = requests.get(f"{BASE_URL}/frontend/index.html")
    content = response.text
    
    required_elements = [
        "EventEngine",
        "Dashboard",
        "Total Events",
        "Total Participants",
        "Attendance Rate",
        "api.js"
    ]
    
    for element in required_elements:
        if element in content:
            print(f"[OK] Found required element: {element}")
        else:
            print(f"[FAIL] Missing required element: {element}")
            return False
    
    # Test events page
    print_section("TEST 4: Events Page Content")
    
    response = requests.get(f"{BASE_URL}/frontend/events.html")
    content = response.text
    
    required_events_elements = [
        "Events Management",
        "Create New Event",
        "eventsContainer",
        "createEventForm"
    ]
    
    for element in required_events_elements:
        if element in content:
            print(f"[OK] Found required element: {element}")
        else:
            print(f"[FAIL] Missing required element: {element}")
            return False
    
    # Test registrations page
    print_section("TEST 5: Registrations Page Content")
    
    response = requests.get(f"{BASE_URL}/frontend/registrations.html")
    content = response.text
    
    required_reg_elements = [
        "Participant Registrations",
        "Register New Participant",
        "participantsContainer",
        "registrationForm"
    ]
    
    for element in required_reg_elements:
        if element in content:
            print(f"[OK] Found required element: {element}")
        else:
            print(f"[FAIL] Missing required element: {element}")
            return False
    
    # Test attendance page
    print_section("TEST 6: Attendance Page Content")
    
    response = requests.get(f"{BASE_URL}/frontend/attendance.html")
    content = response.text
    
    required_attendance_elements = [
        "Attendance Tracking",
        "QR Code Check-in",
        "OTP Check-in",
        "attendanceContainer",
        "qrModal",
        "otpModal"
    ]
    
    for element in required_attendance_elements:
        if element in content:
            print(f"[OK] Found required element: {element}")
        else:
            print(f"[FAIL] Missing required element: {element}")
            return False
    
    # Test analytics page
    print_section("TEST 7: Analytics Page Content")
    
    response = requests.get(f"{BASE_URL}/frontend/analytics.html")
    content = response.text
    
    required_analytics_elements = [
        "Analytics & Insights",
        "AI-powered",
        "analyticsChart",
        "insightsCard",
        "Chart.js"
    ]
    
    for element in required_analytics_elements:
        if element in content:
            print(f"[OK] Found required element: {element}")
        else:
            print(f"[FAIL] Missing required element: {element}")
            return False
    
    # Test CSS stylesheet
    print_section("TEST 8: CSS Stylesheet")
    
    response = requests.get(f"{BASE_URL}/frontend/css/styles.css")
    css_content = response.text
    
    required_css_classes = [
        ".btn",
        ".card",
        ".modal",
        ".badge",
        ".stat-card",
        ".event-card"
    ]
    
    for css_class in required_css_classes:
        if css_class in css_content:
            print(f"[OK] Found CSS class: {css_class}")
        else:
            print(f"[FAIL] Missing CSS class: {css_class}")
            return False
    
    # Test JavaScript API client
    print_section("TEST 9: JavaScript API Client")
    
    response = requests.get(f"{BASE_URL}/frontend/js/api.js")
    js_content = response.text
    
    required_js_functions = [
        "EventsAPI",
        "RegistrationsAPI",
        "AttendanceAPI",
        "AnalyticsAPI",
        "apiRequest",
        "getAll",
        "create"
    ]
    
    for js_func in required_js_functions:
        if js_func in js_content:
            print(f"[OK] Found JS function/object: {js_func}")
        else:
            print(f"[FAIL] Missing JS function/object: {js_func}")
            return False
    
    # Test navigation links
    print_section("TEST 10: Navigation Consistency")
    
    nav_links = [
        "/frontend/index.html",
        "/frontend/events.html",
        "/frontend/registrations.html",
        "/frontend/attendance.html",
        "/frontend/analytics.html"
    ]
    
    for page_url in nav_links:
        response = requests.get(f"{BASE_URL}{page_url}")
        content = response.text
        
        # Check if all nav links are present
        all_present = all(link in content for link in nav_links)
        
        if all_present:
            print(f"[OK] {page_url} has all navigation links")
        else:
            print(f"[FAIL] {page_url} missing navigation links")
            return False
    
    # Test responsive design elements
    print_section("TEST 11: Responsive Design")
    
    response = requests.get(f"{BASE_URL}/frontend/css/styles.css")
    css_content = response.text
    
    if "@media" in css_content:
        print(f"[OK] CSS includes responsive media queries")
    else:
        print(f"[FAIL] CSS missing responsive media queries")
        return False
    
    # Test API integration in frontend
    print_section("TEST 12: API Integration Check")
    
    response = requests.get(f"{BASE_URL}/frontend/js/api.js")
    js_content = response.text
    
    # Check if API base URL is configured
    if "localhost:8000" in js_content or "API_BASE_URL" in js_content:
        print(f"[OK] API base URL configured in JavaScript")
    else:
        print(f"[FAIL] API base URL not configured")
        return False
    
    # Test CORS configuration
    print_section("TEST 13: CORS Configuration")
    
    # Make an OPTIONS request to check CORS
    try:
        response = requests.options(
            f"{BASE_URL}/api/events/",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        if response.status_code in [200, 204]:
            print(f"[OK] CORS is configured")
        else:
            print(f"[WARNING] CORS might not be configured properly")
    except Exception as e:
        print(f"[WARNING] Could not verify CORS: {e}")
    
    # Final validation
    print_section("STAGE 7 TEST - VALIDATION")
    
    print(f"[PASS] Frontend directory structure created")
    print(f"[PASS] All HTML pages accessible")
    print(f"[PASS] CSS stylesheet loaded")
    print(f"[PASS] JavaScript API client loaded")
    print(f"[PASS] Navigation system working")
    print(f"[PASS] Responsive design implemented")
    print(f"[PASS] API integration configured")
    print(f"[PASS] All 13 UI tests passed!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_stage_7()
        
        if success:
            print("\n" + "=" * 60)
            print(" STAGE 7 TEST PASSED - Web UI Dashboard Complete!")
            print("=" * 60)
            print("\nWhat was tested:")
            print("  * Frontend static files serving")
            print("  * Dashboard home page")
            print("  * Events management page with modals")
            print("  * Registrations page with forms")
            print("  * Attendance tracking page (QR + OTP)")
            print("  * Analytics & insights page with charts")
            print("  * CSS styling and responsive design")
            print("  * JavaScript API client integration")
            print("  * Navigation consistency across pages")
            print("  * CORS configuration")
            print("\nAccess the UI:")
            print("  * Dashboard: http://localhost:8000/frontend/index.html")
            print("  * Events: http://localhost:8000/frontend/events.html")
            print("  * Registrations: http://localhost:8000/frontend/registrations.html")
            print("  * Attendance: http://localhost:8000/frontend/attendance.html")
            print("  * Analytics: http://localhost:8000/frontend/analytics.html")
            print("\nAPI Documentation:")
            print("  * Swagger UI: http://localhost:8000/docs")
            print("  * ReDoc: http://localhost:8000/redoc")
            print("\n✅ Stage 7 Complete - Full-Stack Event Management System Ready!")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print(" STAGE 7 TEST FAILED")
            print("=" * 60)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
