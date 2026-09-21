import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        try:
            print("Connecting to Teacher Canary (9222)...")
            teacher_browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            teacher_context = teacher_browser.contexts[0]
            teacher_page = teacher_context.pages[0] if teacher_context.pages else await teacher_context.new_page()
            
            print("Teacher connected. Checking title...")
            await teacher_page.goto("http://localhost:5173")
            print("Teacher title:", await teacher_page.title())
            
            # Wait a bit
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Teacher connection failed: {e}")

        try:
            print("Connecting to Student Chrome (9223)...")
            student_browser = await p.chromium.connect_over_cdp("http://localhost:9223")
            student_context = student_browser.contexts[0]
            student_page = student_context.pages[0] if student_context.pages else await student_context.new_page()
            
            print("Student connected. Checking title...")
            await student_page.goto("http://localhost:5173")
            print("Student title:", await student_page.title())
            
            # Wait a bit
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Student connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
