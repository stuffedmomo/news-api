#!/usr/bin/env python3
import requests
import json
import os
import feedparser
import time
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────────────────────────
API_KEY = os.getenv('NEWS_API_KEY')
if not API_KEY:
    raise ValueError("NEWS_API_KEY environment variable not set. Please set it in your .env file.")
BASE_URL = 'https://newsapi.org/v2'
LOG_FILE = 'api_usage.json'
DAILY_LIMIT = 100
OUTPUT_DIR = 'news_data'
SOURCES_CACHE_FILE = os.path.join(OUTPUT_DIR, 'sources_cache.json')

# RSS Feed URLs
HINDU_RSS = "https://www.thehindu.com/news/national/feeder/default.rss"
PIB_RSS = "https://pib.gov.in/RssMain.aspx"

# ─── UTILS: request counting ────────────────────────────────────────────────────
def load_usage():
    """Load or initialize today's usage count."""
    today = date.today().isoformat()
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                data = json.load(f)
                if data.get('date') == today:
                    return data['count']
        except (json.JSONDecodeError, KeyError):
            # Handle corrupted log file
            pass
    return 0

def save_usage(count):
    """Save today's usage count."""
    with open(LOG_FILE, 'w') as f:
        json.dump({'date': date.today().isoformat(), 'count': count}, f)

def record_request():
    """Increment and persist request count; abort if over limit."""
    count = load_usage() + 1
    if count > DAILY_LIMIT:
        raise RuntimeError(f"API limit reached: {count}/{DAILY_LIMIT}")
    save_usage(count)
    return count

def check_remaining_requests(needed=1):
    """Check if we have enough requests left and return count."""
    current = load_usage()
    remaining = DAILY_LIMIT - current
    if remaining < needed:
        print(f"Warning: Only {remaining} requests left, need {needed}")
        return False
    return True

# ─── CORE FETCHERS ──────────────────────────────────────────────────────────────
def fetch_sources(category=None, language='en', country=None, use_cache=True):
    """GET /v2/top-headlines/sources → list of source objects with optional caching."""
    # Check if we have a valid cache to use
    if use_cache and os.path.exists(SOURCES_CACHE_FILE):
        try:
            with open(SOURCES_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                cache_date = datetime.fromisoformat(cache_data.get('date', '2000-01-01'))
                
                # If cache is less than 20 days old, use it
                if (datetime.now() - cache_date).days < 20:
                    print(f"Using cached sources data (last updated: {cache_date.strftime('%Y-%m-%d')})")
                    sources = cache_data.get('sources', [])
                    
                    # Filter if needed
                    if category or language or country:
                        filtered_sources = []
                        for source in sources:
                            if (category and source.get('category') != category):
                                continue
                            if (language and source.get('language') != language):
                                continue
                            if (country and source.get('country') != country):
                                continue
                            filtered_sources.append(source)
                        return filtered_sources
                    
                    return sources
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Cache error: {e}, fetching fresh data")
    
    # If no valid cache or cache not requested, fetch fresh data
    params = {'apiKey': API_KEY}
    if category:  params['category'] = category
    if language:  params['language'] = language
    if country:   params['country'] = country
    
    print(f"Fetching sources with params: {params}")
    try:
        resp = requests.get(f"{BASE_URL}/top-headlines/sources", params=params)
        resp.raise_for_status()  # Raise exception for 4XX/5XX responses
        record_request()
        result = resp.json()
        print(f"Sources API response status: {result.get('status')}")
        if result.get('status') != 'ok':
            print(f"Error message: {result.get('message')}")
            print(f"Error code: {result.get('code')}")
            return []
        
        sources = result.get('sources', [])
        
        # Cache the sources if we're fetching all or a significant subset
        if not category and not country:
            with open(SOURCES_CACHE_FILE, 'w') as f:
                json.dump({
                    'date': datetime.now().isoformat(),
                    'sources': sources
                }, f)
            print(f"Cached {len(sources)} sources data")
        
        return sources
    except requests.exceptions.RequestException as e:
        print(f"Error fetching sources: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return []

def fetch_headlines(category=None, country=None, sources=None, q=None, page_size=10, page=1):
    """GET /v2/top-headlines → list of article objects."""
    params = {
        'apiKey': API_KEY,
        'pageSize': page_size,
        'page': page
    }
    if category: params['category'] = category
    if country: params['country'] = country
    if sources: params['sources'] = sources
    if q: params['q'] = q
    
    # Cannot mix sources with country/category parameters
    if sources and (country or category):
        print("Warning: Cannot mix 'sources' parameter with 'country' or 'category'")
        if sources:
            params.pop('country', None)
            params.pop('category', None)
        else:
            params.pop('sources', None)
    
    print(f"Fetching headlines with params: {params}")
    try:
        resp = requests.get(f"{BASE_URL}/top-headlines", params=params)
        resp.raise_for_status()
        record_request()
        result = resp.json()
        print(f"Headlines API response status: {result.get('status')}")
        if result.get('status') != 'ok':
            print(f"Error message: {result.get('message')}")
            print(f"Error code: {result.get('code')}")
        return result.get('articles', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching headlines: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return []

def fetch_everything(q, sources=None, domains=None, exclude_domains=None, 
                    from_date=None, to_date=None, language=None, 
                    sort_by='publishedAt', search_in=None, page_size=10, page=1):
    """GET /v2/everything → list of article objects with all available parameters."""
    params = {
        'apiKey': API_KEY,
        'q': q,
        'pageSize': page_size,
        'page': page,
        'sortBy': sort_by
    }
    if sources: params['sources'] = sources
    if domains: params['domains'] = domains
    if exclude_domains: params['excludeDomains'] = exclude_domains
    if from_date: params['from'] = from_date
    if to_date: params['to'] = to_date
    if language: params['language'] = language
    if search_in: params['searchIn'] = search_in
    
    print(f"Fetching everything with params: {params}")
    try:
        resp = requests.get(f"{BASE_URL}/everything", params=params)
        resp.raise_for_status()
        record_request()
        result = resp.json()
        print(f"Everything API response status: {result.get('status')}")
        if result.get('status') != 'ok':
            print(f"Error message: {result.get('message')}")
            print(f"Error code: {result.get('code')}")
        return result.get('articles', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching everything: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return []

# ─── RSS FEED FETCHING ────────────────────────────────────────────────────────
def fetch_rss_news(rss_url, source_name, max_articles=10):
    """Fetch news from RSS feed and crawl the full content."""
    print(f"Fetching RSS feed from {source_name}...")
    
    articles = []
    try:
        # Parse the RSS feed
        feed = feedparser.parse(rss_url)
        
        # Limit to max_articles
        entries = feed.entries[:max_articles]
        
        for entry in entries:
            title = entry.title
            link = entry.link
            published = entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            description = entry.get('description', '')
            
            # Crawl the full article content
            print(f"Crawling article: {title}")
            try:
                full_content = crawl_article_content(link, source_name)
            except Exception as e:
                print(f"Error crawling article: {e}")
                full_content = description
            
            article = {
                'title': title,
                'url': link,
                'publishedAt': published,
                'description': description,
                'content': full_content,
                'source': {'id': source_name.lower().replace(' ', '-'), 'name': source_name}
            }
            
            articles.append(article)
            # Be nice to servers - add a small delay between requests
            time.sleep(1)
            
        return articles
    except Exception as e:
        print(f"Error fetching RSS feed from {source_name}: {e}")
        return []

def crawl_article_content(url, source_name):
    """Crawl article page and extract full content."""
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Different extraction logic based on source
    if "thehindu" in url:
        # The Hindu article content extraction
        content_div = soup.select_one('.article-content')
        if content_div:
            paragraphs = content_div.select('p')
            content = ' '.join([p.text for p in paragraphs])
            return content
    elif "pib.gov.in" in url:
        # PIB article content extraction
        content_div = soup.select_one('.innner-page-main-about-us')
        if content_div:
            paragraphs = content_div.select('p')
            content = ' '.join([p.text for p in paragraphs])
            return content
    
    # Fallback: try to extract any paragraphs
    paragraphs = soup.select('p')
    content = ' '.join([p.text for p in paragraphs])
    
    return content

def fetch_india_news_from_rss(page_size=15):
    """Fetch news specifically from Indian RSS sources."""
    print(f"Fetching news from Indian RSS sources...")
    try:
        hindu_articles = fetch_rss_news(HINDU_RSS, "The Hindu", max_articles=page_size//2)
        pib_articles = fetch_rss_news(PIB_RSS, "Press Information Bureau", max_articles=page_size//2)
        
        # Combine articles from both sources
        all_articles = hindu_articles + pib_articles
        
        # Sort by publishedAt date (newest first)
        all_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
        
        return all_articles[:page_size]
    except Exception as e:
        print(f"Error fetching Indian news from RSS: {e}")
        return []

# ─── UPSC TOPIC FETCHERS ─────────────────────────────────────────────────────
def fetch_upsc_topic(topic, query, from_date, to_date, page_size=10):
    """Fetch news for a specific UPSC topic."""
    print(f"Fetching news about {topic}...")
    try:
        # Include Indian domains for more relevant results
        domains = "thehindu.com,timesofindia.indiatimes.com,indianexpress.com,livemint.com,business-standard.com"
        return fetch_everything(
            q=query, 
            from_date=from_date, 
            to_date=to_date,
            domains=domains,
            language='en',
            page_size=page_size
        )
    except Exception as e:
        print(f"Error fetching {topic} news: {e}")
        return []

def fetch_topic_from_rss(topic, max_articles=10):
    """Fetch news from RSS feeds and filter by UPSC topic."""
    print(f"Fetching {topic} news from RSS feeds...")
    
    # Keywords for each topic to use as filters
    topic_keywords = {
        'polity': ['constitution', 'governance', 'law', 'parliament', 'judiciary', 'supreme court', 'high court',
                  'bill', 'amendment', 'election', 'democracy', 'federalism', 'rights', 'fundamental'],
        'economy': ['economy', 'economic', 'finance', 'budget', 'fiscal', 'monetary', 'inflation', 'gdp', 
                   'growth', 'tax', 'market', 'banking', 'rbi', 'trade', 'commerce', 'industry'],
        'international': ['foreign', 'international', 'global', 'bilateral', 'multilateral', 'diplomacy',
                         'treaty', 'agreement', 'relations', 'affairs', 'g20', 'un', 'who', 'world'],
        'environment': ['environment', 'climate', 'green', 'sustainable', 'pollution', 'ecology', 'biodiversity',
                       'conservation', 'renewable', 'energy', 'forest', 'wildlife', 'disaster'],
        'science': ['science', 'technology', 'innovation', 'research', 'space', 'digital', 'satellite',
                   'computer', 'ai', 'artificial intelligence', 'quantum', 'biotech', 'medicine'],
        'governance': ['governance', 'policy', 'scheme', 'initiative', 'program', 'welfare', 'ministry',
                     'commission', 'social', 'development', 'reform', 'administration', 'public']
    }
    
    # Get keywords for the requested topic
    keywords = topic_keywords.get(topic.lower(), [])
    if not keywords:
        print(f"No keywords defined for topic: {topic}")
        return []
    
    # Fetch articles from RSS feeds
    articles = fetch_india_news_from_rss(page_size=30)  # Get more articles to filter from
    
    # Filter articles by topic keywords
    filtered_articles = []
    for article in articles:
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = article.get('content', '').lower()
        
        # Check if any keyword is present in title, description, or content
        matches = False
        for keyword in keywords:
            if keyword.lower() in title or keyword.lower() in description or keyword.lower() in content:
                matches = True
                break
        
        if matches:
            filtered_articles.append(article)
    
    return filtered_articles[:max_articles]

# ─── OUTPUT FORMATTERS ───────────────────────────────────────────────────────
def save_to_markdown(data, filename, title=None):
    """Save data to markdown file."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.md")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if not data:
            md_content = f"# {title}\n\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\nNo articles found."
        elif isinstance(data[0], dict) and 'name' in data[0]:  # Sources
            # It's a list of sources
            md_content = format_sources_as_markdown(data, title or "News Sources")
        else:  # Articles
            # It's a list of articles
            md_content = format_articles_as_markdown(data, title or filename.replace('_', ' ').title())
        
        f.write(md_content)
    
    print(f"Saved {len(data) if data else 0} items to {filepath}")
    return filepath

def format_sources_as_markdown(sources, title):
    """Format sources as markdown."""
    md = f"# {title}\n\n"
    md += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    md += f"Total sources: {len(sources)}\n\n"
    
    # Group sources by category
    categories = {}
    for source in sources:
        cat = source.get('category', 'uncategorized')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(source)
    
    # Create markdown for each category
    for category, cat_sources in sorted(categories.items()):
        md += f"## {category.title()}\n\n"
        for source in sorted(cat_sources, key=lambda x: x.get('name', '')):
            md += f"### {source.get('name')}\n\n"
            md += f"- **ID**: {source.get('id')}\n"
            md += f"- **Description**: {source.get('description')}\n"
            md += f"- **URL**: [{source.get('url')}]({source.get('url')})\n"
            md += f"- **Language**: {source.get('language')}\n"
            md += f"- **Country**: {source.get('country')}\n\n"
    
    return md

def format_articles_as_markdown(articles, title):
    """Format articles as markdown."""
    md = f"# {title}\n\n"
    md += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    md += f"Total articles: {len(articles)}\n\n"
    
    for i, article in enumerate(articles, 1):
        # Title and source
        source_name = article.get('source', {}).get('name', 'Unknown Source')
        md += f"## {i}. {article.get('title')}\n\n"
        md += f"**Source**: {source_name}\n\n"
        
        # Published date
        pub_date = article.get('publishedAt', '')
        if pub_date:
            try:
                # Format the date if possible
                if isinstance(pub_date, str):
                    # Try to parse various date formats
                    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S %z'):
                        try:
                            date_obj = datetime.strptime(pub_date, fmt)
                            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                            md += f"**Published**: {formatted_date}\n\n"
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format matched, just use the original string
                        md += f"**Published**: {pub_date}\n\n"
                else:
                    md += f"**Published**: {pub_date}\n\n"
            except ValueError:
                md += f"**Published**: {pub_date}\n\n"
        
        # Author
        author = article.get('author')
        if author:
            md += f"**Author**: {author}\n\n"
        
        # Description
        description = article.get('description')
        if description:
            md += f"**Description**: {description}\n\n"
        
        # Content
        content = article.get('content')
        if content:
            md += f"**Content**:\n\n{content}\n\n"
        
        # URL
        url = article.get('url')
        if url:
            md += f"**URL**: [{url}]({url})\n\n"
        
        # Add image if available
        image_url = article.get('urlToImage')
        if image_url:
            md += f"**Image**: ![Article Image]({image_url})\n\n"
        
        # Add separator between articles
        md += "---\n\n"
    
    return md 