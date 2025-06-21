import re
from typing import Dict, List, Any

class JobFilter:
    def __init__(self, config):
        self.config = config
        
        # Define degree requirement patterns
        self.degree_patterns = [
            r'bachelor\'?s?\s+degree',
            r'bs\s+degree',
            r'college\s+degree',
            r'university\s+degree',
            r'4-year\s+degree',
            r'degree\s+required',
            r'degree\s+in\s+computer\s+science',
            r'cs\s+degree',
            r'computer\s+science\s+degree',
            r'engineering\s+degree',
            r'master\'?s?\s+degree',
            r'phd',
            r'doctorate'
        ]
        
        # Define experience requirement patterns
        self.experience_patterns = [
            r'\d+\+?\s+years?\s+of?\s+experience',
            r'\d+\+?\s+years?\s+experience',
            r'minimum\s+\d+\s+years?',
            r'at\s+least\s+\d+\s+years?',
            r'\d+\s+to\s+\d+\s+years?\s+experience',
            r'senior\s+level',
            r'experienced\s+developer',
            r'minimum\s+experience',
            r'years?\s+of\s+professional\s+experience',
            r'proven\s+experience',
            r'extensive\s+experience'
        ]
        
        # Define tech keywords
        self.tech_keywords = config.get('tech_keywords', [
            'software', 'developer', 'engineer', 'programming', 'frontend', 'backend',
            'fullstack', 'devops', 'data', 'analyst', 'python', 'javascript', 'react',
            'node', 'api', 'database', 'cloud', 'aws', 'docker', 'kubernetes', 'ml',
            'machine learning', 'ai', 'artificial intelligence', 'web development'
        ])
        
        # Define startup indicators
        self.startup_indicators = [
            'startup', 'early stage', 'seed stage', 'series a', 'series b',
            'fast-growing', 'scaling', 'venture backed', 'y combinator',
            'techstars', 'accelerator', 'disruptive', 'innovative'
        ]
        
        # Define large company names to exclude
        self.large_companies = [
            'google', 'microsoft', 'amazon', 'apple', 'facebook', 'meta',
            'netflix', 'tesla', 'ibm', 'oracle', 'salesforce', 'adobe',
            'intel', 'nvidia', 'cisco', 'vmware', 'dell', 'hp', 'sony',
            'samsung', 'lg', 'toyota', 'ford', 'general motors', 'walmart',
            'target', 'starbucks', 'mcdonalds', 'coca cola', 'pepsi'
        ]
        
        # Define internship/unpaid patterns
        self.internship_patterns = [
            r'intern\b',
            r'internship',
            r'unpaid',
            r'no salary',
            r'volunteer',
            r'part.time',
            r'part time',
            r'contract.*unpaid',
            r'equity.only',
            r'equity only'
        ]
    
    def passes_all_filters(self, job: Dict[str, Any]) -> bool:
        """Check if job passes all filters"""
        try:
            # Check if remote
            if not self.is_remote(job):
                return False
            
            # Check if tech role
            if not self.is_tech_role(job):
                return False
            
            # Check degree requirements
            if self.requires_degree(job):
                return False
            
            # Check experience requirements
            if self.requires_experience(job):
                return False
            
            # Check if startup (optional filter)
            if not self.is_startup_related(job):
                return False
            
            # Check for internships/unpaid if configured
            if self.config.get('exclude_internships', True) and self.is_internship_or_unpaid(job):
                return False
            
            # Add relevant tags
            job['tags'] = self.generate_tags(job)
            
            return True
            
        except Exception as e:
            print(f"Error filtering job: {e}")
            return False
    
    def is_remote(self, job: Dict[str, Any]) -> bool:
        """Check if job is remote"""
        text_fields = [
            job.get('title', ''),
            job.get('description', ''),
            job.get('job_type', ''),
            job.get('benefits', '')
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        remote_indicators = [
            'remote', 'work from home', 'wfh', 'distributed team',
            'anywhere', 'location independent', 'telecommute',
            'virtual', 'home office'
        ]
        
        return any(indicator in combined_text for indicator in remote_indicators)
    
    def is_tech_role(self, job: Dict[str, Any]) -> bool:
        """Check if job is a tech role"""
        text_fields = [
            job.get('title', ''),
            job.get('description', ''),
            str(job.get('tags', []))
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        # Check for tech keywords
        for keyword in self.tech_keywords:
            if keyword.lower() in combined_text:
                return True
        
        return False
    
    def requires_degree(self, job: Dict[str, Any]) -> bool:
        """Check if job requires a degree"""
        text_fields = [
            job.get('description', ''),
            job.get('title', '')
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        # Check for degree requirement patterns
        for pattern in self.degree_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
        
        return False
    
    def is_startup_related(self, job: Dict[str, Any]) -> bool:
        """Check if job is from a startup or startup-related"""
        text_fields = [
            job.get('company', ''),
            job.get('description', ''),
            job.get('source_site', ''),
            str(job.get('tags', []))
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        # If from Wellfound/AngelList, assume it's startup-related
        if 'wellfound' in combined_text or 'angellist' in combined_text:
            return True
        
        # Check for startup indicators
        for indicator in self.startup_indicators:
            if indicator.lower() in combined_text:
                return True
        
        # Check if it's NOT a large company
        company_name = job.get('company', '').lower()
        for large_company in self.large_companies:
            if large_company in company_name:
                return False
        
        # If we can't determine, assume it could be a startup
        return True
    
    def is_internship_or_unpaid(self, job: Dict[str, Any]) -> bool:
        """Check if job is an internship or unpaid position"""
        text_fields = [
            job.get('title', ''),
            job.get('description', ''),
            job.get('salary', '')
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        # Check for internship/unpaid patterns
        for pattern in self.internship_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
        
        return False
    
    def requires_experience(self, job: Dict[str, Any]) -> bool:
        """Check if job requires specific years of experience"""
        text_fields = [
            job.get('description', ''),
            job.get('title', '')
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        # Check for experience requirement patterns
        for pattern in self.experience_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
        
        return False
    
    def generate_tags(self, job: Dict[str, Any]) -> List[str]:
        """Generate relevant tags for the job"""
        tags = []
        
        text_fields = [
            job.get('title', ''),
            job.get('description', ''),
            job.get('company', '')
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        # Add basic tags
        tags.extend(['Remote', 'Tech', 'No Degree', 'No Experience'])
        
        # Add startup tag if applicable
        if self.is_startup_related(job):
            tags.append('Startup')
        
        # Add technology-specific tags
        tech_tags = {
            'python': 'Python',
            'javascript': 'JavaScript',
            'react': 'React',
            'node': 'Node.js',
            'django': 'Django',
            'flask': 'Flask',
            'aws': 'AWS',
            'docker': 'Docker',
            'kubernetes': 'Kubernetes',
            'machine learning': 'ML',
            'data science': 'Data Science',
            'frontend': 'Frontend',
            'backend': 'Backend',
            'fullstack': 'Full Stack',
            'devops': 'DevOps'
        }
        
        for keyword, tag in tech_tags.items():
            if keyword in combined_text:
                tags.append(tag)
        
        # Add role-level tags
        if any(level in combined_text for level in ['senior', 'sr.']):
            tags.append('Senior')
        elif any(level in combined_text for level in ['junior', 'jr.', 'entry']):
            tags.append('Junior')
        elif any(level in combined_text for level in ['lead', 'principal', 'staff']):
            tags.append('Lead')
        
        return list(set(tags))  # Remove duplicates
