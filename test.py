from playwright.sync_api import sync_playwright

print("Launching Playwright test...")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://example.com")
    print("Page title:", page.title())
    browser.close()

print("✅ Playwright test completed successfully.")
