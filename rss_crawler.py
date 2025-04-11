#!/usr/bin/env python3
import requests
import feedparser
import time
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("rss_crawler")

# Constants
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
REQUEST_DELAY = 2  # seconds between requests to be respectful

# RSS Sources
RSS_SOURCES = {
    "the_hindu": {
        "name": "The Hindu",
        "main_feed": "https://www.thehindu.com/news/national/feeder/default.rss",
        "topic_feeds": {
            "economy": "https://www.thehindu.com/business/feeder/default.rss",
            "polity": "https://www.thehindu.com/news/national/feeder/default.rss",
            "international": "https://www.thehindu.com/news/international/feeder/default.rss",
            "science": "https://www.thehindu.com/sci-tech/feeder/default.rss",
            "environment": "https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss"
        }
    },
    "pib": {
        "name": "Press Information Bureau",
        "main_feed": "https://pib.gov.in/RssMain.aspx",
        "topic_feeds": {
            "economy": "https://pib.gov.in/RSS/Economy.xml",
            "science": "https://pib.gov.in/RSS/ScienceandTechnology.xml",
            "governance": "https://pib.gov.in/RSS/HomeAffairs.xml"
        }
    }
}

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(url, source_id):
    """Generate a cache file path based on URL."""
    # Create a filename from the URL that's safe for file systems
    safe_url = re.sub(r'[^\w]', '_', url)
    # Truncate to avoid excessively long filenames
    safe_url = safe_url[:100] if len(safe_url) > 100 else safe_url
    return os.path.join(CACHE_DIR, f"{source_id}_{safe_url}.json")

def get_from_cache(url, source_id, max_age_hours=24):
    """Try to get content from cache if it exists and is recent."""
    cache_path = get_cache_path(url, source_id)
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cache_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01T00:00:00'))
                
                # Check if cache is recent enough
                age = (datetime.now() - cache_time).total_seconds() / 3600
                if age <= max_age_hours:
                    logger.info(f"Using cached content for {url} (age: {age:.1f} hours)")
                    return data.get('content')
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Cache error for {url}: {e}")
    
    return None

def save_to_cache(url, source_id, content):
    """Save content to cache."""
    cache_path = get_cache_path(url, source_id)
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            data = {
                'timestamp': datetime.now().isoformat(),
                'content': content
            }
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved content to cache: {cache_path}")
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")

def fetch_rss_feed(feed_url, source_id):
    """Fetch and parse an RSS feed."""
    logger.info(f"Fetching RSS feed: {feed_url}")
    
    try:
        # Parse the RSS feed
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            logger.warning(f"No entries found in feed: {feed_url}")
            return []
            
        logger.info(f"Found {len(feed.entries)} entries in feed")
        return feed.entries
    except Exception as e:
        logger.error(f"Error fetching RSS feed {feed_url}: {e}")
        return []

def extract_content_from_hindu(soup):
    """Extract content from The Hindu article page."""
    content = ""
    
    # Try different content selectors
    content_selectors = [
        '.article-content', 
        '#content-body', 
        '.article-text',
        '.article'
    ]
    
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            # Extract paragraphs
            paragraphs = content_div.select('p')
            if paragraphs:
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs])
                break
    
    # Fallback: if no content found with selectors, try to get all paragraphs
    if not content:
        paragraphs = soup.select('article p') or soup.select('p')
        content = '\n\n'.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
    
    return content

def extract_content_from_pib(soup):
    """Extract content from PIB article page."""
    content = ""
    
    # Try different content selectors
    content_selectors = [
        '.innner-page-main-about-us',
        '.ReleaseCont',
        '#content',
        '.content-area'
    ]
    
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            # Extract paragraphs
            paragraphs = content_div.select('p')
            if paragraphs:
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs])
                break
    
    # Fallback: if no content found with selectors, try to get all paragraphs
    if not content:
        paragraphs = soup.select('p')
        content = '\n\n'.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
    
    return content

def crawl_article(url, source_id):
    """Crawl a single article webpage and extract content."""
    # Check cache first
    cached_content = get_from_cache(url, source_id)
    if cached_content:
        return cached_content
    
    logger.info(f"Crawling article: {url}")
    
    try:
        # Be respectful with request rate
        time.sleep(REQUEST_DELAY)
        
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = ""
        title_tag = soup.select_one('h1') or soup.select_one('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract content based on source
        if "thehindu.com" in url:
            content = extract_content_from_hindu(soup)
        elif "pib.gov.in" in url:
            content = extract_content_from_pib(soup)
        else:
            # Generic extraction
            content_div = soup.select_one('article') or soup.select_one('.content') or soup.select_one('#content')
            if content_div:
                paragraphs = content_div.select('p')
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs])
            else:
                # Fallback to all paragraphs
                paragraphs = soup.select('p')
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
        
        # Extract publication date
        pub_date = ""
        date_selectors = [
            'meta[property="article:published_time"]',
            'time',
            '.time',
            '.date',
            '.publish-date',
            '.article-date'
        ]
        
        for selector in date_selectors:
            date_tag = soup.select_one(selector)
            if date_tag:
                if date_tag.name == 'meta':
                    pub_date = date_tag.get('content', '')
                else:
                    pub_date = date_tag.get_text().strip()
                break
        
        # Extract author
        author = ""
        author_selectors = [
            '.author',
            '.byline',
            'meta[name="author"]'
        ]
        
        for selector in author_selectors:
            author_tag = soup.select_one(selector)
            if author_tag:
                if author_tag.name == 'meta':
                    author = author_tag.get('content', '')
                else:
                    author = author_tag.get_text().strip()
                break
        
        # Create article data
        article_data = {
            'title': title,
            'content': content,
            'published_date': pub_date,
            'author': author,
            'url': url
        }
        
        # Cache the article data
        save_to_cache(url, source_id, article_data)
        
        return article_data
    except Exception as e:
        logger.error(f"Error crawling article {url}: {e}")
        return None

def fetch_source_articles(source_id, topic=None, max_articles=10):
    """Fetch articles from a specific source, optionally filtering by topic."""
    if source_id not in RSS_SOURCES:
        logger.error(f"Unknown source ID: {source_id}")
        return []
    
    source = RSS_SOURCES[source_id]
    
    # Determine which feed URL to use
    if topic and topic in source.get('topic_feeds', {}):
        feed_url = source['topic_feeds'][topic]
    else:
        feed_url = source['main_feed']
    
    # Fetch the RSS feed
    entries = fetch_rss_feed(feed_url, source_id)
    
    # Process entries
    articles = []
    for entry in entries[:max_articles]:
        title = entry.get('title', '')
        link = entry.get('link', '')
        description = entry.get('description', '')
        
        # Skip if no link
        if not link:
            continue
        
        # Crawl the article content
        article_data = crawl_article(link, source_id)
        
        if article_data:
            articles.append({
                'title': article_data.get('title', title),
                'description': description,
                'content': article_data.get('content', ''),
                'url': link,
                'publishedAt': article_data.get('published_date', entry.get('published', '')),
                'author': article_data.get('author', ''),
                'source': {'id': source_id, 'name': source['name']}
            })
        else:
            # Fallback to just the RSS data if crawling failed
            articles.append({
                'title': title,
                'description': description,
                'content': description,
                'url': link,
                'publishedAt': entry.get('published', ''),
                'author': entry.get('author', ''),
                'source': {'id': source_id, 'name': source['name']}
            })
    
    return articles

def fetch_topic_articles(topic, max_articles=10):
    """Fetch articles for a specific UPSC topic from all sources."""
    all_articles = []
    
    # Topic keywords for filtering
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
    
    # Get articles from each source
    for source_id, source_data in RSS_SOURCES.items():
        # Check if source has a specific feed for this topic
        if topic in source_data.get('topic_feeds', {}):
            # Fetch directly from the topic-specific feed
            articles = fetch_source_articles(source_id, topic, max_articles=max_articles//len(RSS_SOURCES))
        else:
            # Fetch from main feed and filter by keywords
            articles = fetch_source_articles(source_id, None, max_articles=max_articles)
            
            # Filter articles by topic keywords
            if topic in topic_keywords:
                filtered_articles = []
                keywords = topic_keywords[topic]
                
                for article in articles:
                    title = article.get('title', '').lower()
                    description = article.get('description', '').lower()
                    content = article.get('content', '').lower()
                    
                    # Check if any keyword is present
                    for keyword in keywords:
                        if keyword.lower() in title or keyword.lower() in description or keyword.lower() in content:
                            filtered_articles.append(article)
                            break
                
                articles = filtered_articles
        
        all_articles.extend(articles)
    
    # Sort by date (newest first)
    all_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    
    # Limit to max_articles
    return all_articles[:max_articles]

def fetch_latest_news(max_articles=15):
    """Fetch the latest news from all sources."""
    all_articles = []
    
    # Get articles from each source
    for source_id in RSS_SOURCES:
        articles = fetch_source_articles(source_id, None, max_articles=max_articles//len(RSS_SOURCES))
        all_articles.extend(articles)
    
    # Sort by date (newest first)
    all_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    
    # Limit to max_articles
    return all_articles[:max_articles]

if __name__ == "__main__":
    # Test the crawler
    print("Testing RSS crawler...")
    
    # Fetch latest news
    latest_news = fetch_latest_news(max_articles=5)
    print(f"\nLatest News ({len(latest_news)} articles):")
    for article in latest_news:
        print(f"  - {article['title']}")
        print(f"    Source: {article['source']['name']} | {article['publishedAt'][:10]}")
    
    # Fetch topic-specific news
    topics = ['economy', 'polity', 'international', 'environment', 'science', 'governance']
    for topic in topics:
        topic_news = fetch_topic_articles(topic, max_articles=3)
        print(f"\n{topic.title()} News ({len(topic_news)} articles):")
        for article in topic_news:
            print(f"  - {article['title']}")
            print(f"    Source: {article['source']['name']} | {article['publishedAt'][:10]}") 