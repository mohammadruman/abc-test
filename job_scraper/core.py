import subprocess
import sys
import json
import re
import requests
import html
from bs4 import BeautifulSoup


# --------------------------- #
# ✅ Utility for cleaning HTML
# --------------------------- #
def clean_html(raw_html: str) -> str:
    """Convert HTML job description to clean text."""
    if not raw_html:
        return ""
    decoded = html.unescape(raw_html)
    soup = BeautifulSoup(decoded, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


# --------------------------- #
# ✅ Capgemini API Scraper (KEEPED)
# --------------------------- #
def crawl_capgemini_api(start_url, skills, max_jobs=10, max_pages=10):
    """Fetches jobs directly from Capgemini's internal API endpoint."""
    print("🔍 Detected Capgemini URL — using API endpoint.")
    API_URL = "https://cg-job-search-microservices.azurewebsites.net/api/job-search"
    HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0)"}

    all_jobs = []
    page = 1
    country_code = "in-en"
    size = 50  # jobs per page

    while page <= max_pages and len(all_jobs) < max_jobs:
        params = {"page": page, "size": size, "country_code": country_code}

        try:
            response = requests.get(API_URL, headers=HEADERS, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"❌ Error fetching page {page}: {e}")
            break

        jobs = data.get("data", [])
        if not jobs:
            print(f"⚠️ No jobs found after page {page}. Stopping.")
            break

        for job in jobs:
            if len(all_jobs) >= max_jobs:
                break
            description_text = clean_html(job.get("description", ""))
            job_obj = {
                "job_id": job.get("id"),
                "title": job.get("title"),
                "brand": job.get("brand"),
                "contract_type": job.get("contract_type"),
                "experience_level": job.get("experience_level"),
                "professional_community": job.get("professional_communities"),
                "location": job.get("location"),
                "department": job.get("department"),
                "sbu": job.get("sbu"),
                "apply_url": job.get("apply_job_url"),
                "description": description_text,
            }

            if not skills or any(s.lower() in description_text.lower() for s in skills):
                all_jobs.append(job_obj)

        print(f"✅ Page {page}: Collected {len(jobs)} jobs (total: {len(all_jobs)})")
        page += 1

    print(f"🎯 Total collected: {len(all_jobs)} Capgemini jobs.")
    return all_jobs


# --------------------------- #
# ✅ Barclays Scraper (NEW)
# --------------------------- #
def crawl_barclays(start_url, skills, max_jobs=10, max_pages=5):
    print("🔍 Detected Barclays URL — using static HTML scraper.")
    HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0)"}

    all_jobs = []
    page = 1

    while page <= max_pages and len(all_jobs) < max_jobs:
        # Barclays pagination uses CurrentPage in query string
        if "CurrentPage=" in start_url:
            url = re.sub(r"CurrentPage=\d+", f"CurrentPage={page}", start_url)
        elif "?" in start_url:
            url = f"{start_url}&CurrentPage={page}"
        else:
            url = f"{start_url}?CurrentPage={page}"

        print(f"🌀 [Barclays] Fetching page {page} ...")
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            if response.status_code != 200:
                print(f"⚠️ Barclays failed on page {page}: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.select(".list-item.list-item--card")

            if not job_cards:
                print("⚠️ No job cards found — possibly last page.")
                break

            for card in job_cards:
                if len(all_jobs) >= max_jobs:
                    break

                # Extract title and link
                title_tag = card.select_one(".job-title--link")
                title = title_tag.get_text(strip=True) if title_tag else "N/A"
                link = title_tag["href"] if title_tag and title_tag.has_attr("href") else None
                if link and not link.startswith("http"):
                    link = f"https://search.jobs.barclays{link}"

                # Extract location
                location_tag = card.select_one(".job-location")
                location = location_tag.get_text(strip=True) if location_tag else "N/A"

                # Extract posted date
                date_tag = card.select_one(".job-date span")
                date_posted = date_tag.get_text(strip=True) if date_tag else "N/A"

                job = {
                    "company": "Barclays",
                    "title": title,
                    "location": location,
                    "date_posted": date_posted,
                    "apply_url": link,
                    "description": "",
                }

                # Filter by skill if provided
                if not skills or any(s.lower() in title.lower() for s in skills):
                    all_jobs.append(job)

            print(f"✅ [Barclays] Page {page} done — total jobs so far: {len(all_jobs)}")
            page += 1

        except Exception as e:
            print(f"❌ Error scraping Barclays page {page}: {e}")
            break

    print(f"🎯 Total collected: {len(all_jobs)} Barclays jobs.")
    return all_jobs


# --------------------------- #
# ✅ Main Dispatcher
# --------------------------- #
def crawl_jobs(start_url, skills, max_jobs=10, max_pages=3):
    """
    Smart job crawler:
    - Capgemini → API-based
    - Barclays → HTML-based
    - Others → Playwright worker
    """
    if "capgemini.com" in start_url:
        return crawl_capgemini_api(start_url, skills, max_jobs, max_pages)

    elif "barclays" in start_url:
        return crawl_barclays(start_url, skills, max_jobs, max_pages)

    # ✅ Fallback for all other URLs (like Syngenta)
    args = [
        sys.executable,
        "-m",
        "job_scraper.run_playwright_worker",
        json.dumps(
            {
                "url": start_url,
                "skills": skills,
                "max_jobs": max_jobs,
                "max_pages": max_pages,
            }
        ),
    ]
    out = subprocess.run(args, capture_output=True, text=True)

    if out.returncode != 0:
        print("❌ Subprocess failed:\n", out.stderr)
        return []

    if not out.stdout.strip():
        print("⚠️ Worker returned no JSON. STDERR:\n", out.stderr)
        return []

    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        print("⚠️ Could not decode worker output:\n", out.stdout)
        return []
