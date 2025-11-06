import sys, os, json, asyncio, traceback, re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from job_scraper.parsers import get_job_links
from job_scraper.extractors import extract_job_details
from job_scraper.utils import text_contains_any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def crawl(params):
    start_url = params["url"]
    skills = params["skills"]
    max_jobs = params["max_jobs"]
    max_pages = params["max_pages"]

    results = []
    visited = set()
    retries = 2

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(start_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)

            current_page = 1
            while current_page <= max_pages and len(results) < max_jobs:
                print(f"🌀 Extracting Barclays page {current_page}", file=sys.stderr)
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                job_links = get_job_links(soup, start_url)
                print(f"🔗 Found {len(job_links)} job links on page {current_page}", file=sys.stderr)

                for link in job_links:
                    if len(results) >= max_jobs or link in visited:
                        continue
                    visited.add(link)

                    for attempt in range(retries):
                        job_page = await context.new_page()
                        try:
                            print(f"➡️ Visiting job {len(results)+1}: {link}", file=sys.stderr)
                            await job_page.goto(link, wait_until="domcontentloaded", timeout=40000)
                            job_html = await job_page.content()
                            job_soup = BeautifulSoup(job_html, "html.parser")
                            job = extract_job_details(job_soup, link)
                            if not skills or text_contains_any(job["description"], skills):
                                results.append(job)
                            await job_page.close()
                            break
                        except Exception as e:
                            print(f"❌ Error scraping job ({attempt+1}/{retries}): {e}", file=sys.stderr)
                            await job_page.close()
                            if attempt < retries - 1:
                                await asyncio.sleep(2)
                            else:
                                print("⏭️ Skipping after retries", file=sys.stderr)

                # ✅ Try clicking the “Next” pagination button
                try:
                    next_button = await page.query_selector("button[aria-label='Next']")
                    if next_button:
                        await next_button.click()
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(3)
                        current_page += 1
                        print(f"➡️ Navigated to next page ({current_page})", file=sys.stderr)
                    else:
                        print("⚠️ No next button found. Stopping pagination.", file=sys.stderr)
                        break
                except Exception as e:
                    print(f"⚠️ Failed to navigate to next page: {e}", file=sys.stderr)
                    break

            await context.close()
            await browser.close()

    except Exception:
        traceback.print_exc(file=sys.stderr)
        return []

    print(json.dumps(results))


if __name__ == "__main__":
    params = json.loads(sys.argv[1])
    asyncio.run(crawl(params))
