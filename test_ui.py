import asyncio
from playwright.async_api import async_playwright
import time

async def main():
    async with async_playwright() as p:
        print("Connecting to Teacher (Canary) on port 9222...")
        browser_t = await p.chromium.connect_over_cdp("http://localhost:9222")
        context_t = browser_t.contexts[0]
        page_t = context_t.pages[0] if context_t.pages else await context_t.new_page()
        
        print("Connecting to Student (Chrome) on port 9223...")
        browser_s = await p.chromium.connect_over_cdp("http://localhost:9223")
        context_s = browser_s.contexts[0]
        page_s = context_s.pages[0] if context_s.pages else await context_s.new_page()

        # ----- TEACHER FLOW -----
        print("Teacher: Registering...")
        await page_t.goto("http://localhost:5173/register")
        await page_t.fill("input[type='text']", "Test Teacher") # Full Name
        await page_t.fill("input[type='text']:nth-child(2)", "teacher1") # Username - wait this selector is bad
        # Use more precise selectors
        await page_t.fill("label:has-text('Full Name') input", "Mr. Test Teacher")
        await page_t.fill("label:has-text('Username') input", "mrteacher")
        await page_t.fill("label:has-text('Email') input", "teacher@test.com")
        await page_t.fill("label:has-text('Password') input", "password123")
        await page_t.click("button:has-text('Register')")
        
        await page_t.wait_for_url("**/login")
        print("Teacher: Logging in...")
        await page_t.fill("input[placeholder='Email or Username']", "mrteacher")
        await page_t.fill("input[placeholder='Password']", "password123")
        await page_t.click("button:has-text('Sign In')")
        
        await page_t.wait_for_url("**/")
        print("Teacher: Creating Exam...")
        await page_t.goto("http://localhost:5173/teacher-exams")
        
        # We don't have the create exam UI mapped perfectly in memory, let's just create an exam via API 
        # Actually I can just click around
        await page_t.click("button:has-text('Create New Exam')")
        
        await page_t.fill("input[type='text']", "E2E Test Exam")
        await page_t.fill("textarea", "This is an E2E test exam")
        await page_t.click("button:has-text('Save Exam')")
        
        await asyncio.sleep(1) # wait for save
        
        # ----- STUDENT FLOW -----
        print("Student: Registering...")
        await page_s.goto("http://localhost:5173/register")
        await page_s.fill("label:has-text('Full Name') input", "Test Student")
        await page_s.fill("label:has-text('Username') input", "teststudent")
        await page_s.fill("label:has-text('Email') input", "student@test.com")
        await page_s.fill("label:has-text('Password') input", "password123")
        await page_s.click("button:has-text('Register')")
        
        await page_s.wait_for_url("**/login")
        print("Student: Logging in...")
        await page_s.fill("input[placeholder='Email or Username']", "teststudent")
        await page_s.fill("input[placeholder='Password']", "password123")
        await page_s.click("button:has-text('Sign In')")
        
        await page_s.wait_for_url("**/")
        print("Student: Viewing Exams...")
        await page_s.goto("http://localhost:5173/exam")
        
        # Wait a bit to see it visually
        await asyncio.sleep(5)
        
        print("Test complete.")

asyncio.run(main())

