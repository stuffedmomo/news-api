import http.server
import socketserver
import os
import json
import markdown
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, unquote, parse_qs
from dotenv import load_dotenv
from feedback_system import handle_feedback_request

# Load environment variables
load_dotenv()

# Directory where markdown files are stored
NEWS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_data")
# Directory for web files
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
# Directory for feedback data
FEEDBACK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback_data")

# Get API Key
API_KEY = os.getenv('NEWS_API_KEY')
if not API_KEY:
    print("Warning: NEWS_API_KEY not set in environment variables.")
    API_KEY = "demo-key"  # Placeholder for development

# API Endpoints
BASE_URL = 'https://newsapi.org/v2'

# RSS Feed URLs
HINDU_RSS = "https://www.thehindu.com/news/national/feeder/default.rss"
PIB_RSS = "https://pib.gov.in/RssMain.aspx"
TOI_RSS = "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"

# Custom request handler class
class UPSCNewsServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # API Endpoint to list news files
        if path == '/api/files':
            self.handle_api_files()
            return
            
        # API Endpoint for headlines
        elif path == '/api/headlines':
            self.handle_api_headlines(parsed_path)
            return
            
        # API Endpoint for everything search
        elif path == '/api/everything':
            self.handle_api_everything(parsed_path)
            return
            
        # API Endpoint for search (alias for everything)
        elif path == '/api/search':
            self.handle_api_everything(parsed_path)
            return
            
        # API Endpoint for RSS feed
        elif path == '/api/rss':
            self.handle_api_rss(parsed_path)
            return
            
        # API Endpoint for recent news
        elif path == '/api/recent':
            self.handle_api_recent()
            return
            
        # API Endpoint for getting feedback data
        elif path == '/api/feedback':
            self.handle_get_feedback()
            return
            
        # Serve the view endpoint for markdown conversion
        elif path.startswith('/view/'):
            self.handle_view(path)
            return
        
        # For all other paths, let SimpleHTTPRequestHandler serve files from WEB_DIR
        return super().do_GET()
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Handle feedback endpoint
        if path == '/api/feedback':
            self.handle_post_feedback()
            return
            
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))
    
    def handle_api_files(self):
        """Handle the /api/files endpoint to list available markdown files."""
        try:
            files = [f for f in os.listdir(NEWS_DIR) if f.endswith('.md')]
            # Create a list of dictionaries with filename and title
            file_data = []
            for file in files:
                title = file.replace('.md', '').replace('_', ' ').title()
                file_data.append({'filename': file, 'title': title})
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS header
            self.end_headers()
            self.wfile.write(json.dumps(file_data).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def handle_api_headlines(self, parsed_path):
        """Handle the /api/headlines endpoint (NewsAPI top-headlines)."""
        try:
            # Parse query parameters
            query = parse_qs(parsed_path.query)
            country = query.get('country', ['us'])[0]
            category = query.get('category', ['general'])[0]
            page_size = int(query.get('pageSize', ['10'])[0])
            page = int(query.get('page', ['1'])[0])
            
            # For countries other than US, fall back to sample data if API call fails
            try:
                # Build API request
                params = {
                    'apiKey': API_KEY,
                    'country': country,
                    'category': category,
                    'pageSize': min(page_size, 30),  # Max 30 per request
                    'page': page
                }
                
                # Make request to NewsAPI
                response = requests.get(f"{BASE_URL}/top-headlines", params=params)
                data = response.json()
                
                if 'status' in data and data['status'] != 'ok':
                    raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
                    
            except Exception as api_error:
                print(f"API error: {api_error}. Using sample data for {country}")
                
                # Use sample data for countries other than US or when API fails
                data = {
                    "status": "ok",
                    "totalResults": 10,
                    "articles": []
                }
                
                # Load some sample articles from existing markdown files
                if country.lower() == 'in':
                    file_path = os.path.join(NEWS_DIR, 'india_news.md')
                else:
                    file_path = os.path.join(NEWS_DIR, 'global_headlines.md')
                
                if os.path.exists(file_path):
                    articles = self.extract_articles_from_markdown(file_path)
                    data["articles"] = articles[:page_size]
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def handle_api_everything(self, parsed_path):
        """Handle the /api/everything endpoint (NewsAPI everything)."""
        try:
            # Parse query parameters
            query = parse_qs(parsed_path.query)
            q = query.get('q', [''])[0]
            
            # Return error if query is empty
            if not q:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Query parameter "q" is required'}).encode('utf-8'))
                return
            
            # Get other parameters
            language = query.get('language', ['en'])[0]
            search_in = query.get('searchIn', [''])[0]
            from_date = query.get('from', [''])[0]
            to_date = query.get('to', [''])[0]
            sort_by = query.get('sortBy', ['publishedAt'])[0]
            page_size = int(query.get('pageSize', ['10'])[0])
            page = int(query.get('page', ['1'])[0])
            
            # Build API request
            params = {
                'apiKey': API_KEY,
                'q': q,
                'language': language,
                'pageSize': min(page_size, 25),  # Max 25 per request
                'page': page,
                'sortBy': sort_by
            }
            
            # Add optional parameters
            if search_in:
                params['searchIn'] = search_in
            if from_date:
                params['from'] = from_date
            if to_date:
                params['to'] = to_date
            
            # Make request to NewsAPI
            response = requests.get(f"{BASE_URL}/everything", params=params)
            data = response.json()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def handle_api_rss(self, parsed_path):
        """Handle the /api/rss endpoint to fetch from RSS feeds."""
        try:
            # Parse query parameters
            query = parse_qs(parsed_path.query)
            source = query.get('source', ['hindu'])[0]
            max_articles = int(query.get('max', ['10'])[0])
            
            # Determine the RSS URL based on source
            if source.lower() == 'hindu':
                rss_url = HINDU_RSS
                source_name = 'The Hindu'
            elif source.lower() == 'toi' or source.lower() == 'times':
                rss_url = TOI_RSS
                source_name = 'Times of India'
            elif source.lower() == 'pib':
                rss_url = PIB_RSS
                source_name = 'Press Information Bureau'
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid source. Available sources: hindu, toi, pib'}).encode('utf-8'))
                return
            
            # Parse the RSS feed
            feed = feedparser.parse(rss_url)
            
            # Format the articles
            articles = []
            for entry in feed.entries[:max_articles]:
                articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    'description': entry.get('description', ''),
                    'source': {'name': source_name},
                    'url': entry.link  # Add a url field to make it compatible with the news API format
                })
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'articles': articles}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def extract_articles_from_markdown(self, file_path):
        """Extract articles from a markdown file."""
        articles = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract article titles and descriptions
            lines = content.split('\n')
            
            # If it's a new format with ## headings for articles
            title = None
            source = None
            description = None
            content_text = None
            url = None
            published_at = None
            image_url = None
            current_section = None
            
            # Get base source name from file
            source_name = os.path.basename(file_path).replace('.md', '').replace('_', ' ').title()
            
            for line in lines:
                line = line.strip()
                
                # Check for article header (## N. Title)
                if line.startswith('## '):
                    # If we have collected an article, add it before starting a new one
                    if title:
                        article = {
                            'title': title,
                            'description': description or "",
                            'content': content_text or description or "",
                            'url': url or "#",
                            'source': {'name': source or source_name},
                            'publishedAt': published_at or datetime.now().strftime('%Y-%m-%d'),
                            'urlToImage': image_url
                        }
                        articles.append(article)
                    
                    # Extract new title (remove the ## and any numbering)
                    title_parts = line[3:].split('. ', 1)
                    title = title_parts[-1] if len(title_parts) > 0 else line[3:]
                    
                    # Reset other fields
                    source = None
                    description = None
                    content_text = None
                    url = None
                    published_at = None
                    image_url = None
                    current_section = None
                
                # Check for source
                elif line.startswith('**Source**:'):
                    source = line[line.find(':')+1:].strip()
                    current_section = 'source'
                
                # Check for description
                elif line.startswith('**Description**:'):
                    description = line[line.find(':')+1:].strip()
                    current_section = 'description'
                
                # Check for content
                elif line.startswith('**Content**:'):
                    content_text = line[line.find(':')+1:].strip()
                    current_section = 'content'
                
                # Check for URL
                elif line.startswith('**URL**:'):
                    url_line = line[line.find(':')+1:].strip()
                    # Extract URL from markdown link if present
                    if '[' in url_line and '](' in url_line and ')' in url_line:
                        url_start = url_line.find('](') + 2
                        url_end = url_line.find(')', url_start)
                        url = url_line[url_start:url_end]
                    else:
                        url = url_line
                    current_section = 'url'
                
                # Check for published date
                elif line.startswith('**Published**:'):
                    published_at = line[line.find(':')+1:].strip()
                    current_section = 'published'
                
                # Check for image
                elif line.startswith('**Image**:') or line.startswith('!['):
                    if '![' in line and '](' in line and ')' in line:
                        img_start = line.find('](') + 2
                        img_end = line.find(')', img_start)
                        image_url = line[img_start:img_end]
                    current_section = 'image'
                
                # Continue previous section if it's not a new section
                elif current_section and line and not line.startswith('---'):
                    if current_section == 'description':
                        description = (description or "") + " " + line
                    elif current_section == 'content':
                        content_text = (content_text or "") + " " + line
            
            # Add the last article if there is one
            if title:
                article = {
                    'title': title,
                    'description': description or "",
                    'content': content_text or description or "",
                    'url': url or "#",
                    'source': {'name': source or source_name},
                    'publishedAt': published_at or datetime.now().strftime('%Y-%m-%d'),
                    'urlToImage': image_url
                }
                articles.append(article)
                
        except Exception as e:
            print(f"Error extracting articles from {file_path}: {e}")
            
        return articles
    
    def handle_api_recent(self):
        """Handle the /api/recent endpoint to get recent news."""
        try:
            articles = []
            
            # Load articles from India news
            india_news_path = os.path.join(NEWS_DIR, 'india_news.md')
            if os.path.exists(india_news_path):
                india_articles = self.extract_articles_from_markdown(india_news_path)
                articles.extend(india_articles[:5])
            
            # If we have less than 10 articles, add some from global headlines
            if len(articles) < 10:
                global_news_path = os.path.join(NEWS_DIR, 'global_headlines.md')
                if os.path.exists(global_news_path):
                    global_articles = self.extract_articles_from_markdown(global_news_path)
                    articles.extend(global_articles[:10-len(articles)])
            
            # Limit to 10 articles
            articles = articles[:10]
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'articles': articles}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def handle_view(self, path):
        """Handle the /view/ endpoint to serve markdown files as JSON."""
        filename = unquote(path[len('/view/'):])
        file_path = os.path.join(NEWS_DIR, filename)
        
        if not os.path.exists(file_path):
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f"File not found: {filename}"}).encode('utf-8'))
            return
        
        try:
            # Read the raw markdown content
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                
            # Extract articles from the markdown file
            articles = self.extract_articles_from_markdown(file_path)
            
            # Create a response with both structured data and raw content
            response = {
                'title': filename.replace('.md', '').replace('_', ' ').title(),
                'articles': articles,
                'raw_content': raw_content
            }
            
            # Send JSON response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def handle_get_feedback(self):
        """Handle GET request to /api/feedback."""
        try:
            # Load feedback data from JSON files
            feedback_data = {}
            
            # Check if article feedback file exists
            article_feedback_path = os.path.join(FEEDBACK_DIR, 'article_feedback.json')
            if os.path.exists(article_feedback_path):
                with open(article_feedback_path, 'r', encoding='utf-8') as f:
                    article_data = json.load(f)
                    if article_data and 'articles' in article_data:
                        feedback_data = article_data['articles']
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(feedback_data).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def handle_post_feedback(self):
        """Handle POST request to /api/feedback."""
        try:
            # Get content length to read the POST body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            feedback_data = json.loads(post_data.decode('utf-8'))
            
            # Save feedback data to JSON file
            article_feedback_path = os.path.join(FEEDBACK_DIR, 'article_feedback.json')
            
            # Create directory if it doesn't exist
            os.makedirs(FEEDBACK_DIR, exist_ok=True)
            
            # Save to file
            with open(article_feedback_path, 'w', encoding='utf-8') as f:
                json.dump({'articles': feedback_data}, f, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

def run_server(port=8000, bind="127.0.0.1"):
    """Start the web server."""
    # Create a new output directory if it doesn't exist
    if not os.path.exists(NEWS_DIR):
        os.makedirs(NEWS_DIR)
    if not os.path.exists(FEEDBACK_DIR):
        os.makedirs(FEEDBACK_DIR)
        
    print(f"Serving from directory: {WEB_DIR}")
    print(f"News data directory: {NEWS_DIR}")
    
    server_address = (bind, port)
    with socketserver.TCPServer(server_address, UPSCNewsServerHandler) as httpd:
        print(f"Server running at http://{bind}:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close()

import socket

if __name__ == "__main__":
    # Dynamically get the local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    run_server(bind=local_ip)