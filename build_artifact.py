import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "public", "data.json")
APP_JS_FILE = os.path.join(BASE_DIR, "public", "app.js")
INDEX_HTML_FILE = os.path.join(BASE_DIR, "public", "index.html")
ARTIFACT_FILE = r"C:\Users\mahes\.gemini\antigravity\brain\bc57e943-c603-4146-9505-d908932268de\streamflix_dashboard.html"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    customers = json.load(f)

with open(APP_JS_FILE, "r", encoding="utf-8") as f:
    app_js = f.read()

with open(INDEX_HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

# Replace Tailwind CDN with allowlisted gstatic Tailwind if desired, or keep both
# gstatic tailwind is https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js
html = html.replace(
    '<script src="https://cdn.tailwindcss.com"></script>',
    '<script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>'
)

# Replace script src="app.js" with inline bundle
embedded_script = f"""
<script>
const EMBEDDED_CUSTOMERS = {json.dumps(customers)};

// Fallback to embedded customers for artifact rendering
RetentionService.fetchCustomers = async function() {{
    return JSON.parse(JSON.stringify(EMBEDDED_CUSTOMERS));
}};

{app_js}
</script>
"""

html = html.replace('<script src="app.js"></script>', embedded_script)

with open(ARTIFACT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Successfully generated standalone artifact: {ARTIFACT_FILE} ({len(html)} bytes)")
