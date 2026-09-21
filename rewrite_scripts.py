import os

def rewrite_start():
    with open('scripts/local/start.ps1', 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace specific strings
    content = content.replace('WIWM local stack', 'PlannedEducation local stack')
    content = content.replace('https://127.0.0.1:5173', 'http://localhost:5173')
    content = content.replace('http://127.0.0.1:8000', 'http://localhost:8000')
    content = content.replace('wiwm-canary-debug-profile', 'plannededucation-canary-profile')
    content = content.replace('wiwm', 'plannededucation')
    content = content.replace('WIWM', 'PlannedEducation')
    
    # Remove admin bits
    lines = content.split('\n')
    new_lines = []
    skip = False
    for line in lines:
        if 'AdminUrl' in line or 'AdminDir' in line or 'admin' in line.lower() and not 'admin' in new_lines:
            pass # We need to selectively remove admin
    
    # It's easier to just do regex or manually edit. Let's do a few simple replacements
    content = content.replace('$AdminUrl = "http://127.0.0.1:5174"', '')
    content = content.replace('$AdminDir = Join-Path $RepoRoot "web\\apps\\admin"', '')
    content = content.replace('Test-LocalPort 5174', '$true')
    
    # In launch Admin:
    # We will just write a new start.ps1 based on the logic.
