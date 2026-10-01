import os
import re
import json
import requests
import urllib3
import ssl
import time
import random
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
WP_APP_PASSWORD = "wROu XuCa YNm1 aC5k ah1B zBq9"  # Paste your WordPress Application Password here

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
            "target_urls": [
            "https://ssc.gov.in/",
            "https://www.ibps.in/careers/",
            "https://tpsc.tripura.gov.in/advertisement",
            "https://appsc.gov.in/Index/sub_page/doc2195/Advertisements",
            "https://mppsc.mp.gov.in/Advertisement",
            "https://psc.uk.gov.in/candidate-corner/recruitment",
            "https://rpsc.rajasthan.gov.in/advertisements",
            "https://uppsc.up.nic.in/CandidatePages/Notifications.aspx",
            "https://gpsc.goa.gov.in/advertisements/",
            "https://mpscmanipur.gov.in/whats_new.html",
            "https://spsc.sikkim.gov.in/Advertisement.html",
            "https://gpsc.gujarat.gov.in/dashboard?stage=Advertisement",
            "https://www.jpsc.gov.in/",
            "https://www.opsc.gov.in/Public/OPSC/Default.aspx",
            "https://psc.cg.gov.in/htm/Advertisement%20-%20Latest.htm",
            "https://hpsc.gov.in/en-us/Instructions",
            "https://ppsc.gov.in/Advertisement/openadv.aspx?id=1",
            "https://www.upsc.gov.in/recruitment/recruitment-advertisement",
            "https://hppsc.hp.gov.in/CommonControls/ViewContinuousLinkPage?qs=mhlKjiXMMItGo46f60VBXX8%2B1SQ83OzVLj9MfDScpvboDSdMygkK4iLV47Bu%2FJzMpJLanI%2BihrK9p8W6JsSQUgHTy39NyiuO%BFtbEmiPQyc%3D",
            "https://apsc.nic.in/advt_2026.php#advertisement",
            "https://mpsc.mizoram.gov.in/category/notifications",
            "https://www.ossc.gov.in/Public/OSSC/Default.aspx",
            "https://www.hssc.gov.in/advertisement",
            "https://ladakh.gov.in/recruitment-corner/",
            "https://lakshadweep.gov.in/notice_category/recruitment/",
            "https://dpar.py.gov.in/Exam/Recruitment/Recruitment.htm",
            "https://dnh.gov.in/notice_category/job/",
            "https://ddd.gov.in/#1600945272016-0a6a909f-83cb",
            "https://ddd.gov.in/notice-category/Recruitments/",
            "https://northmiddle.andaman.nic.in/past-notices/recruitment/",
            "https://andamannicobar.gov.in/vacancy_all",
            "https://ssbodisha.ac.in/advertisement/",
            "https://rsmssb.rajasthan.gov.in/page?menuName=EJwE/Y7GD1hMok0YfKTFOtUJMJFGLBa;455611;jbRgWtRe9q4=",
            "https://sssc.uk.gov.in/recruitment-notification/",
            "https://dsssb.delhi.gov.in/",
            "https://gsssb.gujarat.gov.in/Notification",
            "https://rssb.rajasthan.gov.in/advertisements",
            "https://upsssc.gov.in/AllNotifications.aspx",
            "https://bankofbaroda.bank.in/career/current-opportunities",
            "https://www.southindianbank.bank.in/",
            "https://sbi.bank.in/web/careers/current-openings",
            "https://www.idbi.bank.in/idbi-bank-careers-current-openings.aspx",
            "https://rajcrb.rajasthan.gov.in/RecruitmentAdvertisements.aspx?menu_id=13",
            "https://www.nhb.org.in/oppurtunitiesnhb/",
            "https://opportunities.rbi.org.in/Scripts/Vacancies.aspx",
            "https://pnb.bank.in/Recruitments.aspx",
            "https://bankofindia.bank.in/career/recruitment-notice",
            "https://www.canarabank.bank.in/pages/career",
            "https://www.nainitalbank.bank.in/en/Careers/careerslist",
            "https://www.nabard.org/careers-notices1.aspx?cid=693&id=26",
            "https://www.epfo.gov.in/recruitments/",
            "https://licindia.in/en/web/guest/careers",
            "https://esic.gov.in/recruitments",
            "https://jkb.bank.in/career"
        ]
    }

# ---------------------------------------------------------------------------
# 3. SCRAPE TARGET URL FOR PDF LINKS
# ---------------------------------------------------------------------------
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
          "advt_number": "Notification/Advertisement reference number or 'N/A'",
          "hiring_organization": "Official board or department name (e.g. SSC, IBPS, UPSC)",
          "job_location": "City/State or 'India'",
          "salary_amount": 0,
          "formatted_post_content": "HTML formatted blog post including heading <h2>, overview, eligibility table, important dates table, and official link."
        }
        Note:
        - If salary_amount is a range or monthly pay, extract the lower or standard numeric integer value (e.g., 35400). If unspecified, set to 0.
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
# 5. SCHEMA.ORG JSON-LD GENERATOR (Task 1)
# ---------------------------------------------------------------------------
def build_job_schema(data):
    """
    Generates Google-compliant JobPosting JSON-LD script tag.
    """
    issue_date = data.get("notification_issue_date") or datetime.now().strftime("%Y-%m-%d")
    
    # Calculate fallback closing date if not provided (+30 days)
    last_date = data.get("last_date_to_apply")
    if not last_date or "Not Specified" in str(last_date):
        valid_through = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT23:59:59")
    else:
        valid_through = f"{last_date}T23:59:59"

    org_name = data.get("hiring_organization") or "Government Recruitment Board"
    location = data.get("job_location") or "India"

    schema = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": data.get("job_title", "Government Job Vacancy"),
        "description": data.get("eligibility_summary", "Official government recruitment notification."),
        "identifier": {
            "@type": "PropertyValue",
            "name": org_name,
            "value": data.get("advt_number", "N/A")
        },
        "datePosted": issue_date,
        "validThrough": valid_through,
        "employmentType": "FULL_TIME",
        "hiringOrganization": {
            "@type": "Organization",
            "name": org_name,
            "sameAs": WP_SITE_URL
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": location,
                "addressRegion": location,
                "addressCountry": "IN"
            }
        }
    }

    # Include base salary if available
    salary_val = data.get("salary_amount", 0)
    if isinstance(salary_val, (int, float)) and salary_val > 0:
        schema["baseSalary"] = {
            "@type": "MonetaryAmount",
            "currency": "INR",
            "value": {
                "@type": "QuantitativeValue",
                "value": salary_val,
                "unitText": "MONTH"
            }
        }

    return f'\n\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>\n'

# ---------------------------------------------------------------------------
# 6. POST DRAFT TO WORDPRESS REST API
# ---------------------------------------------------------------------------
def create_wordpress_draft(data, post_status):
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    
    # Build post body with JSON-LD Schema attached
    post_html = data.get("formatted_post_content", "")
    schema_markup = build_job_schema(data)
    final_content = post_html + schema_markup

    post_body = {
        "title": data.get("job_title", "New Job Notification"),
        "content": final_content,
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
            print(f"🎉 SUCCESS! Draft created in WordPress (with JobPosting Schema): {data.get('job_title')}")
        else:
            print(f"❌ Failed to post to WP. Status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ WordPress REST API Error: {e}")

# ---------------------------------------------------------------------------
# 7. MAIN EXECUTION CONTROLLER
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
