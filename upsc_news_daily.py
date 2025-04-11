#!/usr/bin/env python3
import requests, json, os
import feedparser
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

# RSS Feed URLs
HINDU_RSS = "https://www.thehindu.com/news/national/feeder/default.rss"
TOI_RSS = "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"

# ─── UTILS: request counting ────────────────────────────────────────────────────
def load_usage():
    """Load usage data or initialize empty history."""
    today = date.today().isoformat()
    
    # Initialize empty data structure
    usage_data = {}
    
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                usage_data = json.load(f)
                
                # Handle old format for backward compatibility
                if isinstance(usage_data, dict) and 'date' in usage_data and 'count' in usage_data:
                    old_date = usage_data['date']
                    old_count = usage_data['count']
                    usage_data = {old_date: [{"timestamp": datetime.now().isoformat(), "endpoint": "unknown"} for _ in range(old_count)]}
                # Handle version where we just stored timestamps as strings
                elif isinstance(usage_data, dict):
                    for date_key, entries in list(usage_data.items()):
                        if entries and isinstance(entries[0], str):
                            usage_data[date_key] = [{"timestamp": entry, "endpoint": "unknown"} for entry in entries]
        except json.JSONDecodeError:
            # Handle corrupted log file
            pass
    
    # Get today's count
    today_count = len(usage_data.get(today, []))
    return today_count, usage_data

def save_usage(data):
    """Save usage data with timestamps."""
    with open(LOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def record_request(endpoint='unknown'):
    """Record request with timestamp and endpoint; abort if over limit."""
    now = datetime.now().isoformat()
    today = date.today().isoformat()
    
    # Load existing data
    usage_data = {}
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                usage_data = json.load(f)
        except json.JSONDecodeError:
            pass
    
    # Initialize today's entry if needed
    usage_data.setdefault(today, [])
    
    # Append the timestamp with endpoint info
    usage_data[today].append({
        'timestamp': now,
        'endpoint': endpoint
    })
    
    # Check limit
    today_count = len(usage_data[today])
    if today_count > DAILY_LIMIT:
        raise RuntimeError(f"API limit reached: {today_count}/{DAILY_LIMIT}")
    
    # Save back
    save_usage(usage_data)
    
    print(f"Logging request to {endpoint} at {now} under date {today}")
    return today_count

def check_remaining_requests(needed=1):
    """Check if we have enough requests left and return count."""
    today_count, _ = load_usage()
    remaining = DAILY_LIMIT - today_count
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
        record_request('top-headlines/sources')
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
        record_request('top-headlines')
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
        record_request('everything')
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
    """Fetch news from Indian RSS feeds."""
    print(f"Fetching news from Indian RSS feeds...")
    articles = []
    
    try:
        # The Hindu RSS Feed
        hindu_feed = feedparser.parse(HINDU_RSS)
        for entry in hindu_feed.entries[:page_size // 2]:
            article = {
                'title': entry.title,
                'description': entry.get('summary', ''),
                'url': entry.link,
                'publishedAt': entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'source': {'name': 'The Hindu'},
                'content': entry.get('content', [{'value': ''}])[0].get('value', '') 
                            if 'content' in entry else entry.get('summary', '')
            }
            articles.append(article)
            
        # Times of India RSS Feed
        toi_feed = feedparser.parse(TOI_RSS)
        for entry in toi_feed.entries[:page_size // 2]:
            article = {
                'title': entry.title,
                'description': entry.get('summary', ''),
                'url': entry.link,
                'publishedAt': entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'source': {'name': 'Times of India'},
                'content': entry.get('content', [{'value': ''}])[0].get('value', '') 
                            if 'content' in entry else entry.get('summary', '')
            }
            articles.append(article)
        
        return articles
    except Exception as e:
        print(f"Error fetching Indian news from RSS: {e}")
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
    needed_requests = 7  # Base + 4 UPSC topics
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
    
    # 2. India-specific news (from RSS feeds)
    india_news = fetch_india_news(page_size=15)
    print(f"\nIndian news headlines ({len(india_news)}):")
    for a in india_news[:5]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']} | {a.get('publishedAt', '')[:10]}")
    
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
    
    print("\n" + "="*50)
    print("FETCHING UPSC TOPICS DATA")
    print("="*50)
    
    # Fetch and save each UPSC topic (with updated filenames without the 'upsc_' prefix)
    for topic, query in upsc_topics.items():
        print(f"\nProcessing topic: {topic}")
        articles = fetch_upsc_topic(topic, query, week_ago, today)
        print(f"{topic.title()} news for UPSC ({len(articles)}):")
        for a in articles[:3]:
            print(f" - {a['title']}")
            print(f"   Source: {a['source']['name']} | {a['publishedAt'][:10]}")
        
        # Ensure we're saving to a filename matching the topic key
        output_filename = f"{topic}"
        print(f"Saving to {output_filename}.md")
        save_to_markdown(articles, output_filename, f"{topic.title()} News and Analysis")
    
    print("="*50)
    print("FINISHED FETCHING UPSC TOPICS")
    print("="*50)
    
    # 6. Usage counter
    used, usage_history = load_usage()
    print(f"\nAPI requests used today: {used}/{DAILY_LIMIT}")
    
    # Print usage history summary
    print("\nAPI Usage History:")
    for date_str, timestamps in sorted(usage_history.items()):
        print(f" - {date_str}: {len(timestamps)} requests")
    
    # Group and count by endpoint for today's requests
    if today in usage_history and usage_history[today]:
        endpoint_counts = {}
        for entry in usage_history[today]:
            if isinstance(entry, dict):
                endpoint = entry.get('endpoint', 'unknown')
                endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        
        print("\nToday's Requests by Endpoint:")
        for endpoint, count in sorted(endpoint_counts.items()):
            print(f" - {endpoint}: {count} requests")

if __name__ == '__main__':
    main()