#!/usr/bin/env python3
"""
Original UPSC News Daily script (kept for reference).
This script was the original version that uses tokens/calls to the News API.
The newer upsc_news_daily.py is recommended for daily use.
"""
import os
from datetime import datetime, date, timedelta
from news_api_utils import (
    fetch_sources, fetch_headlines, fetch_everything, 
    fetch_india_news_from_rss, fetch_upsc_topic, fetch_topic_from_rss,
    save_to_markdown, check_remaining_requests, load_usage, DAILY_LIMIT
)

# Directory to store output
OUTPUT_DIR = 'news_data'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ─── MAIN WORKFLOW ─────────────────────────────────────────────────────────────
def main():
    print("\n===== UPSC Daily News Fetcher (Original Version) =====")
    print(f"Running on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("NOTE: This is the original token-counting version kept for reference.")
    print("      Consider using upsc_news_daily.py for regular daily updates.")
    
    # Check if we have enough requests for the whole script
    needed_requests = 9  # Projected number of API calls
    if not check_remaining_requests(needed_requests):
        print(f"Not enough API requests remaining (need {needed_requests}).")
        print(f"Running in limited mode with RSS feeds only.")
        run_rss_only()
        return
    
    # 1. Sources - Use cached if available, fetch new if older than 20 days
    sources = fetch_sources(language='en', use_cache=True)
    print(f"Available sources: {len(sources)}")
    for i, s in enumerate(sources[:5], 1):
        print(f" {i}. {s['id']} ({s['category']}): {s['name']}")
    
    if len(sources) > 5:
        print(f"   ... and {len(sources) - 5} more sources")
    
    save_to_markdown(sources, "sources", "News API Sources")
    
    # 2. India-specific news (from RSS feeds)
    india_news = fetch_india_news_from_rss(page_size=15)
    print(f"\nIndian news headlines ({len(india_news)}):")
    for a in india_news[:3]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']} | {a.get('publishedAt', 'Unknown date')[:10]}")
    
    save_to_markdown(india_news, "india_news", "Latest News from India")
    
    # 3. Global headlines
    gen = fetch_headlines(category='general', country='us')
    print(f"\nGlobal headlines ({len(gen)}):")
    for a in gen[:3]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']} | {a['publishedAt'][:10]}")
    
    save_to_markdown(gen, "global_headlines", "Global Headlines")
    
    # 4. Business and Economy news
    bus = fetch_headlines(category='business', country='us')
    print(f"\nBusiness and economy headlines ({len(bus)}):")
    for a in bus[:3]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']} | {a['publishedAt'][:10]}")
    
    save_to_markdown(bus, "business_headlines", "Business and Economy News")
    
    # 5. UPSC specific topics from both NewsAPI and RSS
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    
    # Define UPSC topics and queries
    upsc_topics = {
        "economy": "economy OR GDP OR fiscal OR monetary OR budget OR finance OR RBI OR inflation OR tax",
        "environment": "climate OR environment OR pollution OR biodiversity OR conservation OR sustainable OR renewable",
        "international": "diplomacy OR bilateral OR G20 OR UN OR treaty OR international relations OR foreign policy",
        "governance": "governance OR policy OR legislation OR reform OR scheme OR initiative OR ministry OR welfare"
    }
    
    # Fetch UPSC topics - try NewsAPI first, fall back to RSS if needed
    for topic, query in upsc_topics.items():
        # Try NewsAPI first
        articles = fetch_upsc_topic(topic, query, week_ago, today)
        
        # If no results or very few, supplement with RSS filtered by topic
        if len(articles) < 5:
            print(f"Few results from NewsAPI for {topic}, supplementing with RSS feeds...")
            rss_articles = fetch_topic_from_rss(topic)
            articles.extend(rss_articles)
            
            # Deduplicate by URL (in case there's overlap)
            unique_urls = set()
            unique_articles = []
            for article in articles:
                url = article.get('url')
                if url and url not in unique_urls:
                    unique_urls.add(url)
                    unique_articles.append(article)
            
            articles = unique_articles
        
        print(f"\n{topic.title()} news for UPSC ({len(articles)}):")
        for a in articles[:3]:
            print(f" - {a['title']}")
            source_name = a.get('source', {}).get('name', 'Unknown')
            pub_date = a.get('publishedAt', 'Unknown date')
            print(f"   Source: {source_name} | {pub_date[:10] if isinstance(pub_date, str) else pub_date}")
        
        save_to_markdown(articles, f"upsc_{topic}", f"UPSC: {topic.title()} News and Analysis")
    
    # 6. Usage counter
    used = load_usage()
    print(f"\nAPI requests used today: {used}/{DAILY_LIMIT}")

def run_rss_only():
    """Run a limited version of the script using only RSS feeds."""
    print("Running with RSS feeds only...")
    
    # 1. India-specific news from RSS
    india_news = fetch_india_news_from_rss(page_size=15)
    print(f"\nIndian news headlines ({len(india_news)}):")
    for a in india_news[:3]:
        print(f" - {a['title']}")
        print(f"   Source: {a['source']['name']}")
    
    save_to_markdown(india_news, "india_news", "Latest News from India")
    
    # 2. UPSC topics from RSS
    for topic in ["economy", "environment", "international", "governance", "polity", "science"]:
        articles = fetch_topic_from_rss(topic)
        print(f"\n{topic.title()} news for UPSC ({len(articles)}):")
        for a in articles[:3]:
            print(f" - {a['title']}")
            print(f"   Source: {a['source']['name']}")
        
        save_to_markdown(articles, f"upsc_{topic}", f"UPSC: {topic.title()} News and Analysis")
    
    print("\nCompleted RSS-only run. No NewsAPI requests were used.")

if __name__ == '__main__':
    main() 