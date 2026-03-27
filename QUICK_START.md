# EventEngine - Quick Start Guide

## 🚀 How to Start the Complete System

You have **TWO important components** that need to run together:

### Option 1: Quick Start (Recommended)
```batch
# Double-click this file or run in terminal:
start_system.bat
```
This opens **2 windows**:
- Window 1: API Server (handles web requests)
- Window 2: Autonomous Agent (handles automatic transitions)

### Option 2: Manual Start (Separate terminals)
```batch
# Terminal 1 - API Server
python run.py

# Terminal 2 - Agent (in a new terminal)
python scripts\run_agent.py
```

---

## 🔍 What Each Component Does

### 1️⃣ API Server (`run.py`)
**Purpose:** Handles all web requests from frontend
- ✅ User login/registration
- ✅ Event creation via UI
- ✅ Manual transitions (clicking "Transition..." button)
- ✅ Viewing dashboards
- ❌ Does NOT do automatic transitions

### 2️⃣ Autonomous Agent (`scripts\run_agent.py`)
**Purpose:** Monitors events and performs actions automatically
- ✅ Opens attendance 30 min before event start
- ✅ Transitions events at scheduled times
- ✅ Completes events after end time
- ✅ Sends reminder notifications
- ✅ Generates analytics automatically

---

## 🔧 How to Check System Status

Run this diagnostic script:
```batch
python check_system.py
```

This will tell you:
- ✅ Is API Server running?
- ✅ Is Database connected?
- ✅ Is Agent running (automatic transitions enabled)?
- ✅ Are there events ready for registration?

---

## 📋 Registration Issue Fix

If participants can't register:

1. **Check event state:** Only events in `REGISTRATION_OPEN` state accept registrations
   - Login as organizer
   - Go to event card
   - Click "Transition..." → "Open Registration"

2. **Check API server:** Must be running
   ```batch
   python run.py
   ```

3. **Check browser console:** Press F12, look for errors

---

## ⚙️ Automatic Transitions

**When Agent is Running:**

| Current State | Auto Transition To | When? |
|--------------|-------------------|-------|
| SCHEDULED | ATTENDANCE_OPEN | 30 min before start |
| ATTENDANCE_OPEN | RUNNING | At start time |
| RUNNING | COMPLETED | 15 min after end time |
| COMPLETED | ANALYZING | Immediately |

**When Agent is NOT Running:**
- ❌ No automatic transitions
- 🖱️ Must click "Transition..." button manually

---

## 🎯 URLs

- **Frontend:** http://localhost:8000/frontend/login.html
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## ❓ Common Questions

**Q: Do I need to run agent for basic testing?**
A: No, but events won't transition automatically. You'll need to click buttons manually.

**Q: Can I run agent later?**
A: Yes! Start API first, then start agent anytime. They work independently.

**Q: What happens if I close agent?**
A: Automatic transitions stop. Manual transitions via UI still work.

**Q: How often does agent check events?**
A: Every 60 seconds by default (configurable in `.env` as `AGENT_LOOP_INTERVAL_SECONDS`)

---

## 🛠️ Troubleshooting

### Issue: "Registration failed" in participant portal

**Cause:** Event is not in REGISTRATION_OPEN state

**Fix:**
1. Login as organizer
2. Find the event
3. Click "Transition..." button
4. Select "Open Registration"

### Issue: Attendance doesn't open 30 min before event

**Cause:** Agent is not running

**Fix:**
1. Run `start_system.bat` OR
2. Run `python scripts\run_agent.py` in separate terminal

### Issue: Can't login to portal

**Cause:** No user account or wrong credentials

**Fix:**
1. Go to login page
2. Click "Register" tab
3. Create participant account
4. Login with those credentials
