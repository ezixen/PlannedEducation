import asyncio
from playwright.async_api import async_playwright
import requests

def get_token(email, username, name):
    requests.post('http://localhost:8000/auth/register', json={'email': email, 'username': username, 'password': 'password123', 'full_name': name})
    return requests.post('http://localhost:8000/auth/token', data={'username': email, 'password': 'password123'}).json()['access_token']

async def main():
    # Setup test data
    teacher_token = get_token('mrmagoo@test.com', 'mrmagoo', 'Mr. Magoo')
    student_token = get_token('timmy@test.com', 'timmy', 'Timmy Turner')
    
    # Create Exam as Teacher
    exam_res = requests.post('http://localhost:8000/exams/', json={'title': 'Math Midterm', 'duration_minutes': 60, 'description': 'Test exam'}, headers={'Authorization': f'Bearer {teacher_token}'}).json()
    print("Created Exam:", exam_res)

    async with async_playwright() as p:
        browser_t = await p.chromium.connect_over_cdp('http://localhost:9222')
        context_t = browser_t.contexts[0]
        page_t = context_t.pages[0] if context_t.pages else await context_t.new_page()
        
        browser_s = await p.chromium.connect_over_cdp('http://localhost:9223')
        context_s = browser_s.contexts[0]
        page_s = context_s.pages[0] if context_s.pages else await context_s.new_page()

        # Login Teacher
        await page_t.goto('http://localhost:5173/login')
        await page_t.evaluate(f"window.localStorage.setItem('access_token', '{teacher_token}')")
        await page_t.goto('http://localhost:5173/teacher-exams')
        
        # Login Student
        await page_s.goto('http://localhost:5173/login')
        await page_s.evaluate(f"window.localStorage.setItem('access_token', '{student_token}')")
        await page_s.goto('http://localhost:5173/exam')
        
        print("Both browsers are logged in and navigated!")

asyncio.run(main())
