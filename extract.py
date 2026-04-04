import re

with open('frontend/dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# find all script tags
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
for i, s in enumerate(scripts):
    with open(f'frontend/temp_script_{i}.js', 'w', encoding='utf-8') as f:
        f.write(s)

print(f"Extracted {len(scripts)} scripts. Running node -c...")
