#!/usr/bin/env python3
import requests, json, os
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
def fetch_sources(category=None, language='en', country=None):
    """GET /v2/top-headlines/sources → list of source objects."""
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
        return result.get('sources', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching sources: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return []

def fetch_headlines(category=None, country=None, sources=None, page_size=10):
    """GET /v2/top-headlines → list of article objects."""
    params = {
        'apiKey': API_KEY,
        'pageSize': page_size,
    }
    if category: params['category'] = category
    if country: params['country'] = country
    if sources: params['sources'] = sources
    
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

def fetch_everything(query, from_date=None, to_date=None, sources=None, domains=None, page_size=10):
    """GET /v2/everything → list of article objects."""
    params = {
        'apiKey': API_KEY,
        'q': query,
        'pageSize': page_size,
        'sortBy': 'publishedAt'
    }
    if from_date: params['from'] = from_date
    if to_date: params['to'] = to_date
    if sources: params['sources'] = sources
    if domains: params['domains'] = domains
    
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

def fetch_india_news(page_size=15):
    """Fetch news specifically from Indian sources."""
    # Using sources approach for Indian news
    indian_sources = "the-hindu,the-times-of-india"
    
    print(f"Fetching news from Indian sources...")
    try:
        return fetch_headlines(sources=indian_sources, page_size=page_size)
    except Exception as e:
        print(f"Error fetching Indian news: {e}")
        return []

def fetch_upsc_topic(topic, query, from_date, to_date, page_size=10):
    """Fetch news for a specific UPSC topic."""
    print(f"Fetching news about {topic}...")
    try:
        # Include Indian domains for more relevant results
        domains = "thehindu.com,timesofindia.indiatimes.com,indianexpress.com,livemint.com,business-standard.com"
        return fetch_everything(
            query=query, 
            from_date=from_date, 
            to_date=to_date,
            domains=domains,
            page_size=page_size
        )
    except Exception as e:
        print(f"Error fetching {topic} news: {e}")
        return []

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
                date_obj = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                md += f"**Published**: {formatted_date}\n\n"
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

# ─── MAIN WORKFLOW ─────────────────────────────────────────────────────────────
def main():
    # Check if we have enough requests for the extended script
    needed_requests = 9  # Base + India + 4 UPSC topics
    if not check_remaining_requests(needed_requests):
        print(f"Not enough API requests remaining for full execution (need {needed_requests}).")
        return
    
    # 1. Sources - no country filter to get more sources
    sources = fetch_sources(language='en')
    print(f"Available sources: {len(sources)}")
    for i, s in enumerate(sources[:10], 1):
        print(f" {i}. {s['id']} ({s['category']}): {s['name']}")
    
    if len(sources) > 10:
        print(f"   ... and {len(sources) - 10} more sources")
    
    save_to_markdown(sources, "sources", "News API Sources")
    
    # 2. India-specific news (from Indian sources)
    india_news = fetch_india_news(page_size=15)
    print(f"\nIndian news headlines ({len(india_news)}):")
    for a in india_news[:5]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']} | {a['publishedAt'][:10]}")
    
    save_to_markdown(india_news, "india_news", "Latest News from India")
    
    # 3. Global headlines
    gen = fetch_headlines(category='general', country='us')
    print(f"\nGlobal headlines ({len(gen)}):")
    for a in gen[:5]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']} | {a['publishedAt'][:10]}")
    
    save_to_markdown(gen, "global_headlines", "Global Headlines")
    
    # 4. Business and Economy news
    bus = fetch_headlines(category='business', country='us')
    print(f"\nBusiness and economy headlines ({len(bus)}):")
    for a in bus[:5]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']} | {a['publishedAt'][:10]}")
    
    save_to_markdown(bus, "business_headlines", "Business and Economy News")
    
    # 5. UPSC specific topics
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    
    # Define UPSC topics and queries
    upsc_topics = {
        "economy": "economy OR GDP OR fiscal OR monetary OR budget OR finance OR RBI OR inflation OR tax",
        "environment": "climate OR environment OR pollution OR biodiversity OR conservation OR sustainable OR renewable",
        "international": "diplomacy OR bilateral OR G20 OR UN OR treaty OR international relations OR foreign policy",
        "governance": "governance OR policy OR legislation OR reform OR scheme OR initiative OR ministry OR welfare"
    }
    
    # Fetch and save each UPSC topic
    for topic, query in upsc_topics.items():
        articles = fetch_upsc_topic(topic, query, week_ago, today)
        print(f"\n{topic.title()} news for UPSC ({len(articles)}):")
        for a in articles[:3]:
            print(f" - {a['title']}")
            print(f"   Source: {a['source']['name']} | {a['publishedAt'][:10]}")
        
        save_to_markdown(articles, f"upsc_{topic}", f"UPSC: {topic.title()} News and Analysis")
    
    # 6. Usage counter
    used = load_usage()
    print(f"\nAPI requests used today: {used}/{DAILY_LIMIT}")

if __name__ == '__main__':
    main()