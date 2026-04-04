import sys

with open('frontend/portal.html', 'r', encoding='utf-8') as f:
    text = f.read()

bad_segment = '''            if (activeEvents.length === 0) {
                container.innerHTML = '<div class="empty"><div class="icon">📅</div><div class="title">No events available</div></div>';
                return;
            }


                    <div class="card">
                        <div class="card-header">'''

good_segment = '''            if (activeEvents.length === 0) {
                container.innerHTML = '<div class="empty"><div class="icon">📅</div><div class="title">No events available</div></div>';
                return;
            }

            container.innerHTML = activeEvents.map(ev => {
                const isReg = myRegistrations ? myRegistrations.some(r => r.event_id === ev.id) : false;
                const canRegister = ['REGISTRATION_OPEN', 'SCHEDULED', 'ATTENDANCE_OPEN', 'RUNNING'].includes(ev.state) && !isReg;
                
                return \
                    <div class="card">
                        <div class="card-header">'''

if bad_segment in text:
    text = text.replace(bad_segment, good_segment)
    with open('frontend/portal.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Patched successfully!')
else:
    print('Failed to find bad segment.')

