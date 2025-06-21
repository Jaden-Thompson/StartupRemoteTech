from flask import Flask, render_template, request, jsonify, send_file
import json
import csv
import io
import threading
from datetime import datetime
from scraper import JobScraper

app = Flask(__name__)

# Global variable to store scraping results
scraping_results = []
scraping_status = {"running": False, "progress": "", "error": None}

@app.route('/reset_status', methods=['POST'])
def reset_status():
    """Reset scraping status if stuck"""
    global scraping_status
    scraping_status = {"running": False, "progress": "", "error": None}
    return jsonify({"message": "Status reset successfully"})

@app.route('/')
def index():
    """Main page with scraping configuration form"""
    return render_template('index.html')

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    """Start the scraping process in a background thread"""
    global scraping_status, scraping_results
    
    if scraping_status["running"]:
        return jsonify({"error": "Scraping is already in progress"}), 400
    
    # Get configuration from form
    config = {
        'sites': request.json.get('sites', ['remoteok', 'wellfound', 'weworkremotely', 'remotive', 'justremote', 'linkedin']),
        'max_jobs_per_site': int(request.json.get('max_jobs_per_site', 50)),
        'exclude_internships': request.json.get('exclude_internships', True),
        'tech_keywords': request.json.get('tech_keywords', [
            'software', 'developer', 'engineer', 'programming', 'frontend', 'backend',
            'fullstack', 'devops', 'data', 'analyst', 'python', 'javascript', 'react',
            'node', 'api', 'database', 'cloud', 'aws', 'docker', 'kubernetes'
        ])
    }
    
    # Reset results and status
    scraping_results = []
    scraping_status = {"running": True, "progress": "Starting scraper...", "error": None}
    
    # Start scraping in background thread
    thread = threading.Thread(target=run_scraper, args=(config,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Scraping started successfully"})

def run_scraper(config):
    """Run the scraper in background thread"""
    global scraping_results, scraping_status
    
    try:
        scraper = JobScraper(config)
        
        def update_progress(message):
            scraping_status["progress"] = message
        
        scraping_results = scraper.scrape_all_sites(progress_callback=update_progress)
        scraping_status["running"] = False
        scraping_status["progress"] = f"Completed! Found {len(scraping_results)} jobs"
        
    except Exception as e:
        scraping_status["running"] = False
        scraping_status["error"] = str(e)
        scraping_status["progress"] = "Error occurred during scraping"

@app.route('/status')
def get_status():
    """Get current scraping status"""
    return jsonify(scraping_status)

@app.route('/results')
def get_results():
    """Get scraping results"""
    return jsonify({
        "jobs": scraping_results,
        "count": len(scraping_results)
    })

@app.route('/results_page')
def results_page():
    """Results page template"""
    return render_template('results.html')

@app.route('/export_csv')
def export_csv():
    """Export results to CSV file"""
    if not scraping_results:
        return jsonify({"error": "No results to export"}), 400
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'title', 'company', 'job_type', 'salary', 'benefits', 'description_preview',
        'apply_link', 'recruiter_name', 'recruiter_title', 'recruiter_linkedin',
        'tags', 'source_site', 'scraped_at'
    ])
    
    writer.writeheader()
    for job in scraping_results:
        writer.writerow({
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'job_type': job.get('job_type', ''),
            'salary': job.get('salary', ''),
            'benefits': job.get('benefits', ''),
            'description_preview': job.get('description', '')[:200] + '...' if len(job.get('description', '')) > 200 else job.get('description', ''),
            'apply_link': job.get('apply_link', ''),
            'recruiter_name': job.get('recruiter_name', ''),
            'recruiter_title': job.get('recruiter_title', ''),
            'recruiter_linkedin': job.get('recruiter_linkedin', ''),
            'tags': ', '.join(job.get('tags', [])),
            'source_site': job.get('source_site', ''),
            'scraped_at': job.get('scraped_at', '')
        })
    
    # Create file-like object
    output.seek(0)
    csv_data = output.getvalue()
    output.close()
    
    # Create BytesIO for file download
    csv_bytes = io.BytesIO()
    csv_bytes.write(csv_data.encode('utf-8'))
    csv_bytes.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"startup_tech_jobs_{timestamp}.csv"
    
    return send_file(
        csv_bytes,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )
