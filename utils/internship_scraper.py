import requests
from bs4 import BeautifulSoup
import re

def scrape_live_internships(field: str, location: str = "") -> list:
    """
    Scrapes real live internships from Internshala based on field and location.
    Returns a list of dictionaries with real details to prevent AI hallucinations.
    """
    try:
        # Format query for URL
        query = re.sub(r'[^a-zA-Z0-9]+', '-', field.lower()).strip('-')
        loc = re.sub(r'[^a-zA-Z0-9]+', '-', location.lower()).strip('-')
        
        if loc:
            url = f"https://internshala.com/internships/keywords-{query}-internships-in-{loc}/"
        else:
            url = f"https://internshala.com/internships/keywords-{query}/"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        internships = []
        
        cards = soup.find_all('div', class_=re.compile(r'individual_internship'))
        for card in cards[:10]: # Fetch top 10 live postings
            # Extract Title
            title_elem = card.find('h2', class_='job-internship-name')
            if not title_elem:
                title_elem = card.find('h3', class_='job-internship-name')
            title = title_elem.text.strip() if title_elem else "Internship Role"
            
            # Extract Company
            company_elem = card.find('p', class_='company-name')
            company = company_elem.text.strip() if company_elem else "Company"
            
            # Extract Stipend
            stipend_elem = card.find('span', class_='stipend')
            stipend = stipend_elem.text.strip() if stipend_elem else "Unpaid / Market Standard"
            
            # Extract Duration (Usually in the meta details)
            duration = "Flexible"
            meta_items = card.find_all('div', class_='item_body')
            for item in meta_items:
                text = item.text.strip().lower()
                if 'month' in text or 'week' in text:
                    duration = item.text.strip()
                    break
            
            # Extract Link
            link_path = card.get('data-href', '')
            if link_path:
                link = f"https://internshala.com{link_path}"
            else:
                link = url
                
            internships.append({
                "role": title,
                "company": company,
                "stipend": stipend,
                "duration": duration,
                "platform": "Internshala",
                "link": link
            })
            
        return internships
    except Exception as e:
        print(f"Scrape Error: {str(e)}")
        return []
