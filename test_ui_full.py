import asyncio
from playwright.async_api import async_playwright

async def fill_login(page, email, password):
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(2000)

async def test_themes(page):
    print("Testing themes in Settings...")
    await page.goto("http://localhost:5173/settings")
    await page.wait_for_load_state("networkidle")
    
    # Try selecting a theme
    await page.select_option('select', label='Sunset Cabin')
    await page.wait_for_timeout(500)
    
    # Try selecting a border style
    await page.select_option('select', label='Round Edges')
    await page.wait_for_timeout(500)
    
    print("Themes updated.")

async def main():
    async with async_playwright() as p:
        teacher_browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        teacher_context = teacher_browser.contexts[0]
        t_page = teacher_context.pages[0] if teacher_context.pages else await teacher_context.new_page()

        student_browser = await p.chromium.connect_over_cdp("http://localhost:9223")
        student_context = student_browser.contexts[0]
        s_page = student_context.pages[0] if student_context.pages else await student_context.new_page()

        print("--- Testing Teacher (Canary) ---")
        await t_page.goto("http://localhost:5173")
        await t_page.wait_for_load_state("networkidle")
        
        # Logout if logged in
        try:
            await t_page.click("button:has-text('Logout')", timeout=2000)
            await t_page.wait_for_timeout(1000)
        except:
            pass
            
        print("Logging in teacher...")
        await fill_login(t_page, "testuser@plannededucation.com", "Admin123!")
        
        if "login" in t_page.url:
            print("Teacher login failed! Trying to register...")
            await t_page.click("text=Register here")
            await t_page.wait_for_timeout(500)
            await t_page.fill('input[type="text"]', 'testuser')
            await t_page.fill('input[type="email"]', 'testuser@plannededucation.com')
            await t_page.fill('input[type="password"]', 'Admin123!')
            await t_page.click('button[type="submit"]')
            await t_page.wait_for_timeout(2000)
            await fill_login(t_page, "testuser@plannededucation.com", "Admin123!")
            
        await test_themes(t_page)
        
        print("--- Testing Student (Chrome) ---")
        await s_page.goto("http://localhost:5173")
        await s_page.wait_for_load_state("networkidle")
        
        try:
            await s_page.click("button:has-text('Logout')", timeout=2000)
            await s_page.wait_for_timeout(1000)
        except:
            pass
            
        print("Logging in student...")
        await fill_login(s_page, "student@plannededucation.com", "Student123!")
        
        if "login" in s_page.url:
            print("Student login failed! Trying to register...")
            await s_page.click("text=Register here")
            await s_page.wait_for_timeout(500)
            await s_page.fill('input[type="text"]', 'student')
            await s_page.fill('input[type="email"]', 'student@plannededucation.com')
            await s_page.fill('input[type="password"]', 'Student123!')
            await s_page.click('button[type="submit"]')
            await s_page.wait_for_timeout(2000)
            await fill_login(s_page, "student@plannededucation.com", "Student123!")
            
        await test_themes(s_page)
        print("--- All visual tests completed ---")

if __name__ == "__main__":
    asyncio.run(main())
