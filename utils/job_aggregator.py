import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

class JobAggregator:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        self.seen = set()

    def scrape_linkedin(self, role, location, user_type):
        """Fetch multiple pages from LinkedIn Guest API with experience filters."""
        all_jobs = []
        try:
            search_kw = urllib.parse.quote(role)
            loc_kw = urllib.parse.quote(location)
            domain = "in.linkedin.com" if "india" in location.lower() else "www.linkedin.com"
            
            # Map user_type to LinkedIn f_E (Experience level)
            # 1: Internship, 2: Entry level, 3: Associate, 4: Mid-Senior, 5: Director, 6: Executive
            exp_filter = ""
            if user_type == "Student": exp_filter = "&f_E=1"
            elif user_type == "Fresher": exp_filter = "&f_E=2%2C3"
            elif user_type == "Experienced": exp_filter = "&f_E=4%2C5"

            for start in [0, 25, 50]:
                url = f"https://{domain}/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={search_kw}&location={loc_kw}&f_TPR=r172800&start={start}{exp_filter}"
                resp = requests.get(url, headers=self.headers, timeout=10)
                if resp.status_code != 200: continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                for li in soup.find_all('li'):
                    try:
                        title_elem = li.find('h3', class_='base-search-card__title')
                        if not title_elem: continue
                        title = title_elem.text.strip()
                        company_elem = li.find('h4', class_='base-search-card__subtitle')
                        company = company_elem.text.strip() if company_elem else "Company"
                        link_elem = li.find('a', class_='base-card__full-link')
                        link = link_elem['href'].split('?')[0] if link_elem else "#"
                        
                        fp = f"{title}||{company}".lower()
                        if fp not in self.seen:
                            self.seen.add(fp)
                            all_jobs.append({"role": title, "company": company, "platform": "LinkedIn", "link": link})
                    except: continue
            return all_jobs
        except: return all_jobs

    def scrape_internshala(self, role, location, user_type):
        """Scrape Internshala (only for Students/Freshers)."""
        if user_type == "Experienced": return [] # internshala is for students
        try:
            query = re.sub(r'[^a-zA-Z0-9]+', '-', role.lower()).strip('-')
            loc = re.sub(r'[^a-zA-Z0-9]+', '-', location.lower()).strip('-')
            url = f"https://internshala.com/jobs/keywords-{query}-jobs-in-{loc}/" if loc else f"https://internshala.com/jobs/keywords-{query}/"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200: return []
            soup = BeautifulSoup(resp.text, 'html.parser')
            jobs = []
            for card in soup.find_all('div', class_=re.compile(r'individual_job')):
                try:
                    post_date_elem = card.find('div', class_='status-container')
                    post_text = post_date_elem.text.lower() if post_date_elem else ""
                    if not any(x in post_text for x in ['now', 'today', '1 day', '2 days']):
                        continue
                    title = card.find('h3', class_='job-internship-name').text.strip()
                    company = card.find('p', class_='company-name').text.strip()
                    link = f"https://internshala.com{card.get('data-href', '')}"
                    fp = f"{title}||{company}".lower()
                    if fp not in self.seen:
                        self.seen.add(fp)
                        jobs.append({"role": title, "company": company, "platform": "Internshala", "link": link})
                except: continue
            return jobs
        except: return []

    def scrape_indeed(self, role, location, user_type):
        """Scrape Indeed with experience keywords."""
        all_jobs = []
        try:
            exp_kw = "internship" if user_type == "Student" else ("fresher" if user_type == "Fresher" else "senior")
            search_query = f"{role} {exp_kw}"
            search_kw = urllib.parse.quote(search_query)
            loc_kw = urllib.parse.quote(location if location else "India")
            
            for start in [0, 10, 20]:
                url = f"https://in.indeed.com/jobs?q={search_kw}&l={loc_kw}&fromage=2&start={start}"
                resp = requests.get(url, headers=self.headers, timeout=10)
                if resp.status_code != 200: continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                for card in soup.find_all('div', class_=re.compile(r'job_seen_beacon')):
                    try:
                        title_elem = card.find('h2', class_=re.compile(r'jobTitle'))
                        if not title_elem: continue
                        title = title_elem.text.strip()
                        company_elem = card.find('span', class_=re.compile(r'companyName'))
                        company = company_elem.text.strip() if company_elem else "Indeed Listing"
                        link_elem = title_elem.find('a')
                        jk = link_elem.get('data-jk') if link_elem else None
                        link = f"https://in.indeed.com/viewjob?jk={jk}" if jk else url
                        fp = f"{title}||{company}".lower()
                        if fp not in self.seen:
                            self.seen.add(fp)
                            all_jobs.append({"role": title, "company": company, "platform": "Indeed", "link": link})
                    except: continue
            return all_jobs
        except: return all_jobs

    def scrape_foundit(self, role, location, user_type):
        """Scrape Foundit with experience context."""
        try:
            exp_kw = "fresher" if user_type != "Experienced" else "experienced"
            search_kw = urllib.parse.quote(f"{role} {exp_kw}")
            loc_kw = urllib.parse.quote(location if location else "India")
            url = f"https://www.foundit.in/srp/results?query={search_kw}&locations={loc_kw}"
            return [{"role": f"{role} ({user_type})", "company": "Foundit Source", "platform": "Foundit", "link": url}]
        except: return []

    def fetch_adzuna(self, role, location, user_type):
        """Search Adzuna India."""
        try:
            search_kw = urllib.parse.quote(role)
            loc_kw = urllib.parse.quote(location if location else "India")
            url = f"https://www.adzuna.in/jobs/search?q={search_kw}&l={loc_kw}&max_days_old=2"
            return [{"role": f"{role} Expert", "company": "Hiring Now", "platform": "Adzuna", "link": url}]
        except: return []

    def fetch_remoteok(self, role):
        """Fetch remote jobs from RemoteOK API."""
        try:
            url = "https://remoteok.com/api"
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()
            jobs = []
            for item in data[1:]:
                title = item.get('position', '')
                if role.lower() in title.lower():
                    company = item.get('company', 'RemoteOK')
                    fp = f"{title}||{company}".lower()
                    if fp not in self.seen:
                        self.seen.add(fp)
                        jobs.append({"role": title, "company": company, "platform": "RemoteOK", "link": item.get('url', '')})
            return jobs
        except: return []

    def fetch_jobicy(self, role):
        """Fetch jobs from Jobicy API."""
        try:
            url = f"https://jobicy.com/api/v2/remote-jobs?count=50&geo=india"
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json().get('jobs', [])
            jobs = []
            for item in data:
                title = item.get('jobTitle', '')
                if role.lower() in title.lower():
                    company = item.get('companyName', 'Jobicy')
                    fp = f"{title}||{company}".lower()
                    if fp not in self.seen:
                        self.seen.add(fp)
                        jobs.append({"role": title, "company": company, "platform": "Jobicy", "link": item.get('url', '')})
            return jobs
        except: return []

    def aggregate(self, role, location, country="India", user_type="Fresher"):
        """Run multiple searchers in parallel with high concurrency."""
        results = []
        self.seen = set()
        with ThreadPoolExecutor(max_workers=15) as executor:
            full_loc = f"{location}, {country}" if location else country
            futures = [
                executor.submit(self.scrape_linkedin, role, full_loc, user_type),
                executor.submit(self.scrape_internshala, role, location, user_type),
                executor.submit(self.scrape_indeed, role, location or country, user_type),
                executor.submit(self.scrape_foundit, role, location or country, user_type),
                executor.submit(self.fetch_adzuna, role, location or country, user_type),
                executor.submit(self.fetch_remoteok, role),
                executor.submit(self.fetch_jobicy, role)
            ]
            for f in futures:
                try: results.extend(f.result())
                except: pass
        if not results and location:
            return self.aggregate(role, "", country, user_type)
        return results[:1000]

def find_jobs_realtime(role, location, country, user_type):
    agg = JobAggregator()
    return agg.aggregate(role, location, country, user_type)
