import os
import re
import json
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# Disable SSL warning popups for government portals with self-signed SSL certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# 1. CONFIGURATION & CREDENTIALS
# ---------------------------------------------------------------------------
WP_SITE_URL = "https://sarkarijobsguide.in"
WP_USERNAME = "yashthakkar81@gmail.com"
WP_APP_PASSWORD = "x3Gi 5gKg WuHp YnWI K56d xiXy"  # Paste your WordPress Application Password here

GEMINI_API_KEY = "AQ.Ab8RN6LyR03t9eBaZX6cQMuX-yxLOv3bfSN8KJ_qPKyIKUcb_A"            # Paste your Gemini API key here

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# 2. FETCH SETTINGS FROM YOUR WORDPRESS PLUGIN
# ---------------------------------------------------------------------------
def get_wp_settings():
    endpoint = f"{WP_SITE_URL}/wp-json/sarkari-ai/v1/settings"
    try:
        response = requests.get(endpoint, timeout=10, verify=False)
        if response.status_code == 200:
            print("✅ WordPress settings endpoint reachable!")
            return response.json()
    except Exception as e:
        print(f"❌ Error fetching WP settings: {e}")
    
    return {
        "max_age_days": 7,
        "post_status": "draft",
        "target_urls": [
            "https://ssc.gov.in/notice-board",
            "https://apsc.nic.in/notif_2026.html",
            "https://www.ibps.in/careers/"
        ]
    }

# ---------------------------------------------------------------------------
# 3. SCRAPE TARGET URL FOR PDF LINKS
# ---------------------------------------------------------------------------
import ssl
import urllib3

# Suppress insecure request warnings caused by disabling SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacySSLAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Supports legacy ciphers used by government servers
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

def find_pdf_links(target_url):
    print(f"🔍 Scanning page for PDFs: {target_url}")
    pdf_links = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        session = requests.Session()
        session.verify = False
        session.headers.update(headers)
        adapter = LegacySSLAdapter()
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        response = session.get(target_url, timeout=20, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')

        for link in soup.find_all('a', href=True):
            href = link['href']
            if '.pdf' in href.lower():
                if not href.startswith('http'):
                    href = requests.compat.urljoin(target_url, href)
                pdf_links.append(href)
    except Exception as e:
        print(f"❌ Scraper error on {target_url}: {e}")

    return list(set(pdf_links))

# ---------------------------------------------------------------------------
# 4. PROCESS PDF WITH GEMINI 3.8 FLASH
# ---------------------------------------------------------------------------
import time
import random

def parse_pdf_with_gemini(pdf_url, max_retries=4):
    print(f"📥 Downloading PDF for AI Analysis: {pdf_url}")
    try:
        pdf_response = requests.get(pdf_url, timeout=25, verify=False)
        pdf_bytes = pdf_response.content

        prompt = """
        Analyze this official recruitment notification PDF.
        Extract the following information and output strictly valid JSON matching this schema:
        {
          "job_title": "Full Official Job Title",
          "notification_issue_date": "YYYY-MM-DD",
          "total_vacancies": "Total positions or 'Not Specified'",
          "eligibility_summary": "Brief eligibility requirements",
          "last_date_to_apply": "YYYY-MM-DD or 'Not Specified'",
          "formatted_post_content": "HTML formatted blog post including heading <h2>, overview, eligibility table, important dates table, and official link."
        }
        """

        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=[
                        types.Part.from_bytes(
                            data=pdf_bytes,
                            mime_type='application/pdf',
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                return json.loads(response.text)
            except Exception as e:
                if "503" in str(e) and attempt < max_retries:
                    wait_time = (attempt * 10) + random.randint(1, 5)
                    print(f"⚠️ 503 High Demand Error. Retrying in {wait_time}s (Attempt {attempt}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    raise e

    except Exception as e:
        print(f"❌ Gemini Parsing Error: {e}")
        return None

# ---------------------------------------------------------------------------
# 5. POST DRAFT TO WORDPRESS REST API
# ---------------------------------------------------------------------------
def create_wordpress_draft(data, post_status):
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    
    post_body = {
        "title": data.get("job_title", "New Job Notification"),
        "content": data.get("formatted_post_content", ""),
        "status": post_status
    }
    
    try:
        response = requests.post(
            endpoint,
            auth=(WP_USERNAME, WP_APP_PASSWORD),
            json=post_body,
            timeout=15,
            verify=False
        )
        if response.status_code in [200, 201]:
            print(f"🎉 SUCCESS! Draft created in WordPress: {data.get('job_title')}")
        else:
            print(f"❌ Failed to post to WP. Status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ WordPress REST API Error: {e}")

# ---------------------------------------------------------------------------
# 6. MAIN EXECUTION CONTROLLER
# ---------------------------------------------------------------------------
def main():
    settings = get_wp_settings()
    max_days = settings.get("max_age_days", 7)
    post_status = settings.get("post_status", "draft")
    target_urls = settings.get("target_urls", [])

    print(f"🚀 Engine started. Age limit: {max_days} days | Post status: {post_status}")
    cutoff_date = datetime.now() - timedelta(days=max_days)

    for url in target_urls:
        pdf_list = find_pdf_links(url)
        print(f"📄 Found {len(pdf_list)} PDF link(s) on {url}.")
        
        for pdf_url in pdf_list[:2]:  # Test with first 2 PDFs found
            extracted_data = parse_pdf_with_gemini(pdf_url)
            
            if not extracted_data:
                continue

            issue_date_str = extracted_data.get("notification_issue_date", "")
            try:
                issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
                if issue_date < cutoff_date:
                    print(f"⛔ Skipped old post dated {issue_date_str}. Cutoff date is {cutoff_date.strftime('%Y-%m-%d')}")
                    continue
            except ValueError:
                print(f"⚠️ Could not parse date ({issue_date_str}). Proceeding...")

            create_wordpress_draft(extracted_data, post_status)

if __name__ == "__main__":
    main()
