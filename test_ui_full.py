import asyncio
import os

from playwright.async_api import async_playwright

async def fill_login(page, email, password):
    print(f"  Filling login for {email}...")
    await page.wait_for_selector('input[type="email"]', timeout=10000)
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)
    
    # Listen for all console messages BEFORE clicking
    page.on("console", lambda msg: print(f"  Browser Console [{msg.type}]: {msg.text}"))
    
    # Listen for network requests
    page.on("request", lambda req: print(f"  Request: {req.method} {req.url}") if "auth" in req.url else None)
    page.on("response", lambda resp: print(f"  Response: {resp.status} {resp.url}") if "auth" in resp.url else None)
    
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(5000)
    print(f"  After login, URL: {page.url}")
    
    # Check for error messages
    error_elements = await page.query_selector_all('.toast, .error, [role="alert"], .alert')
    for el in error_elements:
        text = await el.inner_text()
        if text.strip():
            print(f"  Error message: {text.strip()}")

async def test_themes(page):
    print("Testing themes in Settings...")
    await page.goto("http://localhost:5175/settings")
    await page.wait_for_load_state("networkidle")
    
    # Check if we're on login page (not authenticated)
    if "login" in page.url:
        print("Not authenticated, skipping theme test")
        return
    
    # Try selecting a theme
    try:
        await page.select_option('select', label='Sunset Cabin')
        await page.wait_for_timeout(500)
    except:
        print("Theme select not found, skipping")
    
    # Try selecting a border style
    try:
        await page.select_option('select', label='Round Edges')
        await page.wait_for_timeout(500)
    except:
        print("Border select not found, skipping")
    
    print("Themes updated.")


async def smoke_test() -> None:
    """Validate public portal navigation without manual CDP browser setup."""
    portal_url = os.getenv("PORTAL_URL", "http://127.0.0.1:5175")
    executable_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if not executable_path and os.name == "nt":
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if os.path.exists(chrome_path):
            executable_path = chrome_path
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path=executable_path)
        page = await browser.new_page()
        console_errors: list[str] = []
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        try:
            await page.goto(f"{portal_url}/login", wait_until="networkidle")
            assert page.url.endswith("/login")
            assert await page.get_by_role("heading", name="Planned Education").is_visible()
            assert await page.get_by_text("Google sign-in is not configured.").is_visible()

            await page.get_by_role("link", name="Register here").click()
            await page.wait_for_url(f"{portal_url}/register")
            assert await page.get_by_role("textbox", name="Full Name").is_visible()
            assert await page.get_by_role("textbox", name="Username").is_visible()
            assert await page.get_by_role("textbox", name="Email").is_visible()
            assert await page.get_by_role("button", name="Register").is_visible()
            assert not console_errors, f"Browser console errors: {console_errors}"
        finally:
            await browser.close()


async def main():
    async with async_playwright() as p:
        teacher_browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        teacher_context = teacher_browser.contexts[0]
        t_page = teacher_context.pages[0] if teacher_context.pages else await teacher_context.new_page()

        student_browser = await p.chromium.connect_over_cdp("http://localhost:9223")
        student_context = student_browser.contexts[0]
        s_page = student_context.pages[0] if student_context.pages else await student_context.new_page()

        parent_browser = await p.chromium.connect_over_cdp("http://localhost:9224")
        parent_context = parent_browser.contexts[0]
        p_page = parent_context.pages[0] if parent_context.pages else await parent_context.new_page()

        print("--- Testing Teacher (Canary) ---")
        await t_page.goto("http://localhost:5175/login")
        await t_page.wait_for_load_state("networkidle")
        
        # Logout if logged in
        try:
            await t_page.click("button:has-text('Logout')", timeout=2000)
            await t_page.wait_for_timeout(1000)
        except:
            pass
            
        print("Logging in teacher...")
        await fill_login(t_page, "teacher@example.com", "TestPass123!")
        
        if "login" in t_page.url:
            print("Teacher login failed!")
            
        await test_themes(t_page)
        
        print("--- Testing Student (Chrome) ---")
        await s_page.goto("http://localhost:5175/login")
        await s_page.wait_for_load_state("networkidle")
        
        try:
            await s_page.click("button:has-text('Logout')", timeout=2000)
            await s_page.wait_for_timeout(1000)
        except:
            pass
            
        print("Logging in student...")
        await fill_login(s_page, "student@example.com", "TestPass123!")
        
        if "login" in s_page.url:
            print("Student login failed!")
            
        await test_themes(s_page)
        
        print("--- Testing Parent (Chrome) ---")
        await p_page.goto("http://localhost:5175/login")
        await p_page.wait_for_load_state("networkidle")
        
        try:
            await p_page.click("button:has-text('Logout')", timeout=2000)
            await p_page.wait_for_timeout(1000)
        except:
            pass
            
        print("Logging in parent...")
        await fill_login(p_page, "parent@example.com", "TestPass123!")
        
        if "login" in p_page.url:
            print("Parent login failed!")
            
        await test_themes(p_page)
        print("--- All visual tests completed ---")

if __name__ == "__main__":
    asyncio.run(smoke_test())

