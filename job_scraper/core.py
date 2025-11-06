import subprocess
import sys
import json
import re
import requests
import html
from bs4 import BeautifulSoup


def clean_html(raw_html: str) -> str:
    """Convert HTML job description to clean text."""
    if not raw_html:
        return ""
    decoded = html.unescape(raw_html)
    soup = BeautifulSoup(decoded, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def crawl_capgemini_api(start_url, skills, max_jobs=10, max_pages=10):
    """
    Fetches jobs directly from Capgemini's internal API endpoint.
    """
    print("🔍 Detected Capgemini URL — using API endpoint.")
    API_URL = "https://cg-job-search-microservices.azurewebsites.net/api/job-search"
    HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0)"}

    all_jobs = []
    page = 1
    country_code = "in-en"
    size = 50  # jobs per page

    while page <= max_pages and len(all_jobs) < max_jobs:
        params = {
            "page": page,
            "size": size,
            "country_code": country_code
        }

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
                "description": description_text
            }

            if not skills or any(s.lower() in description_text.lower() for s in skills):
                all_jobs.append(job_obj)

        print(f"✅ Page {page}: Collected {len(jobs)} jobs (total: {len(all_jobs)})")
        page += 1

    print(f"🎯 Total collected: {len(all_jobs)} Capgemini jobs.")
    return all_jobs


def crawl_jobs(start_url, skills, max_jobs=10, max_pages=3):
    """
    Smart job crawler:
    - Uses Capgemini API if URL is Capgemini
    - Otherwise uses Playwright worker subprocess
    """
    # ✅ Detect Capgemini and switch to API
    if "capgemini.com" in start_url:
        return crawl_capgemini_api(start_url, skills, max_jobs, max_pages)

    # ✅ Otherwise, fall back to Playwright
    args = [
        sys.executable,
        "-m",
        "job_scraper.run_playwright_worker",
        json.dumps({
            "url": start_url,
            "skills": skills,
            "max_jobs": max_jobs,
            "max_pages": max_pages
        }),
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
