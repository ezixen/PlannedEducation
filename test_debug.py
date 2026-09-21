import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser_t = await p.chromium.connect_over_cdp('http://localhost:9222')
        context_t = browser_t.contexts[0]
        page_t = context_t.pages[0] if context_t.pages else await context_t.new_page()
        
        page_t.on('console', lambda msg: print(f'Console: {msg.text}'))
        
        await page_t.goto('http://localhost:5173/login')
        await page_t.fill("input[placeholder='Email address']", 'teacher3@test.com')
        await page_t.fill("input[placeholder='Password']", 'password123')
        print("Clicking submit...")
        await page_t.click("button[type='submit']")
        
        await asyncio.sleep(2)
        print("Current URL:", page_t.url)
        body = await page_t.inner_text("body")
        print("Body preview:", body[:100])

asyncio.run(main())
