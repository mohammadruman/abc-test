import sys, os, json, asyncio, traceback, re, requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from job_scraper.parsers import get_job_links
from job_scraper.extractors import extract_job_details
from job_scraper.utils import text_contains_any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# ✅ Helper: Scrape Syngenta static pages
def scrape_syngenta_html(start_url, skills, max_jobs=10, max_pages=5):
    print("🕸️ Using static HTML scraper for Syngenta...", file=sys.stderr)
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    all_jobs = []
    page = 1

    while page <= max_pages and len(all_jobs) < max_jobs:
        if "page=" in start_url:
            url = re.sub(r"page=\d+", f"page={page}", start_url)
        elif "?" in start_url:
            url = f"{start_url}&page={page}"
        else:
            url = f"{start_url}?page={page}"

        print(f"🌀 [Syngenta] Fetching page {page} ...", file=sys.stderr)
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code != 200:
                print(f"⚠️ Syngenta failed on page {page} (status {res.status_code})", file=sys.stderr)
                break

            soup = BeautifulSoup(res.text, "html.parser")
            job_cards = soup.select(".attrax-vacancy-tile")

            if not job_cards:
                print("⚠️ No job cards found — stopping pagination.", file=sys.stderr)
                break

            for card in job_cards:
                if len(all_jobs) >= max_jobs:
                    break

                title_el = card.select_one(".attrax-vacancy-tile__title")
                title = title_el.get_text(strip=True) if title_el else "N/A"

                link = title_el["href"] if title_el and title_el.has_attr("href") else None
                if link and not link.startswith("http"):
                    link = f"https://jobs.syngenta.com{link}"

                location_el = card.select_one(".attrax-vacancy-tile__option-location .attrax-vacancy-tile__item-value")
                location = location_el.get_text(strip=True) if location_el else "N/A"

                desc_el = card.select_one(".attrax-vacancy-tile__description-value")
                desc = desc_el.get_text(strip=True) if desc_el else ""

                job_obj = {
                    "company": "Syngenta",
                    "title": title,
                    "location": location,
                    "apply_url": link,
                    "description": desc
                }

                if not skills or any(s.lower() in desc.lower() for s in skills):
                    all_jobs.append(job_obj)

            print(f"✅ [Syngenta] Page {page} done — total jobs: {len(all_jobs)}", file=sys.stderr)
            page += 1
        except Exception as e:
            print(f"❌ Error on Syngenta page {page}: {e}", file=sys.stderr)
            break

    return all_jobs


# ✅ Main async crawler (Barclays)
async def crawl(params):
    start_url = params["url"]
    skills = params["skills"]
    max_jobs = params["max_jobs"]
    max_pages = params["max_pages"]

    # --- handle Syngenta directly ---
    if "syngenta" in start_url.lower():
        results = scrape_syngenta_html(start_url, skills, max_jobs, max_pages)
        print(json.dumps(results))
        return

    results = []
    visited = set()
    retries = 2

    company_name = "Barclays" if "barclays" in start_url.lower() else "Unknown"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()

            print(f"🔍 Detected {company_name} URL — using Playwright scraper.", file=sys.stderr)
            await page.goto(start_url, wait_until="networkidle", timeout=60000)

            await page.wait_for_selector("a[href*='job'], .job, .job-card", timeout=60000)
            await asyncio.sleep(2)

            current_page = 1
            while current_page <= max_pages and len(results) < max_jobs:
                print(f"🌀 Extracting {company_name} page {current_page}", file=sys.stderr)
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
                            job["company"] = company_name
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

                # ✅ Try pagination (Barclays only)
                next_button = await page.query_selector("button[aria-label='Next'], a.pagination__next")
                if next_button:
                    print(f"➡️ Navigating to next page ({current_page+1})", file=sys.stderr)
                    await next_button.click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(4)
                    current_page += 1
                else:
                    print("⚠️ No next button found — stopping pagination.", file=sys.stderr)
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
