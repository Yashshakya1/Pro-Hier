import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from datetime import datetime

def scrape_internshala(field: str, location: str = "") -> list:
    """Scrape Internshala ensuring < 3 days old."""
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
            
            company_elem = card.find('p', class_='company-name')
            company = company_elem.text.strip() if company_elem else "Company"
            
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
            if len(internships) >= 5: # Limit
                break
        return internships
    except:
        return []

def scrape_linkedin_live(field: str, location: str = "") -> list:
    """Scrape LinkedIn Guest API strictly limited to past 72 hours (f_TPR=r259200)."""
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
        
        for li in soup.find_all('li')[:5]:
            title_elem = li.find('h3', class_='base-search-card__title')
            title = title_elem.text.strip() if title_elem else "Internship Role"
            
            company_elem = li.find('h4', class_='base-search-card__subtitle')
            company = company_elem.text.strip() if company_elem else "Company"
            
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
            
        return internships
    except:
        return []

def scrape_live_internships(field: str, location: str = "") -> list:
    """Combines LinkedIn and Internshala results strictly < 3 days."""
    linkedin = scrape_linkedin_live(field, location)
    internshala = scrape_internshala(field, location)
    
    # Interleave results for variety
    combined = []
    for i in range(max(len(linkedin), len(internshala))):
        if i < len(linkedin): combined.append(linkedin[i])
        if i < len(internshala): combined.append(internshala[i])
        
    return combined[:10]
