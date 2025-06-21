import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
from filters import JobFilter
import trafilatura
from urllib.parse import urljoin, urlparse
import json

class JobScraper:
    def __init__(self, config):
        self.config = config
        self.filter = JobFilter(config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.rate_limit_delay = 2  # seconds between requests
        
    def scrape_all_sites(self, progress_callback=None):
        """Scrape all configured sites and return filtered results"""
        all_jobs = []
        
        for site in self.config['sites']:
            if progress_callback:
                progress_callback(f"Scraping {site}...")
            
            try:
                if site.lower() == 'remoteok':
                    jobs = self.scrape_remoteok()
                elif site.lower() == 'wellfound':
                    jobs = self.scrape_wellfound()
                elif site.lower() == 'weworkremotely':
                    jobs = self.scrape_weworkremotely()
                elif site.lower() == 'remotive':
                    jobs = self.scrape_remotive()
                elif site.lower() == 'justremote':
                    jobs = self.scrape_justremote()
                elif site.lower() == 'linkedin':
                    jobs = self.scrape_linkedin()
                else:
                    continue
                
                if progress_callback:
                    progress_callback(f"Found {len(jobs)} jobs from {site}, filtering...")
                
                # Filter jobs
                filtered_jobs = []
                for job in jobs:
                    if self.filter.passes_all_filters(job):
                        filtered_jobs.append(job)
                
                all_jobs.extend(filtered_jobs)
                
                if progress_callback:
                    progress_callback(f"Added {len(filtered_jobs)} jobs from {site}")
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error scraping {site}: {str(e)}")
                continue
        
        return all_jobs
    
    def scrape_remoteok(self):
        """Scrape jobs from RemoteOK"""
        jobs = []
        
        try:
            # RemoteOK has a JSON API endpoint
            url = "https://remoteok.io/api"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Skip the first item which is metadata
            if len(data) > 1:
                job_listings = data[1:]
            else:
                job_listings = []
            
            count = 0
            for job_data in job_listings:
                if count >= self.config['max_jobs_per_site']:
                    break
                
                try:
                    job = {
                        'title': job_data.get('position', ''),
                        'company': job_data.get('company', ''),
                        'job_type': 'Remote',
                        'salary': self.extract_salary_from_text(job_data.get('description', '')),
                        'benefits': '',
                        'description': job_data.get('description', ''),
                        'apply_link': job_data.get('url', ''),
                        'tags': job_data.get('tags', []),
                        'source_site': 'RemoteOK',
                        'scraped_at': datetime.now().isoformat(),
                        'raw_data': job_data
                    }
                    
                    jobs.append(job)
                    count += 1
                    
                except Exception as e:
                    continue
                
                time.sleep(self.rate_limit_delay)
                
        except Exception as e:
            print(f"Error scraping RemoteOK: {e}")
        
        return jobs
    
    def scrape_wellfound(self):
        """Scrape jobs from Wellfound (AngelList)"""
        jobs = []
        
        # Note: Wellfound requires more complex scraping due to their anti-bot measures
        # This is a simplified version that attempts to scrape public job listings
        
        try:
            # Try to access the public jobs page
            url = "https://wellfound.com/jobs"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for job listing elements (this may need adjustment based on current HTML structure)
            job_elements = soup.find_all(['div', 'article'], class_=re.compile(r'job|listing|card'))
            
            count = 0
            for job_element in job_elements:
                if count >= self.config['max_jobs_per_site']:
                    break
                
                try:
                    # Extract job information
                    title_elem = job_element.find(['h1', 'h2', 'h3', 'a'], string=re.compile(r'engineer|developer|analyst|data|software', re.I))
                    if not title_elem:
                        title_elem = job_element.find(['h1', 'h2', 'h3'])
                    
                    company_elem = job_element.find(string=re.compile(r'company|startup', re.I))
                    if not company_elem:
                        company_elem = job_element.find(['span', 'div'], class_=re.compile(r'company'))
                    
                    # Extract text content for better parsing
                    job_text = job_element.get_text(strip=True)
                    
                    if not job_text or len(job_text) < 50:
                        continue
                    
                    job = {
                        'title': title_elem.get_text(strip=True) if title_elem else self.extract_title_from_text(job_text),
                        'company': company_elem.get_text(strip=True) if company_elem else self.extract_company_from_text(job_text),
                        'job_type': 'Remote',
                        'salary': self.extract_salary_from_text(job_text),
                        'benefits': self.extract_benefits_from_text(job_text),
                        'description': job_text,
                        'apply_link': self.extract_apply_link(job_element),
                        'tags': ['Startup', 'Tech'],
                        'source_site': 'Wellfound',
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    # Only add if we have meaningful data
                    if job['title'] and job['company']:
                        jobs.append(job)
                        count += 1
                    
                except Exception as e:
                    continue
                
                time.sleep(self.rate_limit_delay)
                
        except Exception as e:
            print(f"Error scraping Wellfound: {e}")
            # Fallback: try to get some sample startup job data
            jobs = self.get_fallback_startup_jobs()
        
        return jobs
    
    def get_fallback_startup_jobs(self):
        """Fallback method to demonstrate structure when direct scraping fails"""
        # This would normally not be used in production, but provides structure
        return []
    
    def extract_salary_from_text(self, text):
        """Extract salary information from job text"""
        if not text:
            return ''
        
        # Look for salary patterns
        salary_patterns = [
            r'\$[\d,]+\s*-\s*\$[\d,]+',  # $50,000 - $70,000
            r'\$[\d,]+k?\s*-\s*[\d,]+k?',  # $50k - 70k
            r'[\d,]+\s*-\s*[\d,]+\s*USD',  # 50,000 - 70,000 USD
            r'salary:\s*\$?[\d,]+',  # salary: $50000
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ''
    
    def extract_benefits_from_text(self, text):
        """Extract benefits information from job text"""
        if not text:
            return ''
        
        benefit_keywords = [
            'health insurance', 'dental', 'vision', '401k', 'equity', 'stock options',
            'flexible schedule', 'work from home', 'unlimited pto', 'vacation',
            'parental leave', 'learning budget', 'conference', 'gym membership'
        ]
        
        found_benefits = []
        text_lower = text.lower()
        
        for benefit in benefit_keywords:
            if benefit in text_lower:
                found_benefits.append(benefit.title())
        
        return ', '.join(found_benefits)
    
    def extract_title_from_text(self, text):
        """Extract job title from text using common patterns"""
        title_patterns = [
            r'(senior|junior|lead)?\s*(software|web|frontend|backend|full.?stack|data)\s*(engineer|developer|analyst)',
            r'(python|javascript|react|node\.?js|django)\s*(developer|engineer)',
            r'(devops|cloud|platform)\s*(engineer|specialist)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        # Fallback: look for common job titles
        lines = text.split('\n')
        for line in lines[:5]:  # Check first few lines
            if any(keyword in line.lower() for keyword in ['engineer', 'developer', 'analyst']):
                return line.strip()[:100]  # Limit length
        
        return 'Tech Position'
    
    def extract_company_from_text(self, text):
        """Extract company name from text"""
        lines = text.split('\n')
        
        # Look for company indicators
        for line in lines[:10]:  # Check first 10 lines
            if any(indicator in line.lower() for indicator in ['company:', 'startup:', 'at ']):
                # Extract the company name
                company = re.sub(r'(company:|startup:|at\s)', '', line, flags=re.IGNORECASE).strip()
                return company[:50]  # Limit length
        
        # Fallback: return first substantial line
        for line in lines[:5]:
            if len(line.strip()) > 3 and len(line.strip()) < 100:
                return line.strip()
        
        return 'Startup Company'
    
    def extract_apply_link(self, job_element):
        """Extract application link from job element"""
        # Look for apply links
        apply_link = job_element.find('a', string=re.compile(r'apply|join|contact', re.I))
        if apply_link and apply_link.get('href'):
            return apply_link['href']
        
        # Look for any external links
        external_links = job_element.find_all('a', href=True)
        for link in external_links:
            href = link['href']
            if href.startswith('http') and 'apply' in href.lower():
                return href
        
        return ''
    
    def scrape_weworkremotely(self):
        """Scrape jobs from WeWorkRemotely"""
        jobs = []
        
        try:
            url = "https://weworkremotely.com/categories/remote-programming-jobs"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            job_elements = soup.find_all('li', class_='feature')
            
            count = 0
            for job_element in job_elements:
                if count >= self.config['max_jobs_per_site']:
                    break
                
                try:
                    title_elem = job_element.find('span', class_='title')
                    company_elem = job_element.find('span', class_='company')
                    link_elem = job_element.find('a')
                    
                    if title_elem and company_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'job_type': 'Remote',
                            'salary': '',
                            'benefits': '',
                            'description': title_elem.get_text(strip=True),
                            'apply_link': f"https://weworkremotely.com{link_elem['href']}" if link_elem else '',
                            'tags': ['Remote', 'Tech'],
                            'source_site': 'WeWorkRemotely',
                            'scraped_at': datetime.now().isoformat()
                        }
                        jobs.append(job)
                        count += 1
                    
                except Exception:
                    continue
                
                time.sleep(self.rate_limit_delay)
                
        except Exception as e:
            print(f"Error scraping WeWorkRemotely: {e}")
        
        return jobs
    
    def scrape_remotive(self):
        """Scrape jobs from Remotive"""
        jobs = []
        
        try:
            url = "https://remotive.io/remote-jobs/software-dev"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            job_elements = soup.find_all('div', class_=['job-tile', 'job-list-item'])
            
            count = 0
            for job_element in job_elements:
                if count >= self.config['max_jobs_per_site']:
                    break
                
                try:
                    title_elem = job_element.find(['h3', 'h2', 'a'], class_=['job-title', 'title'])
                    company_elem = job_element.find(['span', 'div'], class_=['company', 'company-name'])
                    
                    if title_elem and company_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'job_type': 'Remote',
                            'salary': '',
                            'benefits': '',
                            'description': title_elem.get_text(strip=True),
                            'apply_link': title_elem.get('href', '') if title_elem.name == 'a' else '',
                            'tags': ['Remote', 'Tech'],
                            'source_site': 'Remotive',
                            'scraped_at': datetime.now().isoformat()
                        }
                        jobs.append(job)
                        count += 1
                    
                except Exception:
                    continue
                
                time.sleep(self.rate_limit_delay)
                
        except Exception as e:
            print(f"Error scraping Remotive: {e}")
        
        return jobs
    
    def scrape_justremote(self):
        """Scrape jobs from JustRemote"""
        jobs = []
        
        try:
            url = "https://justremote.co/remote-developer-jobs"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            job_elements = soup.find_all('div', class_=['job-card', 'job-item'])
            
            count = 0
            for job_element in job_elements:
                if count >= self.config['max_jobs_per_site']:
                    break
                
                try:
                    title_elem = job_element.find(['h3', 'h2', 'a'])
                    company_elem = job_element.find('span', class_='company')
                    
                    if title_elem and company_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'job_type': 'Remote',
                            'salary': '',
                            'benefits': '',
                            'description': title_elem.get_text(strip=True),
                            'apply_link': title_elem.get('href', '') if title_elem.name == 'a' else '',
                            'tags': ['Remote', 'Tech'],
                            'source_site': 'JustRemote',
                            'scraped_at': datetime.now().isoformat()
                        }
                        jobs.append(job)
                        count += 1
                    
                except Exception:
                    continue
                
                time.sleep(self.rate_limit_delay)
                
        except Exception as e:
            print(f"Error scraping JustRemote: {e}")
        
        return jobs
    
    def scrape_linkedin(self):
        """Scrape jobs from LinkedIn with recruiter info"""
        jobs = []
        
        try:
            # LinkedIn jobs search URL for remote positions
            url = "https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=Remote&f_TPR=r86400&f_WT=2"
            
            # Enhanced headers to mimic real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # LinkedIn job cards have specific class names
            job_elements = soup.find_all('div', class_=['job-search-card', 'base-card'])
            
            count = 0
            for job_element in job_elements:
                if count >= self.config['max_jobs_per_site']:
                    break
                
                try:
                    # Extract job title
                    title_elem = job_element.find('h3', class_='base-search-card__title')
                    if not title_elem:
                        title_elem = job_element.find('a', class_='job-search-card__title-link')
                    
                    # Extract company
                    company_elem = job_element.find('h4', class_='base-search-card__subtitle')
                    if not company_elem:
                        company_elem = job_element.find('a', class_='hidden-nested-link')
                    
                    # Extract location
                    location_elem = job_element.find('span', class_='job-search-card__location')
                    
                    # Extract job link for more details
                    link_elem = job_element.find('a', href=True)
                    job_url = link_elem['href'] if link_elem else ''
                    
                    # Try to get recruiter info by following the job link
                    recruiter_info = self.get_linkedin_recruiter_info(job_url) if job_url else {}
                    
                    if title_elem and company_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True),
                            'job_type': 'Remote',
                            'location': location_elem.get_text(strip=True) if location_elem else 'Remote',
                            'salary': '',
                            'benefits': '',
                            'description': title_elem.get_text(strip=True),
                            'apply_link': job_url,
                            'recruiter_name': recruiter_info.get('name', ''),
                            'recruiter_title': recruiter_info.get('title', ''),
                            'recruiter_linkedin': recruiter_info.get('profile_url', ''),
                            'tags': ['Remote', 'Tech', 'LinkedIn'],
                            'source_site': 'LinkedIn',
                            'scraped_at': datetime.now().isoformat()
                        }
                        jobs.append(job)
                        count += 1
                    
                except Exception as e:
                    continue
                
                time.sleep(self.rate_limit_delay * 2)  # Longer delay for LinkedIn
                
        except Exception as e:
            print(f"Error scraping LinkedIn: {e}")
            # Note: LinkedIn has strong anti-bot measures, this is expected
        
        return jobs
    
    def get_linkedin_recruiter_info(self, job_url):
        """Extract recruiter information from LinkedIn job page"""
        recruiter_info = {}
        
        try:
            if not job_url.startswith('http'):
                job_url = f"https://www.linkedin.com{job_url}"
            
            response = self.session.get(job_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for recruiter/hiring manager information
            recruiter_section = soup.find('div', class_=['job-details-hiring-team', 'hiring-team'])
            
            if recruiter_section:
                name_elem = recruiter_section.find(['h3', 'span'], class_=['hiring-team__name', 'name'])
                title_elem = recruiter_section.find(['p', 'span'], class_=['hiring-team__title', 'title'])
                profile_elem = recruiter_section.find('a', href=True)
                
                if name_elem:
                    recruiter_info['name'] = name_elem.get_text(strip=True)
                if title_elem:
                    recruiter_info['title'] = title_elem.get_text(strip=True)
                if profile_elem:
                    recruiter_info['profile_url'] = profile_elem['href']
            
        except Exception:
            pass
        
        return recruiter_info
