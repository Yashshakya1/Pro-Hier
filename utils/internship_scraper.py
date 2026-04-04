import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from datetime import datetime

def is_relevant(title: str, field: str) -> bool:
    t_lower = title.lower()
    f_lower = field.lower()
    
    if f_lower in t_lower: return True
    
    aliases = {
        "ai/ml": ["ai", "ml", "artificial intelligence", "machine learning", "data"],
        "web dev": ["web", "frontend", "backend", "full stack", "fullstack", "react", "node", "django", "php", "javascript"],
        "mobile dev": ["mobile", "android", "ios", "flutter", "react native", "app", "kotlin", "swift"],
        "devops": ["devops", "cloud", "aws", "azure", "docker", "kubernetes", "sre", "platform"],
        "cybersecurity": ["security", "cyber", "infosec", "penetration", "hacker"],
        "data science": ["data", "machine learning", "ai", "ml", "analytics", "scientist", "analyst"],
        "ui/ux design": ["ui", "ux", "design", "figma", "graphic", "product design", "designer"],
        "marketing": ["marketing", "seo", "social media", "digital", "branding", "b2b", "content", "writer"],
        "hr & sales": ["hr", "human resources", "recruiter", "talent", "hiring", "sales", "business development", "bde", "revenue", "account"],
        "finance": ["finance", "accounting", "audit", "tax", "banking", "financial", "economics"]
    }
    
    for key, values in aliases.items():
        if key in f_lower or f_lower in key:
            if any(v in t_lower for v in values):
                return True
                
    f_words = set(re.findall(r'\w+', f_lower))
    t_words = set(re.findall(r'\w+', t_lower))
    stop_words = {"developer", "engineer", "intern", "internship", "role", "student", "specialist"}
    f_words -= stop_words
    
    if not f_words:
        return True
        
    return len(f_words.intersection(t_words)) > 0

def is_entry_level(title: str) -> bool:
    t_lower = title.lower()
    # Reject high-level seniority titles
    senior_keywords = ["senior", "sr.", "sr ", "principal", "lead", "manager", "staff", "vp", "director", "head", "architect", "expert", "vp"]
    for kw in senior_keywords:
        if f"{kw} " in t_lower or f" {kw}" in t_lower or t_lower.startswith(kw):
            return False
    return True

def scrape_internshala(field: str, location: str = "", seen: set = None) -> list:
    """Scrape Internshala ensuring < 3 days old."""
    if seen is None:
        seen = set()
    try:
        if location.lower().strip() == "banglore":
            location = "bangalore"
            
        query = re.sub(r'[^a-zA-Z0-9]+', '-', field.lower()).strip('-')
        loc = re.sub(r'[^a-zA-Z0-9]+', '-', location.lower()).strip('-')
        
        url = f"https://internshala.com/internships/keywords-{query}-internships-in-{loc}/" if loc else f"https://internshala.com/internships/keywords-{query}/"
            
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        internships = []
        
        cards = soup.find_all('div', class_=re.compile(r'individual_internship'))
        for card in cards:
            # Check 3 Day Rule
            status_elem = card.find('div', class_='status-inactive') or card.find('div', class_='status-success') or card.find('div', class_='status-info')
            status_text = status_elem.text.strip().lower() if status_elem else ""
            
            # We reject if it has 'week' or 'month' or '3 days' etc.
            if 'week' in status_text or 'month' in status_text:
                continue
            # Also drop 4 days, 5 days, 6 days.
            if re.search(r'([4-9]|[1-9][0-9]) days ago', status_text):
                continue
                
            title_elem = card.find('h2', class_='job-internship-name') or card.find('h3', class_='job-internship-name')
            title = title_elem.text.strip() if title_elem else "Internship Role"
            
            if not is_relevant(title, field) or not is_entry_level(title):
                continue
                
            if location.strip():
                loc_check = location.lower().strip()
                card_text = card.text.lower()
                if loc_check not in card_text and "work from home" not in card_text and "remote" not in card_text:
                    continue
                    
            company_elem = card.find('p', class_='company-name')
            company = company_elem.text.strip() if company_elem else "Company"
            
            fingerprint = f"{title.lower().strip()}||{company.lower().strip()}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            
            stipend_elem = card.find('span', class_='stipend')
            stipend = stipend_elem.text.strip() if stipend_elem else "Check Listing"
            
            duration = "Flexible"
            for item in card.find_all('div', class_='item_body'):
                t = item.text.strip().lower()
                if 'month' in t or 'week' in t:
                    duration = item.text.strip()
                    break
            
            link_path = card.get('data-href', '')
            link = f"https://internshala.com{link_path}" if link_path else url
                
            internships.append({
                "role": title,
                "company": company,
                "stipend": stipend,
                "duration": duration,
                "platform": "Internshala",
                "link": link
            })
            if len(internships) >= 50: # Increased Limit
                break
        return internships
    except:
        return []

def scrape_linkedin_live(field: str, location: str = "", seen: set = None) -> list:
    """Scrape LinkedIn Guest API strictly limited to past 72 hours (f_TPR=r259200)."""
    if seen is None:
        seen = set()
    try:
        search_kw = urllib.parse.quote(f"{field} internship")
        loc_kw = urllib.parse.quote(location if location else "India")
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={search_kw}&location={loc_kw}&f_TPR=r259200"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        internships = []
        
        for li in soup.find_all('li'):
            title_elem = li.find('h3', class_='base-search-card__title')
            title = title_elem.text.strip() if title_elem else "Internship Role"
            
            if not is_relevant(title, field) or not is_entry_level(title):
                continue
                
            if location.strip():
                loc_check = location.lower().strip()
                card_text = li.text.lower()
                if loc_check not in card_text and "remote" not in card_text and "work from home" not in card_text:
                    continue
                    
            company_elem = li.find('h4', class_='base-search-card__subtitle')
            company = company_elem.text.strip() if company_elem else "Company"
            
            fingerprint = f"{title.lower().strip()}||{company.lower().strip()}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            
            link_elem = li.find('a', class_='base-card__full-link')
            link = link_elem['href'].split('?')[0] if link_elem else "https://linkedin.com/jobs"
            
            internships.append({
                "role": title,
                "company": company,
                "stipend": "Standard",
                "duration": "Depends on Role",
                "platform": "LinkedIn",
                "link": link
            })
            
            if len(internships) >= 50:
                break
            
        return internships
    except:
        return []

def scrape_remoteok(field: str, seen: set = None) -> list:
    """Scrape RemoteOK JSON API for remote internships/jobs."""
    if seen is None:
        seen = set()
    try:
        url = "https://remoteok.com/api"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        jobs = response.json()
        internships = []
        
        # Skip the first item (it's often a legal/info object)
        for job in jobs[1:]:
            if not isinstance(job, dict):
                continue
            title = job.get('position', 'Internship Role')
            
            if not is_relevant(title, field) or not is_entry_level(title):
                continue
                
            location_tag = job.get('location', '').lower()
            if any(x in location_tag for x in ['usa', 'us only', 'uk only', 'europe', 'europe only', 'north america']):
                continue
                
            company = job.get('company', 'Company')
            fingerprint = f"{title.lower().strip()}||{company.lower().strip()}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            
            internships.append({
                "role": title,
                "company": company,
                "stipend": "Paid (Check Listing)",
                "duration": "Remote",
                "platform": "RemoteOK",
                "link": job.get('url', url)
            })
            if len(internships) >= 30:
                break
        return internships
    except:
        return []

def scrape_jobicy(field: str, seen: set = None) -> list:
    """Scrape Jobicy JSON API for unblocked remote tech jobs."""
    if seen is None:
        seen = set()
    try:
        url = "https://jobicy.com/api/v2/remote-jobs"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        jobs = response.json().get('jobs', [])
        internships = []
        
        for job in jobs:
            title = job.get('jobTitle', 'Internship Role')
            
            if not is_relevant(title, field) or not is_entry_level(title):
                continue
                
            geo = job.get('jobGeo', 'Anywhere').lower()
            allowed_geos = ["anywhere", "worldwide", "global", "india", "apac", "asia", "remote"]
            
            is_geo_ok = False
            for g in allowed_geos:
                if g in geo:
                    is_geo_ok = True
                    break
                    
            if not is_geo_ok:
                continue
                
            company = job.get('companyName', 'Company')
            fingerprint = f"{title.lower().strip()}||{company.lower().strip()}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            
            geo = job.get('jobGeo', 'Anywhere')
            
            internships.append({
                "role": title,
                "company": company,
                "stipend": "Paid (Check Listing)",
                "duration": f"Remote ({geo})",
                "platform": "Jobicy",
                "link": job.get('url', url)
            })
            if len(internships) >= 30:
                break
        return internships
    except:
        return []

def scrape_live_internships(field: str, location: str = "") -> list:
    """Combines LinkedIn, Internshala, RemoteOK, and Jobicy results."""
    seen = set()
    linkedin = scrape_linkedin_live(field, location, seen)
    internshala = scrape_internshala(field, location, seen)
    remoteok = scrape_remoteok(field, seen)
    jobicy = scrape_jobicy(field, seen)
    
    # Interleave results for variety
    combined = []
    max_len = max(len(linkedin), len(internshala), len(remoteok), len(jobicy))
    for i in range(max_len):
        if i < len(linkedin): combined.append(linkedin[i])
        if i < len(internshala): combined.append(internshala[i])
        if i < len(remoteok): combined.append(remoteok[i])
        if i < len(jobicy): combined.append(jobicy[i])
        
    result = combined[:150]
    if len(result) == 0 and location.strip():
        # Fallback to nationwide search if location is too restrictive
        return scrape_live_internships(field, "")
    
    return result
