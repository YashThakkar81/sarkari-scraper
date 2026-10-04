
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
def find_pdf_links(target_url):
    print(f"🔍 Scanning page for PDFs: {target_url}")
    pdf_links = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # verify=False prevents SSL Certificate Verification failures on government sites
        response = requests.get(target_url, headers=headers, timeout=15, verify=False)
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
# 4. PROCESS PDF WITH GEMINI 2.5 FLASH
# ---------------------------------------------------------------------------
def parse_pdf_with_gemini(pdf_url):
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

        response = client.models.generate_content(
            model='gemini-2.5-flash',
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
