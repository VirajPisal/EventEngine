import sys

with open('rules/transition_rules.py', 'r', encoding='utf-8') as f:
    text = f.read()

bad_segment = '''    # CREATED → REGISTRATION_OPEN (Immediate or 1 minute after creation)
    if event.state == EventState.CREATED:
        # Check if basic details are present
        if event.start_time and event.end_time:
            return {
                "should_transition": True,
                "target_state": EventState.REGISTRATION_OPEN,
                "reason": "Event validated, opening registration autonomously"
            }'''

good_segment = '''    # CREATED → REGISTRATION_OPEN (Immediate or 1 minute after creation)
    if event.state == EventState.CREATED:
        # Only auto-open if event was created more than 2 minutes ago (gives organizer time to review)
        created_at = ensure_timezone_aware(event.created_at)
        if (now - created_at).total_seconds() > 120:
            if event.start_time and event.end_time:
                return {
                    "should_transition": True,
                    "target_state": EventState.REGISTRATION_OPEN,
                    "reason": "Event review period complete, opening registration"
                }'''

if bad_segment in text:
    text = text.replace(bad_segment, good_segment)
    with open('rules/transition_rules.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Patched successfully!')
else:
    print('Failed to find bad segment. Please check.')

