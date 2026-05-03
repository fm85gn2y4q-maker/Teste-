import asyncio
from playwright.async_api import async_playwright

async def extract():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()

        print("Navigating to URL...")
        await page.goto("https://api.draftable.com/compare/wRpSDIPociou", wait_until="networkidle", timeout=60000)

        print("Waiting for content to load...")
        await asyncio.sleep(5)

        # Get the full page title
        title = await page.title()
        print(f"Page title: {title}")

        # Try to get all text content
        full_text = await page.evaluate("""
            () => {
                // Get all text from the page
                const elements = document.querySelectorAll('*');
                let texts = [];
                for (let el of elements) {
                    if (el.children.length === 0 && el.textContent.trim()) {
                        texts.push(el.textContent.trim());
                    }
                }
                return texts.join('\\n');
            }
        """)

        # Also get full inner text
        body_text = await page.inner_text('body')

        # Get HTML structure to understand what's there
        html_snippet = await page.evaluate("() => document.body.innerHTML.substring(0, 5000)")

        # Try to find comparison-specific elements
        # Draftable typically shows documents in iframes or specific containers
        iframes = await page.frames

        print(f"Number of frames: {len(page.frames)}")

        all_content = []
        all_content.append(f"=== PAGE TITLE ===\n{title}\n")
        all_content.append(f"=== URL ===\nhttps://api.draftable.com/compare/wRpSDIPociou\n")
        all_content.append(f"=== BODY TEXT ===\n{body_text}\n")
        all_content.append(f"\n=== EXTRACTED TEXT ELEMENTS ===\n{full_text}\n")

        # Check for iframes and extract content from them
        for i, frame in enumerate(page.frames):
            if frame != page.main_frame:
                try:
                    frame_url = frame.url
                    frame_text = await frame.inner_text('body')
                    if frame_text.strip():
                        all_content.append(f"\n=== IFRAME {i} ({frame_url}) ===\n{frame_text}\n")
                        print(f"Frame {i} URL: {frame_url}")
                except Exception as e:
                    print(f"Error reading frame {i}: {e}")

        # Take a screenshot to see what's visible
        await page.screenshot(path="/home/user/Teste-/screenshot.png", full_page=True)

        # Save HTML for debugging
        html_content = await page.content()
        with open("/home/user/Teste-/page_source.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        content = "\n".join(all_content)
        with open("/home/user/Teste-/conteudo_draftable.txt", "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Content saved. Total chars: {len(content)}")
        print("\nFirst 2000 chars of body text:")
        print(body_text[:2000])

        await browser.close()

asyncio.run(extract())
