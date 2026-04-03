import requests
from bs4 import BeautifulSoup
import re

def scrape_internshala(field, location=""):
    try:
        query = re.sub(r'[^a-zA-Z0-9]+', '-', field.lower()).strip('-')
        loc = re.sub(r'[^a-zA-Z0-9]+', '-', location.lower()).strip('-')
        
        if loc:
            url = f"https://internshala.com/internships/keywords-{query}-internships-in-{loc}/"
        else:
            url = f"https://internshala.com/internships/keywords-{query}/"
            
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        internships = []
        
        cards = soup.find_all('div', class_=re.compile(r'individual_internship'))
        for card in cards[:5]:
            title_elem = card.find('h3', class_='job-internship-name')
            title = title_elem.text.strip() if title_elem else "Role"
            
            company_elem = card.find('p', class_='company-name')
            company = company_elem.text.strip() if company_elem else "Company"
            
            stipend_elem = card.find('span', class_='stipend')
            stipend = stipend_elem.text.strip() if stipend_elem else "Unpaid"
            
            duration_elem = card.find('div', class_='row-1-item')
            # duration is usually near month text
            
            link = "https://internshala.com" + card.get('data-href', '')
            
            internships.append({
                "role": title,
                "company": company,
                "stipend": stipend,
                "link": link
            })
            
        return internships
    except Exception as e:
        return str(e)

print(scrape_internshala("software engineering", "delhi"))
